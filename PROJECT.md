# Project: AutoVideoFactory Comprehensive Upgrade

## Architecture
AutoVideoFactory is a Python-based automated short video creation and publishing platform.
This upgrade transforms the system from an unstable Celery/Redis background task model on Windows to a robust native FastAPI `BackgroundTasks` architecture with a rich 5-tier Timeline Feed Inspector in Streamlit, supporting both fully automated rendering and a step-by-step studio workflow.

```
                      Streamlit Dashboard UI
   ┌─────────────────────────────────────────────────────────────┐
   │ create_video.py  │  preview_approve.py  │  job_list.py      │
   │ (Mode, Preset,   │  (5-Tier Timeline    │  (Stage badges,   │
   │  Voice upload)   │   Feed Inspector)    │   Inspector jump) │
   └────────────────────────────────┬────────────────────────────┘
                                    │ HTTP API / Static Mounts
                                    ▼
                          FastAPI Application
   ┌─────────────────────────────────────────────────────────────┐
   │ dashboard/api/main.py: Mounts /files, /assets; /voices      │
   │ dashboard/api/routes/jobs.py: BackgroundTasks execution     │
   │ dashboard/api/database.py: SQLite with PRAGMA auto-migration│
   │ dashboard/api/models.py: Pydantic schemas for all payloads  │
   └────────────────────────────────┬────────────────────────────┘
                                    │ BackgroundTasks (In-process threadpool)
                                    ▼
                       Pipeline Execution Worker
   ┌─────────────────────────────────────────────────────────────┐
   │ dashboard/worker/video_tasks.py                             │
   │ Stage 1: script_ready (ScriptGenerator with fallback)       │
   │ Stage 2: voice_ready (TTSManager / VieNeu-TTS / EdgeTTS)    │
   │ Stage 3: assets_ready (Art Style + CascadeAssetOrchestrator)│
   │          ──> Pause if mode == "step_by_step"                │
   │ Stage 4: rendering (SubtitleGenerator ASS + FFmpeg cmd)     │
   │ Stage 5: done (FFmpeg assemble final_video.mp4)             │
   │ Audit Trail: Persisted in pipeline_data on every stage      │
   └─────────────────────────────────────────────────────────────┘
```

## Feature Inventory
Every requirement from ORIGINAL_REQUEST.md is enumerated and mapped:
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Database Extension | Add `stage`, `mode`, `art_style`, `voice_preset`, `pipeline_data_json` with property `pipeline_data` to `VideoJob` | M1 | R1 |
| 2 | SQLite PRAGMA Migration | Add check in `create_tables()` with `PRAGMA table_info` and `ALTER TABLE ADD COLUMN` to prevent SQLite column errors | M1 | R1 |
| 3 | DB Helper Functions | Implement `update_job_stage`, `update_scene_image`, extend `create_job` and `get_job` | M1 | R1 |
| 4 | Pydantic Schemas | Extend `CreateJobRequest`, `JobResponse`; create `RegenerateSceneRequest`, `ContinueRenderRequest` | M1 | R1 |
| 5 | Static Files Mount | Mount `data/` at `/files` and `assets/` at `/assets` with directory auto-creation | M1 | R1 |
| 6 | Voice API Endpoints | Implement `GET /voices` and `POST /voices/upload` scanning and saving in `assets/voices/` | M1 | R1 |
| 7 | Eliminate Celery/Redis | Replace `create_video_task.delay` in `POST /jobs` and `retry` with FastAPI native `BackgroundTasks` | M1 | R1 |
| 8 | Scene Regeneration API | Implement `POST /jobs/{job_id}/regenerate-scene` to regenerate scene image and update `pipeline_data` | M1 | R1 |
| 9 | Scene Image Upload API | Implement `POST /jobs/{job_id}/upload-scene-image` for custom user image overrides | M1 | R1 |
| 10| Continue Render API | Implement `POST /jobs/{job_id}/continue-render` to resume from `assets_ready` to `rendering` | M1 | R1 |
| 11| Export ZIP API | Implement `GET /jobs/{job_id}/export-zip` packaging project assets into a downloadable archive | M1 | R1 |
| 12| 5-Stage Worker Pipeline | Replace mock `video_tasks.py` with 5-stage pipeline with full audit trail in `pipeline_data` | M2 | R2 |
| 13| Hybrid Step-by-Step Pause | Pause pipeline at `assets_ready` when `job.mode == "step_by_step"` and resume via `continue-render` | M2 | R2 |
| 14| Art Style Preset Integration | Map Art Style presets into visual prompts in `CascadeAssetOrchestrator` / `ImageGenerator` | M2 | R2 |
| 15| VieNeu-TTS Voice Integration | Synthesize scene audio with VieNeu-TTS voice preset, fallback to EdgeTTS, record durations | M2 | R2 |
| 16| Subtitles & FFmpeg Assembly | Generate dynamic chunked ASS (2-4 words, 180px margin) and compose FFmpeg Ken Burns commands | M2 | R2 |
| 17| Error Handling & Status | Graceful failure tracking setting stage/status to `failed` and capturing error messages | M2 | R2 |
| 18| Create Video UI Upgrades | Add Mode radio (Auto vs Step-by-Step), Art Style Preset selectbox, VieNeu voice selector & upload | M3 | R3 |
| 19| Post-Creation Jump Links | Session state transition to `preview_approve.py` immediately following job creation | M3 | R3 |
| 20| 5-Tier Timeline Feed Inspector | Implement 5-tier vertical timeline feed in `preview_approve.py` (Script, Voice, Storyboard, FX, Master) | M3 | R4 |
| 21| Vision Gate & Storyboard Cards | Scene cards with Tier 1-4 badges, Vision Gate score/reasoning, regenerate & upload buttons | M3 | R4 |
| 22| Step-by-Step Approval Button | Prominent `🚀 PHÊ DUYỆT STORYBOARD & TIẾP TỤC RENDER VIDEO` button for `assets_ready` jobs | M3 | R4 |
| 23| FX & Master Video UI | Ken Burns info, ASS subtitle specs, FFmpeg code block, Master video player, ZIP download button | M3 | R4 |
| 24| Job List Badges & Quick Jump | Update `job_list.py` with Vietnamese stage badges and "🔍 Soi Quy Trình" jump button | M3 | R5 |
| 25| Automated Test Suite | Implement `tests/test_dashboard_full_flow.py` covering all acceptance criteria with 100% pass | M4 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend API & Database Restructuring | `dashboard/api/database.py`, `dashboard/api/models.py`, `dashboard/api/main.py`, `dashboard/api/routes/jobs.py` | none | DONE |
| M2 | Realistic Pipeline Worker & Audit Trail | `dashboard/worker/video_tasks.py` (5 stages, `pipeline_data`, hybrid pause, error handling) | M1 | DONE |
| M3 | Streamlit UI Pages Upgrade | `dashboard/ui/pages/create_video.py`, `dashboard/ui/pages/preview_approve.py`, `dashboard/ui/pages/job_list.py` | M1, M2 | DONE |
| M4 | E2E Automated Test Suite & Verification | `tests/test_dashboard_full_flow.py` and full acceptance criteria verification | M1, M2, M3 | DONE |

