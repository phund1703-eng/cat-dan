"""
Create Video Page (Requirement R3)
dashboard/ui/pages/create_video.py
"""
import os
from pathlib import Path
import streamlit as st
import requests

API_URL = os.getenv('API_URL', 'http://localhost:8000')

st.title("🎬 Tạo Dự Án Video Mới")

def fetch_voice_presets():
    """Lấy danh sách mẫu giọng đọc từ API hoặc fallback đĩa cứng."""
    try:
        r = requests.get(f"{API_URL}/voices", timeout=2.0)
        if r.status_code == 200:
            voices = r.json().get("voices", [])
            if voices:
                return voices
    except Exception:
        pass
    
    # Fallback đĩa cứng cục bộ nếu API chưa bật
    local_dir = Path("assets/voices")
    if local_dir.exists():
        files = [f.name for f in local_dir.glob("*.wav")] + [f.name for f in local_dir.glob("*.mp3")]
        if files:
            res = ["default"]
            for f in sorted(files):
                if f not in res:
                    res.append(f)
            return res
            
    return ["default", "Minh Quân (Nam)", "Mai Phương (Nữ)"]

# =========================================================================
# KHU VỰC QUẢN LÝ & NGHE THỬ MẪU GIỌNG ĐỌC (VieNeu-TTS)
# =========================================================================
with st.expander("🎙️ Quản lý & Nghe Thử Mẫu Giọng Đọc (VieNeu-TTS)", expanded=True):
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
        test_voice = st.selectbox(
            "Chọn mẫu giọng để nghe thử:",
            options=fetch_voice_presets(),
            key="preview_voice_select"
        )
    with col_p2:
        st.write("")
        st.write("")
        if st.button("🔊 Nghe thử mẫu giọng này", key="btn_preview_audio", use_container_width=True):
            with st.spinner("Đang tạo âm thanh mẫu..."):
                try:
                    r = requests.get(f"{API_URL}/voices/preview", params={"voice": test_voice}, timeout=15.0)
                    if r.status_code == 200:
                        st.audio(r.content, format="audio/wav")
                        st.success(f"Đang phát mẫu giọng: **{test_voice}**")
                    else:
                        st.error(f"Không thể tạo âm thanh mẫu: {r.text}")
                except Exception as e:
                    st.error(f"Lỗi kết nối khi nghe thử giọng: {e}")

    st.divider()
    st.markdown("**Tải lên mẫu giọng riêng** `.wav` hoặc `.mp3` (3-10 giây) để clone giọng mới:")
    col_v1, col_v2 = st.columns([3, 1])
    with col_v1:
        voice_file = st.file_uploader("Chọn file giọng đọc (.wav, .mp3)", type=["wav", "mp3"], key="voice_uploader")
    with col_v2:
        st.write("")
        st.write("")
        if voice_file and st.button("📤 Tải lên giọng", key="upload_voice_btn", use_container_width=True):
            try:
                files = {"file": (voice_file.name, voice_file.getvalue(), voice_file.type or "audio/wav")}
                res = requests.post(f"{API_URL}/voices/upload", files=files, timeout=10.0)
                if res.status_code in [200, 201]:
                    st.success(f"Đã lưu mẫu giọng: `{voice_file.name}`")
                    st.rerun()
                else:
                    st.error(f"Lỗi tải lên: {res.text}")
            except Exception as e:
                st.error(f"Lỗi kết nối khi tải giọng: {e}")

