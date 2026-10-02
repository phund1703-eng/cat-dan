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
