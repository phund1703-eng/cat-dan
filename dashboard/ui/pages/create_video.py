"""
Create Video Page (Requirement R3)
dashboard/ui/pages/create_video.py
"""
import os
from pathlib import Path
import streamlit as st
import requests

from core.script_engine.script_style_presets import (
    get_all_script_styles,
    save_script_style,
    get_script_style_by_id
)

API_URL = os.getenv('API_URL', 'http://localhost:8000')


class _ApiSession(requests.Session):
    """requests.Session tự đính kèm X-API-Key cho POST/PUT/PATCH/DELETE."""

    def request(self, method, url, **kwargs):
        api_key = os.getenv("SECRET_KEY", "").strip()
        if api_key and str(method).upper() not in ("GET", "HEAD", "OPTIONS"):
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("X-API-Key", api_key)
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


api = _ApiSession()

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


def fetch_script_style_presets():
    """Lấy danh sách mẫu phong cách kịch bản từ API hoặc fallback file cục bộ."""
    try:
        r = requests.get(f"{API_URL}/script-styles", timeout=2.0)
        if r.status_code == 200:
            styles = r.json()
            if styles:
                return styles
    except Exception:
        pass
    return get_all_script_styles()


# =========================================================================
# KHU VỰC QUẢN LÝ & NGHE THỬ MẪU GIỌNG ĐỌC (VieNeu-TTS)
# =========================================================================
with st.expander("🎙️ Quản lý & Nghe Thử Mẫu Giọng Đọc (VieNeu-TTS)", expanded=False):
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
    st.markdown("**Clone giọng đọc riêng từ file mẫu (3–10 giây):**")
    st.info(
        "💡 **Giải đáp về Clone giọng:** VieNeu-TTS v3 Turbo sử dụng mô hình học âm sắc Flow-Matching trực tiếp "
        "từ sóng âm (waveform). **Bạn KHÔNG cần nhập chữ/văn bản đã nói**, AI tự động trích xuất đặc trưng giọng "
        "nói để đọc bất kỳ câu thoại nào sau này!"
    )

    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        voice_file = st.file_uploader("Chọn file giọng mẫu (.wav, .mp3)", type=["wav", "mp3"], key="voice_uploader")
        friendly_voice_name = st.text_input(
            "Tên gợi nhớ cho giọng này (tuỳ chọn):",
            placeholder="Ví dụ: Giọng Thầy Giáo, Giọng Kể Chuyện Đêm...",
            key="friendly_voice_name_input"
        )
    with col_v2:
        st.write("")
        st.write("")
        if voice_file and st.button("📤 Tải lên & Lưu Giọng", key="upload_voice_btn", use_container_width=True):
            try:
                fname = voice_file.name
                if friendly_voice_name.strip():
                    ext = Path(fname).suffix or ".wav"
                    fname = f"{friendly_voice_name.strip()}{ext}"
                files = {"file": (fname, voice_file.getvalue(), voice_file.type or "audio/wav")}
                res = api.post(f"{API_URL}/voices/upload", files=files, timeout=10.0)
                if res.status_code in [200, 201]:
                    st.success(f"Đã lưu mẫu giọng: `{fname}`")
                    st.rerun()
                else:
                    st.error(f"Lỗi tải lên: {res.text}")
            except Exception as e:
                st.error(f"Lỗi kết nối khi tải giọng: {e}")


# =========================================================================
# LỰA CHỌN PHƯƠNG THỨC NHẬP KỊCH BẢN & PHONG CÁCH VIẾT
# =========================================================================
st.markdown("### ✍️ Thiết Lập Kịch Bản & Nội Dung")

script_mode = st.radio(
    "Chọn cách thức tạo nội dung video:",
    options=["ai_generate", "custom_script"],
    format_func=lambda x: {
        "ai_generate": "🤖 Nhập Chủ Đề (AI Tự Động Viết Kịch Bản Chuyên Nghiệp)",
        "custom_script": "📝 Tự Nhập Kịch Bản / Lời Thoại Sẵn Có (Giữ Nguyên 100% Câu Chữ)"
    }.get(x, x),
    horizontal=True,
    key="radio_script_mode"
)

