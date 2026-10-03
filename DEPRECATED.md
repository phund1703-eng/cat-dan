# DEPRECATED — Entrypoint cũ (Task 1.1)

Điểm vào tạo video duy nhất: `core/pipeline/factory.py::create_video`.
Đường Dashboard (DB 5-stage, step-by-step): `dashboard/worker/video_tasks.py`.

| File cũ | Trạng thái |
|---|---|
| `run_pipeline_v4.py` | Wrapper mỏng → canonical (giữ `run_production_v4`, `TARGET_VIDEOS_V4`) |
| `run_pipeline_v5.py` | Wrapper mỏng → canonical (giữ `PipelineV5`, `run_v5_verification`) |
| `produce_human_body_video.py` | Wrapper mỏng → canonical (giữ `produce_human_body_video`) |
| `produce_human_body_v2.py` | Wrapper mỏng → canonical (giữ `produce_human_body_v2`) |
| `scripts/produce_3_random_videos.py` | Wrapper mỏng → canonical (giữ `produce_all`, `VIDEOS_CONFIG`) |
| `scripts/produce_domain_test_videos.py` | Wrapper mỏng → canonical (giữ `produce_all`, `VIDEOS_CONFIG`) |
| `scripts/produce_universal_collage_videos.py` | Wrapper mỏng → canonical (giữ `produce_universal_videos`, `VIDEOS_CONFIG`) |
| `prepare_human_body_assets.py` | Shim thư viện → `core/media_engine/human_body_assets.py` |
| `pipeline.py` | Cài đặt gốc (`VideoFactory`); CLI đã chuyển qua canonical |

## Hàng đợi bền (Task 4.1)

| Hạng mục cũ | Trạng thái |
|---|---|
| `dashboard/worker/celery_app.py` | **Đã xoá** — thay bằng worker poll DB `python -m dashboard.worker.runner` (`dashboard/worker/runner.py`) |
| `create_video_task` / `publish_video_task` (Celery tasks) | Adapter thường giữ tương thích ngược, ủy quyền `resume_video_pipeline` / `publish_video` |
| `celery`, `redis`, `flower`, `manim` trong `requirements.txt` | Chuyển sang `requirements-optional.txt` |
| API tự chạy pipeline bằng FastAPI `BackgroundTasks` khi tạo/retry job | Đã bỏ — API chỉ tạo job `pending`, worker mới thực thi; job dở dang được resume từ stage đã lưu |
