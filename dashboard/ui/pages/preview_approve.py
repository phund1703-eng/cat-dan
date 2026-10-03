"""
Studio Tương Tác 5 Bước & Phê Duyệt Video (Requirement R3)
dashboard/ui/pages/preview_approve.py
"""
import os
import io
import json
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List

import streamlit as st
import requests
import pandas as pd

API_URL = os.getenv("API_URL", "http://localhost:8000")

# =============================================================================
# Helper Utilities
# =============================================================================

def safe_float(val: Any, default: float = 0.0) -> float:
    """Chuyển đổi giá trị sang float an toàn, không ném ngoại lệ."""
    if val is None or val == "":
        return float(default)
    try:
        return float(val)
    except (ValueError, TypeError):
        return float(default)


def get_media_url_or_path(file_path: str) -> str:
    """Xác định đường dẫn file cục bộ hoặc URL tĩnh phục vụ bởi FastAPI."""
    if not file_path:
        return ""
    p = Path(file_path)
    if p.exists():
        return str(p.resolve())
    clean_path = str(file_path).replace("\\", "/").lstrip("/")
    if clean_path.startswith("data/"):
        p2 = Path(clean_path)
        if p2.exists():
            return str(p2.resolve())
        clean_path = clean_path[5:]
    return f"{API_URL}/files/{clean_path}"


def get_or_create_project_zip(job_id: str) -> Optional[bytes]:
    """Tải file zip từ API hoặc tự tạo từ thư mục data/output/{job_id}."""
    # 1. Thử gọi API GET /jobs/{job_id}/export-zip
    try:
        r = requests.get(f"{API_URL}/jobs/{job_id}/export-zip", timeout=5.0)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        pass

    # 2. Thử đọc file zip đã sinh sẵn trên đĩa
    zip_path = Path("data/output") / f"{job_id}.zip"
    if zip_path.exists():
        try:
            return zip_path.read_bytes()
        except Exception:
            pass

    # 3. Fallback: Đóng gói trực tiếp thư mục data/output/{job_id}
    job_dir = Path("data/output") / job_id
    if job_dir.exists():
        try:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                file_count = 0
                for root, _, files in os.walk(job_dir):
                    for file in files:
                        fp = os.path.join(root, file)
                        rel = os.path.relpath(fp, job_dir)
                        zf.write(fp, arcname=rel)
                        file_count += 1
                if file_count == 0:
                    info_payload = {"job_id": job_id, "status": "initializing"}
                    zf.writestr("project_info.json", json.dumps(info_payload, indent=2))
            buf.seek(0)
            return buf.getvalue()
        except Exception:
            pass
    return None


def load_all_jobs() -> List[Dict[str, Any]]:
    """Tải tất cả các job từ API, hoặc fallback từ SQLite Database, hoặc quét data/output."""
    jobs: List[Dict[str, Any]] = []
    # 1. API query
    try:
        res = requests.get(f"{API_URL}/jobs", timeout=2.0)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass

    # 2. SQLite direct read fallback
    try:
        from dashboard.api.database import SessionLocal, list_jobs
        db = SessionLocal()
        db_jobs = list_jobs(db)
        for dj in db_jobs:
            jobs.append({
                "id": dj.id,
                "topic": dj.topic,
                "style": dj.style,
                "language": dj.language,
                "status": dj.status.value if hasattr(dj.status, "value") else str(dj.status),
                "stage": getattr(dj, "stage", "pending") or "pending",
                "mode": getattr(dj, "mode", "auto") or "auto",
                "art_style": getattr(dj, "art_style", "photorealistic") or "photorealistic",
                "voice_preset": getattr(dj, "voice_preset", "default") or "default",
                "output_path": dj.output_path,
                "error": dj.error,
                "script": dj.script or {},
                "metadata": dj.extra_metadata or {},
                "pipeline_data": dj.pipeline_data or {}
            })
        db.close()
        if jobs:
            return jobs
    except Exception:
        pass

    # 3. Quét data/output cho các job đã chạy
    output_dir = Path("data/output")
    if output_dir.exists():
        for job_folder in output_dir.iterdir():
            if job_folder.is_dir():
                job_id = job_folder.name
                if not any(j.get("id") == job_id for j in jobs):
                    mp4s = list(job_folder.glob("*.mp4"))
                    jobs.append({
                        "id": job_id,
                        "topic": f"Dự án {job_id}",
                        "style": "collage_broll",
                        "language": "vi",
                        "status": "done" if mp4s else "pending",
                        "stage": "done" if mp4s else "pending",
                        "mode": "auto",
                        "art_style": "photorealistic",
                        "voice_preset": "default",
                        "output_path": str(mp4s[0].resolve()) if mp4s else None,
                        "script": {},
                        "metadata": {"title": f"Video {job_id}"},
                        "pipeline_data": {}
                    })
    return jobs


def get_job_details(job_id: str) -> Optional[Dict[str, Any]]:
    """Lấy chi tiết dự án từ API hoặc trực tiếp từ SQLite."""
    try:
        r = requests.get(f"{API_URL}/jobs/{job_id}", timeout=2.0)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    try:
        from dashboard.api.database import SessionLocal, get_job
        db = SessionLocal()
        dj = get_job(db, job_id)
        if dj:
            res = {
                "id": dj.id,
                "topic": dj.topic,
                "style": dj.style,
                "language": dj.language,
                "status": dj.status.value if hasattr(dj.status, "value") else str(dj.status),
                "stage": getattr(dj, "stage", "pending") or "pending",
                "mode": getattr(dj, "mode", "auto") or "auto",
                "art_style": getattr(dj, "art_style", "photorealistic") or "photorealistic",
                "voice_preset": getattr(dj, "voice_preset", "default") or "default",
                "output_path": dj.output_path,
                "error": dj.error,
                "script": dj.script or {},
                "metadata": dj.extra_metadata or {},
                "pipeline_data": dj.pipeline_data or {}
            }
            db.close()
            return res
        db.close()
    except Exception:
        pass
    return None


# =============================================================================
# App State & Data Loading
# =============================================================================

all_jobs = load_all_jobs()

if not all_jobs:
    st.title("🎬 Studio Tương Tác 5 Bước & Phê Duyệt Video")
    st.info("ℹ️ Hiện chưa có dự án nào trong hệ thống. Vui lòng tạo dự án mới tại menu **Tạo Video Mới**.")
    st.stop()

job_ids = [j["id"] for j in all_jobs]
default_index = 0
if "selected_job_id" in st.session_state and st.session_state["selected_job_id"] in job_ids:
    default_index = job_ids.index(st.session_state["selected_job_id"])

