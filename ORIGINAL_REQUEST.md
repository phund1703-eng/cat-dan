# Original User Request

## 2026-09-26T05:47:10Z

Nâng cấp toàn diện hệ thống AutoVideoFactory: Khắc phục triệt để lỗi 500 Server Error (loại bỏ hoàn toàn Celery/Redis trên Windows bằng FastAPI BackgroundTasks + ThreadPool), xây dựng giao diện Timeline Feed Inspector đa tầng, triển khai Chế độ Vận hành kép (Auto / Step-by-Step Studio), bổ sung bộ chọn Art Style Preset, quản lý mẫu giọng VieNeu-TTS và xuất trọn gói tài nguyên dự án dạng .ZIP.

Working directory: c:\Users\phund\OneDrive\Documents\Githb\Video cắt dán
Integrity mode: development

## Requirements

### R1. Tái Cấu Trúc Backend API & Database (`database.py`, `models.py`, `main.py`, `routes/jobs.py`)
- **Database Model (`dashboard/api/database.py`)**:
  - Bổ sung vào model `VideoJob`:
    - `stage` (String, default="pending"): `pending`, `script_ready`, `voice_ready`, `assets_ready`, `rendering`, `done`, `failed`.
    - `mode` (String, default="auto"): `auto` hoặc `step_by_step`.
    - `art_style` (String, default="photorealistic").
    - `voice_preset` (String, default="default").
    - `pipeline_data_json` (Text, nullable=True) kèm getter/setter `@property def pipeline_data(self)`.
  - Bổ sung helper functions: `update_job_stage`, `update_scene_image`, `get_job`.
- **Pydantic Schemas (`dashboard/api/models.py`)**:
  - Mở rộng `CreateJobRequest` (thêm `mode`, `art_style`, `voice_preset`).
  - Mở rộng `JobResponse` (thêm `stage`, `mode`, `art_style`, `voice_preset`, `pipeline_data`).
  - Tạo model `RegenerateSceneRequest` (`scene_index: int`, `prompt: str`) và `ContinueRenderRequest` (`job_id: str`).
- **Mount StaticFiles & Voice Router (`dashboard/api/main.py`)**:
  - Mount `data` tại `/files` và `assets` tại `/assets`. Tự động tạo thư mục nếu chưa có.
  - Endpoint `GET /voices`: Quét thư mục `assets/voices/` và trả về danh sách file `.wav` giọng mẫu.
  - Endpoint `POST /voices/upload`: Nhận upload file `.wav` (`UploadFile`), lưu vào `assets/voices/`.
- **Native Async Tasks & Quản lý Job (`dashboard/api/routes/jobs.py`)**:
  - Loại bỏ hoàn toàn phụ thuộc Celery/Redis (`create_video_task.delay`).
  - Sử dụng `BackgroundTasks` của FastAPI trực tiếp trong `POST /jobs`.
  - Tạo endpoint `POST /jobs/{job_id}/regenerate-scene`: Sinh lại ảnh cho cảnh cụ thể, cập nhật `pipeline_data`.
  - Tạo endpoint `POST /jobs/{job_id}/upload-scene-image`: Nhận file ảnh upload thay thế cho scene, cập nhật đường dẫn ảnh trong `pipeline_data`.
  - Tạo endpoint `POST /jobs/{job_id}/continue-render`: Kích hoạt tiếp tục render khi job đang ở stage `assets_ready` (Step-by-Step).
  - Tạo endpoint `GET /jobs/{job_id}/export-zip`: Đóng gói toàn bộ thư mục `data/output/{job_id}` thành file zip và trả về `FileResponse`.

