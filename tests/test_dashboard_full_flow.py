"""
End-to-End Automated Test Suite for AutoVideoFactory Dashboard Full Flow
tests/test_dashboard_full_flow.py

Comprehensive test suite verifying all Acceptance Criteria from ORIGINAL_REQUEST.md:
1. POST /jobs with mode="step_by_step" halts at stage="assets_ready" and status=JobStatus.processing,
   with fully populated pipeline_data (script, voice, storyboard with Vision Gate audit).
2. POST /jobs/{job_id}/regenerate-scene updates the scene asset and stores the new prompt in pipeline_data["storyboard"].
3. POST /jobs/{job_id}/upload-scene-image saves custom image on disk and updates pipeline_data["storyboard"].
4. POST /jobs/{job_id}/continue-render resumes rendering pipeline from assets_ready to stage="done", status=JobStatus.done,
   and verifies valid final_video.mp4 exists on disk.
5. GET /jobs/{job_id}/export-zip downloads valid .ZIP archive containing script, media assets, and master video.
6. GET /voices and POST /voices/upload verify VieNeu-TTS voice sample listing and upload endpoints.
7. Additional validation: Auto mode end-to-end execution through all 5 stages.
8. Error handling and edge cases (400 on invalid state/extension, 404 on nonexistent job).
"""

import io
import os
import sys
import wave
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
from dashboard.api.database import Base, get_db, VideoJob
from dashboard.api.models import JobStatus


