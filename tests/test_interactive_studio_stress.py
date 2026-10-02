"""
tests/test_interactive_studio_stress.py

Adversarial Stress Test Suite for AutoVideoFactory 5-Stage Studio API Endpoints:
1. 404 on non-existent job_id across all 10 step endpoints + 3 legacy endpoints.
2. 400 on negative scene_index (< 0) and out-of-range scene_index on scene endpoints.
3. Single-scene mutation isolation: updating scene 1 audio or image modifies ONLY scene 1,
   leaving scene 0 and scene 2 completely intact.
4. Dynamic chunked ASS generation in /step/effects:
   - TikTok 9:16 resolution (1080x1920)
   - MarginV = 180 (safe zone)
   - FontSize = 44
   - 2-4 words per chunk invariant
   - Alternating styles (TikTokYellow / TikTokWhite)
5. Zip export in /export-zip:
   - Valid application/zip FileResponse
   - Proper extraction structure
   - Empty folder project_info.json fallback
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

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard.api.main import app
from dashboard.api.database import Base, get_db, VideoJob, create_job, get_job, update_job_stage
from dashboard.api.models import JobStatus
from core.render_engine.subtitle_generator import SubtitleGenerator


class TestInteractiveStudioStress(unittest.TestCase):
    """
    Exhaustive empirical stress tests for dashboard/api/routes/jobs.py step endpoints.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "test_studio_stress.db")
        cls.engine = create_engine(
            f"sqlite:///{cls.test_db_path}",
            connect_args={"check_same_thread": False}
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.engine
        )
        Base.metadata.create_all(bind=cls.engine)

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
        app.dependency_overrides.clear()
        cls.temp_dir.cleanup()

    def _create_mock_3_scene_job(self, job_id: str) -> VideoJob:
        """Helper to create a fully initialized 3-scene job in database."""
        db = self.TestingSessionLocal()
        try:
            job = create_job(
                db=db,
                job_id=job_id,
                topic="Hệ miễn dịch và tế bào bạch cầu",
                style="collage_broll",
                language="vi",
                mode="step_by_step",
                art_style="photorealistic",
                voice_preset="default",
                stage="script_ready"
            )

            job_dir = Path("data/output") / job_id
            (job_dir / "audio").mkdir(parents=True, exist_ok=True)
            (job_dir / "images").mkdir(parents=True, exist_ok=True)

            p_data = {
                "script": {
                    "title": "Hệ miễn dịch",
                    "description": "Video khoa học",
                    "hashtags": ["#science", "#biology"],
                    "scenes": [
                        {"index": 0, "narration": "Cảnh 0: Bạch cầu phát hiện vi khuẩn lạ.", "duration": 4.0, "image_path": f"data/output/{job_id}/images/scene_000.png"},
                        {"index": 1, "narration": "Cảnh 1: Kháng thể được tiết ra để vô hiệu hóa.", "duration": 4.5, "image_path": f"data/output/{job_id}/images/scene_001.png"},
                        {"index": 2, "narration": "Cảnh 2: Tế bào ghi nhớ lưu trữ thông tin mầm bệnh.", "duration": 5.0, "image_path": f"data/output/{job_id}/images/scene_002.png"}
                    ]
                },
                "scenes": [
                    {"scene_index": 0, "index": 0, "narration": "Cảnh 0: Bạch cầu phát hiện vi khuẩn lạ.", "duration": 4.0, "audio_duration": 4.0, "audio_path": f"data/output/{job_id}/audio/scene_000.wav", "image_path": f"data/output/{job_id}/images/scene_000.png"},
                    {"scene_index": 1, "index": 1, "narration": "Cảnh 1: Kháng thể được tiết ra để vô hiệu hóa.", "duration": 4.5, "audio_duration": 4.5, "audio_path": f"data/output/{job_id}/audio/scene_001.wav", "image_path": f"data/output/{job_id}/images/scene_001.png"},
                    {"scene_index": 2, "index": 2, "narration": "Cảnh 2: Tế bào ghi nhớ lưu trữ thông tin mầm bệnh.", "duration": 5.0, "audio_duration": 5.0, "audio_path": f"data/output/{job_id}/audio/scene_002.wav", "image_path": f"data/output/{job_id}/images/scene_002.png"}
                ],
                "voice": {
                    "engine": "VieNeu-TTS",
                    "preset": "default",
                    "scenes": [
                        {"scene_index": 0, "text": "Cảnh 0: Bạch cầu phát hiện vi khuẩn lạ.", "audio_path": f"data/output/{job_id}/audio/scene_000.wav", "duration": 4.0},
                        {"scene_index": 1, "text": "Cảnh 1: Kháng thể được tiết ra để vô hiệu hóa.", "audio_path": f"data/output/{job_id}/audio/scene_001.wav", "duration": 4.5},
                        {"scene_index": 2, "text": "Cảnh 2: Tế bào ghi nhớ lưu trữ thông tin mầm bệnh.", "audio_path": f"data/output/{job_id}/audio/scene_002.wav", "duration": 5.0}
                    ]
                },
                "storyboard": [
                    {"scene_index": 0, "image_path": f"data/output/{job_id}/images/scene_000.png", "visual_prompt": "Scene 0 prompt", "tier_used": "tier1_imagen", "vision_gate_score": 0.91, "vision_gate_reasoning": "Scene 0 good"},
                    {"scene_index": 1, "image_path": f"data/output/{job_id}/images/scene_001.png", "visual_prompt": "Scene 1 prompt", "tier_used": "tier1_imagen", "vision_gate_score": 0.92, "vision_gate_reasoning": "Scene 1 good"},
                    {"scene_index": 2, "image_path": f"data/output/{job_id}/images/scene_002.png", "visual_prompt": "Scene 2 prompt", "tier_used": "tier1_imagen", "vision_gate_score": 0.93, "vision_gate_reasoning": "Scene 2 good"}
                ]
            }

            job = update_job_stage(db, job_id, stage="assets_ready", status=JobStatus.processing, pipeline_data=p_data)
            return job
        finally:
            db.close()

    # =========================================================================
    # 1. 404 VERIFICATION ACROSS ALL STEP ENDPOINTS
    # =========================================================================

    def test_01_all_step_endpoints_return_404_on_nonexistent_job(self):
        """Stress-test: Verify every step endpoint returns 404 on nonexistent job_id."""
        bogus_id = "nonexistent-job-uuid-0000"

        endpoints = [
            ("POST", f"/jobs/{bogus_id}/step/script", {"json": {"topic": "test"}}),
            ("PUT", f"/jobs/{bogus_id}/step/script", {"json": {"scenes": []}}),
            ("POST", f"/jobs/{bogus_id}/step/voice", {"json": {}}),
            ("POST", f"/jobs/{bogus_id}/step/voice-scene", {"json": {"scene_index": 0, "text": "test"}}),
            ("POST", f"/jobs/{bogus_id}/step/storyboard", {"json": {}}),
            ("POST", f"/jobs/{bogus_id}/step/regenerate-scene-image", {"json": {"scene_index": 0, "prompt": "test"}}),
            ("POST", f"/jobs/{bogus_id}/regenerate-scene", {"json": {"scene_index": 0, "prompt": "test"}}),
            ("POST", f"/jobs/{bogus_id}/step/upload-scene-image", {"data": {"scene_index": "0"}, "files": {"file": ("test.png", b"fake", "image/png")}}),
            ("POST", f"/jobs/{bogus_id}/upload-scene-image", {"data": {"scene_index": "0"}, "files": {"file": ("test.png", b"fake", "image/png")}}),
            ("POST", f"/jobs/{bogus_id}/step/effects", {"json": {}}),
            ("POST", f"/jobs/{bogus_id}/step/render", {"json": {}}),
            ("POST", f"/jobs/{bogus_id}/continue-render", {"json": {}}),
            ("GET", f"/jobs/{bogus_id}/export-zip", {})
        ]

        for method, url, kwargs in endpoints:
            with self.subTest(method=method, url=url):
                if method == "POST":
                    resp = self.client.post(url, **kwargs)
                elif method == "PUT":
                    resp = self.client.put(url, **kwargs)
                elif method == "GET":
                    resp = self.client.get(url, **kwargs)
                else:
                    self.fail(f"Unsupported method {method}")

                self.assertEqual(resp.status_code, 404, f"{method} {url} returned {resp.status_code}, expected 404. Body: {resp.text}")
                data = resp.json()
                self.assertIn("detail", data)
                self.assertIn("not found", data["detail"].lower())

    # =========================================================================
    # 2. 400 VERIFICATION ON NEGATIVE & OUT-OF-RANGE SCENE INDICES
    # =========================================================================

    def test_02_negative_scene_index_returns_400(self):
        """Stress-test: Verify scene_index < 0 returns 400 Bad Request."""
        job_id = "test-scene-bounds-01"
        self._create_mock_3_scene_job(job_id)

        # A. POST /step/voice-scene with negative index
        resp = self.client.post(
            f"/jobs/{job_id}/step/voice-scene",
            json={"scene_index": -1, "text": "Invalid negative scene"}
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400 for scene_index=-1, got {resp.status_code}: {resp.text}")

        # B. POST /step/regenerate-scene-image with negative index
        resp = self.client.post(
            f"/jobs/{job_id}/step/regenerate-scene-image",
            json={"scene_index": -5, "prompt": "Invalid negative scene"}
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400 for scene_index=-5, got {resp.status_code}: {resp.text}")

        # C. POST /regenerate-scene (legacy) with negative index
        resp = self.client.post(
            f"/jobs/{job_id}/regenerate-scene",
            json={"scene_index": -1, "prompt": "Invalid negative scene"}
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400 for legacy scene_index=-1, got {resp.status_code}: {resp.text}")

        # D. POST /step/upload-scene-image with negative index
        fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimagecontent")
        resp = self.client.post(
            f"/jobs/{job_id}/step/upload-scene-image",
            data={"scene_index": "-1"},
            files={"file": ("custom.png", fake_png, "image/png")}
        )
        self.assertEqual(resp.status_code, 400, f"Expected 400 for upload scene_index=-1, got {resp.status_code}: {resp.text}")

    def test_03_out_of_range_scene_index_returns_400(self):
        """Stress-test: Verify scene_index >= len(scenes) returns 400 Bad Request."""
        job_id = "test-scene-bounds-02"
        self._create_mock_3_scene_job(job_id)  # has scenes 0, 1, 2

        out_of_range_indices = [3, 99, 1000]

        for idx in out_of_range_indices:
            with self.subTest(scene_index=idx):
                # Voice scene
                resp = self.client.post(
                    f"/jobs/{job_id}/step/voice-scene",
                    json={"scene_index": idx, "text": "Out of range"}
                )
                self.assertEqual(resp.status_code, 400, f"Expected 400 for voice scene_index={idx}, got {resp.status_code}: {resp.text}")

                # Regenerate scene image
                resp = self.client.post(
                    f"/jobs/{job_id}/step/regenerate-scene-image",
                    json={"scene_index": idx, "prompt": "Out of range prompt"}
                )
                self.assertEqual(resp.status_code, 400, f"Expected 400 for regen scene_index={idx}, got {resp.status_code}: {resp.text}")

                # Upload scene image
                fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimagecontent")
                resp = self.client.post(
                    f"/jobs/{job_id}/step/upload-scene-image",
                    data={"scene_index": str(idx)},
                    files={"file": ("custom.png", fake_png, "image/png")}
                )
                self.assertEqual(resp.status_code, 400, f"Expected 400 for upload scene_index={idx}, got {resp.status_code}: {resp.text}")

    # =========================================================================
    # 3. SINGLE-SCENE MUTATION ISOLATION
    # =========================================================================

    def test_04_single_scene_voice_mutation_isolation(self):
        """Stress-test: Modifying scene 1 voice leaves scene 0 and scene 2 completely untouched."""
        job_id = "test-mutation-voice-01"
        self._create_mock_3_scene_job(job_id)

        # Baseline snapshot
        db = self.TestingSessionLocal()
        job_before = get_job(db, job_id)
        p_data_before = json.loads(json.dumps(job_before.pipeline_data))
        db.close()

        scene0_before = p_data_before["scenes"][0]
        scene2_before = p_data_before["scenes"][2]
        scene1_before = p_data_before["scenes"][1]

        # Mutate ONLY scene 1
        new_text_1 = "Đột phá mới: Kháng thể đơn dòng trung hòa 99% tác nhân gây hại."
        resp = self.client.post(
            f"/jobs/{job_id}/step/voice-scene",
            json={"scene_index": 1, "text": new_text_1}
        )
        self.assertEqual(resp.status_code, 200, f"Voice mutation failed: {resp.text}")

        # Fetch state after mutation
        db = self.TestingSessionLocal()
        job_after = get_job(db, job_id)
        p_data_after = job_after.pipeline_data
        db.close()

        scene0_after = p_data_after["scenes"][0]
        scene1_after = p_data_after["scenes"][1]
        scene2_after = p_data_after["scenes"][2]

        # 1. Assert scene 1 DID change
        self.assertEqual(scene1_after["narration"], new_text_1)
        self.assertIn("scene_001.wav", scene1_after["audio_path"])

        # 2. Assert scene 0 is STRICTLY UNCHANGED
        self.assertEqual(scene0_after["narration"], scene0_before["narration"])
        self.assertEqual(scene0_after["audio_path"], scene0_before["audio_path"])
        self.assertEqual(scene0_after["duration"], scene0_before["duration"])

        # 3. Assert scene 2 is STRICTLY UNCHANGED
        self.assertEqual(scene2_after["narration"], scene2_before["narration"])
        self.assertEqual(scene2_after["audio_path"], scene2_before["audio_path"])
        self.assertEqual(scene2_after["duration"], scene2_before["duration"])

        # 4. Assert voice.scenes list also reflects strict isolation
        vscenes = p_data_after["voice"]["scenes"]
        self.assertEqual(vscenes[0]["text"], scene0_before["narration"])
        self.assertEqual(vscenes[1]["text"], new_text_1)
        self.assertEqual(vscenes[2]["text"], scene2_before["narration"])

    def test_05_single_scene_image_mutation_isolation(self):
        """Stress-test: Modifying scene 1 image via regen and upload leaves scene 0 & 2 untouched."""
        job_id = "test-mutation-image-01"
        self._create_mock_3_scene_job(job_id)

        # Baseline snapshot
        db = self.TestingSessionLocal()
        job_before = get_job(db, job_id)
        sb_before = json.loads(json.dumps(job_before.pipeline_data["storyboard"]))
        db.close()

        # Step A: Regenerate scene 1 image
        new_prompt_1 = "Microscopic view of antibody neutralizing viral protein, photorealistic 8k"
        resp = self.client.post(
            f"/jobs/{job_id}/step/regenerate-scene-image",
            json={"scene_index": 1, "prompt": new_prompt_1}
        )
        self.assertEqual(resp.status_code, 200, f"Regen failed: {resp.text}")

        db = self.TestingSessionLocal()
        job_after_regen = get_job(db, job_id)
        sb_after_regen = job_after_regen.pipeline_data["storyboard"]
        db.close()

        # Assert scene 1 updated, scene 0 & 2 untouched
        self.assertEqual(sb_after_regen[0]["visual_prompt"], sb_before[0]["visual_prompt"])
        self.assertEqual(sb_after_regen[0]["image_path"], sb_before[0]["image_path"])
        self.assertEqual(sb_after_regen[2]["visual_prompt"], sb_before[2]["visual_prompt"])
        self.assertEqual(sb_after_regen[2]["image_path"], sb_before[2]["image_path"])
        self.assertEqual(sb_after_regen[1]["visual_prompt"], new_prompt_1)
        self.assertIn("scene_1_regen.png", sb_after_regen[1]["image_path"])

        # Step B: Upload replacement image for scene 1
        fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\ncustomuploadedpngdata")
        resp = self.client.post(
            f"/jobs/{job_id}/step/upload-scene-image",
            data={"scene_index": "1"},
            files={"file": ("custom_white_blood_cell.png", fake_png, "image/png")}
        )
        self.assertEqual(resp.status_code, 200, f"Upload failed: {resp.text}")

        db = self.TestingSessionLocal()
        job_after_upload = get_job(db, job_id)
        sb_after_upload = job_after_upload.pipeline_data["storyboard"]
        db.close()

        # Assert scene 1 updated with uploaded path & score 1.0; scene 0 & 2 still intact
        self.assertEqual(sb_after_upload[0]["image_path"], sb_before[0]["image_path"])
        self.assertEqual(sb_after_upload[2]["image_path"], sb_before[2]["image_path"])
        self.assertIn("scene_1_uploaded.png", sb_after_upload[1]["image_path"])
        self.assertEqual(sb_after_upload[1]["vision_gate_score"], 1.0)
        self.assertEqual(sb_after_upload[1]["tier_used"], "user_uploaded")

    # =========================================================================
    # 4. DYNAMIC CHUNKED ASS GENERATION (2-4 WORDS, MARGIN 180 SAFE ZONE)
    # =========================================================================

    def test_06_dynamic_chunked_ass_generator_invariants(self):
        """Stress-test: SubtitleGenerator.generate_dynamic_chunked_ass 2-4 words grouping & safe zone."""
        test_sentences = [
            ("Một hai", 2),
            ("Một hai ba", 3),
            ("Một hai ba bốn", 4),  # should group into [4] because 1 leftover is merged
            ("Một hai ba bốn năm", 5),  # [3, 2]
            ("Một hai ba bốn năm sáu", 6),  # [3, 3]
            ("Một hai ba bốn năm sáu bảy", 7),  # [3, 4]
            ("Hệ miễn dịch của con người là một hệ thống phòng thủ vô cùng tinh vi và mạnh mẽ", 18)
        ]

        with tempfile.TemporaryDirectory() as temp_sub_dir:
            for sentence, word_count in test_sentences:
                with self.subTest(sentence=sentence, words=word_count):
                    out_path = Path(temp_sub_dir) / f"test_{word_count}.ass"
                    SubtitleGenerator.generate_dynamic_chunked_ass(
                        sentence=sentence,
                        duration=5.0,
                        output_path=out_path,
                        chunk_words=3,
                        margin_v=180,
                        font_size=44
                    )

                    self.assertTrue(out_path.exists())
                    content = out_path.read_text(encoding="utf-8")

                    # Invariant A: Header resolution
                    self.assertIn("PlayResX: 1080", content)
                    self.assertIn("PlayResY: 1920", content)

                    # Invariant B: Safe Zone MarginV = 180 & FontSize = 44
                    self.assertIn("TikTokYellow", content)
                    self.assertIn("TikTokWhite", content)
                    self.assertIn(",30,30,180,1", content, "MarginV must be exactly 180 in style definition")
                    self.assertIn(",44,", content, "Font size must be 44")

                    # Invariant C: 2-4 words per chunk
                    dialogue_lines = [line for line in content.splitlines() if line.startswith("Dialogue:")]
                    self.assertGreater(len(dialogue_lines), 0)

                    for d_line in dialogue_lines:
                        parts = d_line.split(",,")
                        text_part = parts[-1].strip()
                        chunk_words = text_part.split()
                        self.assertGreaterEqual(len(chunk_words), 2, f"Chunk has < 2 words: '{text_part}'")
                        self.assertLessEqual(len(chunk_words), 4, f"Chunk has > 4 words: '{text_part}'")

    def test_07_step_effects_endpoint_execution(self):
        """Stress-test: POST /jobs/{job_id}/step/effects produces ASS files, transitions stage, and generates FFmpeg cmds."""
        job_id = "test-effects-endpoint-01"
        self._create_mock_3_scene_job(job_id)

        resp = self.client.post(
            f"/jobs/{job_id}/step/effects",
            json={"chunk_words": 3, "margin_v": 180, "font_size": 44}
        )
        self.assertEqual(resp.status_code, 200, f"Effects failed: {resp.text}")
        data = resp.json()

        # Verify stage transitioned to rendering
        self.assertEqual(data["stage"], "rendering")

        # Verify pipeline_data structure
        p_data = data["pipeline_data"]
        self.assertIn("effects", p_data)
        self.assertEqual(p_data["effects"]["margin_v"], 180)
        self.assertEqual(p_data["effects"]["chunk_words"], 3)
        self.assertEqual(p_data["effects"]["font_size"], 44)

        # Verify ffmpeg_commands populated with zoompan & ass
        ffmpeg_cmds = p_data.get("ffmpeg_commands", [])
        self.assertGreaterEqual(len(ffmpeg_cmds), 3)
        for cmd in ffmpeg_cmds[:-1]:  # scene clips
            self.assertIn("zoompan=", cmd)
            self.assertIn("ass=", cmd)
            self.assertIn("scale=1080:1920", cmd)

        # Verify ass file on disk
        sub_file = Path("data/output") / job_id / "subtitles" / "scene_000.ass"
        self.assertTrue(sub_file.exists(), f"ASS file {sub_file} was not generated")
        ass_txt = sub_file.read_text(encoding="utf-8")
        self.assertIn(",30,30,180,1", ass_txt)

    # =========================================================================
    # 5. ZIP EXPORT VERIFICATION (/export-zip)
    # =========================================================================

    def test_08_export_zip_valid_archive(self):
        """Stress-test: GET /jobs/{job_id}/export-zip produces valid zip containing project files."""
        job_id = "test-export-zip-01"
        self._create_mock_3_scene_job(job_id)

        # Create dummy artifacts
        job_dir = Path("data/output") / job_id
        (job_dir / "script.json").write_text('{"title": "Test Zip"}', encoding="utf-8")
        (job_dir / "audio" / "scene_000.wav").write_bytes(b"RIFFWAVE_FAKE")
        (job_dir / "images" / "scene_000.png").write_bytes(b"\x89PNG_FAKE")

        resp = self.client.get(f"/jobs/{job_id}/export-zip")
        self.assertEqual(resp.status_code, 200, f"Export zip failed: {resp.text}")
        self.assertEqual(resp.headers["content-type"], "application/zip")
        self.assertIn(f"project_{job_id}.zip", resp.headers.get("content-disposition", ""))

        # Verify zip archive validity
        zip_bytes = io.BytesIO(resp.content)
        self.assertTrue(zipfile.is_zipfile(zip_bytes), "Response content is not a valid zip archive")

        with zipfile.ZipFile(zip_bytes, "r") as zf:
            namelist = zf.namelist()
            self.assertTrue(any("script.json" in name for name in namelist), f"script.json missing in {namelist}")
            self.assertTrue(any("scene_000.wav" in name for name in namelist), f"audio missing in {namelist}")
            self.assertTrue(any("scene_000.png" in name for name in namelist), f"images missing in {namelist}")

    def test_09_export_zip_empty_directory_fallback(self):
        """Stress-test: GET /export-zip on a job without output files embeds project_info.json."""
        job_id = "test-export-zip-empty"
        db = self.TestingSessionLocal()
        create_job(db=db, job_id=job_id, topic="Empty Topic", style="collage_broll", language="vi")
        db.close()

        # Ensure no output directory
        empty_dir = Path("data/output") / job_id
        if empty_dir.exists():
            shutil.rmtree(empty_dir)

        resp = self.client.get(f"/jobs/{job_id}/export-zip")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/zip")

        zip_bytes = io.BytesIO(resp.content)
        self.assertTrue(zipfile.is_zipfile(zip_bytes))

        with zipfile.ZipFile(zip_bytes, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("project_info.json", namelist)
            info = json.loads(zf.read("project_info.json").decode("utf-8"))
            self.assertEqual(info["id"], job_id)
            self.assertEqual(info["topic"], "Empty Topic")


if __name__ == "__main__":
    unittest.main()
