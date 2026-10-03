"""
test_adversarial_m1_api.py
Automated Adversarial Stress-Test Suite for Milestone 1 Backend API Endpoints.

Tests:
1. POST /jobs: Invalid/corner-case inputs (invalid mode, missing fields, large payloads, unicode, invalid enums).
2. POST /jobs/{job_id}/regenerate-scene: Non-existent jobs, negative/large scene indices, empty/large prompts.
3. POST /jobs/{job_id}/upload-scene-image: Non-existent jobs, non-image files, empty files, invalid indices.
4. POST /jobs/{job_id}/continue-render: Non-existent jobs, stage != 'assets_ready' vs stage == 'assets_ready'.
5. GET /jobs/{job_id}/export-zip: Non-existent jobs, empty job directory vs populated directory.
6. POST /voices/upload: Valid .wav/.mp3 vs non-audio files (.txt, .exe, .png) and empty filenames.
7. Verification of graceful HTTP status codes (400, 404, 422) vs unhandled 500 crashes.
"""

import os
import io
import sys
import uuid
import zipfile
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Any, List

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from dashboard.api.main import app
from dashboard.api.database import SessionLocal, get_job, update_job_stage, create_job
from dashboard.api.models import JobStatus

class TestCaseResult:
    def __init__(self, category: str, name: str, passed: bool, status_code: int, expected_codes: List[int], details: str = ""):
        self.category = category
        self.name = name
        self.passed = passed
        self.status_code = status_code
        self.expected_codes = expected_codes
        self.details = details

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] [{self.category}] {self.name} -> HTTP {self.status_code} (Expected {self.expected_codes}): {self.details}"

