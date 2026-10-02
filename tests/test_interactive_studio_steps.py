"""
tests/test_interactive_studio_steps.py

Comprehensive End-to-End Test Suite for AutoVideoFactory Interactive 5-Stage Studio:
- Test 1: Generate script with Gemini 3.8 Flash for "3 sự thật bất ngờ từ tế bào của con người"
  (Verify dynamic cellular biology content, 100% elimination of chess fallback).
- Test 2: Edit script via PUT /jobs/{id}/step/script and confirm DB update and persistence (stage="script_ready").
- Test 3: Generate voice via POST /jobs/{id}/step/voice (stage="voice_ready") and re-synthesize scene 1
  via POST /jobs/{id}/step/voice-scene (assert only scene 1 is modified, other scenes untouched).
- Test 4: Generate storyboard via POST /jobs/{id}/step/storyboard (stage="assets_ready"), regenerate scene 1
  via POST /jobs/{id}/step/regenerate-scene-image, upload scene 2 via POST /jobs/{id}/step/upload-scene-image.
- Test 5: Generate effects via POST /jobs/{id}/step/effects (Dynamic Chunked ASS 2-4 words/chunk, margin 180 safe zone, stage="rendering").
- Test 6: Render master video via POST /jobs/{id}/step/render (stage="done", status=JobStatus.done) and export zip via GET /jobs/{id}/export-zip.
- Test 7: Full interactive 5-stage sequential integration flow.
"""

import io
import os
import sys
import json
import shutil
import zipfile
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List

from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import dashboard.api.database as db_mod
import dashboard.api.routes.jobs as jobs_route_mod
import dashboard.worker.video_tasks as video_tasks_mod
from dashboard.api.main import app
from dashboard.api.database import Base, get_db, VideoJob, create_job, get_job
from dashboard.api.models import JobStatus
from core.script_engine.gemini_client import GeminiClient, DEFAULT_FALLBACK_MODELS
from core.script_engine.script_generator import ScriptGenerator