all_styles = fetch_script_style_presets()
style_dict = {s["id"]: s for s in all_styles}
style_options = list(style_dict.keys())

selected_style_id = "storytelling_mystery"
custom_tone_instruction = ""

if script_mode == "ai_generate":
    col_st1, col_st2 = st.columns([2, 1])
    with col_st1:
        selected_style_id = st.selectbox(
            "🎭 Phong cách viết kịch bản AI (Script Tone & Style):",
            options=style_options,
            format_func=lambda sid: f"{style_dict[sid].get('name', sid)}",
            key="script_style_select"
        )
        current_style = style_dict.get(selected_style_id, {})
        st.caption(f"📝 *Mô tả:* {current_style.get('description', '')}")

    with col_st2:
        st.write("")
        st.info(f"🎯 *Khán giả mục tiêu:* {current_style.get('target_audience', 'Mọi đối tượng')}")

    # Expander cho phép xem, tuỳ biến prompt và lưu phong cách riêng
    with st.expander("⚙️ Tinh chỉnh Prompt & Lưu Thành Mẫu Phong Cách Mới", expanded=False):
        prompt_edit = st.text_area(
            "Nội dung Prompt chỉ đạo giọng điệu (Tone Instruction):",
            value=current_style.get("tone_instruction", ""),
            height=120,
            key="tone_instruction_editor"
        )
        custom_tone_instruction = prompt_edit

        c_sav1, c_sav2, c_sav3 = st.columns([2, 2, 1])
        with c_sav1:
            new_preset_name = st.text_input(
                "Tên phong cách mới:",
                placeholder="Ví dụ: Giọng Hùng Biện Truyền Cảm Hứng...",
                key="new_preset_name"
            )
        with c_sav2:
            new_preset_desc = st.text_input(
                "Mô tả ngắn gọn:",
                placeholder="Ví dụ: Lời thoại dứt khoát, nâng cao tinh thần...",
                key="new_preset_desc"
            )
        with c_sav3:
            st.write("")
            st.write("")
            if st.button("💾 Lưu Mẫu Này", key="btn_save_script_preset", use_container_width=True):
                if not new_preset_name.strip():
                    st.error("Vui lòng nhập tên phong cách!")
                elif not prompt_edit.strip():
                    st.error("Nội dung chỉ đạo phong cách không được để trống!")
                else:
                    try:
                        save_payload = {
                            "name": new_preset_name.strip(),
                            "description": new_preset_desc.strip(),
                            "tone_instruction": prompt_edit.strip(),
                            "target_audience": "Khán giả tuỳ chỉnh"
                        }
                        res_p = api.post(f"{API_URL}/script-styles", json=save_payload, timeout=5.0)
                        if res_p.status_code in [200, 201]:
                            st.success(f"Đã lưu thành công mẫu phong cách: **{new_preset_name}**!")
                            st.rerun()
                        else:
                            # Fallback lưu trực tiếp qua core preset manager
                            save_script_style(
                                style_id=new_preset_name.strip(),
                                name=new_preset_name.strip(),
                                description=new_preset_desc.strip(),
                                tone_instruction=prompt_edit.strip()
                            )
                            st.success(f"Đã lưu thành công mẫu phong cách: **{new_preset_name}**!")
                            st.rerun()
                    except Exception as e_sav:
                        st.error(f"Lỗi khi lưu phong cách: {e_sav}")