## Interface Contracts

### M1 ↔ M2 (Backend API ↔ Worker)
- Function `run_video_pipeline(job_id: str)`:
  Invoked via `BackgroundTasks.add_task(run_video_pipeline, job_id)`. Opens its own DB session (`SessionLocal()`).
- Function `continue_video_pipeline(job_id: str)`:
  Invoked when `/jobs/{job_id}/continue-render` is called. Resumes from `assets_ready` through `rendering` to `done`.
- Function `regenerate_scene_asset(job_id: str, scene_index: int, prompt: str) -> dict`:
  Synchronously or asynchronously regenerates the image for a specific scene and updates `pipeline_data["scenes"][scene_index]`.
- Structure of `pipeline_data`:
  ```json
  {
    "script": {
      "title": "string",
      "description": "string",
      "hashtags": ["string"],
      "prompt_used": "string",
      "scenes": [{"index": 0, "narration": "string", "visual_description": "string", "still_image_prompt": "string", "duration": 5.0}]
    },
    "voice": {
      "engine": "VieNeu-TTS",
      "preset": "default",
      "scenes": [{"scene_index": 0, "text": "string", "audio_path": "string", "duration": 5.0}]
    },
    "storyboard": [
      {
        "scene_index": 0,
        "image_path": "string",
        "visual_prompt": "string",
        "tier_used": "tier1_imagen | tier2_flux | tier3_stock | tier4_procedural | user_uploaded",
        "vision_gate_score": 0.88,
        "vision_gate_reasoning": "string"
      }
    ],
    "ffmpeg_commands": ["string"]
  }
  ```

### M1/M2 ↔ M3 (Backend ↔ Streamlit UI)
- `GET /voices` -> `{"voices": ["default", ...]}`
- `POST /voices/upload` (multipart `file`) -> `{"status": "success", "filename": "...", "path": "..."}`
- `POST /jobs` (json payload) -> `JobResponse`
- `GET /jobs/{job_id}` -> `JobResponse` with `stage`, `mode`, `art_style`, `voice_preset`, `pipeline_data`
- `POST /jobs/{job_id}/regenerate-scene` (json `{"scene_index": int, "prompt": str}`) -> `JobResponse`
- `POST /jobs/{job_id}/upload-scene-image` (form `scene_index: int`, multipart `file`) -> `JobResponse`
- `POST /jobs/{job_id}/continue-render` (json `{"job_id": str}`) -> `JobResponse`
- `GET /jobs/{job_id}/export-zip` -> `FileResponse(application/zip)`

## Code Layout
- `dashboard/api/database.py`: SQLAlchemy models, migrations, and CRUD helpers.
- `dashboard/api/models.py`: Pydantic request and response schemas.
- `dashboard/api/main.py`: FastAPI app initialization, static file mounts, voice routes.
- `dashboard/api/routes/jobs.py`: Job endpoints using `BackgroundTasks`.
- `dashboard/worker/video_tasks.py`: 5-stage pipeline, `pipeline_data` tracking, hybrid step-by-step pause.
- `dashboard/ui/pages/create_video.py`: Creation form with mode, preset, and voice upload.
- `dashboard/ui/pages/preview_approve.py`: 5-tier vertical Timeline Feed Inspector.
- `dashboard/ui/pages/job_list.py`: Job table with Vietnamese stage badges and quick inspection navigation.
- `tests/test_dashboard_full_flow.py`: Comprehensive automated test suite.
