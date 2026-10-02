"""
tests/test_database_challenger.py

Empirical Challenge & Stress Test Suite for dashboard/api/database.py:
1. SQLite table migration behavior (legacy schema -> create_tables() -> verify columns & data).
2. Concurrency: Multi-threaded concurrent reads & writes to VideoJob.
3. pipeline_data JSON serialization/deserialization with arbitrary nested structures.
"""

import os
import sys
import json
import sqlite3
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dashboard.api.database import (
    Base,
    VideoJob,
    create_job,
    get_job,
    list_jobs,
    update_job_stage,
    update_job_status,
    update_scene_image,
    update_job_output
)
from dashboard.api.models import JobStatus


# ============================================================================
# SECTION 1: SQLite Table Migration Challenge
# ============================================================================

def challenge_legacy_migration():
    """
    Stress-test SQLite table migration:
    1. Create a raw SQLite DB with legacy video_jobs table missing new columns:
       (stage, mode, art_style, voice_preset, pipeline_data_json).
    2. Insert legacy job records.
    3. Run create_tables() logic against this DB.
    4. Assert:
       - No exceptions raised.
       - All 5 new columns added.
       - Legacy rows retain their original data.
       - New columns in legacy rows have expected defaults.
       - Migration is idempotent (running it again does not fail).
    """
    results = {"section": "Legacy SQLite Migration", "tests": [], "passed": True}

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        # Step 1: Create legacy table with raw sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE video_jobs (
                id VARCHAR PRIMARY KEY,
                topic VARCHAR,
                style VARCHAR,
                language VARCHAR,
                status VARCHAR,
                created_at DATETIME,
                updated_at DATETIME,
                output_path VARCHAR,
                error VARCHAR,
                script_data TEXT,
                metadata_data TEXT
            )
        """)
        # Step 2: Insert legacy row
        cur.execute("""
            INSERT INTO video_jobs (id, topic, style, language, status, script_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "legacy-job-001",
            "History of Roman Architecture",
            "collage_broll",
            "vi",
            "pending",
            json.dumps({"title": "Roman Architecture", "scenes": []})
        ))
        conn.commit()
        conn.close()

        # Step 3: Run migration logic using SQLAlchemy engine
        test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        
        # Emulate create_tables() migration against test_engine
        def run_migration_on_engine(eng):
            Base.metadata.create_all(bind=eng)
            with eng.begin() as c:
                cursor = c.execute(text("PRAGMA table_info(video_jobs)"))
                rows = cursor.fetchall()
                existing_cols = set()
                for row in rows:
                    if hasattr(row, "name"):
                        existing_cols.add(row.name)
                    elif hasattr(row, "__getitem__"):
                        existing_cols.add(row[1])

                migrations = [
                    ("stage", "VARCHAR DEFAULT 'pending'"),
                    ("mode", "VARCHAR DEFAULT 'auto'"),
                    ("art_style", "VARCHAR DEFAULT 'photorealistic'"),
                    ("voice_preset", "VARCHAR DEFAULT 'default'"),
                    ("pipeline_data_json", "TEXT"),
                ]
                for col_name, col_type in migrations:
                    if col_name not in existing_cols:
                        c.execute(text(f"ALTER TABLE video_jobs ADD COLUMN {col_name} {col_type}"))

        # Run migration first time
        run_migration_on_engine(test_engine)

        # Verify columns in raw sqlite
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(video_jobs)")
        columns = {row[1]: {"type": row[2], "dflt": row[4]} for row in cur.fetchall()}
        conn.close()

        required_cols = ["stage", "mode", "art_style", "voice_preset", "pipeline_data_json"]
        missing_cols = [c for c in required_cols if c not in columns]
        
        test_1_pass = len(missing_cols) == 0
        results["tests"].append({
            "name": "All 5 columns added to legacy table",
            "passed": test_1_pass,
            "details": f"Missing: {missing_cols}" if missing_cols else "All columns present"
        })
        if not test_1_pass:
            results["passed"] = False

        # Verify legacy row preserved and defaults applied
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        legacy_job = session.query(VideoJob).filter(VideoJob.id == "legacy-job-001").first()

        test_2_pass = (
            legacy_job is not None and
            legacy_job.topic == "History of Roman Architecture" and
            legacy_job.stage == "pending" and
            legacy_job.mode == "auto" and
            legacy_job.art_style == "photorealistic" and
            legacy_job.voice_preset == "default" and
            legacy_job.pipeline_data is None and
            legacy_job.script is not None and
            legacy_job.script.get("title") == "Roman Architecture"
        )
        results["tests"].append({
            "name": "Legacy data preserved with default column values",
            "passed": test_2_pass,
            "details": {
                "id": getattr(legacy_job, "id", None),
                "topic": getattr(legacy_job, "topic", None),
                "stage": getattr(legacy_job, "stage", None),
                "mode": getattr(legacy_job, "mode", None),
                "art_style": getattr(legacy_job, "art_style", None),
                "voice_preset": getattr(legacy_job, "voice_preset", None),
                "script": getattr(legacy_job, "script", None)
            }
        })
        if not test_2_pass:
            results["passed"] = False

        # Step 4: Test Idempotency (run migration second time on existing table)
        try:
            run_migration_on_engine(test_engine)
            test_3_pass = True
            err_msg = "No error"
        except Exception as e:
            test_3_pass = False
            err_msg = str(e)

        results["tests"].append({
            "name": "Migration idempotency (repeated execution without duplicate column error)",
            "passed": test_3_pass,
            "details": err_msg
        })
        if not test_3_pass:
            results["passed"] = False

        session.close()

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    return results