# =========================================================================
# FORM THIẾT LẬP VÀ KHỞI TẠO DỰ ÁN VIDEO
# =========================================================================
with st.form("create_job_form"):
    topic = st.text_area(
        "📌 Chủ đề video",
        placeholder="Ví dụ: Khám phá 3 sự thật kinh ngạc về vũ trụ bao la...",
        height=100
    )

    col_mode, col_art = st.columns(2)
    with col_mode:
        mode = st.radio(
            "🎯 Chế độ Vận Hành",
            options=["auto", "step_by_step"],
            format_func=lambda x: {
                "auto": "⚡ Tự động hoàn toàn (Auto Pipeline)",
                "step_by_step": "🛠️ Duyệt từng bước (Step-by-Step Studio)"
            }.get(x, x),
            help="⚡ Auto: Chạy liên tục từ Kịch bản đến Master Video.\n🛠️ Step-by-Step: Dừng tại Storyboard để kiểm duyệt ảnh trước khi render."
        )

    with col_art:
        art_styles = {
            "paper_collage": "✂️ Cắt dán Nghệ thuật (Paper Collage & Cutout - Đặc trưng)",
            "photorealistic": "📸 Chân thực (Photorealistic)",
            "cinematic_3d": "🎨 3D Điện ảnh (Cinematic 3D / Pixar Style)",
            "anime": "⛩️ Hoạt hình Nhật Bản (Anime / Manga)",
            "vintage": "📜 Tài liệu cổ điển (Vintage Documentary)",
            "watercolor": "🖌️ Tranh màu nước (Watercolor Art)"
        }
        art_style = st.selectbox(
            "🎨 Phong Cách Mỹ Thuật (Art Style Preset)",
            options=list(art_styles.keys()),
            format_func=lambda k: art_styles[k]
        )

    col_voice, col_style = st.columns(2)
    with col_voice:
        available_voices = fetch_voice_presets()
        voice_preset = st.selectbox(
            "🎙️ Mẫu Giọng Đọc (VieNeu-TTS)",
            options=available_voices
        )
    with col_style:
        style = st.selectbox(
            "🎞️ Phong cách dựng hình",
            options=[
                "collage_broll",
                "animation_2d",
                "clip_overlay",
                "whiteboard",
                "ai_avatar"
            ],
            format_func=lambda x: {
                "collage_broll": "🎬 Cắt dán B-Roll (Paper Collage & Cutout - Khuyên dùng)",
                "animation_2d": "🎨 Hoạt hình 2D (Manim - Thử nghiệm)",
                "clip_overlay": "📹 Chèn Clip Overlay (Stock Video - Thử nghiệm)",
                "whiteboard": "✏️ Bảng trắng (Whiteboard - Thử nghiệm)",
                "ai_avatar": "👤 AI Avatar (SadTalker - Thử nghiệm)"
            }.get(x, x)
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        language = st.selectbox("🌐 Ngôn ngữ", options=["vi", "en", "both"], format_func=lambda x: {
            "vi": "Tiếng Việt",
            "en": "Tiếng Anh",
            "both": "Cả hai"
        }.get(x, x))
    with col2:
        format_type = st.selectbox("📐 Định dạng", options=["shorts", "landscape"], format_func=lambda x: {
            "shorts": "Video Dọc (9:16 - TikTok/Shorts)",
            "landscape": "Video Ngang (16:9 - YouTube Standard)"
        }.get(x, x))
    with col3:
        quality = st.selectbox("💎 Chất lượng AI", options=["standard", "premium"], format_func=lambda x: {
            "standard": "Tiêu chuẩn (Flash Engine)",
            "premium": "Cao cấp (Pro Engine)"
        }.get(x, x))

    submit = st.form_submit_button("🚀 Bắt Đầu Tạo Dự Án Video", type="primary")

    if submit:
        if not topic.strip():
            st.error("Vui lòng nhập chủ đề video!")
        else:
            try:
                # Trích xuất tên voice sạch
                clean_voice = voice_preset
                if " — " in clean_voice:
                    clean_voice = clean_voice.split(" — ")[0].replace("⭐ ", "").strip()
                elif "📁 [Tự tải lên] " in clean_voice:
                    clean_voice = clean_voice.replace("📁 [Tự tải lên] ", "").strip()
                elif "default" in clean_voice.lower():
                    clean_voice = "default"

                payload = {
                    "topic": topic.strip(),
                    "style": style,
                    "language": language,
                    "format": format_type,
                    "quality": quality,
                    "mode": mode,
                    "art_style": art_style,
                    "voice_preset": clean_voice
                }
                res = requests.post(f"{API_URL}/jobs", json=payload, timeout=30.0)
                res.raise_for_status()
                data = res.json()
                job_id = data['id']
                st.session_state["selected_job_id"] = job_id

                st.success(f"🎉 Khởi tạo dự án thành công! Job ID: `{job_id}`")
                st.info("💡 Bạn có thể chuyển sang trang **Xem Trước & Phê Duyệt** để theo dõi Timeline Feed hoặc **Danh Sách Công Việc**.")
            except Exception as e:
                st.error(f"Lỗi khởi tạo dự án: {str(e)}")

# =========================================================================
# ĐIỀU HƯỚNG NHANH SAU KHI TẠO JOB
# =========================================================================
if "selected_job_id" in st.session_state:
    jid = st.session_state["selected_job_id"]
    st.markdown("---")
    st.markdown(f"**Dự án vừa tạo gần nhất:** `{jid}`")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Đến Timeline Feed Inspector ngay", key=f"jump_{jid}", type="primary"):
            try:
                st.switch_page("pages/preview_approve.py")
            except Exception:
                st.info("Vui lòng chọn trang 'Xem Trước & Phê Duyệt' từ thanh điều hướng bên trái.")
    with c2:
        if st.button("📋 Đến Danh Sách Công Việc", key=f"list_{jid}"):
            try:
                st.switch_page("pages/job_list.py")
            except Exception:
                st.info("Vui lòng chọn trang 'Danh Sách Công Việc' từ thanh điều hướng bên trái.")