class TestDashboardFullFlow(unittest.TestCase):
    """
    Full Flow E2E Automated Verification for AutoVideoFactory Dashboard.
    Runs deterministically in test isolation with real database sessions,
    genuine pipeline data structures, and filesystem assertions.
    """

    @classmethod
    def setUpClass(cls):
        cls.created_job_ids: List[str] = []
        cls.uploaded_voice_files: List[str] = []

        # 1. Create isolated temporary directory and SQLite database
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = Path(cls.temp_dir.name) / "test_flow.db"
        cls.test_engine = create_engine(
            f"sqlite:///{cls.test_db_path}",
            connect_args={"check_same_thread": False, "timeout": 30}
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.test_engine)
        Base.metadata.create_all(bind=cls.test_engine)

        # 2. Backup original session makers and engine
        cls._orig_db_engine = db_mod.engine
        cls._orig_db_session = db_mod.SessionLocal
        cls._orig_jobs_session = jobs_route_mod.SessionLocal
        cls._orig_worker_session = video_tasks_mod.SessionLocal

        # 3. Patch SessionLocal across database, route, and worker modules
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

        # Shared step_by_step job ID for sequential flow tests
        cls.step_job_id: str = None

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

        # 2. Clean up uploaded voice files
        for vf in cls.uploaded_voice_files:
            vp = Path("assets/voices") / vf
            if vp.exists():
                try:
                    vp.unlink()
                except Exception:
                    pass

        # 3. Restore original dependencies and sessions
        app.dependency_overrides.clear()
        db_mod.engine = cls._orig_db_engine
        db_mod.SessionLocal = cls._orig_db_session
        jobs_route_mod.SessionLocal = cls._orig_jobs_session
        video_tasks_mod.SessionLocal = cls._orig_worker_session

        # 4. Dispose engine and cleanup temp directory
        try:
            cls.test_engine.dispose()
        except Exception:
            pass
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    @classmethod
    def _create_step_by_step_job(cls) -> str:
        """Helper to create and initialize a step_by_step job up to assets_ready."""
        payload = {
            "topic": "Khám phá bí ẩn hố đen vũ trụ",
            "style": "collage_broll",
            "language": "vi",
            "format": "shorts",
            "quality": "standard",
            "mode": "step_by_step",
            "art_style": "photorealistic",
            "voice_preset": "default"
        }
        res = cls.client.post("/jobs", json=payload)
        assert res.status_code == 200, f"Failed creating step_by_step job: {res.text}"
        data = res.json()
        job_id = data["id"]
        cls.created_job_ids.append(job_id)
        return job_id

    # =========================================================================
    # TEST 1: Step-by-Step Mode Job Creation, Halted Stage & Pipeline Data Audit
    # =========================================================================
    def test_01_create_job_step_by_step_mode(self):
        """
        Test 1:
        Create job via POST /jobs with mode="step_by_step", art_style="photorealistic", voice_preset="default".
        - Confirm response code 200, valid job_id.
        - Query GET /jobs/{job_id}, verify job halted at stage="assets_ready" and status is JobStatus.processing.
        - Verify pipeline_data contains script with scenes, voice with scenes, and storyboard with
          image_path, tier_used, vision_gate_score, vision_gate_reasoning.
        """
        payload = {
            "topic": "Khám phá bí ẩn hố đen vũ trụ",
            "style": "collage_broll",
            "language": "vi",
            "format": "shorts",
            "quality": "standard",
            "mode": "step_by_step",
            "art_style": "photorealistic",
            "voice_preset": "default"
        }

        # 1.1 POST /jobs
        res = self.client.post("/jobs", json=payload)
        self.assertEqual(res.status_code, 200, f"Expected 200, got {res.status_code}: {res.text}")
        data = res.json()
        self.assertIn("id", data)
        job_id = data["id"]
        self.assertTrue(bool(job_id), "job_id must be non-empty string")
        self.assertEqual(data["mode"], "step_by_step")
        self.assertEqual(data["art_style"], "photorealistic")
        self.assertEqual(data["voice_preset"], "default")

        # Save for subsequent tests
        TestDashboardFullFlow.step_job_id = job_id
        TestDashboardFullFlow.created_job_ids.append(job_id)

        # 1.2 GET /jobs/{job_id} after synchronous background task completion
        res_job = self.client.get(f"/jobs/{job_id}")
        self.assertEqual(res_job.status_code, 200)
        job_info = res_job.json()

        # Verify halted at stage="assets_ready" and status is processing
        self.assertEqual(job_info["stage"], "assets_ready", f"Expected stage 'assets_ready', got '{job_info['stage']}'")
        self.assertEqual(job_info["status"], "processing", f"Expected status 'processing', got '{job_info['status']}'")

        # 1.3 Verify pipeline_data structure
        self.assertIn("pipeline_data", job_info)
        p_data = job_info["pipeline_data"]
        self.assertIsInstance(p_data, dict, "pipeline_data must be a dictionary")

        # Script audit
        self.assertIn("script", p_data, "pipeline_data must contain 'script'")
        script_data = p_data["script"]
        self.assertIsInstance(script_data, dict)
        self.assertTrue(bool(script_data.get("title")), "script must contain non-empty title")
        self.assertIn("scenes", script_data, "script must contain 'scenes'")
        self.assertIsInstance(script_data["scenes"], list)
        self.assertGreater(len(script_data["scenes"]), 0, "script['scenes'] must not be empty")

        for sc in script_data["scenes"]:
            self.assertIn("narration", sc)
            self.assertIn("duration", sc)

        # Voice audit
        self.assertIn("voice", p_data, "pipeline_data must contain 'voice'")
        voice_data = p_data["voice"]
        self.assertIsInstance(voice_data, dict)
        self.assertIn("engine", voice_data)
        self.assertIn("scenes", voice_data)
        self.assertIsInstance(voice_data["scenes"], list)
        self.assertGreater(len(voice_data["scenes"]), 0, "voice['scenes'] must not be empty")

        for vs in voice_data["scenes"]:
            self.assertIn("audio_path", vs)
            self.assertIn("duration", vs)
            audio_path = vs["audio_path"]
            self.assertTrue(Path(audio_path).exists(), f"Audio file not found on disk: {audio_path}")
            self.assertGreater(Path(audio_path).stat().st_size, 0, f"Audio file is empty: {audio_path}")

        # Storyboard audit
        self.assertIn("storyboard", p_data, "pipeline_data must contain 'storyboard'")
        storyboard = p_data["storyboard"]
        self.assertIsInstance(storyboard, list)
        self.assertGreater(len(storyboard), 0, "storyboard list must not be empty")

        for sb in storyboard:
            self.assertIn("scene_index", sb)
            self.assertIn("image_path", sb)
            self.assertIn("tier_used", sb)
            self.assertIn("vision_gate_score", sb)
            self.assertIn("vision_gate_reasoning", sb)

            # Assert image exists on disk and has valid content
            img_path = sb["image_path"]
            self.assertTrue(Path(img_path).exists(), f"Storyboard image not found on disk: {img_path}")
            self.assertGreater(Path(img_path).stat().st_size, 0, f"Storyboard image is empty: {img_path}")

            # Assert Vision Gate metrics
            score = float(sb["vision_gate_score"])
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
            self.assertTrue(bool(sb["vision_gate_reasoning"]), "vision_gate_reasoning must not be empty")

    # =========================================================================
    # TEST 2: Regenerate Scene Asset & Update Audit Trail
    # =========================================================================
    def test_02_regenerate_scene(self):
        """
        Test 2:
        Call POST /jobs/{job_id}/regenerate-scene with scene_index=0 and new prompt.
        - Confirm response 200.
        - Verify image is updated and new prompt is stored in pipeline_data["storyboard"][0].
        """
        job_id = TestDashboardFullFlow.step_job_id or self._create_step_by_step_job()
        new_prompt = "Hố đen vũ trụ nuốt chửng ánh sáng phong cách photorealistic 8K cinematic"

        regen_payload = {
            "scene_index": 0,
            "prompt": new_prompt
        }

        # 2.1 Call POST /jobs/{job_id}/regenerate-scene
        res_regen = self.client.post(f"/jobs/{job_id}/regenerate-scene", json=regen_payload)
        self.assertEqual(res_regen.status_code, 200, f"Expected 200, got {res_regen.status_code}: {res_regen.text}")
        data = res_regen.json()

        # 2.2 Verify updated pipeline_data from response and subsequent GET
        p_data = data.get("pipeline_data") or self.client.get(f"/jobs/{job_id}").json()["pipeline_data"]
        storyboard = p_data.get("storyboard", [])
        self.assertGreater(len(storyboard), 0)

        scene_0 = storyboard[0]
        # Check prompt stored
        stored_prompt = scene_0.get("visual_prompt") or scene_0.get("prompt", "")
        self.assertIn(new_prompt, stored_prompt, f"Expected new prompt in storyboard, got: {stored_prompt}")

        # Check image updated on disk
        img_path = scene_0.get("image_path")
        self.assertTrue(bool(img_path), "image_path must not be empty")
        self.assertTrue(Path(img_path).exists(), f"Regenerated image file not found on disk: {img_path}")
        self.assertGreater(Path(img_path).stat().st_size, 0, f"Regenerated image file is empty: {img_path}")

        # Vision Gate re-evaluated
        self.assertIn("vision_gate_score", scene_0)
        self.assertGreater(float(scene_0["vision_gate_score"]), 0.0)

    # =========================================================================
    # TEST 3: Upload Custom Scene Image
    # =========================================================================
    def test_03_upload_scene_image(self):
        """
        Test 3:
        Call POST /jobs/{job_id}/upload-scene-image with scene_index=0 and custom PNG image bytes.
        - Confirm response 200.
        - Verify image file is saved on disk.
        - Verify pipeline_data reflects the uploaded image path.
        """
        job_id = TestDashboardFullFlow.step_job_id or self._create_step_by_step_job()

        # 3.1 Create genuine in-memory 512x512 PNG image
        img_buf = io.BytesIO()
        test_img = Image.new("RGB", (512, 512), color=(40, 80, 160))
        test_img.save(img_buf, format="PNG")
        img_bytes = img_buf.getvalue()

        filename = "custom_uploaded_scene_0.png"

        # 3.2 Call POST /jobs/{job_id}/upload-scene-image
        res_upload = self.client.post(
            f"/jobs/{job_id}/upload-scene-image",
            data={"scene_index": 0},
            files={"file": (filename, img_bytes, "image/png")}
        )
        self.assertEqual(res_upload.status_code, 200, f"Expected 200, got {res_upload.status_code}: {res_upload.text}")
        data = res_upload.json()

        # 3.3 Verify pipeline_data
        p_data = data.get("pipeline_data") or self.client.get(f"/jobs/{job_id}").json()["pipeline_data"]
        storyboard = p_data.get("storyboard", [])
        self.assertGreater(len(storyboard), 0)

        scene_0 = storyboard[0]
        uploaded_path = scene_0.get("image_path", "")
        self.assertTrue(bool(uploaded_path), "Uploaded image path must be present in storyboard")
        self.assertTrue(
            "uploaded" in uploaded_path or filename in uploaded_path,
            f"Image path should indicate uploaded asset: {uploaded_path}"
        )

        # 3.4 Verify file exists on disk and is non-empty
        self.assertTrue(Path(uploaded_path).exists(), f"Uploaded file not found on disk: {uploaded_path}")
        disk_size = Path(uploaded_path).stat().st_size
        self.assertGreater(disk_size, 0, "Uploaded file on disk must not be empty")

        # 3.5 Verify tier_used and vision gate audit reflect user upload
        self.assertEqual(scene_0.get("tier_used"), "user_uploaded")
        self.assertEqual(float(scene_0.get("vision_gate_score", 0)), 1.0)

    # =========================================================================
    # TEST 4: Continue Render & Pipeline Transition to Done
    # =========================================================================
    def test_04_continue_render(self):
        """
        Test 4:
        Call POST /jobs/{job_id}/continue-render with job_id.
        - Confirm response 200.
        - Verify background execution transitions job through rendering to stage="done" and status=JobStatus.done.
        - Verify output_path points to valid final_video.mp4 on disk.
        """
        job_id = TestDashboardFullFlow.step_job_id or self._create_step_by_step_job()

        # Ensure job is at stage assets_ready before continue-render
        current_job = self.client.get(f"/jobs/{job_id}").json()
        self.assertEqual(current_job["stage"], "assets_ready")

        # 4.1 Call POST /jobs/{job_id}/continue-render
        res_continue = self.client.post(f"/jobs/{job_id}/continue-render", json={"job_id": job_id})
        self.assertEqual(res_continue.status_code, 200, f"Expected 200, got {res_continue.status_code}: {res_continue.text}")

        # 4.2 Query GET /jobs/{job_id} to verify completion
        res_done = self.client.get(f"/jobs/{job_id}")
        self.assertEqual(res_done.status_code, 200)
        done_info = res_done.json()

        # Verify state transitions to stage="done" and status="done"
        self.assertEqual(done_info["stage"], "done", f"Expected stage 'done', got '{done_info['stage']}'")
        self.assertEqual(done_info["status"], "done", f"Expected status 'done', got '{done_info['status']}'")

        # 4.3 Verify output_path points to valid final_video.mp4 on disk
        output_path = done_info.get("output_path")
        self.assertTrue(bool(output_path), "output_path must not be empty when job is done")
        self.assertTrue(output_path.endswith("final_video.mp4"), f"output_path should end with final_video.mp4: {output_path}")

        video_path = Path(output_path)
        self.assertTrue(video_path.exists(), f"Final video file not found on disk: {video_path}")
        self.assertGreater(video_path.stat().st_size, 0, f"Final video file is 0 bytes: {video_path}")

        # 4.4 Verify Stage 4 FFmpeg commands recorded in pipeline_data
        p_data = done_info.get("pipeline_data", {})
        self.assertIn("ffmpeg_commands", p_data)
        ffmpeg_cmds = p_data["ffmpeg_commands"]
        self.assertIsInstance(ffmpeg_cmds, list)
        self.assertGreater(len(ffmpeg_cmds), 0, "ffmpeg_commands list must not be empty")

        # 4.5 Verify that the user uploaded image from Test 3 was resolved for video rendering (Requirement 2)
        sb_img = p_data.get("storyboard", [{}])[0].get("image_path", "")
        if "uploaded" in sb_img:
            scenes = p_data.get("scenes", [])
            if scenes:
                self.assertEqual(scenes[0].get("image_path"), sb_img, "Scene image must be resolved to uploaded storyboard image")

    # =========================================================================
    # TEST 5: Export Full Project ZIP Package
    # =========================================================================
    def test_05_export_zip(self):
        """
        Test 5:
        Call GET /jobs/{job_id}/export-zip.
        - Confirm response 200 and Content-Type application/zip.
        - Inspect zip archive using zipfile.ZipFile: verify it is a valid zip archive
          containing script, media files, and video assets.
        """
        job_id = TestDashboardFullFlow.step_job_id
        if not job_id:
            job_id = self._create_step_by_step_job()
            self.client.post(f"/jobs/{job_id}/continue-render", json={"job_id": job_id})
        else:
            job_info = self.client.get(f"/jobs/{job_id}").json()
            if job_info.get("stage") != "done":
                self.client.post(f"/jobs/{job_id}/continue-render", json={"job_id": job_id})

        # 5.1 Call GET /jobs/{job_id}/export-zip
        res_zip = self.client.get(f"/jobs/{job_id}/export-zip")
        self.assertEqual(res_zip.status_code, 200, f"Expected 200, got {res_zip.status_code}")
        content_type = res_zip.headers.get("content-type", "")
        self.assertIn("application/zip", content_type, f"Expected application/zip header, got {content_type}")

        # 5.2 Inspect zip archive structure
        zip_bytes = io.BytesIO(res_zip.content)
        with zipfile.ZipFile(zip_bytes, "r") as zf:
            # Check CRC integrity
            corrupted = zf.testzip()
            self.assertIsNone(corrupted, f"Zip archive has corrupted file: {corrupted}")

            file_list = zf.namelist()
            self.assertGreater(len(file_list), 0, "Exported zip archive must contain files")

            # Verify presence of script file (script.json or project_info.json)
            has_script = any(f.endswith(".json") or "script" in f.lower() for f in file_list)
            self.assertTrue(has_script, f"Zip archive missing script/json metadata. Files: {file_list}")

            # Verify presence of media files (images or audio)
            has_images = any(f.endswith((".png", ".jpg", ".jpeg", ".webp")) for f in file_list)
            has_audio = any(f.endswith((".wav", ".mp3")) for f in file_list)
            self.assertTrue(has_images or has_audio, f"Zip archive missing media files. Files: {file_list}")

            # Verify presence of video file (final_video.mp4 or .mp4)
            has_video = any(f.endswith(".mp4") for f in file_list)
            self.assertTrue(has_video, f"Zip archive missing video (.mp4) assets. Files: {file_list}")

    # =========================================================================
    # TEST 6: Voice Management Endpoints (GET /voices, POST /voices/upload)
    # =========================================================================
    def test_06_voice_management_endpoints(self):
        """
        Test 6:
        Call GET /voices and POST /voices/upload to verify voice management endpoints.
        - GET /voices returns 200 and list of available presets including 'default'.
        - POST /voices/upload accepts valid .wav file and persists it in assets/voices/.
        - Subsequent GET /voices reflects the newly uploaded voice file.
        """
        # 6.1 GET /voices
        res_voices = self.client.get("/voices")
        self.assertEqual(res_voices.status_code, 200)
        data = res_voices.json()
        self.assertIn("voices", data)
        self.assertIsInstance(data["voices"], list)
        self.assertIn("default", data["voices"])

        # 6.2 POST /voices/upload
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 4000)
        wav_bytes = wav_buf.getvalue()

        test_voice_name = "test_custom_m4_preset.wav"
        TestDashboardFullFlow.uploaded_voice_files.append(test_voice_name)

        res_upload = self.client.post(
            "/voices/upload",
            files={"file": (test_voice_name, wav_bytes, "audio/wav")}
        )
        self.assertEqual(res_upload.status_code, 200, f"Expected 200, got {res_upload.status_code}: {res_upload.text}")
        upload_data = res_upload.json()
        self.assertEqual(upload_data.get("status"), "success")
        self.assertEqual(upload_data.get("filename"), test_voice_name)

        # 6.3 Verify file persisted on disk
        saved_voice_path = Path("assets/voices") / test_voice_name
        self.assertTrue(saved_voice_path.exists(), f"Uploaded voice file not found at {saved_voice_path}")

        # 6.4 GET /voices reflects new voice
        res_voices_after = self.client.get("/voices")
        self.assertEqual(res_voices_after.status_code, 200)
        voices_list = res_voices_after.json().get("voices", [])
        self.assertIn(test_voice_name, voices_list)

    # =========================================================================
    # TEST 7: Auto Pipeline Mode End-to-End Execution
    # =========================================================================
    def test_07_auto_pipeline_mode_flow(self):
        """
        Test 7:
        Create job with mode="auto" to verify continuous execution across all 5 stages
        straight to stage="done" and status=JobStatus.done without halting.
        """
        auto_payload = {
            "topic": "Sự hình thành hệ Mặt Trời",
            "style": "collage_broll",
            "language": "vi",
            "format": "shorts",
            "quality": "standard",
            "mode": "auto",
            "art_style": "cinematic_3d",
            "voice_preset": "default"
        }

        res = self.client.post("/jobs", json=auto_payload)
        self.assertEqual(res.status_code, 200)
        job_id = res.json()["id"]
        TestDashboardFullFlow.created_job_ids.append(job_id)

        # In TestClient, BackgroundTasks complete before POST returns
        res_job = self.client.get(f"/jobs/{job_id}")
        self.assertEqual(res_job.status_code, 200)
        job_info = res_job.json()

        # In auto mode, job must finish completely at done
        self.assertEqual(job_info["stage"], "done")
        self.assertEqual(job_info["status"], "done")
        self.assertTrue(bool(job_info.get("output_path")))
        self.assertTrue(Path(job_info["output_path"]).exists())

    # =========================================================================
    # TEST 8: Error Handling, HTTP 400 Validation & HTTP 404 Nonexistent Endpoints
    # =========================================================================
    def test_08_error_handling_and_validation(self):
        """
        Test 8:
        Verify error responses for invalid state transitions and non-existent IDs:
        - Continue render when not in assets_ready returns 400.
        - Nonexistent job IDs return 404 on GET, regenerate, upload, continue-render, export-zip.
        - Upload voice with invalid file extension returns 400.
        - Upload scene image with invalid file extension returns 400.
        """
        # 8.1 Continue render on already done job returns 400
        done_job_id = self._create_step_by_step_job()
        self.client.post(f"/jobs/{done_job_id}/continue-render", json={"job_id": done_job_id})

        res_invalid_continue = self.client.post(f"/jobs/{done_job_id}/continue-render", json={"job_id": done_job_id})
        self.assertEqual(res_invalid_continue.status_code, 400, "Should return 400 when continuing a job not in assets_ready")

        # 8.2 Nonexistent job ID returns 404
        fake_id = "nonexistent-job-uuid-0000"
        self.assertEqual(self.client.get(f"/jobs/{fake_id}").status_code, 404)
        self.assertEqual(
            self.client.post(f"/jobs/{fake_id}/regenerate-scene", json={"scene_index": 0, "prompt": "foo"}).status_code,
            404
        )
        self.assertEqual(
            self.client.post(
                f"/jobs/{fake_id}/upload-scene-image",
                data={"scene_index": 0},
                files={"file": ("img.png", b"\x89PNG\r\n\x1a\n", "image/png")}
            ).status_code,
            404
        )
        self.assertEqual(
            self.client.post(f"/jobs/{fake_id}/continue-render", json={"job_id": fake_id}).status_code,
            404
        )
        self.assertEqual(self.client.get(f"/jobs/{fake_id}/export-zip").status_code, 404)

        # 8.3 Upload voice with invalid extension returns 400
        res_bad_voice = self.client.post(
            "/voices/upload",
            files={"file": ("invalid_voice.exe", b"binary", "application/octet-stream")}
        )
        self.assertEqual(res_bad_voice.status_code, 400)

        # 8.4 Upload scene image with invalid extension returns 400
        res_bad_img = self.client.post(
            f"/jobs/{done_job_id}/upload-scene-image",
            data={"scene_index": 0},
            files={"file": ("document.pdf", b"%PDF", "application/pdf")}
        )
        self.assertEqual(res_bad_img.status_code, 400)


if __name__ == "__main__":
    unittest.main()