### R2. Thực Thi Pipeline Thực Tế Có Audit Trail (`dashboard/worker/video_tasks.py`)
- Thay thế hoàn toàn mã mock bằng pipeline thực tế 5 giai đoạn:
  - **Stage 1 (`script_ready`)**: Sinh kịch bản qua `ScriptGenerator`, lưu prompt và danh sách scene vào `pipeline_data`.
  - **Stage 2 (`voice_ready`)**: Tạo audio từng cảnh qua `TTSManager` (kết hợp `VieNeuClient` với `voice_preset`), lưu đường dẫn audio và thời lượng vào `pipeline_data`.
  - **Stage 3 (`assets_ready`)**: Áp dụng Art Style Preset vào prompt, điều phối sinh ảnh qua `CascadeAssetOrchestrator` / `ImageGenerator`. Ghi nhận chi tiết từng scene (`image_path`, `prompt`, `tier_used`, `vision_gate_score`, `vision_gate_reasoning`).
    - **Kiểm tra Hybrid Mode**: Nếu `job.mode == "step_by_step"`, dừng tiến trình tại stage `assets_ready`, giữ trạng thái chờ người dùng phê duyệt/can thiệp.
  - **Stage 4 (`rendering`)**: Sinh phụ đề động Karaoke Dynamic qua `SubtitleGenerator.generate_dynamic_chunked_ass` (2-4 từ/cụm, margin 180px safe zone), tổng hợp câu lệnh FFmpeg kèm hiệu ứng Ken Burns/chuyển cảnh vào `pipeline_data["ffmpeg_commands"]`.
  - **Stage 5 (`done`)**: Chạy FFmpeg tổng hợp video hoàn chỉnh tại `data/output/{job_id}/final_video.mp4`, cập nhật stage `done` và status `JobStatus.done`.
- Xử lý lỗi toàn diện: Nếu phát sinh ngoại lệ, cập nhật stage `failed`, status `JobStatus.failed`, và lưu thông báo lỗi vào `error`.

### R3. Giao Diện Tạo Video & Thiết Lập Dự Án (`dashboard/ui/pages/create_video.py`)
- Thêm Radio chọn **Chế độ Vận Hành**:
  - `⚡ Tự động hoàn toàn (Auto Pipeline)`: Render liên tục đến khi hoàn tất video.
  - `🛠️ Duyệt từng bước (Step-by-Step Studio)`: Dừng tại khâu Storyboard để kiểm tra và can thiệp trước khi render.
- Thêm Selectbox chọn **Phong Cách Mỹ Thuật (Art Style Preset)**:
  - 📸 Chân thực (Photorealistic)
  - 🎨 3D Điện ảnh (Cinematic 3D / Pixar Style)
  - ⛩️ Hoạt hình Nhật Bản (Anime / Manga)
  - 📜 Tài liệu cổ điển (Vintage Documentary)
  - 🖌️ Tranh màu nước (Watercolor Art)
- Thêm khu vực **Mẫu Giọng Đọc (VieNeu-TTS)**:
  - Dropdown chọn mẫu giọng lấy từ `GET /voices`.
  - File uploader cho phép tải file `.wav` mới trực tiếp lên `POST /voices/upload`.
- Chuyển hướng hoặc cung cấp liên kết sang trang kiểm tra tiến trình sau khi bấm tạo job.

