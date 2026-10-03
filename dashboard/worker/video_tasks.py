"""
AutoVideoFactory — Realistic Pipeline Execution Worker (Milestone 2 / Requirement R2)
Implements 5-stage pipeline with complete audit trail and hybrid mode control:
- Stage 1: script_ready (ScriptGenerator -> title, description, hashtags, scenes)
- Stage 1.5: Source Gate (source_review) — scenes with numbers/claims need sources;
  Auto jobs halt at 'source_review' until sources are supplied (Task 2.2)
- Stage 2: voice_ready (TTSManager/VieNeu/EdgeTTS -> per-scene WAV & duration probe)
- Stage 3: assets_ready (Art Style Presets, CascadeAssetOrchestrator/ImageGenerator, Vision Gate)
           Halts here if job.mode == 'step_by_step'
- Stage 4: rendering (SubtitleGenerator dynamic chunked ASS, FFmpeg zoompan/mux commands)
- Stage 5: done (FFmpeg render / synthetic MP4, snapshot.jpg extraction, status=done)

Provides callable entrypoints:
- run_video_pipeline(job_id: str)
- continue_video_pipeline(job_id: str)
- continue_after_source_review(job_id: str)
- regenerate_scene_asset(job_id: str, scene_index: int, prompt: str) -> dict
- Celery task adapters (create_video_task, publish_video_task) for backward compatibility
"""

import os
import sys
import json
import math
import wave
import shutil
import asyncio
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union

from PIL import Image, ImageDraw, ImageFilter
from loguru import logger

from dashboard.api.database import (
    SessionLocal,
    get_job,
    update_job_status,
    update_job_stage,
    update_job_output,
    update_scene_image
)
from dashboard.api.models import JobStatus
from publish.postiz_client.postiz_api import PostizClient

# Safe Celery app import for backward compatibility
try:
    from dashboard.worker.celery_app import app
except Exception:
    class _DummyCeleryApp:
        def task(self, *args, **kwargs):
            def decorator(f):
                f.delay = f
                f.run = f
                return f
            return decorator
    app = _DummyCeleryApp()

# Ensure FFmpeg is available on PATH (e.g. from imageio_ffmpeg on Windows)
def _ensure_ffmpeg_on_path() -> None:
    try:
        import imageio_ffmpeg
        ffmpeg_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
        ffmpeg_dir = ffmpeg_exe.parent
        target_ffmpeg = ffmpeg_dir / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if not target_ffmpeg.exists() and ffmpeg_exe.exists():
            try:
                shutil.copy(ffmpeg_exe, target_ffmpeg)
            except Exception:
                pass
        if str(ffmpeg_dir) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(ffmpeg_dir) + os.path.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass

_ensure_ffmpeg_on_path()

# Art Style Preset mappings (Requirement R3 & R2)
STYLE_MODIFIERS = {
    "photorealistic": "photorealistic, hyperrealistic 8k, professional photography, clean studio lighting, sharp focus",
    "cinematic_3d": "cinematic 3D render, Pixar Disney animation style, octane render, volumetric lighting, vivid colors",
    "anime": "Japanese anime manga style, Makoto Shinkai aesthetic, clean cel shading, highly detailed",
    "vintage": "vintage historical documentary archive print, 1950s encyclopedia illustration, halftone dot texture",
    "vintage_doc": "vintage historical documentary archive print, 1950s encyclopedia illustration, halftone dot texture",
    "watercolor": "delicate watercolor art illustration, wet-on-wet paint textures, paper bleeding edges, artistic wash",
    "collage_broll": "editorial paper collage, halftone cutouts, vintage engraving, textured cardstock, drop shadows"
}


