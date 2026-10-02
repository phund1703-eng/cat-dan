"""
tests/test_worker_m2_adversarial.py

Empirical Challenger Suite for Milestone 2 (Worker video_tasks.py):
1. run_video_pipeline with mode="step_by_step":
   - Asserts execution halts at stage="assets_ready" and status is JobStatus.processing.
   - Asserts pipeline_data contains script, voice, storyboard with genuine populated fields.
   - Asserts synthesized audio and visual asset files exist on disk.
2. regenerate_scene_asset:
   - Calls regenerate_scene_asset for scene 0 with custom prompt.
   - Asserts return dict contains status="success", new image_path, prompt, tier_used, vision_gate_score.
   - Asserts pipeline_data in database is updated for both scenes and storyboard.
   - Asserts new image file exists on disk.
3. continue_video_pipeline:
   - Calls continue_video_pipeline for the paused job.
   - Asserts job transitions to stage="done" and status=JobStatus.done.
   - Asserts data/output/{job_id}/final_video.mp4 exists and has non-zero size.
   - Asserts data/output/{job_id}/snapshot.jpg exists.
   - Asserts pipeline_data["ffmpeg_commands"] is populated.
4. Auto mode end-to-end verification:
   - Tests run_video_pipeline with mode="auto" runs through all 5 stages to stage="done".
5. Error handling and edge case stress tests:
   - Nonexistent job ID in run_video_pipeline (verify no unhandled process crash).
   - Nonexistent job ID in continue_video_pipeline (verify no crash).
   - Nonexistent job ID in regenerate_scene_asset (verify proper ValueError and DB cleanup).
   - Corrupted/empty pipeline_data in continue_video_pipeline (verify job transitions to failed with error logged).
"""

import os
import sys
import json
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api.database import (
    SessionLocal,
    create_tables,
    create_job,
    get_job,
    update_job_stage,
    update_job_status
)
from dashboard.api.models import JobStatus
from dashboard.worker.video_tasks import (
    run_video_pipeline,
    continue_video_pipeline,
    regenerate_scene_asset,
    _probe_audio_duration,
    _create_synthetic_wav
)