### R4. Giao Diện Timeline Feed Inspector & Phê Duyệt (`dashboard/ui/pages/preview_approve.py`)
- Bố cục **Dòng thời gian cuộn dọc (Timeline Feed)** gồm 5 giai đoạn trực quan:
  - **Header**: Thanh tiến trình trạng thái (`📝 Kịch Bản` ➔ `🎙️ Âm Thanh` ➔ `🖼️ Storyboard` ➔ `🎬 Hiệu Ứng` ➔ `🏆 Master Video`).
  - **Giai đoạn 1 (Kịch bản)**: Hiển thị nguyên văn AI Prompt trong `st.code`, bảng phân cảnh (STT, lời thoại tiếng Việt, mô tả cảnh).
  - **Giai đoạn 2 (Âm thanh)**: Thông số engine TTS, trình phát `st.audio` nghe thử từng cảnh.
  - **Giai đoạn 3 (Storyboard & Vision Gate)**:
    - Hiển thị từng Scene Card: Ảnh xem trước lớn, Badge phân tầng (`Tier 1 Imagen 3`, `Tier 2 Flux`, `Tier 3 Stock`, `Tier 4 Procedural`), điểm số và nhận xét của Gemini Vision Gate, nguyên văn Visual Prompt.
    - Công cụ can thiệp: Ô sửa Prompt kèm nút `🔄 Sinh lại ảnh cảnh này`, nút `📤 Tải ảnh từ máy tính lên`.
    - Khi job ở stage `assets_ready` (Step-by-Step): Hiển thị nút bấm nổi bật `🚀 PHÊ DUYỆT STORYBOARD & TIẾP TỤC RENDER VIDEO` gọi API `/jobs/{job_id}/continue-render`.
  - **Giai đoạn 4 (Hiệu ứng & Phụ đề Dynamic)**: Thông số chuyển động Ken Burns, cấu trúc phụ đề Dynamic Chunked ASS (2-4 từ, margin 180px safe zone), khối `st.code` hiển thị toàn bộ câu lệnh kỹ thuật FFmpeg.
  - **Giai đoạn 5 (Master Video & Xuất Bản)**: Trình phát `st.video`, form sửa metadata (Tiêu đề, Mô tả, Hashtag), nút `📦 Tải Về Trọn Gói Dự Án (.ZIP)` và nút Phê duyệt xuất bản.

### R5. Danh Sách Công Việc & Điều Hướng (`dashboard/ui/pages/job_list.py`)
- Cập nhật hiển thị cột Trạng thái kèm badge Stage chi tiết (`📝 Kịch bản xong`, `🎙️ Voice xong`, `🖼️ Chờ duyệt ảnh (Step-by-Step)`, `🎬 Đang render`, `✅ Hoàn thành`, `❌ Thất bại`).
- Thêm nút hành động "🔍 Soi Quy Trình" dẫn thẳng sang trang `preview_approve.py` của Job tương ứng.

## Acceptance Criteria

### Tính Năng Hệ Thống & Trải Nghiệm Người Dùng (Functional & UI Verification)
- [ ] Không còn lỗi 500 Server Error (`WinError 10061`) khi tạo job qua `POST /jobs` mà không cần Redis/Celery chạy nền.
- [ ] Chế độ Step-by-Step dừng chính xác ở stage `assets_ready`, cho phép sửa prompt sinh lại ảnh hoặc tải ảnh lên thay thế.
- [ ] Bấm nút "Tiếp tục Render" chuyển tiếp suôn sẻ sang stage `rendering` và hoàn tất xuất video master ở stage `done`.
- [ ] Trang `preview_approve.py` hiển thị đầy đủ 5 tầng thông tin của Timeline Feed kèm nghe thử âm thanh, xem ảnh kèm điểm Vision Gate, mã lệnh FFmpeg và trình phát video master.
- [ ] API `/jobs/{job_id}/export-zip` tải về file .ZIP chứa đầy đủ tài nguyên của job (kịch bản JSON, media ảnh/audio, file .ass và video .mp4).

### Kiểm Thử Tự Động Đầu Cuối (Programmatic Verification)
- [ ] Xây dựng test suite tự động `tests/test_dashboard_full_flow.py` kiểm thử toàn bộ luồng:
  - Tạo job qua FastAPI TestClient/HTTP request với `mode="step_by_step"`.
  - Xác nhận job dừng ở `assets_ready` với đầy đủ `pipeline_data`.
  - Gọi `POST /jobs/{job_id}/regenerate-scene` và kiểm tra ảnh được cập nhật.
  - Gọi `POST /jobs/{job_id}/upload-scene-image` và kiểm tra ảnh upload được lưu trữ chính xác.
  - Gọi `POST /jobs/{job_id}/continue-render` và xác nhận job chuyển tiếp thành công đến `done`.
  - Gọi `GET /jobs/{job_id}/export-zip` và kiểm tra file ZIP hợp lệ chứa đầy đủ cấu trúc thư mục.
- [ ] Test suite chạy thành công 100% (exit code 0).