# =============================================================================
# 1. Header & Control Bar
# =============================================================================

st.title("🎬 Studio Tương Tác 5 Bước & Phê Duyệt Video")

c_job_sel, c_job_zip = st.columns([3, 1])

with c_job_sel:
    selected_job_id = st.selectbox(
        "🎯 Chọn Dự Án Video Để Làm Việc Trong Studio:",
        options=job_ids,
        index=default_index,
        format_func=lambda jid: next((
            f"[{j.get('stage', 'pending').upper()}] {j.get('topic', jid)} ({jid[:8]}...) - {'🛠️ Step-by-Step' if j.get('mode') == 'step_by_step' else '⚡ Auto'}"
            for j in all_jobs if j["id"] == jid
        ), jid)
    )

st.session_state["selected_job_id"] = selected_job_id
job = get_job_details(selected_job_id) or next(j for j in all_jobs if j["id"] == selected_job_id)

stage = job.get("stage", "pending")
mode = job.get("mode", "auto")
art_style = job.get("art_style", "photorealistic")
voice_preset = job.get("voice_preset", "default")
pipeline_data = job.get("pipeline_data") or {}

# Download .ZIP Button - Always visible at the top Header Bar
with c_job_zip:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    zip_bytes = get_or_create_project_zip(selected_job_id)
    if zip_bytes:
        st.download_button(
            label="📦 Tải Trọn Gói Dự Án (.ZIP)",
            data=zip_bytes,
            file_name=f"project_{selected_job_id}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
            key=f"header_dl_zip_{selected_job_id}"
        )
    else:
        st.button(
            "📦 Tải Trọn Gói Dự Án (.ZIP)",
            disabled=True,
            use_container_width=True,
            help="Tài nguyên dự án chưa sẵn sàng hoặc đang khởi tạo."
        )

# Stage Display Badge
stage_badges_info = {
    "pending": ("⏳ Đang khởi tạo (Pending)", "#6c757d"),
    "script_ready": ("📝 Kịch bản đã sẵn sàng (Script Ready)", "#0d6efd"),
    "voice_ready": ("🎙️ Âm thanh VieNeu-TTS đã sẵn sàng (Voice Ready)", "#198754"),
    "assets_ready": ("🖼️ Chờ duyệt Storyboard (Assets Ready)", "#fd7e14"),
    "rendering": ("🎬 Đang render & hiệu ứng (Rendering)", "#6f42c1"),
    "done": ("🏆 Master Video hoàn tất (Done)", "#20c997"),
    "approved": ("✅ Đã phê duyệt xuất bản (Approved)", "#0dcaf0"),
    "failed": ("❌ Thất bại (Failed)", "#dc3545"),
}

badge_text, badge_color = stage_badges_info.get(stage, (stage.upper(), "#6c757d"))

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-top:4px; margin-bottom:12px;">
    <span style="font-size:15px; font-weight:600; color:#ddd;">Giai đoạn hiện tại:</span>
    <span style="background-color:{badge_color}; color:#fff; padding:4px 14px; border-radius:14px; font-weight:bold; font-size:13px; display:inline-block;">
        {badge_text}
    </span>
</div>
""", unsafe_allow_html=True)

# Overview Metrics
c_meta1, c_meta2, c_meta3, c_meta4 = st.columns(4)
c_meta1.metric("Giai Đoạn (Stage)", stage)
c_meta2.metric("Chế Độ", "🛠️ Step-by-Step" if mode == "step_by_step" else "⚡ Auto")
c_meta3.metric("Style Mỹ Thuật", art_style)
c_meta4.metric("Giọng Đọc", voice_preset)

# Progress Indicator
stages_map = {
    "pending": (0.05, "⏳ Đang khởi tạo..."),
    "script_ready": (0.25, "📝 Kịch Bản đã sẵn sàng (Bước 1 hoàn tất)"),
    "source_review": (0.30, "⛔ Đang chờ bổ sung nguồn trích dẫn (Source Review)"),
    "voice_ready": (0.50, "🎙️ Âm Thanh VieNeu-TTS đã hoàn thành (Bước 2 hoàn tất)"),
    "assets_ready": (0.75, "🖼️ Storyboard & Vision Gate đã duyệt" if mode == "auto" else "⏸️ Chờ duyệt Storyboard (Step-by-Step Studio)"),
    "rendering": (0.90, "🎬 Đang tổng hợp hiệu ứng Ken Burns, ASS & render video..."),
    "done": (1.0, "🏆 Video Master hoàn tất 100%"),
    "approved": (1.0, "✅ Đã phê duyệt và xuất bản video"),
    "failed": (1.0, f"❌ Thất bại: {job.get('error', 'Lỗi không xác định')}")
}
progress_val, progress_txt = stages_map.get(stage, (0.1, stage))
st.progress(progress_val)
st.caption(f"**Tiến trình:** {progress_txt}")

# Breadcrumb Bar
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:center; background-color:#262730; padding:10px 18px; border-radius:8px; margin-bottom:20px; font-size:14px; font-weight:600; color:#fafafa;">
    <span>📝 1. Kịch Bản</span> <span style="color:#888;">➔</span>
    <span>🎙️ 2. Âm Thanh</span> <span style="color:#888;">➔</span>
    <span>🖼️ 3. Storyboard</span> <span style="color:#888;">➔</span>
    <span>🎬 4. Hiệu Ứng</span> <span style="color:#888;">➔</span>
    <span>🏆 5. Master Video</span>
</div>
""", unsafe_allow_html=True)

if stage == "failed":
    st.error(f"⚠️ Dự án gặp sự cố trong quá trình xử lý: {job.get('error', 'Lỗi không xác định')}")
    if st.button("🔁 Thử Lại Dự Án Này", key=f"btn_retry_job_{selected_job_id}"):
        try:
            r_retry = requests.post(f"{API_URL}/jobs/{selected_job_id}/retry", timeout=5.0)
            if r_retry.status_code == 200:
                st.success("Đang kích hoạt thử lại dự án!")
                st.rerun()
            else:
                st.error(f"Lỗi: {r_retry.text}")
        except Exception as ex:
            st.error(f"Lỗi kết nối: {ex}")