class AdversarialAPITester:
    def __init__(self):
        self.client = TestClient(app)
        self.results: List[TestCaseResult] = []

    def record(self, category: str, name: str, passed: bool, status_code: int, expected_codes: List[int], details: str = ""):
        res = TestCaseResult(category, name, passed, status_code, expected_codes, details)
        self.results.append(res)
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] [{category}] {name} -> HTTP {status_code} (Expected {expected_codes}) | {details}")

    # =========================================================================
    # 1. Job Creation Edge Cases (POST /jobs)
    # =========================================================================
    def test_job_creation_corner_cases(self):
        cat = "POST /jobs"

        # 1.1 Missing required field: topic
        r = self.client.post("/jobs", json={
            "style": "collage_broll",
            "language": "vi"
        })
        passed = (r.status_code == 422)
        self.record(cat, "missing_topic_field", passed, r.status_code, [422], "Should return 422 for missing required field 'topic'")

        # 1.2 Missing required field: style
        r = self.client.post("/jobs", json={
            "topic": "History of Rome",
            "language": "vi"
        })
        passed = (r.status_code == 422)
        self.record(cat, "missing_style_field", passed, r.status_code, [422], "Should return 422 for missing required field 'style'")

        # 1.3 Completely empty payload
        r = self.client.post("/jobs", json={})
        passed = (r.status_code == 422)
        self.record(cat, "empty_json_body", passed, r.status_code, [422], "Should return 422 for empty payload")

        # 1.4 Invalid enum value for style
        r = self.client.post("/jobs", json={
            "topic": "Quantum Computing",
            "style": "non_existent_style_xyz",
            "language": "vi"
        })
        passed = (r.status_code == 422)
        self.record(cat, "invalid_style_enum", passed, r.status_code, [422], "Should return 422 for unknown style enum")

        # 1.5 Invalid enum value for language
        r = self.client.post("/jobs", json={
            "topic": "Quantum Computing",
            "style": "collage_broll",
            "language": "klingon"
        })
        passed = (r.status_code == 422)
        self.record(cat, "invalid_language_enum", passed, r.status_code, [422], "Should return 422 for unknown language enum")

        # 1.6 Invalid mode: mode='invalid' (Checking behavior: does it crash or return 400/422/200?)
        r = self.client.post("/jobs", json={
            "topic": "Black Holes",
            "style": "collage_broll",
            "language": "en",
            "mode": "invalid_mode_value_123"
        })
        # If mode is unconstrained string in model, it returns 200 without crashing (or 422 if validated)
        # It must NOT return 500
        passed = (r.status_code in [200, 400, 422])
        self.record(cat, "invalid_mode_string", passed, r.status_code, [200, 400, 422], 
                    f"Invalid mode accepted without 500 crash. Status: {r.status_code}")

        # 1.7 Extremely large payload (100k characters topic)
        large_topic = "Topic_" + ("A" * 100000)
        r = self.client.post("/jobs", json={
            "topic": large_topic,
            "style": "collage_broll",
            "language": "vi"
        })
        passed = (r.status_code in [200, 400, 413, 422])
        self.record(cat, "large_topic_100k_chars", passed, r.status_code, [200, 400, 413, 422],
                    f"100k char topic handled gracefully without 500 crash. Status: {r.status_code}")

        # 1.8 Unicode, emojis, and special injection strings
        tricky_topic = "🚀 Lịch sử Việt Nam & ' OR '1'='1; -- <script>alert(1)</script>"
        r = self.client.post("/jobs", json={
            "topic": tricky_topic,
            "style": "collage_broll",
            "language": "vi"
        })
        passed = (r.status_code == 200)
        self.record(cat, "unicode_emojis_sql_injection_topic", passed, r.status_code, [200],
                    f"Special characters in topic handled safely. Status: {r.status_code}")

    # =========================================================================
    # 2. Regenerate Scene (POST /jobs/{job_id}/regenerate-scene)
    # =========================================================================
    def test_regenerate_scene_corner_cases(self):
        cat = "POST /jobs/{job_id}/regenerate-scene"

        # 2.1 Non-existent job
        non_existent_id = str(uuid.uuid4())
        r = self.client.post(f"/jobs/{non_existent_id}/regenerate-scene", json={
            "scene_index": 0,
            "prompt": "New visual prompt"
        })
        passed = (r.status_code == 404)
        self.record(cat, "non_existent_job_id", passed, r.status_code, [404],
                    f"Non-existent job returns 404. Detail: {r.json() if r.status_code == 404 else r.text}")

        # Create a valid test job for remaining scene tests
        cr_res = self.client.post("/jobs", json={
            "topic": "Test Scene Regeneration",
            "style": "collage_broll",
            "language": "vi",
            "mode": "step_by_step"
        })
        test_job_id = cr_res.json()["id"]

        # 2.2 Missing required prompt in request body
        r = self.client.post(f"/jobs/{test_job_id}/regenerate-scene", json={
            "scene_index": 0
        })
        passed = (r.status_code == 422)
        self.record(cat, "missing_prompt_field", passed, r.status_code, [422],
                    "Missing prompt returns 422 Unprocessable Entity")

        # 2.3 Invalid scene index: negative scene_index (-1)
        r = self.client.post(f"/jobs/{test_job_id}/regenerate-scene", json={
            "scene_index": -1,
            "prompt": "Regenerate negative scene"
        })
        # Should gracefully respond (200 or 400), not crash with 500
        passed = (r.status_code in [200, 400, 422])
        self.record(cat, "negative_scene_index", passed, r.status_code, [200, 400, 422],
                    f"Negative scene index handled without 500 crash. Status: {r.status_code}")

        # 2.4 Very large scene index (999999)
        r = self.client.post(f"/jobs/{test_job_id}/regenerate-scene", json={
            "scene_index": 999999,
            "prompt": "Regenerate huge index scene"
        })
        passed = (r.status_code in [200, 400, 422])
        self.record(cat, "huge_scene_index", passed, r.status_code, [200, 400, 422],
                    f"Large scene index handled without 500 crash. Status: {r.status_code}")

        # 2.5 Empty prompt string
        r = self.client.post(f"/jobs/{test_job_id}/regenerate-scene", json={
            "scene_index": 0,
            "prompt": ""
        })
        passed = (r.status_code in [200, 400, 422])
        self.record(cat, "empty_prompt_string", passed, r.status_code, [200, 400, 422],
                    f"Empty prompt string handled without 500 crash. Status: {r.status_code}")

        # 2.6 Extremely long prompt string (50k characters)
        r = self.client.post(f"/jobs/{test_job_id}/regenerate-scene", json={
            "scene_index": 0,
            "prompt": "A" * 50000
        })
        passed = (r.status_code in [200, 400, 413, 422])
        self.record(cat, "extremely_long_prompt", passed, r.status_code, [200, 400, 413, 422],
                    f"50k character prompt handled without 500 crash. Status: {r.status_code}")

    # =========================================================================
    # 3. Upload Scene Image (POST /jobs/{job_id}/upload-scene-image)
    # =========================================================================
    def test_upload_scene_image_corner_cases(self):
        cat = "POST /jobs/{job_id}/upload-scene-image"

        # 3.1 Non-existent job
        non_existent_id = str(uuid.uuid4())
        fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")
        r = self.client.post(
            f"/jobs/{non_existent_id}/upload-scene-image",
            data={"scene_index": 0},
            files={"file": ("test.png", fake_png, "image/png")}
        )
        passed = (r.status_code == 404)
        self.record(cat, "non_existent_job_id", passed, r.status_code, [404],
                    f"Non-existent job returns 404. Detail: {r.json() if r.status_code == 404 else r.text}")

        # Create a valid test job
        cr_res = self.client.post("/jobs", json={
            "topic": "Test Scene Upload",
            "style": "collage_broll",
            "language": "vi",
            "mode": "step_by_step"
        })
        test_job_id = cr_res.json()["id"]

        # 3.2 Valid image upload (.png)
        valid_png = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82")
        r = self.client.post(
            f"/jobs/{test_job_id}/upload-scene-image",
            data={"scene_index": 0},
            files={"file": ("valid_sample.png", valid_png, "image/png")}
        )
        passed = (r.status_code == 200)
        self.record(cat, "valid_png_upload", passed, r.status_code, [200],
                    f"Valid PNG upload returns 200 OK. Status: {r.status_code}")

        # 3.3 Non-image file: text file (.txt)
        txt_file = io.BytesIO(b"This is a plain text file, not an image.")
        r = self.client.post(
            f"/jobs/{test_job_id}/upload-scene-image",
            data={"scene_index": 0},
            files={"file": ("malicious_script.txt", txt_file, "text/plain")}
        )
        # An image upload endpoint should reject non-images with 400 Bad Request
        # If it returns 200 without validation, we flag it as vulnerability/flaw
        passed = (r.status_code == 400)
        self.record(cat, "non_image_txt_upload", passed, r.status_code, [400],
                    f"Non-image text file should be rejected with 400. Got: {r.status_code}")

        # 3.4 Non-image file: executable / binary script (.exe)
        exe_file = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00fake executable content")
        r = self.client.post(
            f"/jobs/{test_job_id}/upload-scene-image",
            data={"scene_index": 0},
            files={"file": ("exploit.exe", exe_file, "application/octet-stream")}
        )
        passed = (r.status_code == 400)
        self.record(cat, "non_image_exe_upload", passed, r.status_code, [400],
                    f"Non-image .exe upload should be rejected with 400. Got: {r.status_code}")

        # 3.5 Negative scene index (-1)
        valid_png2 = io.BytesIO(b"\x89PNG\r\n\x1a\nfake image")
        r = self.client.post(
            f"/jobs/{test_job_id}/upload-scene-image",
            data={"scene_index": -1},
            files={"file": ("scene_neg.png", valid_png2, "image/png")}
        )
        passed = (r.status_code in [200, 400, 422])
        self.record(cat, "negative_scene_index", passed, r.status_code, [200, 400, 422],
                    f"Negative scene index handled without 500 crash. Status: {r.status_code}")

        # 3.6 Missing file upload
        r = self.client.post(
            f"/jobs/{test_job_id}/upload-scene-image",
            data={"scene_index": 0}
        )
        passed = (r.status_code == 422)
        self.record(cat, "missing_file_parameter", passed, r.status_code, [422],
                    "Missing file returns 422 Unprocessable Entity")

        # 3.7 Missing scene_index parameter
        valid_png3 = io.BytesIO(b"\x89PNG\r\n\x1a\nfake image")
        r = self.client.post(
            f"/jobs/{test_job_id}/upload-scene-image",
            files={"file": ("test.png", valid_png3, "image/png")}
        )
        passed = (r.status_code == 422)
        self.record(cat, "missing_scene_index_parameter", passed, r.status_code, [422],
                    "Missing scene_index returns 422 Unprocessable Entity")

    # =========================================================================
    # 4. Continue Render (POST /jobs/{job_id}/continue-render)
    # =========================================================================
    def test_continue_render_corner_cases(self):
        cat = "POST /jobs/{job_id}/continue-render"

        # 4.1 Non-existent job
        non_existent_id = str(uuid.uuid4())
        r = self.client.post(f"/jobs/{non_existent_id}/continue-render")
        passed = (r.status_code == 404)
        self.record(cat, "non_existent_job_id", passed, r.status_code, [404],
                    f"Non-existent job returns 404. Detail: {r.json() if r.status_code == 404 else r.text}")

        # Create a new job (initial stage is 'pending')
        cr_res = self.client.post("/jobs", json={
            "topic": "Test Continue Render",
            "style": "collage_broll",
            "language": "vi",
            "mode": "step_by_step"
        })
        test_job_id = cr_res.json()["id"]

        # 4.2 Calling continue-render when job is NOT in 'assets_ready' (stage='pending')
        r = self.client.post(f"/jobs/{test_job_id}/continue-render")
        passed = (r.status_code == 400)
        self.record(cat, "stage_not_assets_ready_pending", passed, r.status_code, [400],
                    f"Job not in 'assets_ready' returns 400. Response: {r.json() if r.status_code == 400 else r.text}")

        # 4.3 Manually update job to 'failed' stage and test continue-render
        db = SessionLocal()
        try:
            update_job_stage(db, test_job_id, stage="failed", status=JobStatus.failed, error="Previous error")
        finally:
            db.close()

        r = self.client.post(f"/jobs/{test_job_id}/continue-render")
        passed = (r.status_code == 400)
        self.record(cat, "stage_not_assets_ready_failed", passed, r.status_code, [400],
                    f"Failed job returns 400 on continue-render. Status: {r.status_code}")

        # 4.4 Update job stage to 'assets_ready' and test continue-render
        db = SessionLocal()
        try:
            update_job_stage(db, test_job_id, stage="assets_ready", status=JobStatus.processing)
        finally:
            db.close()

        r = self.client.post(f"/jobs/{test_job_id}/continue-render")
        passed = (r.status_code == 200)
        self.record(cat, "stage_is_assets_ready_success", passed, r.status_code, [200],
                    f"Calling continue-render on 'assets_ready' transitions to rendering (200 OK). Status: {r.status_code}")

    # =========================================================================
    # 5. Export ZIP (GET /jobs/{job_id}/export-zip)
    # =========================================================================
    def test_export_zip_corner_cases(self):
        cat = "GET /jobs/{job_id}/export-zip"

        # 5.1 Non-existent job
        non_existent_id = str(uuid.uuid4())
        r = self.client.get(f"/jobs/{non_existent_id}/export-zip")
        passed = (r.status_code == 404)
        self.record(cat, "non_existent_job_id", passed, r.status_code, [404],
                    f"Non-existent job returns 404. Detail: {r.json() if r.status_code == 404 else r.text}")

        # Create a new job
        cr_res = self.client.post("/jobs", json={
            "topic": "Test Zip Export",
            "style": "collage_broll",
            "language": "vi",
            "mode": "auto"
        })
        test_job_id = cr_res.json()["id"]

        # 5.2 Empty job directory export (Verify it creates a valid zip containing project_info.json)
        # Ensure job directory is cleaned/empty
        job_dir = Path("data") / "output" / test_job_id
        if job_dir.exists():
            for f in job_dir.glob("**/*"):
                if f.is_file():
                    try:
                        f.unlink()
                    except Exception:
                        pass

        r = self.client.get(f"/jobs/{test_job_id}/export-zip")
        is_zip = False
        has_project_info = False
        if r.status_code == 200:
            try:
                zip_bytes = io.BytesIO(r.content)
                with zipfile.ZipFile(zip_bytes, "r") as zf:
                    is_zip = True
                    has_project_info = "project_info.json" in zf.namelist()
            except Exception as e:
                is_zip = False

        passed = (r.status_code == 200 and is_zip and has_project_info)
        self.record(cat, "empty_job_dir_export_zip", passed, r.status_code, [200],
                    f"Empty dir returns valid zip containing project_info.json: is_zip={is_zip}, has_json={has_project_info}")

        # 5.3 Populated job directory export
        job_dir.mkdir(parents=True, exist_ok=True)
        sample_img = job_dir / "scene_0.png"
        sample_audio = job_dir / "scene_0.wav"
        sample_img.write_bytes(b"\x89PNG\r\n\x1a\nTEST_IMAGE")
        sample_audio.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt TEST_AUDIO")

        r = self.client.get(f"/jobs/{test_job_id}/export-zip")
        is_zip = False
        namelist = []
        if r.status_code == 200:
            try:
                zip_bytes = io.BytesIO(r.content)
                with zipfile.ZipFile(zip_bytes, "r") as zf:
                    is_zip = True
                    namelist = zf.namelist()
            except Exception as e:
                is_zip = False

        has_files = ("scene_0.png" in namelist or "scene_0.png" in [os.path.basename(n) for n in namelist])
        passed = (r.status_code == 200 and is_zip and has_files)
        self.record(cat, "populated_job_dir_export_zip", passed, r.status_code, [200],
                    f"Populated dir returns valid zip with files: is_zip={is_zip}, namelist={namelist}")

    # =========================================================================
    # 6. Voices Upload (POST /voices/upload)
    # =========================================================================
    def test_voices_upload_corner_cases(self):
        cat = "POST /voices/upload"

        # 6.1 Valid .wav upload
        wav_content = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        wav_file = io.BytesIO(wav_content)
        r = self.client.post("/voices/upload", files={"file": ("test_voice_sample.wav", wav_file, "audio/wav")})
        passed = (r.status_code == 200 and r.json().get("status") == "success")
        self.record(cat, "valid_wav_upload", passed, r.status_code, [200],
                    f"Valid .wav upload returns 200 OK. Response: {r.json() if r.status_code == 200 else r.text}")

        # 6.2 Valid .mp3 upload
        mp3_content = b"\xff\xfb\x90d\x00\x00\x00\x00\x00\x00\x00\x00"
        mp3_file = io.BytesIO(mp3_content)
        r = self.client.post("/voices/upload", files={"file": ("test_voice_sample.mp3", mp3_file, "audio/mpeg")})
        passed = (r.status_code == 200 and r.json().get("status") == "success")
        self.record(cat, "valid_mp3_upload", passed, r.status_code, [200],
                    f"Valid .mp3 upload returns 200 OK. Response: {r.json() if r.status_code == 200 else r.text}")

        # 6.3 Non-audio file: text file (.txt)
        txt_file = io.BytesIO(b"Hello world, not a voice file")
        r = self.client.post("/voices/upload", files={"file": ("notes.txt", txt_file, "text/plain")})
        passed = (r.status_code == 400)
        self.record(cat, "non_audio_txt_upload", passed, r.status_code, [400],
                    f"Non-audio .txt upload rejected with 400 Bad Request. Detail: {r.json() if r.status_code == 400 else r.text}")

        # 6.4 Non-audio file: image file (.png)
        png_file = io.BytesIO(b"\x89PNG\r\n\x1a\nFake PNG")
        r = self.client.post("/voices/upload", files={"file": ("image.png", png_file, "image/png")})
        passed = (r.status_code == 400)
        self.record(cat, "non_audio_png_upload", passed, r.status_code, [400],
                    f"Non-audio .png upload rejected with 400 Bad Request. Detail: {r.json() if r.status_code == 400 else r.text}")

        # 6.5 Non-audio file: executable (.exe)
        exe_file = io.BytesIO(b"MZ\x90\x00\x03fake exe")
        r = self.client.post("/voices/upload", files={"file": ("malware.exe", exe_file, "application/octet-stream")})
        passed = (r.status_code == 400)
        self.record(cat, "non_audio_exe_upload", passed, r.status_code, [400],
                    f"Non-audio .exe upload rejected with 400 Bad Request. Detail: {r.json() if r.status_code == 400 else r.text}")

        # 6.6 Empty filename
        empty_name_file = io.BytesIO(b"dummy")
        r = self.client.post("/voices/upload", files={"file": ("", empty_name_file, "application/octet-stream")})
        passed = (r.status_code in [400, 422])
        self.record(cat, "empty_filename_upload", passed, r.status_code, [400, 422],
                    f"Empty filename rejected with 400/422. Detail: {r.json() if r.status_code in [400, 422] else r.text}")

    # =========================================================================
    # 7. Additional Endpoints Robustness Check
    # =========================================================================
    def test_other_endpoints_robustness(self):
        cat = "ADDITIONAL /jobs endpoints"

        # 7.1 GET /jobs/{job_id} with non-existent id
        non_existent_id = str(uuid.uuid4())
        r = self.client.get(f"/jobs/{non_existent_id}")
        passed = (r.status_code == 404)
        self.record(cat, "get_non_existent_job", passed, r.status_code, [404],
                    f"Non-existent job returns 404: {r.json() if r.status_code == 404 else r.text}")

        # 7.2 GET /jobs/{job_id}/preview when output video is not ready
        cr_res = self.client.post("/jobs", json={
            "topic": "Test Preview 404",
            "style": "collage_broll",
            "language": "vi",
            "mode": "step_by_step"
        })
        job_id = cr_res.json()["id"]
        # Clear any output_path in DB to test preview 404
        db = SessionLocal()
        try:
            job = get_job(db, job_id)
            if job:
                job.output_path = None
                db.commit()
        finally:
            db.close()

        # If preview not ready, should return 404, not 500
        r = self.client.get(f"/jobs/{job_id}/preview")
        passed = (r.status_code == 404)
        self.record(cat, "preview_video_not_ready_returns_404", passed, r.status_code, [404],
                    f"Preview not ready returns 404: {r.json() if r.status_code == 404 else r.text}")

        # 7.3 PUT /jobs/{job_id}/reject on non-existent job
        r = self.client.put(f"/jobs/{non_existent_id}/reject")
        passed = (r.status_code == 404)
        self.record(cat, "reject_non_existent_job", passed, r.status_code, [404],
                    f"Reject non-existent job returns 404: {r.json() if r.status_code == 404 else r.text}")

        # 7.4 DELETE /jobs/{job_id} on non-existent job
        r = self.client.delete(f"/jobs/{non_existent_id}")
        passed = (r.status_code == 404)
        self.record(cat, "delete_non_existent_job", passed, r.status_code, [404],
                    f"Delete non-existent job returns 404: {r.json() if r.status_code == 404 else r.text}")

    def run_all(self) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("RUNNING ADVERSARIAL STRESS-TEST SUITE FOR MILESTONE 1 BACKEND API")
        print("="*80 + "\n")

        self.test_job_creation_corner_cases()
        print("-" * 80)
        self.test_regenerate_scene_corner_cases()
        print("-" * 80)
        self.test_upload_scene_image_corner_cases()
        print("-" * 80)
        self.test_continue_render_corner_cases()
        print("-" * 80)
        self.test_export_zip_corner_cases()
        print("-" * 80)
        self.test_voices_upload_corner_cases()
        print("-" * 80)
        self.test_other_endpoints_robustness()

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        failures = [r for r in self.results if not r.passed]

        print("\n" + "="*80)
        print(f"TEST SUITE COMPLETE: {passed}/{total} Passed ({round(passed/total*100, 1)}%)")
        print(f"FAILED TESTS: {failed}")
        for f in failures:
            print(f"  [FAIL] [{f.category}] {f.name} -> Got HTTP {f.status_code}, expected {f.expected_codes}. Details: {f.details}")
        print("="*80 + "\n")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "failures": failures
        }

if __name__ == "__main__":
    tester = AdversarialAPITester()
    summary = tester.run_all()
    if summary["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