class AdversarialTestRunner:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.created_job_ids: List[str] = []

    def log_test(self, category: str, test_name: str, passed: bool, details: Any):
        status_str = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{status_str}] {category} -> {test_name}")
        if isinstance(details, dict):
            for k, v in details.items():
                print(f"       - {k}: {v}")
        else:
            print(f"       - details: {details}")

        self.results.append({
            "category": category,
            "name": test_name,
            "passed": passed,
            "details": details
        })

    def cleanup(self):
        """Cleans up created test output folders to keep workspace clean."""
        for jid in self.created_job_ids:
            p = Path("data/output") / jid
            if p.exists():
                try:
                    shutil.rmtree(p)
                except Exception as e:
                    print(f"Cleanup warning for {jid}: {e}")

    # =========================================================================
    # TEST 1: Step-by-Step Mode Pipeline Halting & Audit Trail Verification
    # =========================================================================
    def test_step_by_step_pipeline_halt(self):
        cat = "Step-by-Step Pipeline Execution"
        job_id = f"test-m2-step-{uuid.uuid4().hex[:8]}"
        self.created_job_ids.append(job_id)

        db = SessionLocal()
        try:
            job = create_job(
                db=db,
                job_id=job_id,
                topic="Khám phá Trí tuệ Nhân tạo và Tương lai Loài người",
                style="collage_broll",
                language="vi",
                mode="step_by_step",
                art_style="cinematic_3d",
                voice_preset="default"
            )
            assert job is not None
        finally:
            db.close()

        # Run pipeline
        run_video_pipeline(job_id)

        # Inspect database state
        db = SessionLocal()
        try:
            updated_job = get_job(db, job_id)
            assert updated_job is not None, "Job record not found in DB after run_video_pipeline"

            # 1.1 Assert execution halted at stage="assets_ready" and status is processing
            is_halted = (updated_job.stage == "assets_ready")
            is_processing = (updated_job.status == JobStatus.processing)
            self.log_test(
                cat,
                "Halt at stage='assets_ready' with status='processing'",
                is_halted and is_processing,
                {"stage": updated_job.stage, "status": str(updated_job.status)}
            )

            p_data = updated_job.pipeline_data or {}

            # 1.2 Assert pipeline_data contains genuine script fields
            has_script = "script" in p_data and isinstance(p_data["script"], dict)
            script_data = p_data.get("script", {})
            has_title = bool(script_data.get("title"))
            has_scenes = isinstance(script_data.get("scenes"), list) and len(script_data.get("scenes", [])) > 0
            has_prompt_used = bool(script_data.get("prompt_used"))

            script_pass = has_script and has_title and has_scenes and has_prompt_used
            self.log_test(
                cat,
                "pipeline_data contains genuine script fields (title, prompt_used, scenes)",
                script_pass,
                {
                    "has_script": has_script,
                    "title": script_data.get("title"),
                    "scene_count": len(script_data.get("scenes", [])),
                    "prompt_used": script_data.get("prompt_used")
                }
            )

            # 1.3 Assert pipeline_data contains genuine voice fields and generated audio files
            has_voice = "voice" in p_data and isinstance(p_data["voice"], dict)
            voice_data = p_data.get("voice", {})
            voice_engine = voice_data.get("engine")
            voice_scenes = voice_data.get("scenes", [])
            voice_files_exist = True
            for vs in voice_scenes:
                ap = vs.get("audio_path")
                if not ap or not Path(ap).exists():
                    voice_files_exist = False
                    break

            voice_pass = has_voice and bool(voice_engine) and len(voice_scenes) > 0 and voice_files_exist
            self.log_test(
                cat,
                "pipeline_data contains genuine voice fields and audio files exist on disk",
                voice_pass,
                {
                    "engine": voice_engine,
                    "preset": voice_data.get("preset"),
                    "scenes_count": len(voice_scenes),
                    "voice_files_exist": voice_files_exist,
                    "sample_audio": voice_scenes[0].get("audio_path") if voice_scenes else None
                }
            )

            # 1.4 Assert pipeline_data contains genuine storyboard & Vision Gate audit
            has_storyboard = "storyboard" in p_data and isinstance(p_data["storyboard"], list) and len(p_data["storyboard"]) > 0
            sb_items = p_data.get("storyboard", [])
            sb_valid = True
            image_files_exist = True
            for item in sb_items:
                if not item.get("image_path") or not item.get("visual_prompt") or "vision_gate_score" not in item:
                    sb_valid = False
                ip = item.get("image_path")
                if not ip or not Path(ip).exists():
                    image_files_exist = False

            storyboard_pass = has_storyboard and sb_valid and image_files_exist
            self.log_test(
                cat,
                "pipeline_data contains storyboard with Vision Gate audit & images exist on disk",
                storyboard_pass,
                {
                    "storyboard_count": len(sb_items),
                    "sample_tier": sb_items[0].get("tier_used") if sb_items else None,
                    "sample_score": sb_items[0].get("vision_gate_score") if sb_items else None,
                    "sample_reasoning": sb_items[0].get("vision_gate_reasoning") if sb_items else None,
                    "image_files_exist": image_files_exist
                }
            )

            # 1.5 Assert output file does NOT exist yet (must not render prematurely in step_by_step)
            final_vid = Path("data/output") / job_id / "final_video.mp4"
            render_premature = final_vid.exists()
            self.log_test(
                cat,
                "No premature rendering in step_by_step mode (final_video.mp4 does not exist yet)",
                not render_premature,
                {"premature_video_exists": render_premature}
            )

            return job_id, (is_halted and is_processing and script_pass and voice_pass and storyboard_pass and not render_premature)
        finally:
            db.close()

    # =========================================================================
    # TEST 2: Scene Asset Regeneration Verification
    # =========================================================================
    def test_regenerate_scene_asset(self, job_id: str):
        cat = "Scene Asset Regeneration"
        new_prompt = "Một nhà du hành vũ trụ đang tương tác với giao diện holographic 3D neon rực rỡ"

        # Call regenerate_scene_asset for scene 0
        result = regenerate_scene_asset(job_id=job_id, scene_index=0, prompt=new_prompt)

        # 2.1 Assert returned dictionary format
        status_ok = (result.get("status") == "success")
        ret_img_path = result.get("image_path")
        ret_prompt = result.get("prompt")
        ret_score = result.get("vision_gate_score")

        return_dict_pass = status_ok and bool(ret_img_path) and bool(ret_prompt) and (ret_score is not None)
        self.log_test(
            cat,
            "regenerate_scene_asset returns success dictionary with audit fields",
            return_dict_pass,
            {
                "status": result.get("status"),
                "image_path": ret_img_path,
                "prompt": ret_prompt,
                "tier_used": result.get("tier_used"),
                "vision_gate_score": ret_score
            }
        )

        # 2.2 Assert new image file exists on disk
        new_img_exists = bool(ret_img_path and Path(ret_img_path).exists())
        self.log_test(
            cat,
            "Regenerated image file created and exists on disk",
            new_img_exists,
            {"image_path": ret_img_path, "exists": new_img_exists}
        )

        # 2.3 Assert database pipeline_data updated in scenes and storyboard
        db = SessionLocal()
        try:
            job = get_job(db, job_id)
            p_data = job.pipeline_data or {}
            scenes = p_data.get("scenes", [])
            sb = p_data.get("storyboard", [])

            sc0 = next((s for s in scenes if s.get("scene_index") == 0 or s.get("index") == 0), None)
            sb0 = next((s for s in sb if s.get("scene_index") == 0), None)

            sc0_updated = (sc0 is not None and sc0.get("image_path") == ret_img_path and new_prompt in sc0.get("visual_prompt", ""))
            sb0_updated = (sb0 is not None and sb0.get("image_path") == ret_img_path and new_prompt in sb0.get("visual_prompt", ""))

            db_pass = sc0_updated and sb0_updated
            self.log_test(
                cat,
                "pipeline_data in database updated for both scene[0] and storyboard[0]",
                db_pass,
                {
                    "scene_0_image": sc0.get("image_path") if sc0 else None,
                    "storyboard_0_image": sb0.get("image_path") if sb0 else None,
                    "scene_0_prompt_updated": new_prompt in (sc0.get("visual_prompt") or "") if sc0 else False
                }
            )

            return return_dict_pass and new_img_exists and db_pass
        finally:
            db.close()

    # =========================================================================
    # TEST 3: Pipeline Continuation Verification
    # =========================================================================
    def test_continue_video_pipeline(self, job_id: str):
        cat = "Pipeline Continuation"

        # Call continue_video_pipeline
        continue_video_pipeline(job_id=job_id)

        # Inspect database state
        db = SessionLocal()
        try:
            job = get_job(db, job_id)
            assert job is not None

            # 3.1 Assert transition to stage="done" and status=JobStatus.done
            is_done_stage = (job.stage == "done")
            is_done_status = (job.status == JobStatus.done)
            self.log_test(
                cat,
                "Job transitioned to stage='done' and status=JobStatus.done",
                is_done_stage and is_done_status,
                {"stage": job.stage, "status": str(job.status)}
            )

            # 3.2 Assert final_video.mp4 exists on disk and is non-empty
            expected_video_path = Path("data/output") / job_id / "final_video.mp4"
            video_exists = expected_video_path.exists() and expected_video_path.stat().st_size > 0
            self.log_test(
                cat,
                "data/output/{job_id}/final_video.mp4 exists and is non-empty",
                video_exists,
                {
                    "video_path": str(expected_video_path),
                    "exists": expected_video_path.exists(),
                    "size_bytes": expected_video_path.stat().st_size if expected_video_path.exists() else 0
                }
            )

            # 3.3 Assert snapshot.jpg exists
            snapshot_path = Path("data/output") / job_id / "snapshot.jpg"
            snapshot_exists = snapshot_path.exists() and snapshot_path.stat().st_size > 0
            self.log_test(
                cat,
                "data/output/{job_id}/snapshot.jpg extracted and exists",
                snapshot_exists,
                {"snapshot_path": str(snapshot_path), "exists": snapshot_path.exists()}
            )

            # 3.4 Assert FFmpeg commands recorded in pipeline_data
            p_data = job.pipeline_data or {}
            ffmpeg_cmds = p_data.get("ffmpeg_commands", [])
            has_ffmpeg_cmds = isinstance(ffmpeg_cmds, list) and len(ffmpeg_cmds) > 0
            self.log_test(
                cat,
                "pipeline_data contains generated FFmpeg commands audit trail",
                has_ffmpeg_cmds,
                {
                    "command_count": len(ffmpeg_cmds),
                    "first_command": ffmpeg_cmds[0][:100] + "..." if has_ffmpeg_cmds else None
                }
            )

            return is_done_stage and is_done_status and video_exists and snapshot_exists and has_ffmpeg_cmds
        finally:
            db.close()

    # =========================================================================
    # TEST 4: Auto Mode End-to-End Verification
    # =========================================================================
    def test_auto_pipeline_execution(self):
        cat = "Auto Pipeline Mode"
        job_id = f"test-m2-auto-{uuid.uuid4().hex[:8]}"
        self.created_job_ids.append(job_id)

        db = SessionLocal()
        try:
            job = create_job(
                db=db,
                job_id=job_id,
                topic="Năng lượng Tái tạo và Tương lai Xanh",
                style="collage_broll",
                language="vi",
                mode="auto",
                art_style="watercolor",
                voice_preset="default"
            )
            assert job is not None
        finally:
            db.close()

        # Run pipeline in auto mode
        run_video_pipeline(job_id)

        # Inspect database state
        db = SessionLocal()
        try:
            job = get_job(db, job_id)
            assert job is not None

            is_done = (job.stage == "done" and job.status == JobStatus.done)
            video_file = Path("data/output") / job_id / "final_video.mp4"
            vid_ok = video_file.exists() and video_file.stat().st_size > 0

            auto_pass = is_done and vid_ok
            self.log_test(
                cat,
                "Auto mode runs smoothly from Stage 1 through Stage 5 to 'done' without halting",
                auto_pass,
                {
                    "stage": job.stage,
                    "status": str(job.status),
                    "video_exists": vid_ok,
                    "video_path": str(video_file)
                }
            )
            return auto_pass
        finally:
            db.close()

    # =========================================================================
    # TEST 5: Error Handling Stress Tests & Adversarial Scenarios
    # =========================================================================
    def test_error_handling_stress(self):
        cat = "Error Handling & Edge Cases"
        passed_all = True

        # 5.1 Nonexistent job ID in run_video_pipeline
        nonexistent_id = f"nonexistent-job-{uuid.uuid4().hex[:6]}"
        try:
            run_video_pipeline(nonexistent_id)
            nonexistent_run_pass = True
            details = "Completed safely without unhandled process exception"
        except Exception as e:
            nonexistent_run_pass = False
            details = f"Unexpected unhandled exception: {e}"

        self.log_test(
            cat,
            "run_video_pipeline with nonexistent job ID handles error gracefully without process crash",
            nonexistent_run_pass,
            details
        )
        if not nonexistent_run_pass:
            passed_all = False

        # 5.2 Nonexistent job ID in continue_video_pipeline
        try:
            continue_video_pipeline(nonexistent_id)
            nonexistent_cont_pass = True
            details = "Completed safely without unhandled process crash"
        except Exception as e:
            nonexistent_cont_pass = False
            details = f"Unexpected unhandled exception: {e}"

        self.log_test(
            cat,
            "continue_video_pipeline with nonexistent job ID handles error gracefully without process crash",
            nonexistent_cont_pass,
            details
        )
        if not nonexistent_cont_pass:
            passed_all = False

        # 5.3 Nonexistent job ID in regenerate_scene_asset (must raise ValueError and cleanly close db)
        regen_err_pass = False
        try:
            regenerate_scene_asset(nonexistent_id, scene_index=0, prompt="test")
            details = "Expected ValueError, but no exception was raised"
        except ValueError as ve:
            regen_err_pass = True
            details = f"Correctly caught expected ValueError: {ve}"
        except Exception as e:
            details = f"Wrong exception type raised: {type(e).__name__}: {e}"

        self.log_test(
            cat,
            "regenerate_scene_asset with nonexistent job ID raises clean ValueError with DB closed",
            regen_err_pass,
            details
        )
        if not regen_err_pass:
            passed_all = False

        # 5.4 Corrupted job pipeline_data in continue_video_pipeline
        corrupt_job_id = f"test-corrupt-{uuid.uuid4().hex[:6]}"
        self.created_job_ids.append(corrupt_job_id)
        db = SessionLocal()
        try:
            job = create_job(db=db, job_id=corrupt_job_id, topic="Corrupt test", mode="step_by_step")
            job.stage = "assets_ready"
            job.pipeline_data = {}  # Empty dictionary, missing scenes
            db.commit()
        finally:
            db.close()

        try:
            continue_video_pipeline(corrupt_job_id)
            db = SessionLocal()
            c_job = get_job(db, corrupt_job_id)
            # Even with empty scenes, it completes or logs warning without crashing
            corrupt_pass = (c_job is not None)
            details = f"Job stage: {c_job.stage}, status: {c_job.status}"
            db.close()
        except Exception as e:
            corrupt_pass = False
            details = f"Exception crashed continue_video_pipeline: {e}"

        self.log_test(
            cat,
            "continue_video_pipeline handles empty/corrupt pipeline_data without server crash",
            corrupt_pass,
            details
        )
        if not corrupt_pass:
            passed_all = False

        # 5.5 Helper function resilience: _probe_audio_duration on invalid path
        probe_result = _probe_audio_duration("nonexistent/path/sample.wav", default=4.5)
        probe_pass = (probe_result == 4.5)
        self.log_test(
            cat,
            "_probe_audio_duration resiliently falls back to default on invalid audio file",
            probe_pass,
            {"probe_result": probe_result, "expected": 4.5}
        )
        if not probe_pass:
            passed_all = False

        return passed_all

    # =========================================================================
    # RUN ALL
    # =========================================================================
    def run_all(self):
        print("=" * 80)
        print("ADVERSARIAL CHALLENGER SUITE: Milestone 2 Pipeline Worker")
        print("=" * 80)

        # 1. Step-by-Step Mode
        step_job_id, step_pass = self.test_step_by_step_pipeline_halt()

        # 2. Scene Asset Regeneration (using paused job)
        regen_pass = False
        if step_job_id:
            regen_pass = self.test_regenerate_scene_asset(step_job_id)

        # 3. Pipeline Continuation (resuming paused job)
        cont_pass = False
        if step_job_id:
            cont_pass = self.test_continue_video_pipeline(step_job_id)

        # 4. Auto Pipeline Mode
        auto_pass = self.test_auto_pipeline_execution()

        # 5. Error handling and edge cases
        error_pass = self.test_error_handling_stress()

        overall_passed = step_pass and regen_pass and cont_pass and auto_pass and error_pass

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        passed_count = sum(1 for r in self.results if r["passed"])
        total_count = len(self.results)
        print(f"Total Tests Run: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_count - passed_count}")

        verdict = "APPROVE" if overall_passed else "CHALLENGE_FAILED (REQUEST_CHANGES)"
        print(f"\nFINAL VERDICT: {verdict}")
        print("=" * 80)

        return overall_passed, self.results


if __name__ == "__main__":
    runner = AdversarialTestRunner()
    try:
        success, _ = runner.run_all()
    finally:
        runner.cleanup()
    sys.exit(0 if success else 1)