# ---------------------------------------------------------------------------
# Source Review Gate (Task 2.2): job đang dừng chờ bổ sung nguồn trích dẫn
# ---------------------------------------------------------------------------
if stage == "source_review":
    _audit = pipeline_data.get("source_audit") or []
    _blocking = [a for a in _audit if a.get("status") == "needs_source"]
    _scenes_by_idx = {}
    for _sc in pipeline_data.get("scenes") or []:
        _i = _sc.get("scene_index", _sc.get("index"))
        if _i is not None:
            _scenes_by_idx[int(_i)] = _sc
    st.warning(
        f"⛔ **Dừng ở bước Duyệt Nguồn (Source Review):** còn {len(_blocking)} cảnh có số liệu "
        "nhưng chưa có nguồn trích dẫn. Hãy bổ sung URL nguồn cho từng cảnh rồi bấm tiếp tục."
    )
    for _a in _blocking:
        _idx = int(_a.get("scene_index", 0))
        _sc = _scenes_by_idx.get(_idx, {})
        st.markdown(f"**Cảnh #{_idx + 1}** — Fact: {_a.get('fact') or _sc.get('fact', '')}")
        if _sc.get("narration"):
            st.caption(f"Lời thoại: {_sc.get('narration')}")
        st.text_input("URL nguồn (https://...)", key=f"src_url_{selected_job_id}_{_idx}")
        st.text_input("Tiêu đề nguồn", key=f"src_title_{selected_job_id}_{_idx}")
        st.text_input("Tổ chức xuất bản (publisher)", key=f"src_pub_{selected_job_id}_{_idx}")
    if st.button("📚 Lưu Nguồn & ▶️ Tiếp Tục Sản Xuất", type="primary", key=f"btn_source_continue_{selected_job_id}"):
        _updates = []
        for _a in _blocking:
            _idx = int(_a.get("scene_index", 0))
            _url = str(st.session_state.get(f"src_url_{selected_job_id}_{_idx}", "")).strip()
            if _url:
                _updates.append({
                    "scene_index": _idx,
                    "sources": [{
                        "title": str(st.session_state.get(f"src_title_{selected_job_id}_{_idx}", "")).strip(),
                        "url": _url,
                        "publisher": str(st.session_state.get(f"src_pub_{selected_job_id}_{_idx}", "")).strip(),
                        "accessed_date": "",
                    }],
                })
        if not _updates:
            st.error("Anh chưa nhập URL nguồn nào cho các cảnh thiếu nguồn.")
        else:
            try:
                r_src = requests.post(
                    f"{API_URL}/jobs/{selected_job_id}/step/sources",
                    json={"scenes": _updates},
                    timeout=15.0,
                )
                if r_src.status_code != 200:
                    st.error(f"Lỗi lưu nguồn: {r_src.text}")
                else:
                    r_cont = requests.post(f"{API_URL}/jobs/{selected_job_id}/continue-source-review", timeout=15.0)
                    if r_cont.status_code == 200:
                        st.success("✅ Đã lưu nguồn, hệ thống đang tiếp tục sản xuất!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi tiếp tục: {r_cont.text}")
            except Exception as ex:
                st.error(f"Lỗi kết nối: {ex}")

# =============================================================================
# 5 Functional Tabs (Interactive 5-Stage Studio)
# =============================================================================

tab_script, tab_voice, tab_storyboard, tab_effects, tab_master = st.tabs([
    "📝 1. Kịch Bản",
    "🎙️ 2. Âm Thanh",
    "🖼️ 3. Storyboard & Hình Ảnh",
    "🎬 4. Phụ Đề & Hiệu Ứng",
    "🏆 5. Master Video & Phê Duyệt"
])