class TestInteractiveStudioSteps(unittest.TestCase):
    """
    Automated verification of the Interactive 5-Stage Studio according to Requirement R4.
    Runs deterministically in test isolation with real database sessions,
    genuine pipeline data structures, and filesystem assertions.
    """

    @classmethod
    def setUpClass(cls):
        cls.created_job_ids: List[str] = []

        # 1. Create isolated temporary directory and SQLite database
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "test_interactive_studio.db")
        cls.test_engine = create_engine(
            f"sqlite:///{cls.test_db_path}",
            connect_args={"check_same_thread": False, "timeout": 30}
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.test_engine
        )
        Base.metadata.create_all(bind=cls.test_engine)

        # 2. Backup original session makers and engine
        cls._orig_db_engine = db_mod.engine
        cls._orig_db_session = db_mod.SessionLocal
        cls._orig_jobs_session = jobs_route_mod.SessionLocal
        cls._orig_worker_session = video_tasks_mod.SessionLocal

        # 3. Patch SessionLocal across database, route, and worker modules for strict DB isolation
        db_mod.engine = cls.test_engine
        db_mod.SessionLocal = cls.TestingSessionLocal
        jobs_route_mod.SessionLocal = cls.TestingSessionLocal
        video_tasks_mod.SessionLocal = cls.TestingSessionLocal

        # 4. Override FastAPI get_db dependency
        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        # 1. Clean up created job output directories and zip archives
        for jid in cls.created_job_ids:
            job_dir = Path("data/output") / jid
            if job_dir.exists():
                try:
                    shutil.rmtree(job_dir)
                except Exception:
                    pass
            zip_file = Path("data/output") / f"{jid}.zip"
            if zip_file.exists():
                try:
                    zip_file.unlink()
                except Exception:
                    pass

        # 2. Restore original dependencies and sessions
        app.dependency_overrides.clear()
        db_mod.engine = cls._orig_db_engine
        db_mod.SessionLocal = cls._orig_db_session
        jobs_route_mod.SessionLocal = cls._orig_jobs_session
        video_tasks_mod.SessionLocal = cls._orig_worker_session

        # 3. Dispose test engine and clean up temp directory
        try:
            cls.test_engine.dispose()
        except Exception:
            pass
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def _create_isolated_job(
        self,
        job_id: str,
        topic: str = "3 sự thật bất ngờ từ tế bào của con người",
        mode: str = "step_by_step",
        art_style: str = "photorealistic"
    ) -> str:
        """Helper to create and track a unique test job."""
        self.created_job_ids.append(job_id)
        db = self.TestingSessionLocal()
        try:
            create_job(
                db=db,
                job_id=job_id,
                topic=topic,
                style="collage_broll",
                language="vi",
                mode=mode,
                art_style=art_style,
                voice_preset="default",
                stage="pending"
            )
        finally:
            db.close()
        return job_id

    # -------------------------------------------------------------------------
    # TEST 1: Generate script with Gemini 3.8 Flash for biological topic
    # -------------------------------------------------------------------------
    def test_01_generate_script_gemini_cellular_biology(self):
        """
        Test 1: Generate script with Gemini 3.8 Flash for '3 sự thật bất ngờ từ tế bào của con người'
        - Verify GeminiClient configuration (default model is gemini-3.8-flash, fallback list).
        - Verify dynamic cellular biology content (cell, dna, biology terms).
        - Assert 100% elimination of chess board / puppet fallback content.
        - Verify POST /jobs/{id}/step/script updates DB, returns stage='script_ready',
          status='processing', and writes data/output/{job_id}/script.json.
        """
        # 1. Verify GeminiClient model configuration
        gemini_client = GeminiClient()
        self.assertIn("gemini-3.8-flash", DEFAULT_FALLBACK_MODELS)
        self.assertIn("gemini-3.8-flash", gemini_client.fallback_models)
        self.assertEqual(gemini_client.default_model, "gemini-3.8-flash")
        self.assertEqual(DEFAULT_FALLBACK_MODELS[0], "gemini-3.8-flash")

        # 2. Verify ScriptGenerator generates domain-accurate cellular biology content
        script_gen = ScriptGenerator()
        topic = "3 sự thật bất ngờ từ tế bào của con người"
        fallback_script = script_gen._generate_fallback_script(
            topic=topic,
            style="collage_broll",
            language="vi",
            duration=60
        )
        self.assertIn("scenes", fallback_script)
        scenes = fallback_script["scenes"]
        self.assertGreaterEqual(len(scenes), 3)

        # Aggregate all script text for strict verification
        full_script_corpus = (
            fallback_script.get("title", "") + " " +
            fallback_script.get("description", "") + " " +
            " ".join(
                s.get("narration", "") + " " +
                s.get("visual_metaphor", "") + " " +
                s.get("visual_description", "") + " " +
                s.get("still_image_prompt", "")
                for s in scenes
            )
        ).lower()

        # Strict Negative Assertion: 100% elimination of chess board & puppet fallback
        forbidden_chess_terms = [
            "bàn cờ", "chessboard", "quân cờ", "quân hậu",
            "vua cờ", "con rối", "puppet", "bàn tay đeo găng"
        ]
        for term in forbidden_chess_terms:
            self.assertNotIn(
                term,
                full_script_corpus,
                f"Defect detected: Forbidden chess term '{term}' found in cellular biology script!"
            )

        # Strict Positive Assertion: Must contain authentic biological keywords
        bio_keywords = ["tế bào", "dna", "sinh học", "cơ thể", "bào quan", "ty thể", "bạch cầu"]
        found_bio = any(k in full_script_corpus for k in bio_keywords)
        self.assertTrue(
            found_bio,
            f"Expected cellular biology keywords in script, but found none in: {full_script_corpus}"
        )

        # 3. Test API Endpoint: POST /jobs/{job_id}/step/script
        job_id = "test-isolated-step-01-script"
        self._create_isolated_job(job_id=job_id, topic=topic)

        resp = self.client.post(
            f"/jobs/{job_id}/step/script",
            json={"topic": topic, "art_style": "photorealistic", "duration": 60}
        )
        self.assertEqual(resp.status_code, 200, f"Script step failed: {resp.text}")
        data = resp.json()
        self.assertEqual(data["stage"], "script_ready")
        self.assertEqual(data["status"], "processing")

        api_scenes = data["pipeline_data"]["scenes"]
        self.assertGreaterEqual(len(api_scenes), 3)
        api_narrations = " ".join([s.get("narration", "") for s in api_scenes]).lower()

        for term in forbidden_chess_terms:
            self.assertNotIn(term, api_narrations, f"Chess term '{term}' returned by /step/script API!")

        self.assertTrue(
            any(k in api_narrations for k in bio_keywords),
            f"No biological keywords found in API narrations: {api_narrations}"
        )

        # Confirm script.json saved on disk
        script_file = Path("data/output") / job_id / "script.json"
        self.assertTrue(script_file.exists(), f"script.json was not created at {script_file}")
        with open(script_file, "r", encoding="utf-8") as f:
            disk_script = json.load(f)
            self.assertIn("scenes", disk_script)
            self.assertGreaterEqual(len(disk_script["scenes"]), 3)

    # -------------------------------------------------------------------------
    # TEST 2: Edit script via PUT /jobs/{id}/step/script and verify DB update
    # -------------------------------------------------------------------------
    def test_02_edit_script_put_step_script_persistence(self):
        """
        Test 2: Edit script via PUT /jobs/{id}/step/script
        - Verify DB update with new title, description, and modified scenes (voiceover, duration).
        - Verify stage stays 'script_ready' and changes persist in SQLite DB and script.json.
        - Verify error handling on nonexistent job returns 404.
        """
        job_id = "test-isolated-step-02-edit"
        self._create_isolated_job(job_id=job_id)

        # Generate initial script
        resp_init = self.client.post(
            f"/jobs/{job_id}/step/script",
            json={"topic": "3 sự thật bất ngờ từ tế bào của con người"}
        )
        self.assertEqual(resp_init.status_code, 200)

        # Prepare modified script payload
        modified_scenes = [
            {
                "scene_index": 0,
                "narration": "Sự thật 1: Mỗi phút cơ thể thay thế hơn 300 triệu tế bào cũ.",
                "visual_description": "Mô phỏng 3D tế bào hồng cầu di chuyển trong mạch máu",
                "duration": 5.5
            },
            {
                "scene_index": 1,
                "narration": "Sự thật 2: Ty thể là bào quan tạo năng lượng ATP quý giá.",
                "visual_description": "Cận cảnh ty thể phát ra ánh sáng năng lượng rực rỡ",
                "duration": 6.2
            },
            {
                "scene_index": 2,
                "narration": "Sự thật 3: Nhân tế bào bảo vệ an toàn cho bộ mã di truyền DNA.",
                "visual_description": "Màng nhân tế bào bao bọc chuỗi xoắn kép DNA",
                "duration": 4.8
            }
        ]
        update_payload = {
            "title": "3 Bí Mật Tế Bào Người Đột Phá",
            "description": "Video sinh học vi mô khám phá cơ thể người",
            "hashtags": ["#biology", "#cells", "#science"],
            "scenes": modified_scenes
        }

        # Send PUT request
        resp_put = self.client.put(f"/jobs/{job_id}/step/script", json=update_payload)
        self.assertEqual(resp_put.status_code, 200, f"PUT /step/script failed: {resp_put.text}")
        put_data = resp_put.json()

        # Assert stage remains script_ready
        self.assertEqual(put_data["stage"], "script_ready")
        self.assertEqual(put_data["pipeline_data"]["script"]["title"], "3 Bí Mật Tế Bào Người Đột Phá")
        self.assertEqual(
            put_data["pipeline_data"]["scenes"][0]["narration"],
            "Sự thật 1: Mỗi phút cơ thể thay thế hơn 300 triệu tế bào cũ."
        )
        self.assertEqual(put_data["pipeline_data"]["scenes"][0]["duration"], 5.5)
        self.assertEqual(put_data["pipeline_data"]["scenes"][1]["duration"], 6.2)

        # Verify DB persistence directly via DB session
        db = self.TestingSessionLocal()
        try:
            persisted_job = get_job(db, job_id)
            self.assertIsNotNone(persisted_job)
            self.assertEqual(persisted_job.stage, "script_ready")
            p_data = persisted_job.pipeline_data
            self.assertEqual(p_data["script"]["title"], "3 Bí Mật Tế Bào Người Đột Phá")
            self.assertEqual(p_data["scenes"][0]["duration"], 5.5)
            self.assertEqual(
                p_data["scenes"][0]["narration"],
                "Sự thật 1: Mỗi phút cơ thể thay thế hơn 300 triệu tế bào cũ."
            )
        finally:
            db.close()

        # Verify script.json on disk
        disk_script_path = Path("data/output") / job_id / "script.json"
        self.assertTrue(disk_script_path.exists())
        with open(disk_script_path, "r", encoding="utf-8") as f:
            disk_content = json.load(f)
            self.assertEqual(disk_content["title"], "3 Bí Mật Tế Bào Người Đột Phá")
            self.assertEqual(disk_content["scenes"][0]["duration"], 5.5)

        # Negative test: Nonexistent job returns 404
        resp_404 = self.client.put("/jobs/nonexistent-job-xyz/step/script", json=update_payload)
        self.assertEqual(resp_404.status_code, 404)

    # -------------------------------------------------------------------------
    # TEST 3: Generate voice & Re-synthesize single scene isolated
    # -------------------------------------------------------------------------
    def test_03_generate_voice_and_resynthesize_scene(self):
        """
        Test 3: Generate voice via POST /jobs/{id}/step/voice (stage='voice_ready')
        and re-synthesize scene 1 via POST /jobs/{id}/step/voice-scene.
        Assert that ONLY scene 1 is modified, while other scenes remain untouched.
        Verify error handling on invalid scene index.
        """
        job_id = "test-isolated-step-03-voice"
        self._create_isolated_job(job_id=job_id)

        # Initialize script stage
        self.client.post(
            f"/jobs/{job_id}/step/script",
            json={"topic": "3 sự thật bất ngờ từ tế bào của con người"}
        )

        # 1. Full voice synthesis
        resp_voice = self.client.post(
            f"/jobs/{job_id}/step/voice",
            json={"engine": "auto", "voice_preset": "default"}
        )
        self.assertEqual(resp_voice.status_code, 200, f"Voice step failed: {resp_voice.text}")
        v_data = resp_voice.json()
        self.assertEqual(v_data["stage"], "voice_ready")

        voice_scenes = v_data["pipeline_data"]["voice"]["scenes"]
        self.assertGreaterEqual(len(voice_scenes), 3)

        # Confirm all audio files exist on disk
        for vs in voice_scenes:
            self.assertTrue(os.path.exists(vs["audio_path"]), f"Missing audio: {vs['audio_path']}")
            self.assertGreater(os.path.getsize(vs["audio_path"]), 0)

        # Record scene states before single-scene re-synthesis
        initial_s0_narration = v_data["pipeline_data"]["scenes"][0]["narration"]
        initial_s0_audio = v_data["pipeline_data"]["scenes"][0]["audio_path"]
        initial_s2_narration = v_data["pipeline_data"]["scenes"][2]["narration"]
        initial_s2_audio = v_data["pipeline_data"]["scenes"][2]["audio_path"]

        # 2. Re-synthesize Scene 1 exclusively
        updated_s1_text = "Sự thật 2: Chuỗi xoắn kép DNA trong một tế bào dài tới gần hai mét nếu duỗi thẳng."
        resp_single = self.client.post(
            f"/jobs/{job_id}/step/voice-scene",
            json={"scene_index": 1, "text": updated_s1_text}
        )
        self.assertEqual(resp_single.status_code, 200, f"Voice scene re-synthesis failed: {resp_single.text}")
        single_data = resp_single.json()

        # Assert isolated update: scene 1 is updated with new narration and valid audio
        scenes_after = single_data["pipeline_data"]["scenes"]
        self.assertEqual(scenes_after[1]["narration"], updated_s1_text)
        self.assertTrue(os.path.exists(scenes_after[1]["audio_path"]))
        self.assertGreater(scenes_after[1]["duration"], 0)

        # Assert isolation guarantee: scene 0 and scene 2 remain strictly untouched
        self.assertEqual(
            scenes_after[0]["narration"],
            initial_s0_narration,
            "Defect: Scene 0 narration was unintentionally modified!"
        )
        self.assertEqual(
            scenes_after[0]["audio_path"],
            initial_s0_audio,
            "Defect: Scene 0 audio path was unintentionally modified!"
        )
        self.assertEqual(
            scenes_after[2]["narration"],
            initial_s2_narration,
            "Defect: Scene 2 narration was unintentionally modified!"
        )
        self.assertEqual(
            scenes_after[2]["audio_path"],
            initial_s2_audio,
            "Defect: Scene 2 audio path was unintentionally modified!"
        )

        # 3. Error handling: invalid scene indices
        resp_neg = self.client.post(
            f"/jobs/{job_id}/step/voice-scene",
            json={"scene_index": -1, "text": "Invalid negative index"}
        )
        self.assertEqual(resp_neg.status_code, 400, "Expected 400 for negative scene_index")

        resp_oob = self.client.post(
            f"/jobs/{job_id}/step/voice-scene",
            json={"scene_index": 999, "text": "Out of bounds index"}
        )
        self.assertEqual(resp_oob.status_code, 400, "Expected 400 for out-of-bounds scene_index")

    # -------------------------------------------------------------------------
    # TEST 4: Generate storyboard, Regenerate scene 1 & Upload scene 2 image
    # -------------------------------------------------------------------------
    def test_04_storyboard_regenerate_and_upload_scene_image(self):
        """
        Test 4: Generate storyboard via POST /jobs/{id}/step/storyboard (stage='assets_ready')
        - Regenerate scene 1 image via POST /jobs/{id}/step/regenerate-scene-image
        - Upload custom scene 2 image via POST /jobs/{id}/step/upload-scene-image
        - Verify Vision Gate score, reasoning, tier_used, and file existence.
        - Verify error handling on invalid file type returns 400.
        """
        job_id = "test-isolated-step-04-storyboard"
        self._create_isolated_job(job_id=job_id)

        # Prepare script and voice stages
        self.client.post(
            f"/jobs/{job_id}/step/script",
            json={"topic": "3 sự thật bất ngờ từ tế bào của con người"}
        )
        self.client.post(f"/jobs/{job_id}/step/voice", json={"engine": "auto"})

        # 1. Generate full Storyboard
        resp_sb = self.client.post(
            f"/jobs/{job_id}/step/storyboard",
            json={"art_style": "photorealistic"}
        )
        self.assertEqual(resp_sb.status_code, 200, f"Storyboard step failed: {resp_sb.text}")
        sb_data = resp_sb.json()
        self.assertEqual(sb_data["stage"], "assets_ready")

        storyboard = sb_data["pipeline_data"]["storyboard"]
        self.assertGreaterEqual(len(storyboard), 3)
        for sb in storyboard:
            self.assertIn("image_path", sb)
            self.assertTrue(os.path.exists(sb["image_path"]), f"Image missing: {sb['image_path']}")
            self.assertIn("vision_gate_score", sb)
            self.assertIn("vision_gate_reasoning", sb)
            self.assertIn("tier_used", sb)

        # 2. Regenerate Scene 1 Image with custom prompt
        regen_prompt = "Close-up photorealistic 3D visualization of human cellular DNA strands"
        resp_regen = self.client.post(
            f"/jobs/{job_id}/step/regenerate-scene-image",
            json={"scene_index": 1, "prompt": regen_prompt}
        )
        self.assertEqual(resp_regen.status_code, 200, f"Regenerate scene 1 failed: {resp_regen.text}")
        regen_data = resp_regen.json()

        s1_sb = regen_data["pipeline_data"]["storyboard"][1]
        stored_prompt = s1_sb.get("visual_prompt") or s1_sb.get("prompt", "")
        self.assertIn(regen_prompt, stored_prompt)
        self.assertIn("scene_1_regen.png", s1_sb["image_path"])
        self.assertTrue(os.path.exists(s1_sb["image_path"]))
        self.assertGreaterEqual(s1_sb["vision_gate_score"], 0.8)

        # 3. Upload Custom Image for Scene 2
        img_buffer = io.BytesIO()
        test_img = Image.new("RGB", (512, 512), color=(14, 124, 123))
        test_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        resp_up = self.client.post(
            f"/jobs/{job_id}/step/upload-scene-image",
            data={"scene_index": "2"},
            files={"file": ("mitochondria_custom.png", img_buffer, "image/png")}
        )
        self.assertEqual(resp_up.status_code, 200, f"Upload scene 2 failed: {resp_up.text}")
        up_data = resp_up.json()

        s2_sb = up_data["pipeline_data"]["storyboard"][2]
        self.assertIn("scene_2_uploaded.png", s2_sb["image_path"])
        self.assertTrue(os.path.exists(s2_sb["image_path"]))
        self.assertEqual(s2_sb["tier_used"], "user_uploaded")
        self.assertEqual(s2_sb["vision_gate_score"], 1.0)
        self.assertIn("custom image", s2_sb["vision_gate_reasoning"].lower())

        # 4. Error Handling: Reject non-image upload (e.g. .txt, .exe)
        invalid_file = io.BytesIO(b"executable or text payload")
        resp_invalid = self.client.post(
            f"/jobs/{job_id}/step/upload-scene-image",
            data={"scene_index": "0"},
            files={"file": ("malicious.exe", invalid_file, "application/octet-stream")}
        )
        self.assertEqual(resp_invalid.status_code, 400, "Expected 400 for non-image file extension")

    # -------------------------------------------------------------------------
    # TEST 5: Generate effects via POST /jobs/{id}/step/effects (Dynamic ASS)
    # -------------------------------------------------------------------------
    def test_05_generate_effects_dynamic_chunked_ass(self):
        """
        Test 5: Generate effects via POST /jobs/{id}/step/effects
        - Verify dynamic ASS file created with 2-4 words/chunk, margin 180 safe zone.
        - Verify stage='rendering'.
        - Verify subtitle styling (PlayResX 1080, PlayResY 1920, MarginV 180, font size 44).
        - Verify FFmpeg commands contain Ken Burns zoompan and ASS subtitle filters.
        """
        job_id = "test-isolated-step-05-effects"
        self._create_isolated_job(job_id=job_id)

        # Setup preceding stages
        self.client.post(
            f"/jobs/{job_id}/step/script",
            json={"topic": "3 sự thật bất ngờ từ tế bào của con người"}
        )
        self.client.post(f"/jobs/{job_id}/step/voice", json={"engine": "auto"})
        self.client.post(f"/jobs/{job_id}/step/storyboard", json={"art_style": "photorealistic"})

        # Call effects step
        resp_fx = self.client.post(
            f"/jobs/{job_id}/step/effects",
            json={"chunk_words": 3, "margin_v": 180, "font_size": 44}
        )
        self.assertEqual(resp_fx.status_code, 200, f"Effects step failed: {resp_fx.text}")
        fx_data = resp_fx.json()
        self.assertEqual(fx_data["stage"], "rendering")

        effects_info = fx_data["pipeline_data"]["effects"]
        self.assertEqual(effects_info["margin_v"], 180)
        self.assertEqual(effects_info["chunk_words"], 3)
        self.assertEqual(effects_info["font_size"], 44)

        # Verify ASS file on disk
        ass_path = Path("data/output") / job_id / "subtitles" / "scene_000.ass"
        self.assertTrue(ass_path.exists(), f"ASS file not found at {ass_path}")

        ass_content = ass_path.read_text(encoding="utf-8")
        self.assertIn("PlayResX: 1080", ass_content)
        self.assertIn("PlayResY: 1920", ass_content)
        # MarginV 180 safe zone in Style line
        self.assertIn(",30,30,180,1", ass_content)

        # Verify pop-up dialogue chunks: 2-4 words per chunk
        dialogue_lines = [line for line in ass_content.splitlines() if line.startswith("Dialogue:")]
        self.assertGreater(len(dialogue_lines), 0, "No dialogue lines found in ASS file!")
        for d_line in dialogue_lines:
            text_part = d_line.split(",,", 1)[-1] if ",," in d_line else d_line
            # Strip ASS override tags like {\c&H...&}
            import re
            clean_text = re.sub(r"\{.*?\}", "", text_part).strip()
            if clean_text:
                word_count = len(clean_text.split())
                self.assertGreaterEqual(
                    word_count,
                    2,
                    f"Defect: Subtitle chunk has less than 2 words (orphaned word): '{clean_text}'"
                )
                self.assertLessEqual(
                    word_count,
                    4,
                    f"Defect: Subtitle chunk exceeds 4 words: '{clean_text}'"
                )

        # Verify FFmpeg commands
        ffmpeg_cmds = fx_data["pipeline_data"]["ffmpeg_commands"]
        self.assertGreater(len(ffmpeg_cmds), 1)
        # Must contain zoompan filter for Ken Burns
        self.assertTrue(any("zoompan=" in cmd for cmd in ffmpeg_cmds))
        # Must contain ass filter for burning dynamic subtitles
        self.assertTrue(any("ass=" in cmd for cmd in ffmpeg_cmds))

    # -------------------------------------------------------------------------
    # TEST 6: Render master video & Export zip archive
    # -------------------------------------------------------------------------
    def test_06_render_master_video_and_export_zip(self):
        """
        Test 6: Render master video via POST /jobs/{id}/step/render (stage='done', status=JobStatus.done)
        and download zip via GET /jobs/{id}/export-zip.
        - Verify final_video.mp4 generated and output_path updated.
        - Verify ZIP archive is valid, uncorrupted, and contains script, media, and video.
        - Verify error handling on nonexistent job returns 404.
        """
        job_id = "test-isolated-step-06-render"
        self._create_isolated_job(job_id=job_id)

        # Setup all stages up to effects
        self.client.post(
            f"/jobs/{job_id}/step/script",
            json={"topic": "3 sự thật bất ngờ từ tế bào của con người"}
        )
        self.client.post(f"/jobs/{job_id}/step/voice", json={"engine": "auto"})
        self.client.post(f"/jobs/{job_id}/step/storyboard", json={"art_style": "photorealistic"})
        self.client.post(f"/jobs/{job_id}/step/effects", json={"chunk_words": 3, "margin_v": 180})

        # 1. Render master video
        resp_render = self.client.post(
            f"/jobs/{job_id}/step/render",
            json={"force": True}
        )
        self.assertEqual(resp_render.status_code, 200, f"Render step failed: {resp_render.text}")
        render_data = resp_render.json()
        self.assertEqual(render_data["stage"], "done")
        self.assertEqual(render_data["status"], "done")
        self.assertTrue(render_data["output_path"])

        # Confirm final video file on disk
        final_video_file = Path("data/output") / job_id / "final_video.mp4"
        self.assertTrue(final_video_file.exists(), f"final_video.mp4 missing at {final_video_file}")
        self.assertGreater(final_video_file.stat().st_size, 0)

        # 2. Export ZIP archive
        resp_zip = self.client.get(f"/jobs/{job_id}/export-zip")
        self.assertEqual(resp_zip.status_code, 200, f"Export zip failed: {resp_zip.text}")
        self.assertEqual(resp_zip.headers["content-type"], "application/zip")
        self.assertIn(f"project_{job_id}.zip", resp_zip.headers.get("content-disposition", ""))

        # Verify ZIP integrity and contents
        zip_bytes = io.BytesIO(resp_zip.content)
        self.assertTrue(zipfile.is_zipfile(zip_bytes), "Exported file is not a valid ZIP archive!")

        with zipfile.ZipFile(zip_bytes, "r") as zf:
            # Check CRC integrity (returns None if no corrupt files)
            self.assertIsNone(zf.testzip(), "Corrupted CRC detected in exported ZIP archive!")
            files_in_zip = zf.namelist()
            self.assertTrue(
                any("script.json" in f or "project_info.json" in f for f in files_in_zip),
                f"Missing script in ZIP: {files_in_zip}"
            )
            self.assertTrue(
                any("final_video.mp4" in f for f in files_in_zip),
                f"Missing final_video.mp4 in ZIP: {files_in_zip}"
            )

        # 3. Negative test: Export zip for nonexistent job returns 404
        resp_404_zip = self.client.get("/jobs/nonexistent-job-abc/export-zip")
        self.assertEqual(resp_404_zip.status_code, 404)

    # -------------------------------------------------------------------------
    # TEST 7: Full 5-Stage Studio Sequential Integration Flow
    # -------------------------------------------------------------------------
    def test_07_full_interactive_5_stage_workflow(self):
        """
        Test 7: Full end-to-end integration workflow executing all 5 Studio stages
        sequentially on a single job (test-studio-flow-full).
        Demonstrates seamless data flow from Script -> Voice -> Storyboard -> Effects -> Master Video.
        """
        job_id = "test-studio-flow-full"
        self._create_isolated_job(job_id=job_id, topic="3 sự thật bất ngờ từ tế bào của con người")

        # Stage 1: Script
        resp_s1 = self.client.post(
            f"/jobs/{job_id}/step/script",
            json={"topic": "3 sự thật bất ngờ từ tế bào của con người", "art_style": "photorealistic", "duration": 60}
        )
        self.assertEqual(resp_s1.status_code, 200)
        s1_data = resp_s1.json()
        self.assertEqual(s1_data["stage"], "script_ready")
        scenes = s1_data["pipeline_data"]["scenes"]
        self.assertGreaterEqual(len(scenes), 3)

        # Stage 1 Edit: Modify Scene 0
        scenes[0]["narration"] = "Mỗi giây, cơ thể người sản sinh ra hơn hai triệu tế bào mới kỳ diệu."
        scenes[0]["duration"] = 5.0
        resp_put = self.client.put(
            f"/jobs/{job_id}/step/script",
            json={"title": "3 Sự Thật Đột Phá Về Tế Bào", "scenes": scenes}
        )
        self.assertEqual(resp_put.status_code, 200)

        # Stage 2: Voice
        resp_s2 = self.client.post(f"/jobs/{job_id}/step/voice", json={"engine": "auto"})
        self.assertEqual(resp_s2.status_code, 200)
        self.assertEqual(resp_s2.json()["stage"], "voice_ready")

        # Stage 2 Edit: Re-synthesize Scene 1
        resp_v1 = self.client.post(
            f"/jobs/{job_id}/step/voice-scene",
            json={"scene_index": 1, "text": "DNA trong tế bào nếu duỗi thẳng sẽ vươn tới Sao Diêm Vương."}
        )
        self.assertEqual(resp_v1.status_code, 200)

        # Stage 3: Storyboard
        resp_s3 = self.client.post(f"/jobs/{job_id}/step/storyboard", json={"art_style": "photorealistic"})
        self.assertEqual(resp_s3.status_code, 200)
        self.assertEqual(resp_s3.json()["stage"], "assets_ready")

        # Stage 3 Edit: Regenerate Scene 1 Image
        resp_reg = self.client.post(
            f"/jobs/{job_id}/step/regenerate-scene-image",
            json={"scene_index": 1, "prompt": "Glowing DNA double helix inside cell nucleus"}
        )
        self.assertEqual(resp_reg.status_code, 200)

        # Stage 4: Effects & Subtitles
        resp_s4 = self.client.post(
            f"/jobs/{job_id}/step/effects",
            json={"chunk_words": 3, "margin_v": 180, "font_size": 44}
        )
        self.assertEqual(resp_s4.status_code, 200)
        self.assertEqual(resp_s4.json()["stage"], "rendering")

        # Stage 5: Render Master Video & Export
        resp_s5 = self.client.post(f"/jobs/{job_id}/step/render", json={"force": True})
        self.assertEqual(resp_s5.status_code, 200)
        self.assertEqual(resp_s5.json()["stage"], "done")
        self.assertEqual(resp_s5.json()["status"], "done")

        resp_zip = self.client.get(f"/jobs/{job_id}/export-zip")
        self.assertEqual(resp_zip.status_code, 200)
        self.assertEqual(resp_zip.headers["content-type"], "application/zip")


if __name__ == "__main__":
    unittest.main()