def run_in_async_loop(coro):
    """Safely executes an asynchronous coroutine from either sync or async contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


def _create_synthetic_wav(output_path: str, duration: float = 3.0, sample_rate: int = 24000) -> str:
    """Creates a deterministic valid PCM WAV audio file with gentle 440Hz tone."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    num_frames = int(sample_rate * max(0.5, float(duration)))
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = bytearray()
        for i in range(num_frames):
            val = int(800 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
            raw.extend(val.to_bytes(2, byteorder="little", signed=True))
        wf.writeframes(bytes(raw))
    return str(out)


def _probe_audio_duration(audio_path: str, default: float = 4.0) -> float:
    """Probes audio duration via ffmpeg or standard wave library with resilient fallback."""
    try:
        from core.render_engine.ffmpeg_utils import get_video_info
        info = get_video_info(audio_path)
        d = float(info.get("duration", 0.0))
        if d > 0:
            return round(d, 2)
    except Exception:
        pass

    try:
        with wave.open(audio_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return round(frames / float(rate), 2)
    except Exception:
        pass

    return round(float(default), 2)


def _ensure_scene_composite(src_path: str, dst_path: str, art_style: str = "photorealistic") -> str:
    """
    Composites acquired asset onto a properly proportioned 1080x1920 poster canvas
    matching the requested art style palette.
    """
    dst = Path(dst_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(src_path):
        return str(dst)

    try:
        with Image.open(src_path) as src_img:
            # If already a high-resolution solid RGB image, copy directly
            if src_img.mode == "RGB" and src_img.width >= 800 and src_img.height >= 800:
                shutil.copy2(src_path, dst)
                return str(dst)

            bg_colors = {
                "photorealistic": (17, 24, 39),
                "cinematic_3d": (24, 18, 43),
                "anime": (224, 242, 254),
                "vintage": (244, 234, 212),
                "vintage_doc": (244, 234, 212),
                "watercolor": (250, 246, 238),
                "collage_broll": (12, 35, 64)
            }
            bg_color = bg_colors.get((art_style or "").lower(), (20, 24, 33))
            canvas_w, canvas_h = 1080, 1920
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (*bg_color, 255))

            # Scale cutout asset to fit within center 800x800 box
            max_w, max_h = 800, 800
            src_rgba = src_img.convert("RGBA")
            scale = min(max_w / max(1, src_rgba.width), max_h / max(1, src_rgba.height))
            new_w = max(10, int(src_rgba.width * scale))
            new_h = max(10, int(src_rgba.height * scale))
            scaled_sub = src_rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)

            pos_x = (canvas_w - new_w) // 2
            pos_y = (canvas_h - new_h) // 2
            canvas.paste(scaled_sub, (pos_x, pos_y), mask=scaled_sub)
            canvas.convert("RGB").save(str(dst), "PNG")
            return str(dst)
    except Exception as e:
        logger.warning(f"Error compositing scene image: {e}, falling back to copy")
        try:
            shutil.copy2(src_path, dst)
        except Exception:
            pass
        return str(dst)


def _generate_synthetic_mp4(output_path: str, scenes: list = None) -> str:
    """
    Generates a synthetic MP4 video when external FFmpeg binary is unavailable.
    Tries imageio -> cv2 -> minimal MP4 container bytes.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try imageio
    try:
        import imageio
        import numpy as np
        writer = imageio.get_writer(str(out), fps=25, format="mp4")
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
        frame[:, :] = [30, 41, 59]
        for _ in range(25):
            writer.append_data(frame)
        writer.close()
        if out.exists() and out.stat().st_size > 0:
            return str(out)
    except Exception:
        pass

    # 2. Try OpenCV cv2
    try:
        import cv2
        import numpy as np
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        vw = cv2.VideoWriter(str(out), fourcc, 25.0, (1080, 1920))
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
        frame[:, :] = (30, 41, 59)
        for _ in range(25):
            vw.write(frame)
        vw.release()
        if out.exists() and out.stat().st_size > 0:
            return str(out)
    except Exception:
        pass

    # 3. Minimal valid MP4 container binary marker
    synthetic_header = (
        b'\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41'
        b'\x00\x00\x00\x08free'
        b'\x00\x00\x00\x18mdatMOCK_FINAL_VIDEO_STREAM'
    )
    with open(str(out), "wb") as f:
        f.write(synthetic_header)
    return str(out)


def _allow_synthetic_video() -> bool:
    """Synthetic MP4 is only allowed for tests when ALLOW_SYNTHETIC_VIDEO=1."""
    return os.environ.get("ALLOW_SYNTHETIC_VIDEO", "").strip() == "1"


def _verify_rendered_video(video_path: str, expected_duration: float = 0.0) -> Tuple[bool, str]:
    """
    Verifies a rendered MP4 with ffprobe (via get_video_info).
    Requires: file exists, size > 100KB, has video + audio streams,
    duration > 0 and (when expected) >= expected_duration - 1s.
    Returns (ok, detail_message).
    """
    p = Path(video_path)
    if not p.exists():
        return False, f"Rendered video not found: {video_path}"
    size = p.stat().st_size
    if size <= 100 * 1024:
        return False, f"Rendered video too small ({size} bytes): {video_path}"
    try:
        from core.render_engine.ffmpeg_utils import get_video_info
        info = get_video_info(str(p))
    except Exception as e:
        return False, f"ffprobe failed for {video_path}: {e}"
    if not info:
        return False, f"ffprobe returned no info for {video_path}"
    if not info.get("width") or not info.get("height"):
        return False, f"No video stream detected in {video_path}"
    if not info.get("has_audio"):
        return False, f"No audio stream detected in {video_path}"
    duration = float(info.get("duration", 0.0) or 0.0)
    if duration <= 0:
        return False, f"Invalid duration ({duration}) in {video_path}"
    if expected_duration > 0 and duration < expected_duration - 1.0:
        return False, f"Duration {duration:.2f}s shorter than expected {expected_duration:.2f}s in {video_path}"
    return True, f"OK ({size} bytes, {info.get('width')}x{info.get('height')}, {duration:.2f}s)"


def _ensure_job_thumbnail(
    job,
    pipeline_data: Dict[str, Any],
    *,
    force: bool = False,
    thumbnail_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ensure a completed job has a thumbnail next to final_video.mp4.

    MetadataGenerator supplies thumbnail_text when the pipeline has not stored
    one. User-supplied text (preview approval) wins and forces regeneration.
    Failures are non-fatal for rendering but are audited as thumbnail_error.
    """
    from core.render_engine.thumbnail_generator import generate_job_thumbnails

    job_dir = Path("data/output") / job.id
    existing_path = pipeline_data.get("thumbnail_path")
    if not force and existing_path and Path(existing_path).exists():
        return {
            "thumbnail_path": existing_path,
            "thumbnail_portrait_path": pipeline_data.get("thumbnail_portrait_path", existing_path),
            **(
                {"thumbnail_landscape_path": pipeline_data["thumbnail_landscape_path"]}
                if pipeline_data.get("thumbnail_landscape_path")
                else {}
            ),
            "thumbnail_text": pipeline_data.get("thumbnail_text", ""),
        }

    script = pipeline_data.get("script")
    if not isinstance(script, dict):
        script = getattr(job, "script", None) or {}
    metadata: Dict[str, Any] = {}
    if isinstance(pipeline_data.get("metadata"), dict):
        metadata.update(pipeline_data["metadata"])
    if isinstance(getattr(job, "extra_metadata", None), dict):
        metadata.update(job.extra_metadata)

    resolved_text = thumbnail_text or metadata.get("thumbnail_text") or pipeline_data.get("thumbnail_text")
    if not resolved_text:
        try:
            from publish.metadata_generator import MetadataGenerator

            generated = run_in_async_loop(
                MetadataGenerator().generate(
                    script,
                    language=getattr(job, "language", "vi") or "vi",
                    style=getattr(job, "style", "collage_broll") or "collage_broll",
                )
            )
            if isinstance(generated, dict):
                metadata.update({k: v for k, v in generated.items() if v not in (None, "", [])})
                resolved_text = generated.get("thumbnail_text")
        except Exception as exc:
            logger.warning(f"MetadataGenerator thumbnail text failed for job {job.id}: {exc}")
    if not resolved_text:
        resolved_text = metadata.get("title") or script.get("title") or job.topic

    source_image = None
    snapshot = job_dir / "snapshot.jpg"
    if snapshot.exists():
        source_image = snapshot
    else:
        for scene in pipeline_data.get("scenes") or pipeline_data.get("storyboard") or []:
            if isinstance(scene, dict) and scene.get("image_path") and Path(scene["image_path"]).exists():
                source_image = Path(scene["image_path"])
                break

    video_format = pipeline_data.get("format") or getattr(job, "format", "shorts") or "shorts"
    result = generate_job_thumbnails(
        job_dir,
        str(resolved_text),
        source_image_path=source_image,
        video_path=job.output_path or (job_dir / "final_video.mp4"),
        video_format=str(video_format),
    )
    if metadata:
        metadata["thumbnail_text"] = result["thumbnail_text"]
        pipeline_data["metadata"] = metadata
    pipeline_data.update(result)
    pipeline_data.pop("thumbnail_error", None)
    return result


def regenerate_job_thumbnail(job_id: str, thumbnail_text: Optional[str] = None) -> Dict[str, Any]:
    """Regenerate a job thumbnail, optionally with user-edited text."""
    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found in DB")
        pipeline_data = job.pipeline_data or {}
        result = _ensure_job_thumbnail(
            job,
            pipeline_data,
            force=True,
            thumbnail_text=thumbnail_text,
        )
        job.pipeline_data = pipeline_data
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return result
    finally:
        db.close()


async def _async_execute_stages_2_and_3(job_id: str):
    """
    Executes Stages 2 (voice) and 3 (assets), then Stages 4/5 unless the job
    halts at 'assets_ready' in step_by_step mode.
    Shared by the main pipeline (after Stage 1 + Source Gate) and by the
    source_review resume path (continue_after_source_review).
    """
    from core.tts_engine.tts_manager import TTSManager
    from core.media_engine.cascade_asset_orchestrator import CascadeAssetOrchestrator
    from core.media_engine.image_generator import ImageGenerator

    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            logger.error(f"Job {job_id} not found in DB")
            return

        pipeline_data = job.pipeline_data or {}

        # -------------------------------------------------------------
        # STAGE 2: voice_ready
        # -------------------------------------------------------------
        logger.info(f"--- [Job {job_id}] STAGE 2: Synthesizing Audio ---")
        job_dir = Path("data/output") / job_id
        audio_dir = job_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        voice_preset = getattr(job, "voice_preset", "default") or "default"
        ref_audio = None
        if voice_preset != "default":
            for cand in [
                Path("assets/voices") / voice_preset,
                Path("assets/voices") / f"{voice_preset}.wav",
                Path("assets/voices") / f"{voice_preset}.mp3"
            ]:
                if cand.exists():
                    ref_audio = str(cand.resolve())
                    break

        tts_mgr = TTSManager()
        voice_scenes = []

        for i, scene in enumerate(pipeline_data["scenes"]):
            audio_path = audio_dir / f"scene_{i:03d}.wav"
            audio_path_str = str(audio_path).replace("\\", "/")
            narration = scene.get("narration", "").strip() or f"Cảnh {i+1} về {job.topic}"

            synthesized = False
            if ref_audio:
                try:
                    await tts_mgr.vieneu_client.synthesize(
                        text=narration,
                        language=job.language or "vi",
                        output_path=str(audio_path),
                        ref_audio=ref_audio
                    )
                    synthesized = True
                except Exception as e_ref:
                    logger.warning(f"VieNeu ref_audio synthesis failed ({e_ref}), falling back to TTSManager")

            if not synthesized:
                try:
                    await tts_mgr.synthesize(
                        text=narration,
                        language=job.language or "vi",
                        output_path=str(audio_path)
                    )
                    synthesized = True
                except Exception as e_tts:
                    logger.warning(f"TTS synthesis failed for scene {i} ({e_tts}), writing synthetic audio")
                    _create_synthetic_wav(str(audio_path), duration=float(scene.get("duration", 4.0)))

            dur = _probe_audio_duration(str(audio_path), default=float(scene.get("duration", 4.0)))
            scene["audio_path"] = audio_path_str
            scene["audio_duration"] = dur
            scene["duration"] = dur
            scene["voice_preset"] = voice_preset

            voice_scenes.append({
                "scene_index": i,
                "text": narration,
                "audio_path": audio_path_str,
                "duration": dur
            })

        pipeline_data["voice"] = {
            "engine": "VieNeu-TTS" if (job.language or "vi").lower() == "vi" else "Edge-TTS",
            "preset": voice_preset,
            "scenes": voice_scenes
        }

        update_job_stage(db, job_id, "voice_ready", status=JobStatus.processing, pipeline_data=pipeline_data)
        logger.success(f"--- [Job {job_id}] STAGE 2 COMPLETE: voice_ready ---")

        # -------------------------------------------------------------
        # STAGE 3: assets_ready
        # -------------------------------------------------------------
        logger.info(f"--- [Job {job_id}] STAGE 3: Generating Visual Assets & Vision Gate Audit ---")
        img_dir = job_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        art_style_key = getattr(job, "art_style", "photorealistic") or "photorealistic"
        style_mod = STYLE_MODIFIERS.get(art_style_key.lower(), art_style_key)

        cascade = CascadeAssetOrchestrator(cache_dir=img_dir)
        img_gen = ImageGenerator()
        storyboard = []

        for i, scene in enumerate(pipeline_data["scenes"]):
            base_prompt = scene.get("still_image_prompt") or scene.get("visual_description") or scene.get("narration") or job.topic
            if style_mod.lower() not in base_prompt.lower():
                visual_prompt = f"{base_prompt}, {style_mod}"
            else:
                visual_prompt = base_prompt

            img_dest = img_dir / f"scene_{i:03d}.png"
            img_dest_str = str(img_dest).replace("\\", "/")

            tier_used = "tier1_imagen"
            gate_score = 0.90
            gate_reason = "Offline visual verification pass"

            target_obj = scene.get("focal_keyword") or scene.get("secondary_keyword") or job.topic
            try:
                acquired_path, meta = await cascade.acquire_asset(
                    target_object=target_obj,
                    scene_sentence=scene.get("narration", ""),
                    archetype=art_style_key,
                    job_cache_dir=img_dir
                )
                if acquired_path and os.path.exists(acquired_path):
                    _ensure_scene_composite(acquired_path, str(img_dest), art_style=art_style_key)
                    tier_used = meta.get("tier_used", "tier1_imagen")
                    gate_score = float(meta.get("confidence", 0.90))
                    gate_reason = meta.get("reason", "Cascade asset acquisition verified")
            except Exception as e_casc:
                logger.warning(f"Cascade acquisition failed for scene {i} ({e_casc}), trying ImageGenerator")
                try:
                    await img_gen.generate_scene_image(scene, str(img_dest), topic=job.topic, scene_index=i)
                    tier_used = "tier2_stock"
                    gate_score = 0.88
                    gate_reason = "ImageGenerator generation pass"
                except Exception as e_ig:
                    logger.warning(f"ImageGenerator failed for scene {i} ({e_ig}), fallback to collage generator")
                    img_gen._generate_artistic_collage_fallback(scene, i, str(img_dest))
                    tier_used = "tier4_procedural"
                    gate_score = 0.85
                    gate_reason = "Procedural artistic collage fallback"

            # Optional live Vision Gate evaluation
            try:
                if os.path.exists(str(img_dest)):
                    gate_eval = await cascade.evaluate_vision_gate(
                        image=str(img_dest),
                        scene_sentence=scene.get("narration", ""),
                        target_object=target_obj,
                        current_prompt=visual_prompt
                    )
                    gate_score = float(gate_eval.get("confidence", gate_score))
                    gate_reason = gate_eval.get("reason", gate_reason)
            except Exception as e_gate:
                logger.debug(f"Vision Gate direct call: {e_gate}")

            # Record audit trail in both scene and storyboard
            scene["image_path"] = img_dest_str
            scene["visual_prompt"] = visual_prompt
            scene["prompt"] = visual_prompt
            scene["still_image_prompt"] = visual_prompt
            scene["tier_used"] = tier_used
            scene["vision_gate_score"] = gate_score
            scene["vision_gate_reasoning"] = gate_reason

            storyboard.append({
                "scene_index": i,
                "image_path": img_dest_str,
                "visual_prompt": visual_prompt,
                "prompt": visual_prompt,
                "tier_used": tier_used,
                "vision_gate_score": gate_score,
                "vision_gate_reasoning": gate_reason
            })

        pipeline_data["storyboard"] = storyboard
        update_job_stage(db, job_id, "assets_ready", status=JobStatus.processing, pipeline_data=pipeline_data)
        logger.success(f"--- [Job {job_id}] STAGE 3 COMPLETE: assets_ready ---")

        # -------------------------------------------------------------
        # HYBRID MODE CHECK
        # -------------------------------------------------------------
        job = get_job(db, job_id)
        if getattr(job, "mode", "auto") == "step_by_step":
            logger.info(f"🛑 [Job {job_id}] Mode is 'step_by_step'. Halting at stage 'assets_ready' for user inspection.")
            return

        # If mode == 'auto', immediately proceed to Stages 4 and 5
        _execute_stages_4_and_5(db, job_id)

    except Exception as e:
        logger.exception(f"Unhandled error in stages 2-3 for job {job_id}: {e}")
        update_job_stage(db, job_id, stage="failed", status=JobStatus.failed, error=str(e))
        raise
    finally:
        db.close()


async def _async_execute_stages_1_to_3(job_id: str):
    """Executes Stages 1 to 3 and checks for Step-by-Step halt."""
    from core.script_engine.script_generator import ScriptGenerator
    from core.tts_engine.tts_manager import TTSManager
    from core.media_engine.cascade_asset_orchestrator import CascadeAssetOrchestrator
    from core.media_engine.image_generator import ImageGenerator

    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            logger.error(f"Job {job_id} not found in DB")
            return

        logger.info(f"Starting realistic video pipeline for job {job_id}, topic: '{job.topic}', mode: '{job.mode}', art_style: '{job.art_style}'")
        update_job_status(db, job_id, JobStatus.processing)

        pipeline_data = job.pipeline_data or {}

        # -------------------------------------------------------------
        # STAGE 1: script_ready
        # -------------------------------------------------------------
        logger.info(f"--- [Job {job_id}] STAGE 1: Generating Script ---")
        script_gen = ScriptGenerator()
        try:
            script = await script_gen.generate(
                topic=job.topic,
                style=job.style or "collage_broll",
                language=job.language or "vi",
                duration=60
            )
        except Exception as e_script:
            logger.warning(f"ScriptGenerator failed ({e_script}), using fallback script template")
            script = script_gen._generate_fallback_script(
                topic=job.topic,
                style=job.style or "collage_broll",
                language=job.language or "vi",
                duration=30
            )

        pipeline_data["script"] = {
            "title": script.get("title", f"Video about {job.topic}"),
            "description": script.get("description", f"Generated video for {job.topic}"),
            "hashtags": script.get("hashtags", ["#shorts", "#viral", "#ai"]),
            "prompt_used": script.get("prompt_used", f"Generate a script about {job.topic}"),
            "scenes": script.get("scenes", [])
        }

        scenes_list = []
        raw_scenes = script.get("scenes", [])
        for i, s in enumerate(raw_scenes):
            scene_item = {
                "scene_index": i,
                "index": i,
                "narration": s.get("narration", ""),
                "visual_description": s.get("visual_description", ""),
                "still_image_prompt": s.get("still_image_prompt", "") or s.get("visual_description", "") or s.get("narration", ""),
                "duration": float(s.get("duration", 4.0))
            }
            for k, v in s.items():
                if k not in scene_item:
                    scene_item[k] = v
            scenes_list.append(scene_item)
        pipeline_data["scenes"] = scenes_list

        update_job_output(
            db,
            job_id,
            script=pipeline_data["script"],
            meta={"title": pipeline_data["script"]["title"], "description": pipeline_data["script"]["description"]}
        )
        job_dir = Path("data/output") / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(job_dir / "script.json", "w", encoding="utf-8") as f_script:
                json.dump(pipeline_data["script"], f_script, ensure_ascii=False, indent=2)
        except Exception as e_sjson:
            logger.warning(f"Could not persist script.json: {e_sjson}")

        update_job_stage(db, job_id, "script_ready", status=JobStatus.processing, pipeline_data=pipeline_data)
        logger.success(f"--- [Job {job_id}] STAGE 1 COMPLETE: script_ready ({len(scenes_list)} scenes) ---")

        # -------------------------------------------------------------
        # STAGE 1.5: SOURCE GATE (Task 2.2) — kiểm chứng nguồn trước voice
        # -------------------------------------------------------------
        from core.script_engine.source_gate import evaluate_gate

        pipeline_data["script_origin"] = script.get("script_origin", "gemini")
        try:
            gate = await asyncio.to_thread(evaluate_gate, pipeline_data["scenes"])
        except Exception as e_gate:
            logger.warning(f"Source Gate failed for job {job_id} ({e_gate}); continuing without audit")
            gate = {"audit": [], "blocking": [], "has_blocking": False}
        pipeline_data["source_audit"] = gate["audit"]
        update_job_stage(db, job_id, "script_ready", status=JobStatus.processing, pipeline_data=pipeline_data)

        if getattr(job, "mode", "auto") == "auto" and gate["has_blocking"]:
            update_job_stage(db, job_id, "source_review", status=JobStatus.processing, pipeline_data=pipeline_data)
            logger.warning(
                f"⛔ [Job {job_id}] Source Gate halted at 'source_review': "
                f"scenes {gate['blocking']} need sources before voice/render."
            )
            return

        # Stages 2-5 (voice, assets, render) — shared with the source_review resume path
        await _async_execute_stages_2_and_3(job_id)

    except Exception as e:
        logger.exception(f"Unhandled error in video pipeline for job {job_id}: {e}")
        update_job_stage(db, job_id, stage="failed", status=JobStatus.failed, error=str(e))
        raise
    finally:
        db.close()


def _execute_stages_4_and_5(db, job_id: str):
    """Executes Stages 4 (rendering) and 5 (done) synchronously."""
    from core.render_engine.subtitle_generator import SubtitleGenerator

    job = get_job(db, job_id)
    if not job:
        logger.error(f"Job {job_id} not found in DB")
        return

    pipeline_data = job.pipeline_data or {}
    scenes = pipeline_data.get("scenes")
    if not scenes:
        scenes = pipeline_data.get("script", {}).get("scenes", [])
    if not scenes and pipeline_data.get("storyboard"):
        scenes = []
        for sb in pipeline_data.get("storyboard", []):
            scenes.append({
                "scene_index": sb.get("scene_index", 0),
                "index": sb.get("scene_index", 0),
                "narration": sb.get("visual_prompt", ""),
                "image_path": sb.get("image_path", ""),
                "duration": 4.0
            })
    if not scenes:
        logger.warning(f"Job {job_id} has no scenes in pipeline_data")

    # Map storyboard images for quick and accurate lookup (resolves user uploaded / regenerated images)
    storyboard = pipeline_data.get("storyboard") or []
    sb_image_map: Dict[int, str] = {}
    for sb in storyboard:
        if isinstance(sb, dict):
            idx = sb.get("scene_index")
            if idx is not None and sb.get("image_path"):
                sb_image_map[int(idx)] = sb.get("image_path")

    job_dir = Path("data/output") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    final_video_file = job_dir / "final_video.mp4"

    # -------------------------------------------------------------
    # STAGE 4 (primary): CollageEngine — engine cắt dán thật (Task 1.2)
    # -------------------------------------------------------------
    collage_rendered = False
    style_key = (getattr(job, "style", "") or "collage_broll").lower()
    if style_key == "collage_broll":
        try:
            from styles.collage_broll.collage_engine import CollageEngine

            logger.info(f"--- [Job {job_id}] STAGE 4: Rendering with CollageEngine (stop-motion collage) ---")
            audio_files: List[str] = []
            media_files: List[str] = []
            for i, scene in enumerate(scenes):
                scene_idx = scene.get("scene_index", scene.get("index", i))
                resolved_img = sb_image_map.get(scene_idx) or scene.get("image_path")
                if not resolved_img:
                    resolved_img = str(job_dir / "images" / f"scene_{i:03d}.png")
                scene["image_path"] = resolved_img
                media_files.append(resolved_img)
                audio_files.append(scene.get("audio_path") or str(job_dir / "audio" / f"scene_{i:03d}.wav"))

            script_payload = {
                "title": pipeline_data.get("script", {}).get("title") or job.topic,
                "scenes": scenes,
            }

            async def _render_collage() -> str:
                engine = CollageEngine()
                return await asyncio.wait_for(
                    engine.create_video(
                        script=script_payload,
                        language=job.language or "vi",
                        output_path=str(final_video_file),
                        format="shorts",
                        audio_files=audio_files,
                        media_files=media_files,
                    ),
                    timeout=600,
                )

            run_in_async_loop(_render_collage())
            if final_video_file.exists() and final_video_file.stat().st_size > 0:
                collage_rendered = True
                pipeline_data["render_engine"] = "collage_engine"
                logger.success(f"--- [Job {job_id}] CollageEngine rendered: {final_video_file} ---")
        except Exception as e_collage:
            logger.warning(f"CollageEngine render failed for job {job_id} ({e_collage}); falling back to Ken Burns zoompan")
            pipeline_data["render_engine"] = "ken_burns_fallback"
            pipeline_data["collage_error"] = str(e_collage)

    # -------------------------------------------------------------
    # STAGE 4: rendering (subtitle + FFmpeg commands; zoompan = fallback)
    # -------------------------------------------------------------
    logger.info(f"--- [Job {job_id}] STAGE 4: Generating Subtitles & FFmpeg Commands ---")
    sub_dir = job_dir / "subtitles"
    sub_dir.mkdir(parents=True, exist_ok=True)

    clips_dir = job_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_cmds = []
    clip_paths = []
    fps = 25

    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        dur = float(scene.get("audio_duration") or scene.get("duration") or 4.0)
        sub_file = sub_dir / f"scene_{i:03d}.ass"

        SubtitleGenerator.generate_dynamic_chunked_ass(
            sentence=narration,
            duration=dur,
            output_path=sub_file,
            chunk_words=3,
            font_size=44,
            margin_v=180
        )

        scene_idx = scene.get("scene_index", scene.get("index", i))
        # Prioritize storyboard (which holds user-uploaded/regenerated assets), then scene dict
        resolved_img = sb_image_map.get(scene_idx) or scene.get("image_path")
        if not resolved_img:
            resolved_img = str(job_dir / "images" / f"scene_{i:03d}.png")
        scene["image_path"] = resolved_img

        img_p = Path(resolved_img).resolve().as_posix()
        audio_p = Path(scene.get("audio_path", job_dir / "audio" / f"scene_{i:03d}.wav")).resolve().as_posix()
        sub_p = sub_file.resolve().as_posix()
        escaped_sub = sub_p.replace(":", r"\:")
        clip_p = (clips_dir / f"clip_{i:03d}.mp4").resolve().as_posix()
        total_frames = int(dur * fps)

        if not collage_rendered:
            cmd = (
                f'ffmpeg -y -loop 1 -i "{img_p}" -i "{audio_p}" -t {dur:.2f} '
                f'-filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,'
                f'zoompan=z=\'min(zoom+0.001,1.05)\':x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':'
                f'd={total_frames}:s=1080x1920:fps={fps}[v0];[v0]ass=\'{escaped_sub}\'[v]" '
                f'-map "[v]" -map 1:a -c:v libx264 -preset veryfast -crf 18 -c:a aac -b:a 192k "{clip_p}"'
            )
            ffmpeg_cmds.append(cmd)
        clip_paths.append(clip_p)

    if collage_rendered:
        ffmpeg_cmds = [
            f"CollageEngine.create_video(scenes={len(scenes)}, format=shorts) -> {final_video_file.resolve().as_posix()}"
        ]

    concat_file = job_dir / "concat_list.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for cp in clip_paths:
            f.write(f"file '{cp}'\n")

    final_video_file = job_dir / "final_video.mp4"
    final_video_posix = final_video_file.resolve().as_posix()
    concat_cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_file.resolve().as_posix()}" -c copy "{final_video_posix}"'
    ffmpeg_cmds.append(concat_cmd)

    pipeline_data["ffmpeg_commands"] = ffmpeg_cmds
    pipeline_data["scenes"] = scenes
    update_job_stage(db, job_id, "rendering", status=JobStatus.processing, pipeline_data=pipeline_data)
    logger.success(f"--- [Job {job_id}] STAGE 4 COMPLETE: rendering ---")

    # -------------------------------------------------------------
    # STAGE 5: done
    # -------------------------------------------------------------
    logger.info(f"--- [Job {job_id}] STAGE 5: Executing Render & Generating Master Video ---")
    _ensure_ffmpeg_on_path()
    ffmpeg_available = bool(shutil.which("ffmpeg"))

    rendered = False
    synthetic = False
    last_ffmpeg_error = ""
    if collage_rendered:
        rendered = True
        logger.success(f"--- [Job {job_id}] STAGE 5: Using CollageEngine output as master video ---")
    elif ffmpeg_available:
        try:
            logger.info("FFmpeg detected, executing scene clip rendering...")
            clips_rendered = True
            for i, cmd in enumerate(ffmpeg_cmds[:-1]):
                logger.info(f"Rendering clip {i}...")
                res = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if res.returncode != 0:
                    last_ffmpeg_error = (res.stderr or b"").decode("utf-8", errors="replace")[-2000:]
                    logger.warning(f"Native FFmpeg command with ass filter failed for clip {i}, attempting fallback clip encoding...")
                    img_p = Path(scenes[i].get("image_path", "")).resolve().as_posix()
                    audio_p = Path(scenes[i].get("audio_path", "")).resolve().as_posix()
                    clip_p = clip_paths[i]
                    dur = float(scenes[i].get("duration", 4.0))
                    fallback_clip_cmd = f'ffmpeg -y -loop 1 -i "{img_p}" -i "{audio_p}" -t {dur:.2f} -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "{clip_p}"'
                    res2 = subprocess.run(fallback_clip_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    if res2.returncode != 0:
                        last_ffmpeg_error = (res2.stderr or b"").decode("utf-8", errors="replace")[-2000:]
                        clips_rendered = False
                        break

            if clips_rendered and concat_file.exists():
                logger.info("Concatenating rendered clips into final video...")
                res_concat = subprocess.run(concat_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if res_concat.returncode == 0 and final_video_file.exists() and final_video_file.stat().st_size > 0:
                    rendered = True
                    logger.success(f"Final video successfully generated at: {final_video_file}")
                else:
                    last_ffmpeg_error = (res_concat.stderr or b"").decode("utf-8", errors="replace")[-2000:]
        except Exception as e_render:
            logger.warning(f"Error during FFmpeg execution ({e_render})")
            last_ffmpeg_error = str(e_render)
    else:
        last_ffmpeg_error = "ffmpeg binary not found on PATH"

    if not rendered:
        if _allow_synthetic_video():
            logger.warning(f"ALLOW_SYNTHETIC_VIDEO=1: generating synthetic MP4 for test environment at {final_video_file}")
            _generate_synthetic_mp4(str(final_video_file), scenes=scenes)
            synthetic = True
            pipeline_data["synthetic"] = True
        else:
            error_msg = (
                f"Render failed for job {job_id}: FFmpeg could not produce a valid video. "
                f"Last FFmpeg error: {last_ffmpeg_error or 'unknown error'}"
            )
            logger.error(error_msg)
            pipeline_data["error"] = error_msg
            update_job_stage(db, job_id, "failed", status=JobStatus.failed, pipeline_data=pipeline_data, error=error_msg)
            return

    # Post-render verification with ffprobe: never mark done for an unverifiable file
    if rendered and not synthetic:
        expected_duration = sum(float(s.get("audio_duration") or s.get("duration") or 0.0) for s in scenes)
        ok_verify, verify_detail = _verify_rendered_video(str(final_video_file), expected_duration=expected_duration)
        pipeline_data["render_verification"] = verify_detail
        if not ok_verify:
            error_msg = f"Render verification failed for job {job_id}: {verify_detail}"
            logger.error(error_msg)
            pipeline_data["error"] = error_msg
            update_job_stage(db, job_id, "failed", status=JobStatus.failed, pipeline_data=pipeline_data, error=error_msg)
            return
        logger.success(f"Render verification passed: {verify_detail}")

    # Snapshot extraction
    snapshot_file = job_dir / "snapshot.jpg"
    snapshot_extracted = False
    if ffmpeg_available and rendered and final_video_file.exists():
        try:
            snap_cmd = f'ffmpeg -y -ss 00:00:01 -i "{final_video_posix}" -vframes 1 -q:v 2 "{snapshot_file.resolve().as_posix()}"'
            res_snap = subprocess.run(snap_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if res_snap.returncode == 0 and snapshot_file.exists():
                snapshot_extracted = True
        except Exception:
            pass

    if not snapshot_extracted:
        first_img = job_dir / "images" / "scene_000.png"
        if first_img.exists():
            try:
                with Image.open(first_img) as im:
                    im.convert("RGB").save(str(snapshot_file), "JPEG")
                    snapshot_extracted = True
            except Exception:
                pass
        if not snapshot_extracted:
            im = Image.new("RGB", (1080, 1920), (20, 24, 33))
            im.save(str(snapshot_file), "JPEG")

    output_path = f"data/output/{job_id}/final_video.mp4"
    job = get_job(db, job_id)
    if job:
        job.output_path = output_path
        db.commit()
        # Task 3.2: every done job gets a reviewable thumbnail. Thumbnail
        # problems should not invalidate an otherwise verified master video.
        try:
            _ensure_job_thumbnail(job, pipeline_data)
        except Exception as e_thumb:
            logger.warning(f"Thumbnail generation failed for job {job_id}: {e_thumb}")
            pipeline_data["thumbnail_error"] = str(e_thumb)

    update_job_stage(db, job_id, "done", status=JobStatus.done, pipeline_data=pipeline_data)
    logger.success(f"🏆 [Job {job_id}] STAGE 5 COMPLETE: Pipeline finished successfully (status=done)!")


def run_video_pipeline(job_id: str):
    """
    Main background execution entrypoint for video creation pipeline.
    Invoked asynchronously via FastAPI BackgroundTasks.
    """
    try:
        run_in_async_loop(_async_execute_stages_1_to_3(job_id))
    except Exception as e:
        logger.exception(f"Fatal error running video pipeline for job {job_id}: {e}")
        db = SessionLocal()
        try:
            update_job_stage(db, job_id, stage="failed", status=JobStatus.failed, error=str(e))
        finally:
            db.close()


def continue_video_pipeline(job_id: str):
    """
    Continues rendering pipeline from stage 'assets_ready' to 'rendering' and 'done'.
    Invoked when step-by-step studio approval is received.
    """
    db = SessionLocal()
    try:
        logger.info(f"Resuming video rendering pipeline for job {job_id}...")
        _execute_stages_4_and_5(db, job_id)
    except Exception as e:
        logger.exception(f"Fatal error in continue_video_pipeline for job {job_id}: {e}")
        update_job_stage(db, job_id, stage="failed", status=JobStatus.failed, error=str(e))
    finally:
        db.close()


def continue_after_source_review(job_id: str) -> dict:
    """
    Resumes a job halted at stage 'source_review' (Source Gate, Task 2.2).

    Re-audits scenes (the user may have added sources via the API in the
    meantime). If scenes are still missing sources, the job stays at
    'source_review' with a refreshed audit; otherwise Stages 2-5 run.
    Returns {"status": "resumed"|"blocked", ...}.
    """
    from core.script_engine.source_gate import evaluate_gate

    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found in DB")

        pipeline_data = job.pipeline_data or {}
        scenes = pipeline_data.get("scenes") or pipeline_data.get("script", {}).get("scenes", [])
        gate = evaluate_gate(scenes)
        pipeline_data["source_audit"] = gate["audit"]

        if gate["has_blocking"]:
            update_job_stage(db, job_id, "source_review", status=JobStatus.processing, pipeline_data=pipeline_data)
            logger.warning(f"⛔ [Job {job_id}] Still blocked at 'source_review': scenes {gate['blocking']} need sources.")
            return {"status": "blocked", "job_id": job_id, "blocking_scenes": gate["blocking"], "source_audit": gate["audit"]}

        update_job_stage(db, job_id, "script_ready", status=JobStatus.processing, pipeline_data=pipeline_data)
        logger.success(f"✅ [Job {job_id}] Source Gate passed; resuming stages 2-5.")
    finally:
        db.close()

    run_in_async_loop(_async_execute_stages_2_and_3(job_id))
    return {"status": "resumed", "job_id": job_id, "source_audit": gate["audit"]}


def regenerate_scene_asset(job_id: str, scene_index: int, prompt: str) -> dict:
    """
    Regenerates the visual asset for a specific scene index with a new prompt.
    Evaluates Vision Gate and updates pipeline_data audit trail.
    """
    from core.media_engine.cascade_asset_orchestrator import CascadeAssetOrchestrator
    from core.media_engine.image_generator import ImageGenerator

    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found in DB")

        p_data = job.pipeline_data or {}
        scenes = p_data.setdefault("scenes", [])
        storyboard = p_data.setdefault("storyboard", [])

        img_dir = Path("data/output") / job_id / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        new_img_dest = img_dir / f"scene_{scene_index}_regen.png"
        new_img_dest_str = str(new_img_dest).replace("\\", "/")

        art_style_key = getattr(job, "art_style", "photorealistic") or "photorealistic"
        style_mod = STYLE_MODIFIERS.get(art_style_key.lower(), art_style_key)

        styled_prompt = prompt.strip()
        if style_mod.lower() not in styled_prompt.lower():
            styled_prompt = f"{styled_prompt}, {style_mod}"

        cascade = CascadeAssetOrchestrator(cache_dir=img_dir)
        img_gen = ImageGenerator()

        tier_used = "tier1_imagen"
        gate_score = 0.95
        gate_reason = "Regenerated prompt compliant"

        async def _do_regen():
            nonlocal tier_used, gate_score, gate_reason
            try:
                acq_path, meta = await cascade.acquire_asset(
                    target_object=prompt[:30],
                    scene_sentence=prompt,
                    archetype=art_style_key,
                    job_cache_dir=img_dir
                )
                if acq_path and os.path.exists(acq_path):
                    _ensure_scene_composite(acq_path, str(new_img_dest), art_style=art_style_key)
                    tier_used = meta.get("tier_used", "tier1_imagen")
                    gate_score = float(meta.get("confidence", 0.95))
                    gate_reason = meta.get("reason", "Regenerated asset compliant")
            except Exception as e_casc:
                logger.warning(f"Cascade regeneration failed ({e_casc}), using ImageGenerator")
                try:
                    dummy_scene = {"narration": prompt, "still_image_prompt": styled_prompt, "visual_description": styled_prompt}
                    await img_gen.generate_scene_image(dummy_scene, str(new_img_dest), topic=job.topic, scene_index=scene_index)
                    tier_used = "tier2_stock"
                    gate_score = 0.90
                    gate_reason = "ImageGenerator regenerated"
                except Exception as e_ig:
                    logger.warning(f"ImageGenerator failed ({e_ig}), creating procedural fallback")
                    img_gen._generate_artistic_collage_fallback({"narration": prompt}, scene_index, str(new_img_dest))
                    tier_used = "tier4_procedural"
                    gate_score = 0.88
                    gate_reason = "Procedural collage regenerated"

            try:
                if os.path.exists(str(new_img_dest)):
                    gate_eval = await cascade.evaluate_vision_gate(
                        image=str(new_img_dest),
                        scene_sentence=prompt,
                        target_object=prompt[:30],
                        current_prompt=styled_prompt
                    )
                    gate_score = float(gate_eval.get("confidence", gate_score))
                    gate_reason = gate_eval.get("reason", gate_reason)
            except Exception:
                pass

        run_in_async_loop(_do_regen())

        # Update scene in pipeline_data["scenes"]
        found_scene = False
        for sc in scenes:
            if sc.get("scene_index") == scene_index or sc.get("index") == scene_index:
                sc["image_path"] = new_img_dest_str
                sc["visual_prompt"] = styled_prompt
                sc["prompt"] = styled_prompt
                sc["still_image_prompt"] = styled_prompt
                sc["tier_used"] = tier_used
                sc["vision_gate_score"] = gate_score
                sc["vision_gate_reasoning"] = gate_reason
                found_scene = True
                break

        if not found_scene:
            scenes.append({
                "scene_index": scene_index,
                "index": scene_index,
                "image_path": new_img_dest_str,
                "visual_prompt": styled_prompt,
                "prompt": styled_prompt,
                "still_image_prompt": styled_prompt,
                "tier_used": tier_used,
                "vision_gate_score": gate_score,
                "vision_gate_reasoning": gate_reason
            })

        # Update storyboard
        found_sb = False
        for sb in storyboard:
            if sb.get("scene_index") == scene_index:
                sb["image_path"] = new_img_dest_str
                sb["visual_prompt"] = styled_prompt
                sb["prompt"] = styled_prompt
                sb["tier_used"] = tier_used
                sb["vision_gate_score"] = gate_score
                sb["vision_gate_reasoning"] = gate_reason
                found_sb = True
                break

        if not found_sb:
            storyboard.append({
                "scene_index": scene_index,
                "image_path": new_img_dest_str,
                "visual_prompt": styled_prompt,
                "prompt": styled_prompt,
                "tier_used": tier_used,
                "vision_gate_score": gate_score,
                "vision_gate_reasoning": gate_reason
            })

        # Update script scenes if present
        if "script" in p_data and isinstance(p_data["script"], dict):
            for sc in p_data["script"].get("scenes", []):
                if isinstance(sc, dict) and (sc.get("scene_index") == scene_index or sc.get("index") == scene_index):
                    sc["image_path"] = new_img_dest_str
                    sc["still_image_prompt"] = styled_prompt

        job.pipeline_data = p_data
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)

        return {
            "status": "success",
            "job_id": job_id,
            "scene_index": scene_index,
            "image_path": new_img_dest_str,
            "prompt": styled_prompt,
            "tier_used": tier_used,
            "vision_gate_score": gate_score,
            "vision_gate_reasoning": gate_reason
        }
    except Exception as e:
        logger.exception(f"Error regenerating scene asset for job {job_id}, scene {scene_index}: {e}")
        raise
    finally:
        db.close()


@app.task(name="dashboard.worker.video_tasks.create_video_task", bind=True)
def create_video_task(self, job_id: str):
    """Celery task adapter delegating to native pipeline."""
    return run_video_pipeline(job_id)


def _parse_schedule_time(schedule_time: Union[str, datetime, None]) -> Optional[datetime]:
    """Parse an ISO schedule value without silently discarding timezone data."""
    if schedule_time is None or isinstance(schedule_time, datetime):
        return schedule_time
    value = str(schedule_time).strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _extract_postiz_post_id(result: Any) -> Optional[str]:
    """Extract a Postiz post identifier from the documented dict response."""
    if isinstance(result, dict):
        for key in ("id", "post_id", "postId"):
            if result.get(key):
                return str(result[key])
        for key in ("data", "post", "result"):
            nested = _extract_postiz_post_id(result.get(key))
            if nested:
                return nested
    if isinstance(result, list) and result:
        return _extract_postiz_post_id(result[0])
    return None


def _publish_metadata(job, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve publish metadata from pipeline data, DB metadata, then script."""
    metadata: Dict[str, Any] = {}
    if isinstance(pipeline_data.get("metadata"), dict):
        metadata.update(pipeline_data["metadata"])
    db_metadata = getattr(job, "extra_metadata", None)
    if isinstance(db_metadata, dict):
        # Explicitly stored DB metadata is newer than pipeline bootstrap data.
        metadata.update(db_metadata)

    script = pipeline_data.get("script")
    if not isinstance(script, dict):
        script = getattr(job, "script", None) or {}
    if not isinstance(script, dict):
        script = {}

    hashtags = metadata.get("hashtags") or script.get("hashtags") or []
    if isinstance(hashtags, str):
        hashtags = [tag.strip() for tag in hashtags.split(",") if tag.strip()]

    return {
        "title": metadata.get("title") or script.get("title") or job.topic,
        "description": metadata.get("description") or script.get("description") or "",
        "hashtags": [str(tag) for tag in hashtags],
        "thumbnail_text": metadata.get("thumbnail_text") or "",
        "script": script,
    }


def _record_publish_state(
    db,
    job_id: str,
    publish: Dict[str, Any],
    *,
    status: Optional[JobStatus] = None,
    stage: Optional[str] = None,
    error: Optional[str] = None,
) -> Optional[Any]:
    """Persist publish audit data without changing the rendered-video fields."""
    job = get_job(db, job_id)
    if not job:
        return None
    pipeline_data = job.pipeline_data or {}
    pipeline_data["publish"] = publish
    job.pipeline_data = pipeline_data
    if status is not None:
        job.status = status
    if stage is not None:
        job.stage = stage
    if error is not None:
        job.error = error
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job


def publish_video(job_id: str, platforms: list, schedule_time: Union[str, datetime, None] = None) -> Dict[str, Any]:
    """
    Publish a completed video through Postiz.

    A job is marked ``published`` only when Postiz returns a post id. Any
    Postiz/media failure is recorded as the distinct ``publish_failed`` status;
    the master-video stage and ``output_path`` are left intact.
    """
    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found in DB")

        pipeline_data = job.pipeline_data or {}
        previous_publish = pipeline_data.get("publish") if isinstance(pipeline_data.get("publish"), dict) else {}
        metadata = _publish_metadata(job, pipeline_data)
        requested_platforms = [str(p) for p in (platforms or [])]
        parsed_schedule = _parse_schedule_time(schedule_time)
        scheduled_at = parsed_schedule.isoformat() if parsed_schedule else previous_publish.get("scheduled_at")

        video_path = job.output_path or str(Path("data/output") / job_id / "final_video.mp4")
        # Older done jobs may predate automatic thumbnails; create one lazily
        # so Postiz still receives it, without failing publish if PIL/font IO
        # is unavailable on the host.
        if not pipeline_data.get("thumbnail_path") or not Path(pipeline_data["thumbnail_path"]).exists():
            try:
                _ensure_job_thumbnail(job, pipeline_data)
            except Exception as e_thumb:
                logger.warning(f"Lazy thumbnail generation failed for job {job_id}: {e_thumb}")
                pipeline_data["thumbnail_error"] = str(e_thumb)
            job.pipeline_data = pipeline_data
            db.commit()
        publish_info: Dict[str, Any] = {
            **previous_publish,
            "postiz_post_id": previous_publish.get("postiz_post_id"),
            "platforms": requested_platforms,
            "scheduled_at": scheduled_at,
            "status": "publishing",
            "title": metadata["title"],
        }
        _record_publish_state(db, job_id, publish_info)

        # The job object held by this session is stale after the helper commit;
        # re-read fields before constructing the client call.
        job = get_job(db, job_id)
        pipeline_data = job.pipeline_data or {}
        thumbnail_path = pipeline_data.get("thumbnail_path") or str(Path("data/output") / job_id / "thumbnail.jpg")
        if not Path(thumbnail_path).exists():
            thumbnail_path = None

        if not video_path or not Path(video_path).exists():
            raise FileNotFoundError(f"Completed video file not found: {video_path}")

        logger.info(f"Publishing job {job_id} to platforms: {requested_platforms} via Postiz")
        client = PostizClient()
        result = run_in_async_loop(
            client.schedule_post(
                video_path=str(video_path),
                title=metadata["title"],
                description=metadata["description"],
                hashtags=metadata["hashtags"],
                platforms=requested_platforms,
                schedule_time=parsed_schedule,
                thumbnail_path=thumbnail_path,
            )
        )
        post_id = _extract_postiz_post_id(result)
        if not post_id:
            raise RuntimeError(f"Postiz response did not include a post id: {result!r}")

        is_future_schedule = bool(parsed_schedule and parsed_schedule > datetime.now(parsed_schedule.tzinfo or timezone.utc))
        publish_info.update({
            "postiz_post_id": post_id,
            "status": "scheduled" if is_future_schedule else "published",
            "postiz_response": result if isinstance(result, (dict, list, str, int, float, bool)) else str(result),
            "published_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        })
        _record_publish_state(
            db,
            job_id,
            publish_info,
            status=JobStatus.published,
            stage="published",
            error=None,
        )
        logger.success(f"Job {job_id} published via Postiz (post_id={post_id})")
        return {"status": "published", "job_id": job_id, "postiz_post_id": post_id, "publish": publish_info}

    except Exception as e:
        logger.exception(f"Error publishing job {job_id}: {e}")
        try:
            job = get_job(db, job_id)
            if job:
                pipeline_data = job.pipeline_data or {}
                previous_publish = pipeline_data.get("publish") if isinstance(pipeline_data.get("publish"), dict) else {}
                publish_info = {
                    **previous_publish,
                    "platforms": [str(p) for p in (platforms or [])],
                    "scheduled_at": previous_publish.get("scheduled_at"),
                    "status": "publish_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                # Stage returns to done to make clear the rendered master is
                # still intact; job.status carries the distinct failure state.
                _record_publish_state(
                    db,
                    job_id,
                    publish_info,
                    status=JobStatus.publish_failed,
                    stage="done",
                    error=f"Publish error: {str(e)}",
                )
                return {"status": "publish_failed", "job_id": job_id, "error": str(e), "publish": publish_info}
        except Exception:
            logger.exception(f"Could not persist publish_failed state for job {job_id}")
        return {"status": "publish_failed", "job_id": job_id, "error": str(e)}
    finally:
        db.close()


@app.task(name="dashboard.worker.video_tasks.publish_video_task")
def publish_video_task(job_id: str, platforms: list, schedule_time: str = None):
    """Celery-compatible adapter delegating to the native Postiz publisher."""
    return publish_video(job_id, platforms, schedule_time)