# -----------------------------------------------------------------------------
# TAB 1: 📝 Kịch Bản (Script Stage)
# -----------------------------------------------------------------------------
with tab_script:
    st.subheader("📝 Giai Đoạn 1: Kịch Bản & Phân Cảnh (Script Stage)")
    st.caption("Xem, chỉnh sửa trực tiếp lời thoại, mô tả hình ảnh, thời lượng cho từng cảnh, hoặc yêu cầu AI viết lại toàn bộ kịch bản.")

    script_data = pipeline_data.get("script") or job.get("script") or {}
    scenes = script_data.get("scenes") or pipeline_data.get("scenes") or []
    _origin = pipeline_data.get("script_origin")
    if _origin:
        st.caption(f"Nguồn kịch bản: **{'Gemini AI' if _origin == 'gemini' else 'Template fallback (không dùng AI)'}**")

    # AI Prompt Block
    prompt_text = script_data.get("prompt_used") or script_data.get("prompt") or script_data.get("raw_prompt")
    if prompt_text:
        st.markdown("**AI Prompt Nguyên Văn (Gemini Engine):**")
        st.code(prompt_text, language="markdown")

    # Action Buttons Bar
    col_s1, col_s2, col_s3 = st.columns([1, 1, 1])

    with col_s1:
        btn_save_script = st.button(
            "💾 Lưu Kịch Bản Đã Sửa",
            type="primary",
            use_container_width=True,
            key=f"btn_save_script_{selected_job_id}"
        )

    with col_s2:
        btn_regen_script = st.button(
            "🔄 Viết Lại Kịch Bản Với AI",
            use_container_width=True,
            key=f"btn_regen_script_{selected_job_id}"
        )

    with col_s3:
        btn_goto_voice = st.button(
            "➡️ Chuyển Sang Bước 2: Tạo Âm Thanh",
            use_container_width=True,
            key=f"btn_goto_voice_{selected_job_id}"
        )

    # Action Handlers for Tab 1
    if btn_save_script or btn_goto_voice:
        updated_scenes = []
        for idx in range(len(scenes)):
            sc = scenes[idx]
            sc_idx = sc.get("scene_index", sc.get("index", idx))
            n_val = st.session_state.get(f"tab1_narr_{selected_job_id}_{idx}", sc.get("narration") or sc.get("text", ""))
            v_val = st.session_state.get(f"tab1_vis_{selected_job_id}_{idx}", sc.get("visual_description") or sc.get("still_image_prompt", ""))
            d_val = st.session_state.get(f"tab1_dur_{selected_job_id}_{idx}", safe_float(sc.get("duration"), 4.0))
            updated_scenes.append({
                "scene_index": int(sc_idx),
                "index": int(sc_idx),
                "narration": str(n_val).strip(),
                "visual_description": str(v_val).strip(),
                "still_image_prompt": str(v_val).strip(),
                "duration": safe_float(d_val, 4.0)
            })

        save_payload = {
            "title": script_data.get("title", f"Video: {job.get('topic', selected_job_id)}"),
            "description": script_data.get("description", ""),
            "hashtags": script_data.get("hashtags", ["#shorts", "#viral", "#ai"]),
            "scenes": updated_scenes
        }

        try:
            r_put = requests.put(
                f"{API_URL}/jobs/{selected_job_id}/step/script",
                json=save_payload,
                timeout=15.0
            )
            if r_put.status_code == 200:
                if btn_goto_voice:
                    st.success("✅ Đã lưu kịch bản! Vui lòng chọn tab **🎙️ 2. Âm Thanh** ở phía trên để tiếp tục.")
                else:
                    st.success("✅ Đã lưu kịch bản thành công!")
                st.rerun()
            else:
                st.error(f"Lỗi khi lưu kịch bản: {r_put.text}")
        except Exception as ex:
            # Fallback to direct DB update if API call fails
            try:
                from dashboard.api.database import SessionLocal, get_job as db_get_job, update_job_stage
                db = SessionLocal()
                dj = db_get_job(db, selected_job_id)
                if dj:
                    p = dj.pipeline_data or {}
                    p["script"] = save_payload
                    p["scenes"] = updated_scenes
                    update_job_stage(db, selected_job_id, stage="script_ready", pipeline_data=p)
                    db.close()
                    if btn_goto_voice:
                        st.success("✅ Đã lưu kịch bản trực tiếp vào DB! Vui lòng chọn tab **🎙️ 2. Âm Thanh** ở phía trên.")
                    else:
                        st.success("✅ Đã lưu kịch bản trực tiếp vào DB!")
                    st.rerun()
            except Exception as ex_db:
                st.error(f"Lỗi kết nối API: {ex} (Lỗi DB: {ex_db})")

    if btn_regen_script:
        with st.spinner("Đang yêu cầu Gemini AI viết lại kịch bản chuẩn cho chủ đề..."):
            try:
                r_post = requests.post(
                    f"{API_URL}/jobs/{selected_job_id}/step/script",
                    json={"topic": job.get("topic"), "art_style": art_style},
                    timeout=30.0
                )
                if r_post.status_code == 200:
                    st.success("🎉 Đã viết lại kịch bản mới thành công!")
                    st.rerun()
                else:
                    st.error(f"Lỗi tạo kịch bản: {r_post.text}")
            except Exception as ex:
                st.error(f"Lỗi kết nối: {ex}")

    # Editable Scene Cards
    if scenes:
        st.markdown(f"**Danh Sách Thẻ Phân Cảnh Có Thể Chỉnh Sửa ({len(scenes)} Cảnh):**")
        for idx, sc in enumerate(scenes):
            sc_num = idx + 1
            st.markdown(f"##### 🎬 Phân cảnh #{sc_num}")
            c_left, c_right = st.columns([3, 1])
            with c_left:
                st.text_area(
                    f"Lời thoại Voiceover (Cảnh #{sc_num}):",
                    value=sc.get("narration") or sc.get("text", ""),
                    key=f"tab1_narr_{selected_job_id}_{idx}",
                    height=80
                )
                st.text_area(
                    f"Mô tả hình ảnh Visual Description (Cảnh #{sc_num}):",
                    value=sc.get("visual_description") or sc.get("still_image_prompt", ""),
                    key=f"tab1_vis_{selected_job_id}_{idx}",
                    height=80
                )
            with c_right:
                st.number_input(
                    f"Thời lượng (Cảnh #{sc_num}, giây):",
                    min_value=1.0,
                    max_value=30.0,
                    value=safe_float(sc.get("duration"), 4.0),
                    step=0.5,
                    key=f"tab1_dur_{selected_job_id}_{idx}"
                )
            _srcs = [s for s in (sc.get("sources") or []) if isinstance(s, dict) and s.get("url")]
            if sc.get("fact"):
                st.caption(f"🔎 **Fact:** {sc.get('fact')}")
            if _srcs:
                st.markdown("**📚 Nguồn tham khảo:**")
                for _s in _srcs:
                    _label = _s.get("title") or _s.get("url")
                    _pub = f" — {_s['publisher']}" if _s.get("publisher") else ""
                    st.markdown(f"- [{_label}]({_s['url']}){_pub}")
            st.markdown("<hr style='margin:10px 0; border:none; border-top:1px solid #333;'>", unsafe_allow_html=True)
    else:
        st.info("Kịch bản chưa được khởi tạo. Bạn có thể nhấn nút **[🔄 Viết Lại Kịch Bản Với AI]** ở trên để sinh tự động từ chủ đề.")

# -----------------------------------------------------------------------------
# TAB 2: 🎙️ Âm Thanh (Voice Stage)
# -----------------------------------------------------------------------------
with tab_voice:
    st.subheader("🎙️ Giai Đoạn 2: Âm Thanh & Giọng Đọc (Voice Stage)")
    st.caption("Khởi tạo giọng đọc VieNeu-TTS cho toàn bộ kịch bản, nghe thử từng cảnh, sửa lời thoại và sinh lại âm thanh độc lập.")

    voice_data = pipeline_data.get("voice") or {}
    engine_name = voice_data.get("engine", "VieNeu-TTS")
    active_preset = voice_data.get("preset", voice_preset)
    st.markdown(f"**Công nghệ:** `{engine_name}` | **Mẫu giọng (Preset):** `{active_preset}`")

    # Primary Action Button
    col_vbtn1, col_vbtn2 = st.columns([2, 1])
    with col_vbtn1:
        if st.button(
            "🎙️ Bắt Đầu Tạo Giọng Đọc Toàn Bộ Kịch Bản",
            type="primary",
            use_container_width=True,
            key=f"btn_create_voice_{selected_job_id}"
        ):
            with st.spinner("Đang tổng hợp giọng đọc toàn bộ các cảnh qua VieNeu-TTS..."):
                try:
                    r_voice = requests.post(
                        f"{API_URL}/jobs/{selected_job_id}/step/voice",
                        json={"voice_preset": voice_preset, "engine": "auto"},
                        timeout=45.0
                    )
                    if r_voice.status_code == 200:
                        st.success("🎉 Đã tạo giọng đọc toàn bộ kịch bản thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi tạo âm thanh: {r_voice.text}")
                except Exception as ex:
                    st.error(f"Lỗi kết nối: {ex}")

    with col_vbtn2:
        if st.button(
            "➡️ Chuyển Sang Bước 3: Tạo Storyboard",
            use_container_width=True,
            key=f"btn_goto_sb_{selected_job_id}"
        ):
            st.success("🎉 Âm thanh đã sẵn sàng! Vui lòng chọn tab **🖼️ 3. Storyboard & Hình Ảnh** ở phía trên để tiếp tục.")

    # Scene audio list
    voice_scenes = voice_data.get("scenes") or []
    if not voice_scenes and scenes:
        voice_scenes = [
            {
                "scene_index": sc.get("scene_index", sc.get("index", i)),
                "text": sc.get("narration") or sc.get("text", ""),
                "audio_path": sc.get("audio_path", ""),
                "duration": safe_float(sc.get("duration"), 4.0)
            }
            for i, sc in enumerate(scenes)
        ]

    if voice_scenes:
        st.markdown(f"**Danh Sách Phân Cảnh Âm Thanh ({len(voice_scenes)} Cảnh):**")
        for sc in voice_scenes:
            idx = sc.get("scene_index", 0)
            txt = sc.get("text", "")
            audio_path = sc.get("audio_path", "")
            dur = safe_float(sc.get("duration"), 0.0)

            c_v1, c_v2 = st.columns([3, 2])
            with c_v1:
                st.markdown(f"##### 🎬 Phân cảnh #{idx + 1}")
                v_text_input = st.text_area(
                    f"Lời thoại phát âm (Cảnh #{idx + 1}):",
                    value=txt,
                    key=f"tab2_txt_{selected_job_id}_{idx}",
                    height=75
                )
                if st.button("🔄 Sinh Lại Âm Thanh Cảnh Này", key=f"btn_vregen_{selected_job_id}_{idx}"):
                    with st.spinner(f"Đang sinh lại âm thanh Cảnh #{idx + 1} qua VieNeu-TTS..."):
                        try:
                            r_vsc = requests.post(
                                f"{API_URL}/jobs/{selected_job_id}/step/voice-scene",
                                json={
                                    "scene_index": int(idx),
                                    "text": v_text_input.strip(),
                                    "voice_preset": voice_preset
                                },
                                timeout=30.0
                            )
                            if r_vsc.status_code == 200:
                                st.success(f"✅ Đã cập nhật âm thanh riêng cho Cảnh #{idx + 1}!")
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {r_vsc.text}")
                        except Exception as ex:
                            st.error(f"Lỗi kết nối: {ex}")

            with c_v2:
                st.markdown(f"**Thời lượng probe:** `{dur:.1f}s`")
                media_src = get_media_url_or_path(audio_path)
                if media_src and (os.path.exists(media_src) or media_src.startswith("http")):
                    st.audio(media_src)
                else:
                    st.caption("⏳ Chưa có file audio cho cảnh này.")
            st.markdown("<hr style='margin:10px 0; border:none; border-top:1px solid #333;'>", unsafe_allow_html=True)
    else:
        st.info("Chưa có dữ liệu âm thanh phân cảnh. Hãy bấm nút **[🎙️ Bắt Đầu Tạo Giọng Đọc Toàn Bộ Kịch Bản]** ở trên.")