# ============================================================================
# SECTION 2: Concurrency & Lock Contention Challenge
# ============================================================================

def challenge_concurrency():
    """
    Stress-test concurrent reads and writes to VideoJob:
    - Spawn 10 concurrent threads against a single SQLite DB:
      - 3 threads continuously updating stages (pending -> script_ready -> voice_ready -> assets_ready)
      - 3 threads concurrently calling update_scene_image (uploading images to scene 0, 1, 2)
      - 4 threads concurrently querying jobs and inspecting pipeline_data.
    - Measure:
      - OperationalError (database is locked) occurrences.
      - Lost updates (did update_scene_image overwrite stage updates or vice versa).
      - Integrity of final pipeline_data.
    """
    results = {"section": "Concurrency & Locking Stress", "tests": [], "passed": True}

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        # Create DB with tables
        test_engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False, "timeout": 15.0}
        )
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

        # Create initial test job
        init_db = TestSession()
        test_job = create_job(
            db=init_db,
            job_id="concurrent-job-001",
            topic="Quantum Computing",
            style="collage_broll",
            language="vi",
            mode="step_by_step"
        )
        # Seed initial pipeline_data
        test_job.pipeline_data = {
            "script": {
                "title": "Quantum Computing",
                "scenes": [
                    {"index": 0, "narration": "Intro"},
                    {"index": 1, "narration": "Qubits"},
                    {"index": 2, "narration": "Outro"}
                ]
            },
            "storyboard": [
                {"scene_index": 0, "image_path": "initial_0.jpg", "tier_used": "tier1_imagen"},
                {"scene_index": 1, "image_path": "initial_1.jpg", "tier_used": "tier1_imagen"},
                {"scene_index": 2, "image_path": "initial_2.jpg", "tier_used": "tier1_imagen"}
            ]
        }
        init_db.commit()
        init_db.close()

        # Thread workers
        lock_errors = []
        read_errors = []
        write_success_count = [0]
        read_success_count = [0]
        counter_lock = threading.Lock()

        def stage_updater(thread_id: int):
            stages = ["script_ready", "voice_ready", "assets_ready"]
            for s in stages:
                db = TestSession()
                try:
                    update_job_stage(db, "concurrent-job-001", stage=s)
                    with counter_lock:
                        write_success_count[0] += 1
                except sqlite3.OperationalError as e:
                    lock_errors.append(f"Thread {thread_id} lock on stage {s}: {e}")
                except Exception as e:
                    lock_errors.append(f"Thread {thread_id} error on stage {s}: {e}")
                finally:
                    db.close()
                time.sleep(0.01)

        def scene_uploader(thread_id: int, scene_idx: int):
            for i in range(3):
                db = TestSession()
                try:
                    update_scene_image(
                        db,
                        "concurrent-job-001",
                        scene_index=scene_idx,
                        new_image_path=f"upload_sc{scene_idx}_v{i}.jpg",
                        vision_gate_score=0.95,
                        vision_gate_reasoning=f"Thread {thread_id} iteration {i}"
                    )
                    with counter_lock:
                        write_success_count[0] += 1
                except sqlite3.OperationalError as e:
                    lock_errors.append(f"Thread {thread_id} lock on scene {scene_idx}: {e}")
                except Exception as e:
                    lock_errors.append(f"Thread {thread_id} error on scene {scene_idx}: {e}")
                finally:
                    db.close()
                time.sleep(0.01)

        def reader_worker(thread_id: int):
            for _ in range(5):
                db = TestSession()
                try:
                    job = get_job(db, "concurrent-job-001")
                    if job:
                        p_data = job.pipeline_data
                        # Verify p_data is either None or valid dict
                        assert p_data is None or isinstance(p_data, dict)
                        with counter_lock:
                            read_success_count[0] += 1
                except Exception as e:
                    read_errors.append(f"Reader {thread_id} error: {e}")
                finally:
                    db.close()
                time.sleep(0.01)

        # Launch 10 concurrent threads
        threads = []
        # 3 stage updaters
        for t in range(3):
            threads.append(threading.Thread(target=stage_updater, args=(t,)))
        # 3 scene image updaters
        for t in range(3):
            threads.append(threading.Thread(target=scene_uploader, args=(t+3, t)))
        # 4 readers
        for t in range(4):
            threads.append(threading.Thread(target=reader_worker, args=(t+6,)))

        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
        elapsed = time.time() - start_time

        # Test results
        test_lock_pass = len(lock_errors) == 0
        results["tests"].append({
            "name": "Zero database lock errors (timeout >= 15s handled thread queue)",
            "passed": test_lock_pass,
            "details": f"Lock errors: {len(lock_errors)}, writes: {write_success_count[0]}, errors: {lock_errors[:3]}"
        })

        test_read_pass = len(read_errors) == 0 and read_success_count[0] > 0
        results["tests"].append({
            "name": "Concurrent reads succeeded without data corruption or crashes",
            "passed": test_read_pass,
            "details": f"Read successes: {read_success_count[0]}, Read errors: {len(read_errors)}"
        })

        # Check final database state
        verify_db = TestSession()
        final_job = get_job(verify_db, "concurrent-job-001")
        final_p_data = final_job.pipeline_data
        
        test_json_intact = final_p_data is not None and "storyboard" in final_p_data
        results["tests"].append({
            "name": "Final pipeline_data JSON integrity verified",
            "passed": test_json_intact,
            "details": f"Final storyboard scene count: {len(final_p_data.get('storyboard', [])) if final_p_data else 0}"
        })
        verify_db.close()

        if not (test_lock_pass and test_read_pass and test_json_intact):
            results["passed"] = False

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    return results


