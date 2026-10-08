"""
AutoVideoFactory — Collage B-Roll Engine
Triển khai phong cách editorial paper collage & stop-motion lấy cảm hứng từ gbro-collage-broll.
"""

import os
import math
import random
import asyncio
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageOps
import ffmpeg

import subprocess
from core.render_engine.ffmpeg_utils import get_video_info, concat_videos, add_background_music
from core.render_engine.subtitle_generator import SubtitleGenerator
from core.media_engine.image_generator import ImageGenerator
from core.media_engine.dynamic_cutout_manager import DynamicCutoutManager
from core.media_engine.beat_choreographer import BeatChoreographer
from .gbro_adapter import GbroAdapter


class CollageEngine:
    """
    Collage B-Roll Engine tạo video theo phong cách giấy cắt dán thủ công:
    - Nền phẳng màu sắc mạnh mẽ (Bold flat color fields: Cobalt, Burnt Orange, Mustard, Plum, Teal).
    - Lớp vân giấy (Paper fiber grain texture).
    - Vật thể cắt dán (Cutouts) với viền giấy kem (Cream keylines) và bóng đổ vật lý (Drop shadows).
    - Hiệu ứng nửa sắc độ (Halftone / High-contrast photographic print).
    - Chuyển động Stop-Motion lắp ráp (Assemble-from-empty animation ở 8-12 fps).
    - Xuất video chuẩn Shorts (9:16 - 1080x1920) hoặc Landscape (16:9 - 1920x1080).
    """

    # Bảng màu editorial đặc trưng của gbro-collage-broll
    COLOR_PALETTES = [
        {"bg": (29, 53, 87), "accent": (230, 57, 70), "name": "Deep Cobalt"},      # #1D3557, #E63946
        {"bg": (212, 77, 34), "accent": (244, 241, 222), "name": "Burnt Terracotta"},# #D44D22, #F4F1DE
        {"bg": (233, 196, 106), "accent": (38, 70, 83), "name": "Mustard Cardstock"},# #E9C46A, #264653
        {"bg": (74, 35, 90), "accent": (245, 176, 65), "name": "Plum & Gold"},      # #4A235A, #F5B041
        {"bg": (42, 157, 143), "accent": (231, 111, 81), "name": "Teal & Coral"},   # #2A9D8F, #E76F51
        {"bg": (38, 70, 83), "accent": (233, 196, 106), "name": "Charcoal Kraft"},  # #264653, #E9C46A
    ]

    CREAM_KEYLINE = (255, 253, 247, 255) # Màu viền giấy kem cắt máy
    SHADOW_COLOR = (0, 0, 0, 80)          # Bóng đổ giấy trong suốt

    def __init__(self):
        """Khởi tạo engine, image generator, subtitle generator, cutout manager và gbro adapter."""
        self.sub_generator = SubtitleGenerator(model_size="base")
        self.image_gen = ImageGenerator()
        self.gbro_adapter = GbroAdapter()
        self.cutout_mgr = DynamicCutoutManager()

    async def create_video(
        self,
        script: Dict[str, Any],
        language: str,
        output_path: str,
        format: str = 'shorts',
        audio_files: Optional[List[str]] = None,
        media_files: Optional[List[str]] = None,
    ) -> str:
        """
        Dựng video cắt dán collage b-roll hoàn chỉnh từ kịch bản.

        Args:
            script: Kịch bản video chứa danh sách cảnh (scenes)
            language: Ngôn ngữ ('vi' hoặc 'en')
            output_path: Đường dẫn file mp4 xuất xưởng
            format: 'shorts' (9:16 - 1080x1920) hoặc 'landscape' (16:9 - 1920x1080)
            audio_files: Danh sách file audio TTS tương ứng từng cảnh
            media_files: Danh sách file hình ảnh/video stock cho các cảnh

        Returns:
            str: Đường dẫn file video hoàn thành
        """
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = out_path.parent / f"work_collage_{out_path.stem}"
        work_dir.mkdir(parents=True, exist_ok=True)

        # Xác định độ phân giải
        if format == 'shorts':
            width, height = 1080, 1920
        else:
            width, height = 1920, 1080

        scenes = script.get('scenes', [])
        if not scenes:
            raise ValueError("Kịch bản không có cảnh nào (scenes trống)!")

        topic_title = script.get("title", "Video")
        logger.info(f"🎨 Bắt đầu dựng Collage B-Roll: {len(scenes)} cảnh | {width}x{height} ({format})")

        audio_files = audio_files or []
        media_files = media_files or []

        scene_video_clips = []
        scene_durations = []

        for i, scene in enumerate(scenes):
            scene_dir = work_dir / f"scene_{i:02d}"
            scene_dir.mkdir(parents=True, exist_ok=True)

            # 1. Lấy audio file cho cảnh & tính thời lượng
            scene_audio = audio_files[i] if i < len(audio_files) and audio_files[i] and os.path.exists(audio_files[i]) else None
            
            if scene_audio:
                info = get_video_info(scene_audio)
                audio_dur = info.get('duration', 0.0) or float(scene.get('duration', 5.0))
                scene_duration = max(4.5, audio_dur + 0.6)
            else:
                scene_duration = max(4.5, float(scene.get('duration', 5.0)))
            
            scene_durations.append(scene_duration)

            # 2. Sinh hoặc tải ảnh minh họa chủ đề chất lượng cao (Imagen 3 / NASA / Unsplash)
            scene_media = media_files[i] if i < len(media_files) and media_files[i] and os.path.exists(media_files[i]) else None
            if not scene_media or not os.path.exists(scene_media):
                scene_img_path = str(scene_dir / f"illustration_{i:02d}.png")
                logger.info(f"🖼️ Chuẩn bị ảnh minh họa thực tế cho Scene {i+1}...")
                scene_media = await self.image_gen.generate_scene_image(
                    scene=scene,
                    output_path=scene_img_path,
                    topic=topic_title,
                    scene_index=i
                )

            # 3. Chọn bảng màu tương phản theo từng cảnh
            palette = self.COLOR_PALETTES[i % len(self.COLOR_PALETTES)]
            color_field = scene.get("color_field") or palette["name"]
            color_hex = scene.get("color_hex")
            if not color_hex:
                r, g, b = palette["bg"]
                color_hex = f"{r:02X}{g:02X}{b:02X}"
            assembly_order = scene.get("assembly_order") or "background cardstock -> subject cutout -> physical accents"

            # 4. Trích xuất và chuẩn bị Dynamic Cutout Stickers theo kịch bản
            focal_kw = scene.get("focal_keyword") or ""
            if not focal_kw or len(focal_kw.split()) > 4:
                # Nếu không có focal_keyword riêng, trích xuất ngắn từ visual_description hoặc topic
                focal_kw = "vintage object"
            
            secondary_kw = scene.get("secondary_keyword") or ""
            layout_type = scene.get("layout_type") or "hero_center"
            topic_domain = scene.get("topic_domain") or script.get("topic_domain") or "general"
            has_hand = bool(scene.get("has_hand", False))
            has_camera = bool(scene.get("has_camera", False))

            logger.info(f"🎞️ Đang chuẩn bị Scene {i+1}/{len(scenes)}: Domain [{topic_domain}] | Layout [{layout_type}] | Focal '{focal_kw}' | Hand: {has_hand} | Cam: {has_camera}")
            
            # Thu nạp sticker động cho cảnh (cache / download / rembg AI)
            focal_sticker_path = await self.cutout_mgr.get_cutout_sticker(
                keyword=focal_kw,
                domain=topic_domain,
                is_character=False,
                fallback_scene_index=i
            )
            secondary_sticker_path = ""
            if secondary_kw and secondary_kw.lower().strip() != "none":
                secondary_sticker_path = await self.cutout_mgr.get_cutout_sticker(
                    keyword=secondary_kw,
                    domain=topic_domain,
                    is_character=False,
                    fallback_scene_index=i + 5
                )

            # Render video clip: đường beats (Stage 6) nếu scene có beats,
            # fallback về render_gbro_clip cũ khi beats render lỗi.
            scene_clip_path = str(scene_dir / f"clip_{i:02d}.mp4")
            raw_scene_clip = str(scene_dir / f"clip_raw_{i:02d}.mp4")

            beats = scene.get("beats") or []
            if beats:
                try:
                    logger.info(f"🎭 [Beats] Dựng scene {i+1} theo {len(beats)} story beats...")
                    await self._render_beats_scene(
                        scene=scene,
                        scene_duration=scene_duration,
                        width=width, height=height,
                        scene_dir=scene_dir,
                        scene_index=i,
                        topic_domain=topic_domain,
                        focal_sticker_path=focal_sticker_path,
                        secondary_sticker_path=secondary_sticker_path,
                        output_path=raw_scene_clip,
                    )
                except Exception as e_beats:
                    logger.warning(f"Beats render lỗi ({e_beats}), fallback về render_gbro_clip.")
                    self.gbro_adapter.render_gbro_clip(
                        still_image_path=scene_media,
                        color_field=color_field,
                        color_hex=color_hex,
                        assembly_order=assembly_order,
                        output_path=raw_scene_clip,
                        focal_sticker_path=focal_sticker_path,
                        secondary_sticker_path=secondary_sticker_path,
                        layout_type=layout_type,
                        topic_domain=topic_domain,
                        has_hand=has_hand,
                        has_camera=has_camera,
                        duration=scene_duration,
                        work_dir=scene_dir / "gbro",
                        width=width,
                        height=height
                    )
            else:
                self.gbro_adapter.render_gbro_clip(
                    still_image_path=scene_media,
                    color_field=color_field,
                    color_hex=color_hex,
                    assembly_order=assembly_order,
                    output_path=raw_scene_clip,
                    focal_sticker_path=focal_sticker_path,
                    secondary_sticker_path=secondary_sticker_path,
                    layout_type=layout_type,
                    topic_domain=topic_domain,
                    has_hand=has_hand,
                    has_camera=has_camera,
                    duration=scene_duration,
                    work_dir=scene_dir / "gbro",
                    width=width,
                    height=height
                )

            # Ghép nối audio vào clip nếu có audio
            if scene_audio and os.path.exists(scene_audio):
                merge_cmd = [
                    "ffmpeg", "-y",
                    "-i", raw_scene_clip,
                    "-i", scene_audio,
                    "-filter_complex", f"[1:a]apad=whole_dur={scene_duration:.2f}[a]",
                    "-map", "0:v",
                    "-map", "[a]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-t", f"{scene_duration:.2f}",
                    scene_clip_path
                ]
                subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            else:
                import shutil
                shutil.copyfile(raw_scene_clip, scene_clip_path)

            scene_video_clips.append(scene_clip_path)

        # Ghép nối các cảnh (chèn chuyển cảnh giấy xé giữa các scene)
        raw_concat_path = str(work_dir / "concat_raw.mp4")
        logger.info(f"🔗 Đang ghép nối {len(scene_video_clips)} cảnh thành video chính...")
        mixed_clips = self._insert_paper_wipes(scene_video_clips, work_dir, width, height)
        concat_videos(mixed_clips, raw_concat_path)
        scene_start_times = self._scene_start_times(mixed_clips, scene_durations)

        # Xuất file phụ đề TikTok ASS chuẩn 100% tiếng Việt từ script
        final_video_path = str(out_path)
        ass_path = str(work_dir / "subtitles.ass")
        
        try:
            logger.info("📝 Đang tạo phụ đề karaoke theo nhịp giọng đọc từ kịch bản...")
            try:
                self.sub_generator.generate_wordkaraoke_ass(
                    script=script,
                    scene_audios=audio_files,
                    scene_durations=scene_durations,
                    scene_start_times=scene_start_times,
                    output_path=ass_path,
                    format=format,
                    language=language,
                )
            except Exception as e_wk:
                logger.warning(f"Karaoke word-level lỗi ({e_wk}), fallback phụ đề cụm từ.")
                self.sub_generator.generate_tiktok_ass(
                    script=script,
                    scene_durations=scene_durations,
                    output_path=ass_path,
                    format=format
                )
            sub_video_path = str(work_dir / "video_with_subs.mp4")
            self.sub_generator.burn_subtitles(raw_concat_path, ass_path, sub_video_path)
            current_video = sub_video_path
        except Exception as e:
            logger.warning(f"Lỗi tạo/burn phụ đề TikTok ASS ({e}), sử dụng video gốc.")
            current_video = raw_concat_path

        # Thêm nhạc nền nhẹ nếu có
        bgm_path = self._find_background_music()
        if bgm_path and os.path.exists(bgm_path):
            try:
                logger.info(f"🎵 Thêm nhạc nền từ {bgm_path}...")
                add_background_music(current_video, bgm_path, final_video_path, music_volume=0.07)
            except Exception as e:
                logger.warning(f"Lỗi thêm BGM ({e}), xuất video không BGM.")
                import shutil
                shutil.copyfile(current_video, final_video_path)
        else:
            import shutil
            shutil.copyfile(current_video, final_video_path)

        logger.success(f"🎉 Xuất xưởng video Collage B-Roll thành công: {final_video_path}")
        return final_video_path

    async def _render_beats_scene(
        self,
        scene: Dict[str, Any],
        scene_duration: float,
        width: int,
        height: int,
        scene_dir: Path,
        scene_index: int,
        topic_domain: str,
        focal_sticker_path: str,
        secondary_sticker_path: str,
        output_path: str,
    ) -> str:
        """
        Dựng 1 scene theo story beats (Stage 6):
        choreograph beats -> timeline -> render_multi_element_scene nhiều beat.
        """
        choreo = BeatChoreographer(width=width, height=height).choreograph(scene, scene_duration)

        # Map target -> asset path. Hero/secondary dùng sticker đã lấy ở create_video.
        assets: Dict[str, str] = {}
        if focal_sticker_path and os.path.exists(focal_sticker_path):
            assets["hero"] = focal_sticker_path
        if secondary_sticker_path and os.path.exists(secondary_sticker_path):
            assets["secondary"] = secondary_sticker_path
        prop_n = 0
        for tid, info in (choreo.get("cast") or {}).items():
            if tid in assets:
                continue
            keyword = str(info.get("keyword") or "").strip()
            if not keyword:
                continue
            prop_path = await self.cutout_mgr.get_cutout_sticker(
                keyword=keyword,
                domain=topic_domain,
                is_character=False,
                fallback_scene_index=scene_index + 10 + prop_n,
            )
            prop_n += 1
            if prop_path and os.path.exists(prop_path):
                assets[tid] = prop_path

        # Pose variants cho SWAP_ASSET: thử lấy sticker tư thế khác theo keyword.
        pose_assets: Dict[str, Dict[str, str]] = {}
        for act in choreo.get("timeline", []):
            if str(act.get("action", "")).upper() != "SWAP_ASSET":
                continue
            target = act.get("target")
            pose = str(act.get("pose") or "alt")
            base_path = assets.get(target)
            keyword = str((choreo.get("cast") or {}).get(target, {}).get("keyword") or "")
            if not base_path or not keyword or pose in (pose_assets.get(target) or {}):
                continue
            try:
                variant_path = await self.cutout_mgr.get_cutout_sticker(
                    keyword=f"{keyword} {pose}",
                    domain=topic_domain,
                    is_character=False,
                    fallback_scene_index=scene_index + 30,
                )
            except Exception:
                variant_path = ""
            if (variant_path and os.path.exists(variant_path)
                    and os.path.abspath(variant_path) != os.path.abspath(base_path)):
                pose_assets.setdefault(target, {})[pose] = variant_path
                logger.info(f"🎭 [Beats] pose variant '{pose}' cho '{target}': {Path(variant_path).name}")

        # Lọc timeline theo target có asset thật (tránh element ma ở giữa khung).
        valid = set(assets.keys())
        choreo["timeline"] = [a for a in choreo.get("timeline", []) if a.get("target") in valid]

        return self.gbro_adapter.render_beats_clip(
            scene=scene,
            choreo=choreo,
            assets=assets,
            output_path=output_path,
            work_dir=scene_dir / "beats",
            width=width,
            height=height,
            duration=scene_duration,
            fps=12,
            pose_assets=pose_assets or None,
        )

    @staticmethod
    def _scene_start_times(mixed_clips: List[str], scene_durations: List[float],
                           wipe_duration: float = 0.5) -> List[float]:
        """
        Mốc bắt đầu mỗi scene trên timeline cuối (đã gồm wipe chuyển cảnh),
        để phụ đề/karaoke bám đúng nhịp.
        """
        starts: List[float] = []
        t, si = 0.0, 0
        for c in mixed_clips:
            if Path(c).name.startswith("wipe_"):
                t += wipe_duration
            else:
                starts.append(round(t, 3))
                t += float(scene_durations[si]) if si < len(scene_durations) else 0.0
                si += 1
        return starts

    def _insert_paper_wipes(
        self,
        scene_clips: List[str],
        work_dir: Path,
        width: int,
        height: int,
    ) -> List[str]:
        """
        Chèn clip chuyển cảnh giấy xé giữa các scene. Lỗi ở wipe nào thì bỏ qua
        wipe đó (giữ cắt cứng) chứ không fail cả video.
        """
        if len(scene_clips) < 2:
            return scene_clips
        out: List[str] = [scene_clips[0]]
        for i in range(1, len(scene_clips)):
            wipe_path = str(work_dir / f"wipe_{i-1:02d}_{i:02d}.mp4")
            try:
                self.gbro_adapter.render_paper_wipe(
                    scene_clips[i - 1], scene_clips[i], wipe_path,
                    width=width, height=height,
                )
                out.append(wipe_path)
            except Exception as e:
                logger.warning(f"Bỏ qua paper wipe {i-1}->{i} ({e}), giữ cắt cứng.")
            out.append(scene_clips[i])
        return out

    async def _render_scene_clip(
        self,
        scene: Dict[str, Any],
        palette: Dict[str, Any],
        duration: float,
        audio_path: Optional[str],
        media_path: Optional[str],
        output_path: str,
        width: int,
        height: int,
        scene_index: int,
        format: str
    ):
        """Tạo 1 clip ngắn cho từng cảnh theo phong cách stop-motion assemble."""
        fps = 10 # Tần số khung hình chuẩn stop-motion (8-12 fps tạo độ giật thủ công hoàn hảo)
        total_frames = int(duration * fps)
        if total_frames < 1:
            total_frames = 1

        # Chuẩn bị cutout element
        cutout_img = self._create_cutout_element(scene, media_path, palette, width, height, format)

        # Tạo chuỗi khung hình
        frames_dir = Path(output_path).parent / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        for frame_idx in range(total_frames):
            frame_time = frame_idx / fps
            frame_img = self._render_stopmotion_frame(
                palette=palette,
                cutout_img=cutout_img,
                frame_time=frame_time,
                duration=duration,
                width=width,
                height=height,
                frame_idx=frame_idx,
                scene=scene,
                scene_index=scene_index
            )
            frame_file = frames_dir / f"frame_{frame_idx:04d}.png"
            frame_img.save(str(frame_file), format="PNG")

        # Encode chuỗi ảnh thành video không tiếng
        silent_scene_mp4 = str(Path(output_path).parent / "silent.mp4")
        (
            ffmpeg
            .input(str(frames_dir / "frame_%04d.png"), framerate=fps)
            .output(silent_scene_mp4, vcodec='libx264', pix_fmt='yuv420p', r=24)
            .run(overwrite_output=True, quiet=True)
        )

        # Ghép audio vào clip của cảnh nếu có
        if audio_path and os.path.exists(audio_path):
            try:
                vid = ffmpeg.input(silent_scene_mp4)
                aud = ffmpeg.input(audio_path)
                (
                    ffmpeg
                    .output(vid, aud, output_path, vcodec='copy', acodec='aac', shortest=None)
                    .run(overwrite_output=True, quiet=True)
                )
            except Exception as e:
                logger.warning(f"Lỗi mux audio vào scene clip ({e}), dùng silent clip.")
                import shutil
                shutil.copyfile(silent_scene_mp4, output_path)
        else:
            # Tạo silent audio track để đảm bảo concat không lỗi audio
            try:
                vid = ffmpeg.input(silent_scene_mp4)
                null_aud = ffmpeg.input(f"anullsrc=r=44100:cl=stereo", f='lavfi', t=duration)
                (
                    ffmpeg
                    .output(vid, null_aud, output_path, vcodec='copy', acodec='aac', shortest=None)
                    .run(overwrite_output=True, quiet=True)
                )
            except Exception:
                import shutil
                shutil.copyfile(silent_scene_mp4, output_path)

    def _render_stopmotion_frame(
        self,
        palette: Dict[str, Any],
        cutout_img: Image.Image,
        frame_time: float,
        duration: float,
        width: int,
        height: int,
        frame_idx: int,
        scene: Dict[str, Any],
        scene_index: int
    ) -> Image.Image:
        """Dựng 1 khung hình với hiệu ứng ráp giấy và rung giật stop-motion."""
        # 1. Nền phẳng màu sắc với vân giấy
        bg_rgb = palette["bg"]
        frame = Image.new("RGBA", (width, height), bg_rgb + (255,))
        self._apply_paper_fiber_texture(frame, frame_idx)

        # 2. Logic Assemble-from-empty (Lắp ghép từ trống)
        # Trong 0.5s đầu tiên, vật thể trượt/rơi vào vị trí theo từng bậc (stepped stop-motion)
        assemble_duration = 0.5
        if frame_time < assemble_duration:
            step_progress = int((frame_time / assemble_duration) * 5) / 5.0
            ease = 1.0 - math.pow(1.0 - step_progress, 3)
            # Rơi từ trên xuống hoặc trượt từ dưới lên
            y_offset = int((1.0 - ease) * (height * 0.4))
            scale_factor = 0.7 + 0.3 * ease
        else:
            y_offset = 0
            scale_factor = 1.0

        # 3. Rung giật thủ công Stop-Motion (Handmade jitter)
        # Cứ 2-3 frame đổi góc nghiêng nhẹ một lần
        jitter_step = frame_idx // 3
        rnd = random.Random(scene_index * 1000 + jitter_step)
        rot_deg = rnd.uniform(-1.8, 1.8)
        pos_dx = rnd.randint(-4, 4)
        pos_dy = rnd.randint(-4, 4)

        # 4. Biến đổi Cutout
        c_w, c_h = cutout_img.size
        target_w = int(c_w * scale_factor)
        target_h = int(c_h * scale_factor)
        cur_cutout = cutout_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        if abs(rot_deg) > 0.1:
            cur_cutout = cur_cutout.rotate(rot_deg, resample=Image.Resampling.BICUBIC, expand=True)

        # 5. Dán vật thể lên nền tại vị trí trung tâm
        paste_x = (width - cur_cutout.width) // 2 + pos_dx
        paste_y = (height - cur_cutout.height) // 2 + y_offset + pos_dy

        frame.alpha_composite(cur_cutout, (paste_x, paste_y))

        # 6. Thêm thẻ nhãn chủ đề theo phong cách Editorial Stamp
        self._draw_editorial_label(frame, scene, palette, width, height, scene_index)

        return frame.convert("RGB")

    def _create_cutout_element(
        self,
        scene: Dict[str, Any],
        media_path: Optional[str],
        palette: Dict[str, Any],
        width: int,
        height: int,
        format: str
    ) -> Image.Image:
        """
        Tạo đối tượng cắt dán với viền trắng kem (cream keyline) và bóng đổ giấy.
        Nếu có ảnh stock -> áp dụng hiệu ứng halftone/duotone + cắt viền.
        Nếu không -> tạo thẻ đồ họa phong cách paper collage editorial.
        """
        target_max_w = int(width * 0.78)
        target_max_h = int(height * 0.58)

        base_img = None
        if media_path and os.path.exists(media_path):
            try:
                base_img = Image.open(media_path).convert("RGBA")
            except Exception as e:
                logger.warning(f"Không thể mở ảnh {media_path}: {e}")
                base_img = None

        if base_img is None:
            # Fallback tạo ảnh nghệ thuật vũ trụ/khoa học nếu file ảnh bị lỗi
            cache_fallback = Path("data/cache/images/artistic_fallback.png")
            cache_fallback.parent.mkdir(parents=True, exist_ok=True)
            self.image_gen._generate_artistic_collage_fallback(scene, 0, str(cache_fallback))
            base_img = Image.open(str(cache_fallback)).convert("RGBA")

        # Resize ảnh minh họa vừa vặn khung hình tạp chí
        base_img.thumbnail((target_max_w, target_max_h), Image.Resampling.LANCZOS)

        # Thêm viền giấy kem thủ công dày 14px (Cream keyline)
        cutout_with_border = self._add_paper_keyline_border(base_img, border_thickness=14)

        # Thêm bóng đổ giấy vật lý 3D nhiều lớp (Paper drop shadow)
        cutout_with_shadow = self._add_paper_drop_shadow(cutout_with_border, offset=(16, 20), blur_radius=12)

        return cutout_with_shadow

    def _add_paper_keyline_border(self, img: Image.Image, border_thickness: int = 14) -> Image.Image:
        """Tạo viền giấy dày màu kem bao quanh mép cắt như cắt kéo/máy."""
        w, h = img.size
        new_w = w + border_thickness * 2
        new_h = h + border_thickness * 2

        alpha = img.getchannel("A") if "A" in img.getbands() else Image.new("L", (w, h), 255)
        expanded_alpha = alpha.filter(ImageFilter.MaxFilter(border_thickness * 2 + 1))

        border_img = Image.new("RGBA", (new_w, new_h), self.CREAM_KEYLINE)
        border_mask = Image.new("L", (new_w, new_h), 0)
        border_mask.paste(expanded_alpha, (border_thickness, border_thickness))
        border_img.putalpha(border_mask)

        border_img.paste(img, (border_thickness, border_thickness), img)
        return border_img

    def _add_paper_drop_shadow(
        self,
        img: Image.Image,
        offset: Tuple[int, int] = (16, 20),
        blur_radius: int = 12
    ) -> Image.Image:
        """Tạo bóng đổ giấy nhiều lớp giúp hình ảnh nổi bật trên nền phẳng."""
        w, h = img.size
        pad_x = abs(offset[0]) + blur_radius * 2
        pad_y = abs(offset[1]) + blur_radius * 2

        full_w = w + pad_x * 2
        full_h = h + pad_y * 2

        canvas = Image.new("RGBA", (full_w, full_h), (0, 0, 0, 0))

        alpha = img.getchannel("A")
        shadow_mask = Image.new("L", (full_w, full_h), 0)
        shadow_pos = (pad_x + offset[0], pad_y + offset[1])
        shadow_mask.paste(alpha, shadow_pos)

        blurred_mask = shadow_mask.filter(ImageFilter.GaussianBlur(blur_radius))

        shadow_layer = Image.new("RGBA", (full_w, full_h), (0, 0, 0, 110))
        shadow_layer.putalpha(blurred_mask)

        canvas.alpha_composite(shadow_layer)
        canvas.alpha_composite(img, (pad_x, pad_y))

        return canvas

    def _apply_paper_fiber_texture(self, frame: Image.Image, frame_idx: int):
        """Thêm vân sợi giấy (Uncoated Paper Grain Texture) mộc mạc thủ công."""
        w, h = frame.size
        # Tạo ma trận nhiễu nhẹ
        np.random.seed((frame_idx * 17) % 10000)
        noise = np.random.randint(-12, 12, (h // 2, w // 2), dtype=np.int16)
        noise_img = Image.fromarray(noise.astype(np.uint8), mode="L")
        noise_img = noise_img.resize((w, h), Image.Resampling.NEAREST)

        # Blend nhẹ lên kênh alpha để tạo bề mặt giấy nhám
        texture_overlay = Image.new("RGBA", (w, h), (255, 255, 255, 18))
        texture_overlay.putalpha(noise_img)
        frame.alpha_composite(texture_overlay)

    def _draw_editorial_label(
        self,
        frame: Image.Image,
        scene: Dict[str, Any],
        palette: Dict[str, Any],
        width: int,
        height: int,
        scene_index: int
    ):
        """Vẽ thẻ nhãn số cảnh (Scene Stamp) ở góc trên phong cách cắt dán."""
        draw = ImageDraw.Draw(frame)
        label_text = f"SCENE 0{scene_index + 1}"

        # Hộp nhãn giấy màu vàng nhạt hoặc kem
        box_w, box_h = 240, 60
        box_x = 50
        box_y = 60

        draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=(255, 253, 240, 255), outline=(20, 20, 20, 255), width=3)
        draw.text((box_x + 30, box_y + 16), label_text, fill=(20, 20, 20, 255))

    def _extract_master_audio(self, video_path: str, output_audio: str):
        """Trích xuất file audio từ video đã ghép nối."""
        try:
            (
                ffmpeg
                .input(video_path)
                .output(output_audio, acodec='libmp3lame', q=2)
                .run(overwrite_output=True, quiet=True)
            )
        except Exception as e:
            logger.warning(f"Không thể trích xuất master audio: {e}")

    def _find_background_music(self) -> Optional[str]:
        """Tìm file nhạc nền có sẵn trong thư mục assets/music."""
        music_dir = Path("assets/music")
        if not music_dir.exists():
            return None
        mp3s = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
        return str(mp3s[0]) if mp3s else None