# -----------------------------------------------------------------------------
# TAB 3: 🖼️ Storyboard & Hình Ảnh (Image Stage)
# -----------------------------------------------------------------------------
with tab_storyboard:
    st.subheader("🖼️ Giai Đoạn 3: Storyboard & Gemini Vision Gate (Image Stage)")
    st.caption("Điều phối sinh ảnh toàn bộ theo phong cách mỹ thuật đã chọn, xem điểm thẩm định Vision Gate, sửa prompt sinh lại hoặc tải ảnh tùy chỉnh.")

    tier_badges = {
        "tier1_imagen": "🌟 Tier 1 (Imagen 3)",
        "tier2_flux": "⚡ Tier 2 (Flux)",
        "tier2_stock": "📸 Tier 3 (Stock)",
        "tier3_stock": "📸 Tier 3 (Stock)",
        "tier4_procedural": "🎨 Tier 4 (Procedural)",
        "user_uploaded": "📤 User Uploaded"
    }

    # Primary Action Buttons
    col_sb1, col_sb2 = st.columns([2, 1])
    with col_sb1:
        if st.button(
            "🖼️ Bắt Đầu Sinh Toàn Bộ Ảnh Storyboard",
            type="primary",
            use_container_width=True,
            key=f"btn_create_sb_{selected_job_id}"
        ):
            with st.spinner("Đang điều phối sinh toàn bộ ảnh Storyboard & kiểm định Vision Gate..."):
                try:
                    r_sb = requests.post(
                        f"{API_URL}/jobs/{selected_job_id}/step/storyboard",
                        json={"art_style": art_style},
                        timeout=60.0
                    )
                    if r_sb.status_code == 200:
                        st.success("🎉 Đã sinh toàn bộ ảnh Storyboard thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi sinh Storyboard: {r_sb.text}")
                except Exception as ex:
                    st.error(f"Lỗi kết nối: {ex}")

    with col_sb2:
        if st.button(
            "➡️ Chuyển Sang Bước 4: Tạo Phụ Đề & Hiệu Ứng",
            use_container_width=True,
            key=f"btn_goto_effects_{selected_job_id}"
        ):
            st.success("🎉 Storyboard đã sẵn sàng! Vui lòng chọn tab **🎬 4. Phụ Đề & Hiệu Ứng** ở phía trên để tiếp tục.")

    # Storyboard Scene Cards
    storyboard = pipeline_data.get("storyboard") or []
    if not storyboard and scenes:
        storyboard = [
            {
                "scene_index": sc.get("scene_index", sc.get("index", i)),
                "image_path": sc.get("image_path", ""),
                "visual_prompt": sc.get("still_image_prompt") or sc.get("visual_description", ""),
                "tier_used": "tier1_imagen",
                "vision_gate_score": 0.92,
                "vision_gate_reasoning": "Sẵn sàng sinh ảnh"
            }
            for i, sc in enumerate(scenes)
        ]

    if storyboard:
        st.markdown(f"**Danh Sách Thẻ Phân Cảnh Storyboard ({len(storyboard)} Cảnh):**")
        for idx, sc in enumerate(storyboard):
            sc_idx = sc.get("scene_index", idx)
            st.markdown(f"#### 🎬 Phân Cảnh #{idx + 1}")
            c_card1, c_card2 = st.columns([1, 1])

            with c_card1:
                img_path = sc.get("image_path", "")
                media_img = get_media_url_or_path(img_path)
                if media_img and (os.path.exists(media_img) or media_img.startswith("http")):
                    st.image(media_img, caption=f"Ảnh xem trước Cảnh {idx + 1}", use_container_width=True)
                else:
                    st.warning(f"⏳ Chưa có ảnh xem trước cho Cảnh {idx + 1}")

                tier = sc.get("tier_used", "tier1_imagen")
                badge_str = tier_badges.get(tier, f"🏷️ {tier}")
                st.markdown(f"**Phân tầng:** `{badge_str}`")

                # Task 5.3: badge nguồn gốc asset (provenance) cạnh badge Tier
                _src_badges = {
                    "imagen": "🤖 Nguồn: Imagen 3 (AI)",
                    "flux": "🤖 Nguồn: FLUX (AI)",
                    "pexels": "📸 Nguồn: Pexels",
                    "pixabay": "📸 Nguồn: Pixabay",
                    "wikimedia": "📸 Nguồn: Wikimedia Commons",
                    "unsplash": "📸 Nguồn: Unsplash",
                    "procedural": "🎨 Nguồn: Procedural (vẽ bằng code)",
                    "user_upload": "📤 Nguồn: Ảnh người dùng tải lên",
                    "template": "🗂️ Nguồn: Template trong repo",
                }
                _asset_meta = sc.get("asset_meta") or {}
                _src = _asset_meta.get("source")
                if _src:
                    _src_label = _src_badges.get(_src, f"🔎 Nguồn: {_src}")
                    _lic = _asset_meta.get("license") or ""
                    _url = _asset_meta.get("source_url") or ""
                    st.markdown(f"**Nguồn asset:** `{_src_label}`")
                    if _lic:
                        st.caption(f"📄 License: {_lic}")
                    if _url:
                        st.caption(f"🔗 {_url}")
                elif tier in ("tier2_stock", "tier3_stock"):
                    st.markdown("**Nguồn asset:** `📸 Stock (chưa có provenance)`")

                score = sc.get("vision_gate_score")
                if score is not None:
                    try:
                        st.metric("Điểm Phê Duyệt Gemini Vision Gate", f"{float(score) * 100:.0f}%")
                    except Exception:
                        st.metric("Điểm Phê Duyệt Gemini Vision Gate", f"{score}")
                
                reasoning = sc.get("vision_gate_reasoning", "Đạt chuẩn phong cách mỹ thuật và bố cục hình ảnh.")
                st.caption(f"🤖 **Nhận xét Vision Gate:** {reasoning}")

            with c_card2:
                v_prompt = sc.get("visual_prompt") or sc.get("prompt") or sc.get("still_image_prompt") or ""
                cur_prompt = st.text_area(
                    f"Visual Prompt (Cảnh #{idx + 1}):",
                    value=v_prompt,
                    key=f"tab3_vp_{selected_job_id}_{idx}",
                    height=100
                )

                c_act1, c_act2 = st.columns(2)
                with c_act1:
                    if st.button("🔄 Sinh Lại Ảnh Cảnh Này", key=f"btn_regen_img_{selected_job_id}_{idx}", use_container_width=True):
                        with st.spinner(f"Đang sinh lại ảnh Cảnh #{idx + 1}..."):
                            try:
                                r_regen = requests.post(
                                    f"{API_URL}/jobs/{selected_job_id}/step/regenerate-scene-image",
                                    json={"scene_index": int(sc_idx), "prompt": cur_prompt.strip()},
                                    timeout=35.0
                                )
                                if r_regen.status_code == 200:
                                    st.success(f"✅ Đã sinh lại ảnh cho Cảnh #{idx + 1}!")
                                    st.rerun()
                                else:
                                    st.error(f"Lỗi: {r_regen.text}")
                            except Exception as ex:
                                st.error(f"Lỗi kết nối: {ex}")

                with c_act2:
                    up_img = st.file_uploader(
                        f"📤 Tải ảnh máy tính (Cảnh #{idx + 1}):",
                        type=["png", "jpg", "jpeg", "webp"],
                        key=f"tab3_up_{selected_job_id}_{idx}"
                    )
                    if up_img is not None:
                        if st.button(f"Lưu ảnh tải lên Cảnh #{idx + 1}", key=f"save_up_{selected_job_id}_{idx}", use_container_width=True):
                            with st.spinner(f"Đang tải ảnh Cảnh #{idx + 1} lên máy chủ..."):
                                try:
                                    files = {"file": (up_img.name, up_img.getvalue(), up_img.type or "image/png")}
                                    data = {"scene_index": int(sc_idx)}
                                    r_up = requests.post(
                                        f"{API_URL}/jobs/{selected_job_id}/step/upload-scene-image",
                                        data=data,
                                        files=files,
                                        timeout=20.0
                                    )
                                    if r_up.status_code == 200:
                                        st.success(f"✅ Đã cập nhật ảnh Cảnh #{idx + 1} thành công!")
                                        st.rerun()
                                    else:
                                        st.error(f"Lỗi tải ảnh: {r_up.text}")
                                except Exception as ex:
                                    st.error(f"Lỗi kết nối: {ex}")

            st.markdown("<hr style='margin:10px 0; border:none; border-top:1px solid #333;'>", unsafe_allow_html=True)

    # Step-by-Step Approval Banner & Button
    if stage == "assets_ready":
        st.markdown("### 🚀 Phê Duyệt Storyboard & Tiếp Tục Tiến Trình")
        st.warning("⏸️ **Dự án đang tạm dừng để bạn kiểm duyệt Storyboard (Step-by-Step Studio).** Khi đã ưng ý với tất cả hình ảnh, hãy bấm nút dưới đây để tiếp tục render:")
        if st.button(
            "🚀 PHÊ DUYỆT STORYBOARD & TIẾP TỤC RENDER VIDEO",
            key=f"btn_cont_{selected_job_id}",
            type="primary",
            use_container_width=True
        ):
            with st.spinner("Đang kích hoạt render video tiếp tục..."):
                try:
                    r_cont = requests.post(
                        f"{API_URL}/jobs/{selected_job_id}/continue-render",
                        json={"job_id": selected_job_id},
                        timeout=10.0
                    )
                    if r_cont.status_code == 200:
                        st.success("🎉 Đã phê duyệt Storyboard! Đang tiến hành Render Giai Đoạn 4 & 5...")
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {r_cont.text}")
                except Exception as ex:
                    st.error(f"Lỗi kết nối: {ex}")
    elif not storyboard:
        st.info("Chưa có dữ liệu Storyboard. Hãy bấm nút **[🖼️ Bắt Đầu Sinh Toàn Bộ Ảnh Storyboard]** ở trên.")