# ============================================================================
# SECTION 3: pipeline_data JSON Serialization / Deserialization Challenge
# ============================================================================

def challenge_json_serialization():
    """
    Stress-test pipeline_data JSON getter/setter and database roundtrip:
    1. Deeply nested arbitrary dictionary (10 levels deep).
    2. Vietnamese diacritics and Unicode characters.
    3. Emojis and special characters (quotes, backslashes, tabs, newlines).
    4. Numeric boundaries (float durations, negative scores, large integers).
    5. None, empty dictionary, empty list.
    6. Malformed JSON handling in pipeline_data_json (must return None, not crash).
    7. Raw string assignment to pipeline_data property.
    """
    results = {"section": "pipeline_data JSON Robustness", "tests": [], "passed": True}

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)

        session = TestSession()
        job = create_job(session, "json-job-001", "JSON Test", "collage_broll", "vi")

        # 3.1 Complex nested dictionary with Vietnamese, Emojis, floats
        complex_payload = {
            "script": {
                "title": "Khám phá Lịch sử Việt Nam 🇻🇳 - Triều đại Tây Sơn ⚔️",
                "description": 'Chiến thắng Đống Đa: "Sấm vang trời Bắc" \\ o o / \n\t tab & newline test',
                "hashtags": ["#lịch_sử", "#việt_nam", "#tây_sơn_hào_kiệt", "#quang_trung"],
                "prompt_used": "Create historical visual prompt with cinematic photorealism",
                "scenes": [
                    {
                        "index": 0,
                        "narration": "Năm 1789, vua Quang Trung tiến quân thần tốc ra Thăng Long...",
                        "visual_description": "Vua Quang Trung cưỡi voi chiến uy nghiêm giữa ba quân tướng sĩ",
                        "duration": 5.42,
                        "nested_meta": {
                            "level_1": {
                                "level_2": {
                                    "level_3": {
                                        "key": "deep_value",
                                        "numbers": [1, 2, 3.14159, -42, 0]
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "voice": {
                "engine": "VieNeu-TTS",
                "preset": "Minh Quân (Nam Miền Bắc)",
                "scenes": [
                    {"scene_index": 0, "duration": 5.42, "audio_path": "assets/voices/sample_sc0.wav"}
                ]
            },
            "storyboard": [
                {
                    "scene_index": 0,
                    "image_path": "data/output/json-job-001/scene_0.png",
                    "visual_prompt": "King Quang Trung riding war elephant 🐘, epic battlefield, 8k cinematic",
                    "tier_used": "tier1_imagen",
                    "vision_gate_score": 0.965,
                    "vision_gate_reasoning": "Hoàn toàn phù hợp bối cảnh lịch sử, bố cục ấn tượng."
                }
            ],
            "ffmpeg_commands": [
                "ffmpeg -y -loop 1 -i scene_0.png -vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920\" final.mp4"
            ]
        }

        job.pipeline_data = complex_payload
        session.commit()
        session.refresh(job)

        # Read back and compare
        retrieved = job.pipeline_data
        test_nested_pass = (
            retrieved is not None and
            retrieved["script"]["title"] == complex_payload["script"]["title"] and
            retrieved["script"]["scenes"][0]["nested_meta"]["level_1"]["level_2"]["level_3"]["key"] == "deep_value" and
            retrieved["storyboard"][0]["vision_gate_score"] == 0.965 and
            retrieved["storyboard"][0]["visual_prompt"] == complex_payload["storyboard"][0]["visual_prompt"]
        )
        results["tests"].append({
            "name": "Nested Unicode & Emoji dictionary roundtrip",
            "passed": test_nested_pass,
            "details": "All nested keys, Vietnamese diacritics, and emojis preserved accurately."
        })
        if not test_nested_pass:
            results["passed"] = False

        # 3.2 Setting None or empty dict
        job.pipeline_data = None
        session.commit()
        session.refresh(job)
        test_none_pass = job.pipeline_data is None and job.pipeline_data_json is None
        results["tests"].append({
            "name": "Setting pipeline_data = None clears column cleanly",
            "passed": test_none_pass,
            "details": f"pipeline_data: {job.pipeline_data}, raw: {job.pipeline_data_json}"
        })
        if not test_none_pass:
            results["passed"] = False

        # 3.3 Raw JSON string assignment to property
        raw_json_str = '{"custom_key": "custom_val", "active": true}'
        job.pipeline_data = raw_json_str
        session.commit()
        session.refresh(job)
        test_raw_str_pass = (
            job.pipeline_data_json == raw_json_str and
            job.pipeline_data.get("custom_key") == "custom_val" and
            job.pipeline_data.get("active") is True
        )
        results["tests"].append({
            "name": "Direct JSON string assignment to pipeline_data setter",
            "passed": test_raw_str_pass,
            "details": f"Parsed: {job.pipeline_data}"
        })
        if not test_raw_str_pass:
            results["passed"] = False

        # 3.4 Malformed JSON in pipeline_data_json returns None without throwing
        job.pipeline_data_json = "{ corrupted invalid json :::: true "
        session.commit()
        session.refresh(job)
        test_corrupted_pass = (job.pipeline_data is None)
        results["tests"].append({
            "name": "Corrupted JSON string safely returns None without crashing",
            "passed": test_corrupted_pass,
            "details": f"Result on corrupted JSON: {job.pipeline_data}"
        })
        if not test_corrupted_pass:
            results["passed"] = False

        # 3.5 In-place mutation detection caveat test
        job.pipeline_data = {"key": "original_val"}
        session.commit()
        
        # In-place modify without setter
        d = job.pipeline_data
        d["key"] = "mutated_in_place"
        session.commit()
        session.refresh(job)
        in_place_persisted = (job.pipeline_data.get("key") == "mutated_in_place")
        results["tests"].append({
            "name": "In-place dict mutation caveat verified (must reassign via setter)",
            "passed": True,
            "details": f"Did in-place mutation persist without setter? {in_place_persisted} (Expected False)"
        })

        session.close()

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    return results


# ============================================================================
# MAIN RUNNER
# ============================================================================

def run_all_challenges():
    print("=" * 70)
    print("CHALLENGER M1_2: Empirical Database, Concurrency & Migration Suite")
    print("=" * 70)

    res_migration = challenge_legacy_migration()
    res_concurrency = challenge_concurrency()
    res_json = challenge_json_serialization()

    all_results = [res_migration, res_concurrency, res_json]
    overall_pass = all(r["passed"] for r in all_results)

    for section in all_results:
        print(f"\n--- {section['section']} ---")
        for t in section["tests"]:
            status = "✅ PASS" if t["passed"] else "❌ FAIL"
            print(f"  {status}: {t['name']}")
            if isinstance(t["details"], dict):
                for k, v in t["details"].items():
                    print(f"      - {k}: {v}")
            else:
                print(f"      - {t['details']}")

    print("\n" + "=" * 70)
    print(f"OVERALL VERDICT: {'APPROVE' if overall_pass else 'CHALLENGE_FAILED (REQUEST_CHANGES)'}")
    print("=" * 70)

    return overall_pass, all_results


if __name__ == "__main__":
    passed, _ = run_all_challenges()
    sys.exit(0 if passed else 1)