# =========================================================================
# FORM THIẾT LẬP VÀ KHỞI TẠO DỰ ÁN VIDEO
# =========================================================================
with st.form("create_job_form"):
    topic_input = ""
    custom_script_input = ""

    if script_mode == "ai_generate":
        topic_input = st.text_area(
            "📌 Chủ đề video bạn muốn AI viết kịch bản:",
            placeholder="Ví dụ: Axit dạ dày mạnh đến mức làm tan chảy kim loại, nhưng tại sao dạ dày của chính bạn lại không bị tiêu hoá?...",
            height=90
        )
    else:
        topic_input = st.text_input(
            "📌 Tiêu đề / Tên chủ đề video (tuỳ chọn):",
            placeholder="Ví dụ: Cơ chế bảo vệ kỳ diệu của dạ dày người",
            help="Nếu để trống, hệ thống sẽ tự động lấy câu đầu tiên của kịch bản làm tên dự án."
        )
        custom_script_input = st.text_area(
            "📝 Dán toàn bộ kịch bản / lời thoại có sẵn của bạn vào đây:",
            placeholder="Dán toàn bộ bài viết, đoạn văn hoặc kịch bản của bạn vào đây...\n"
                        "Hệ thống sẽ giữ nguyên vẹn 100% từng câu từ của bạn và tự động chia thành các phân cảnh 3-5 giây kèm hình ảnh cắt dán tương ứng.",
            height=160
        )
        st.info("💡 **Cam kết bảo toàn:** 100% câu chữ của bạn sẽ được giữ nguyên vẹn, không bị AI tự ý sửa hay lược bớt.")

    col_mode, col_art = st.columns(2)
    with col_mode:
        mode = st.radio(
            "🎯 Chế độ Vận Hành",
            options=["auto", "step_by_step"],
            format_func=lambda x: {
                "auto": "⚡ Tự động hoàn toàn (Auto Pipeline)",
                "step_by_step": "🛠️ Duyệt từng bước (Step-by-Step Studio)"
            }.get(x, x),
            help="⚡ Auto: Chạy liên tục từ Kịch bản đến Master Video.\n🛠️ Step-by-Step: Có toàn quyền xem duyệt và sửa kịch bản, lời thoại, ảnh trước khi render."
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
        # Kiểm tra điều kiện đầu vào theo từng mode
        valid = True
        if script_mode == "ai_generate" and not topic_input.strip():
            st.error("Vui lòng nhập chủ đề video để AI viết kịch bản!")
            valid = False
        elif script_mode == "custom_script" and not custom_script_input.strip():
            st.error("Vui lòng dán nội dung kịch bản / lời thoại sẵn có!")
            valid = False

        if valid:
            try:
                clean_voice = voice_preset
                if " — " in clean_voice:
                    clean_voice = clean_voice.split(" — ")[0].replace("⭐ ", "").strip()
                elif "📁 [Tự tải lên] " in clean_voice:
                    clean_voice = clean_voice.replace("📁 [Tự tải lên] ", "").strip()
                elif "default" in clean_voice.lower():
                    clean_voice = "default"

                effective_topic = topic_input.strip()
                if not effective_topic and custom_script_input:
                    effective_topic = custom_script_input.strip()[:40]

                payload = {
                    "topic": effective_topic,
                    "style": style,
                    "language": language,
                    "format": format_type,
                    "quality": quality,
                    "mode": mode,
                    "art_style": art_style,
                    "voice_preset": clean_voice,
                    "script_mode": script_mode,
                    "custom_script_text": custom_script_input.strip() if script_mode == "custom_script" else None,
                    "script_style_id": selected_style_id if script_mode == "ai_generate" else None,
                    "custom_tone_instruction": custom_tone_instruction.strip() if custom_tone_instruction else None
                }
                res = api.post(f"{API_URL}/jobs", json=payload, timeout=30.0)
                res.raise_for_status()
                data = res.json()
                job_id = data['id']
                st.session_state["selected_job_id"] = job_id

                st.success(f"🎉 Khởi tạo dự án thành công! Job ID: `{job_id}`")
                st.info("💡 Bạn có thể chuyển sang trang **2. Phòng Thu & Duyệt 5 Bước** để kiểm duyệt chi tiết.")
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
        if st.button("🎬 Mở Ngay Trong Phòng Thu 5 Bước", key=f"jump_{jid}", type="primary"):
            try:
                st.switch_page("pages/preview_approve.py")
            except Exception:
                st.info("Vui lòng chọn trang '2. Phòng Thu & Duyệt 5 Bước' từ menu bên trái.")
    with c2:
        if st.button("📋 Xem Toàn Bộ Danh Sách Dự Án", key=f"list_{jid}"):
            try:
                st.switch_page("pages/job_list.py")
            except Exception:
                st.info("Vui lòng chọn trang '3. Danh Sách Dự Án' từ menu bên trái.")