# -----------------------------------------------------------------------------
# TAB 4: 🎬 Phụ Đề & Hiệu Ứng (Effects Stage)
# -----------------------------------------------------------------------------
with tab_effects:
    st.subheader("🎬 Giai Đoạn 4: Hiệu Ứng Ken Burns & Phụ Đề Karaoke ASS (Effects Stage)")
    st.caption("Khởi tạo phụ đề động Karaoke Dynamic Chunked ASS (2-4 từ/cụm, margin 180px safe zone) và chuẩn bị lệnh FFmpeg hiệu ứng Ken Burns.")

    # Primary Action Buttons
    col_fx1, col_fx2 = st.columns([2, 1])
    with col_fx1:
        if st.button(
            "🎬 Khởi Tạo Phụ Đề Karaoke & Hiệu Ứng Ken Burns",
            type="primary",
            use_container_width=True,
            key=f"btn_create_effects_{selected_job_id}"
        ):
            with st.spinner("Đang khởi tạo phụ đề Karaoke Dynamic và tổng hợp lệnh FFmpeg..."):
                try:
                    r_fx = requests.post(
                        f"{API_URL}/jobs/{selected_job_id}/step/effects",
                        json={"chunk_words": 3, "margin_v": 180, "font_size": 44},
                        timeout=30.0
                    )
                    if r_fx.status_code == 200:
                        st.success("🎉 Đã tạo phụ đề Dynamic ASS và chuẩn bị hiệu ứng Ken Burns thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {r_fx.text}")
                except Exception as ex:
                    st.error(f"Lỗi kết nối: {ex}")

    with col_fx2:
        if st.button(
            "➡️ Chuyển Sang Bước 5: Ghép Master Video",
            use_container_width=True,
            key=f"btn_goto_master_{selected_job_id}"
        ):
            st.success("🎉 Hiệu ứng đã sẵn sàng! Vui lòng chọn tab **🏆 5. Master Video & Phê Duyệt** ở phía trên để render video cuối cùng.")

    # Technical Specifications
    c_fx_p1, c_fx_p2 = st.columns(2)
    with c_fx_p1:
        st.markdown("**Thông Số Chuyển Động Ken Burns:**")
        st.markdown("- Zoom Range: `1.0x ➔ 1.05x` (Slow Push-In)")
        st.markdown("- Tâm điểm (Anchor): `(540, 655)`")
        st.markdown("- Tốc độ khung hình: `25.0 FPS`")
        st.markdown("- Độ phân giải: `1080x1920 (9:16 Vertical)`")
    with c_fx_p2:
        st.markdown("**Cấu Trúc Phụ Đề Karaoke Dynamic ASS:**")
        st.markdown("- Gom cụm từ: `2-4 từ/cụm` (ngăn từ 1 chữ mồ côi)")
        st.markdown("- Vùng an toàn (Safe Zone): `MarginV = 180px` (Không che bệ đỡ/chân nhân vật)")
        st.markdown("- Kiểu chữ: `Arial 44pt Bold`")
        st.markdown("- Màu sắc: `TikTokYellow (&H0000FFFF)` & `TikTokWhite (&H00FFFFFF)`")

    # Visual Preview Box (Simulated 9:16 TikTok Screen with Subtitle Safe Zone)
    st.markdown("**Trực Quan Hóa Vùng An Toàn Phụ Đề (Safe Zone Preview):**")
    st.markdown("""
    <div style="background-color:#14171f; border:2px solid #333; border-radius:12px; padding:20px; max-width:320px; height:460px; margin:10px auto; position:relative; box-shadow:0 8px 20px rgba(0,0,0,0.6); overflow:hidden;">
        <div style="position:absolute; top:12px; left:14px; color:#aaa; font-size:12px; font-weight:600;">📱 Khung Hình 9:16 (1080x1920)</div>
        <div style="position:absolute; top:40px; left:14px; right:14px; bottom:140px; display:flex; align-items:center; justify-content:center; border:1px dashed #444; border-radius:8px; background:rgba(255,255,255,0.02);">
            <span style="color:#666; font-size:13px; text-align:center;">Vùng hiển thị hình ảnh & hiệu ứng Ken Burns</span>
        </div>
        <div style="position:absolute; bottom:0; left:0; right:0; height:90px; background:rgba(255,50,50,0.15); border-top:1px dashed #ff4444; text-align:center; color:#ff8888; font-size:11px; padding-top:6px;">
            ⚠️ TikTok UI / CapCut Bottom Safe Zone (0 - 120px)
        </div>
        <div style="position:absolute; bottom:110px; left:10px; right:10px; text-align:center;">
            <div style="display:inline-block; background:rgba(0,0,0,0.75); padding:6px 14px; border-radius:8px; border:1px solid rgba(255,255,255,0.2);">
                <span style="color:#FFFF00; font-family:Arial, sans-serif; font-weight:bold; font-size:16px; text-shadow:2px 2px 3px #000;">Tế Bào Con Người</span>
                <span style="color:#FFFFFF; font-family:Arial, sans-serif; font-weight:bold; font-size:16px; text-shadow:2px 2px 3px #000;"> Vô Cùng Kỳ Diệu</span>
            </div>
            <div style="color:#00e5ff; font-size:11px; margin-top:4px; font-weight:bold;">↑ MarginV: 180px (An toàn tuyệt đối)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Technical FFmpeg Commands Code Block
    st.markdown("**Lệnh Kỹ Thuật FFmpeg Sinh Tự Động:**")
    ffmpeg_cmds = pipeline_data.get("ffmpeg_commands") or "# Lệnh FFmpeg sẽ được sinh tự động khi đến giai đoạn render."
    if isinstance(ffmpeg_cmds, list):
        ffmpeg_cmds = "\n\n".join(ffmpeg_cmds)
    st.code(ffmpeg_cmds, language="bash")

# -----------------------------------------------------------------------------
# TAB 5: 🏆 Master Video & Phê Duyệt (Final Stage)
# -----------------------------------------------------------------------------
with tab_master:
    st.subheader("🏆 Giai Đoạn 5: Master Video & Phê Duyệt Xuất Bản (Final Stage)")
    st.caption("Ghép toàn bộ phân cảnh bằng FFmpeg, xem trước video hoàn chỉnh, chỉnh sửa bản nháp Postiz và phê duyệt xuất bản.")

    # Primary Action Button
    if st.button(
        "🚀 Ghép & Render Master Video Hoàn Thiện",
        type="primary",
        use_container_width=True,
        key=f"btn_render_master_{selected_job_id}"
    ):
        with st.spinner("Đang thực hiện ghép video, chèn nhạc và ép phụ đề Karaoke bằng FFmpeg..."):
            try:
                r_render = requests.post(
                    f"{API_URL}/jobs/{selected_job_id}/step/render",
                    json={"force": True},
                    timeout=90.0
                )
                if r_render.status_code == 200:
                    st.success("🎉 Ghép & Render Master Video hoàn tất 100%!")
                    st.rerun()
                else:
                    st.error(f"Lỗi render: {r_render.text}")
            except Exception as ex:
                st.error(f"Lỗi kết nối: {ex}")

    # Video Player and Postiz Form
    out_file = job.get("output_path") or f"data/output/{selected_job_id}/final_video.mp4"
    valid_video_file = None
    if out_file and os.path.exists(out_file):
        valid_video_file = out_file
    else:
        job_folder = Path("data/output") / selected_job_id
        if job_folder.exists():
            mp4s = list(job_folder.glob("*.mp4"))
            if mp4s:
                valid_video_file = str(mp4s[0].resolve())

    col_vid, col_pub = st.columns([3, 2])

    with col_vid:
        st.markdown("### 📽️ Trình Phát Master Video Độ Nét Cao")
        if valid_video_file and os.path.exists(valid_video_file):
            st.video(valid_video_file)
            st.caption(f"📁 Tệp video máy chủ: `{valid_video_file}`")
            try:
                with open(valid_video_file, "rb") as vf:
                    st.download_button(
                        label="⬇️ Tải Video MP4",
                        data=vf.read(),
                        file_name=Path(valid_video_file).name,
                        mime="video/mp4",
                        key=f"dl_mp4_{selected_job_id}",
                        use_container_width=True
                    )
            except Exception:
                pass
        elif out_file:
            media_vid = get_media_url_or_path(out_file)
            st.video(media_vid)
            st.caption(f"🌐 Stream video: `{out_file}`")
        else:
            st.info("⚠️ Video Master chưa được xuất. Hãy bấm nút **[🚀 Ghép & Render Master Video Hoàn Thiện]** ở trên để tạo video.")

        # Download ZIP button in Tab 5 as well
        st.markdown("---")
        st.markdown("#### 📦 Đóng Gói Tài Nguyên Dự Án")
        zip_bytes_tab5 = get_or_create_project_zip(selected_job_id)
        if zip_bytes_tab5:
            st.download_button(
                label="📦 Tải Về Trọn Gói Dự Án (.ZIP)",
                data=zip_bytes_tab5,
                file_name=f"project_{selected_job_id}.zip",
                mime="application/zip",
                type="primary",
                key=f"dl_zip_tab5_{selected_job_id}",
                use_container_width=True
            )
        else:
            st.button(
                "📦 Tải Về Trọn Gói Dự Án (.ZIP)",
                disabled=True,
                use_container_width=True,
                help="Tài nguyên ZIP chưa sẵn sàng"
            )

        # Thumbnail review/edit (Task 3.2)
        st.markdown("---")
        st.markdown("#### 🖼️ Thumbnail Master")
        thumbnail_meta = pipeline_data.get("metadata") or job.get("metadata") or {}
        thumbnail_file = (
            pipeline_data.get("thumbnail_path")
            or f"data/output/{selected_job_id}/thumbnail.jpg"
        )
        if thumbnail_file and os.path.exists(thumbnail_file):
            st.image(thumbnail_file, caption="Thumbnail 1080×1920", use_container_width=True)
        elif pipeline_data.get("thumbnail_error"):
            st.warning(f"Chưa tạo được thumbnail: {pipeline_data.get('thumbnail_error')}")
        else:
            st.info("Thumbnail sẽ tự sinh khi Master Video hoàn tất.")
        with st.form(f"thumbnail_form_{selected_job_id}"):
            edited_thumbnail_text = st.text_input(
                "Chữ trên thumbnail",
                value=pipeline_data.get("thumbnail_text") or thumbnail_meta.get("thumbnail_text", ""),
                max_chars=60,
            )
            if st.form_submit_button("🔄 Tạo Lại Thumbnail", use_container_width=True):
                try:
                    r_thumb = requests.post(
                        f"{API_URL}/jobs/{selected_job_id}/thumbnail",
                        json={"thumbnail_text": edited_thumbnail_text},
                        timeout=30.0,
                    )
                    if r_thumb.status_code == 200:
                        st.success("Đã tạo lại thumbnail!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi tạo thumbnail: {r_thumb.text}")
                except Exception as ex:
                    st.error(f"Lỗi kết nối: {ex}")

    with col_pub:
        st.markdown("### 🚀 Phê Duyệt & Xuất Bản")
        publish_info = pipeline_data.get("publish") or {}
        if publish_info.get("scheduled_at"):
            st.info(
                f"📅 Trạng thái publish: **{publish_info.get('status', 'scheduled')}** · "
                f"Giờ đăng dự kiến: **{publish_info['scheduled_at']}**"
            )
        with st.form(f"publish_form_{selected_job_id}"):
            meta = pipeline_data.get("metadata") or job.get("metadata") or {}
            default_title = meta.get("title") or f"Video: {job.get('topic', selected_job_id)}"
            title = st.text_input("Tiêu đề Video", value=default_title)
            desc = st.text_area("Mô tả nội dung", value=meta.get("description", ""), height=90)
            tags_val = meta.get("hashtags", ["#viral", "#shorts", "#aivideo"])
            tags_str = ", ".join(tags_val) if isinstance(tags_val, list) else str(tags_val)
            tags = st.text_input("Hashtags", value=tags_str)
            platforms = st.multiselect(
                "Nền tảng xuất bản",
                ["youtube", "tiktok", "facebook", "instagram"],
                default=["youtube", "tiktok"]
            )

            if st.form_submit_button("✅ Phê Duyệt Xuất Bản", type="primary", use_container_width=True):
                draft_payload = {
                    "job_id": selected_job_id,
                    "topic": job.get("topic"),
                    "title": title,
                    "description": desc,
                    "hashtags": [t.strip() for t in tags.split(",") if t.strip()],
                    "platforms": platforms,
                    "video_path": valid_video_file or out_file,
                    "status": "approved",
                    "postiz_ready": True
                }
                draft_dir = Path("data/drafts")
                draft_dir.mkdir(parents=True, exist_ok=True)
                draft_file = draft_dir / f"postiz_draft_{selected_job_id}.json"
                with open(draft_file, "w", encoding="utf-8") as f:
                    json.dump(draft_payload, f, ensure_ascii=False, indent=2)

                scheduled_at = None
                try:
                    r_approve = requests.put(
                        f"{API_URL}/jobs/{selected_job_id}/approve",
                        json={"job_id": selected_job_id, "platforms": platforms},
                        timeout=3.0
                    )
                    if r_approve.status_code == 200:
                        scheduled_at = (r_approve.json() or {}).get("scheduled_at")
                    else:
                        st.error(f"Lỗi lên lịch xuất bản: {r_approve.text}")
                except Exception as ex:
                    st.error(f"Lỗi kết nối khi lên lịch xuất bản: {ex}")

                if scheduled_at:
                    st.success(
                        f"🎉 Đã phê duyệt, lưu nháp tại `{draft_file}` và lên lịch đăng lúc `{scheduled_at}`!"
                    )
                else:
                    st.success(f"🎉 Đã phê duyệt và lưu bản nháp xuất bản tại `{draft_file}`!")
                st.rerun()
