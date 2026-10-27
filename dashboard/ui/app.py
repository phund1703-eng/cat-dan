import os
import requests
import streamlit as st
from datetime import datetime

# Configure app layout once at the top
st.set_page_config(
    page_title="AutoVideoFactory - Xưởng Sản Xuất Video AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")


def fetch_api_jobs():
    """Lấy danh sách dự án nhanh từ API Backend."""
    try:
        res = requests.get(f"{API_URL}/jobs", timeout=2.5)
        if res.status_code == 200:
            return res.json(), True
    except Exception:
        pass
    return [], False


def render_sidebar_status(api_online: bool):
    """Hiển thị trạng thái hệ thống và dự án đang mở cố định ở thanh bên."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🖥️ Trạng Thái Hệ Thống")
        if api_online:
            st.success(f"🟢 Máy chủ API: Hoạt động (`{API_URL}`)")
        else:
            st.error(f"🔴 Máy chủ API: Chưa kết nối (`{API_URL}`)")

        selected_id = st.session_state.get("selected_job_id")
        if selected_id:
            st.info(f"🎯 **Đang chọn:** Dự án `{selected_id[:12] if len(selected_id) > 12 else selected_id}`")
            if st.button("🎬 Vào Phòng Thu Dự Án Này", use_container_width=True, key="side_btn_studio"):
                st.switch_page("pages/preview_approve.py")


def render_home_page():
    """Trang chủ - Trung tâm điều khiển toàn diện hệ thống AutoVideoFactory."""
    st.title("🎬 Trung Tâm Điều Khiển AutoVideoFactory")
    st.markdown(
        "Hệ thống tự động sản xuất video ngắn (**Shorts / Reels / TikTok**) bằng trí tuệ nhân tạo: "
        "Biên kịch phân cảnh Gemini, giọng đọc VieNeu-TTS tiếng Việt, tư liệu cắt dán collage và nhịp chuyển động sống động."
    )
    st.markdown("---")

    jobs, api_online = fetch_api_jobs()

    # Hàng 1: Thẻ chỉ số tổng quan (KPI Metrics)
    total_jobs = len(jobs)
    processing_jobs = sum(1 for j in jobs if j.get("status") in ("processing", "pending"))
    done_jobs = sum(1 for j in jobs if j.get("status") in ("done", "approved", "published"))
    failed_jobs = sum(1 for j in jobs if j.get("status") in ("failed", "publish_failed", "rejected"))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📦 Tổng Số Dự Án", total_jobs)
    with c2:
        st.metric("⏳ Đang Xử Lý / Chờ Duyệt", processing_jobs)
    with c3:
        st.metric("✅ Hoàn Thành Xuất Video", done_jobs)
    with c4:
        st.metric("❌ Cần Xử Lý / Lỗi", failed_jobs)

    st.markdown("---")

    # Hàng 2: Nút thao tác nhanh (Quick Actions)
    st.subheader("⚡ Thao Tác Nhanh")
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("➕ Bắt Đầu Tạo Video Mới", type="primary", use_container_width=True):
            st.switch_page("pages/create_video.py")
    with q2:
        if st.button("🎬 Mở Phòng Thu & Duyệt 5 Bước", use_container_width=True):
            st.switch_page("pages/preview_approve.py")
    with q3:
        if st.button("📋 Xem Toàn Bộ Danh Sách Dự Án", use_container_width=True):
            st.switch_page("pages/job_list.py")

    st.markdown("---")

    # Hàng 3: Danh sách dự án gần đây & Tiến độ làm việc
    st.subheader("🔥 Tiến Trình Dự Án Gần Nhất")
    if not api_online:
        st.warning(
            f"⚠️ Không thể kết nối tới máy chủ backend tại `{API_URL}`. "
            "Vui lòng kiểm tra lại tiến trình FastAPI (chạy qua file AutoVideoFactory.bat hoặc `python -m dashboard.api.main`)."
        )
        return

    if not jobs:
        st.info("Chưa có dự án nào được tạo. Hãy bấm nút **'➕ Bắt Đầu Tạo Video Mới'** ở trên để làm video đầu tiên!")
        return

    # Sắp xếp mới nhất lên đầu
    sorted_jobs = sorted(jobs, key=lambda x: x.get("created_at") or "", reverse=True)[:6]

    for job in sorted_jobs:
        job_id = job.get("id", "")
        topic = job.get("topic", "Không có tiêu đề")
        status = job.get("status", "pending")
        stage = job.get("stage", "pending")
        p_data = job.get("pipeline_data") or {}
        progress = p_data.get("progress") or {}

        percent = int(progress.get("percent", 0))
        current_step_text = progress.get("current_step")
        if not current_step_text:
            stage_vn_map = {
                "pending": "Chờ khởi tạo kịch bản",
                "script_ready": "Đã có kịch bản (Bước 1)",
                "source_review": "Đang kiểm chứng nguồn tư liệu",
                "voice_ready": "Đã có giọng đọc (Bước 2)",
                "assets_ready": "Đã có ảnh Storyboard (Bước 3)",
                "rendering": "Đang dựng video & hiệu ứng (Bước 4)",
                "done": "Đã hoàn thành xuất video (Bước 5)",
                "failed": "Gặp lỗi trong xử lý",
            }
            current_step_text = stage_vn_map.get(stage, stage)

        if status == "done":
            percent = 100
        elif status == "failed":
            percent = 0

        with st.container(border=True):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                st.markdown(f"**🎬 {topic}** `[ID: {job_id[:10]}...]`")
                # Hiển thị thanh tiến độ
                st.progress(max(0.0, min(1.0, percent / 100.0)))
                st.caption(f"📍 **Bước:** {current_step_text} | **Tiến độ:** `{percent}%` | **Trạng thái:** `{status.upper()}`")
            with col_action:
                st.write("")
                if st.button("🛠️ Mở Phòng Thu", key=f"open_studio_{job_id}", use_container_width=True):
                    st.session_state["selected_job_id"] = job_id
                    st.switch_page("pages/preview_approve.py")


# Khai báo cấu trúc điều hướng mới (Sidebar Navigation)
home_page = st.Page(render_home_page, title="Trang Chủ & Điều Khiển", icon="🏠", default=True)
create_page = st.Page("pages/create_video.py", title="1. Tạo Dự Án Video Mới", icon="➕")
studio_page = st.Page("pages/preview_approve.py", title="2. Phòng Thu & Duyệt 5 Bước", icon="🎬")
list_page = st.Page("pages/job_list.py", title="3. Danh Sách Dự Án", icon="📋")
analytics_page = st.Page("pages/analytics.py", title="4. Thống Kê & Hiệu Suất", icon="📊")

pg = st.navigation(
    {
        "TỔNG QUAN": [home_page],
        "QUY TRÌNH SẢN XUẤT VIDEO": [create_page, studio_page],
        "QUẢN LÝ & BÁO CÁO": [list_page, analytics_page],
    }
)

# Chạy trang được chọn
pg.run()

# Cập nhật thông tin hệ thống cố định ở chân thanh bên
_, is_online = fetch_api_jobs()
render_sidebar_status(is_online)
