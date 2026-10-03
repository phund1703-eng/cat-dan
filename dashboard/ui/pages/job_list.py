"""
Job List Page (Requirement R5)
dashboard/ui/pages/job_list.py
"""
import os
import streamlit as st
import requests
import pandas as pd

API_URL = os.getenv('API_URL', 'http://localhost:8000')


# Task 5.4: session gọi API tự gắn X-API-Key (lấy từ SECRET_KEY trong env)
# cho các request GHI; khi SECRET_KEY chưa đặt thì không gắn gì (API mở).
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

st.title("📋 Danh Sách Dự Án Video")

def fetch_jobs_data():
    """Lấy danh sách công việc từ API hoặc fallback SQLite."""
    try:
        res = requests.get(f"{API_URL}/jobs", timeout=2.0)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                return data
    except Exception:
        pass

    try:
        from dashboard.api.database import SessionLocal, list_jobs
        db = SessionLocal()
        db_jobs = list_jobs(db)
        res = []
        for dj in db_jobs:
            res.append({
                "id": dj.id,
                "topic": dj.topic,
                "style": dj.style,
                "language": dj.language,
                "status": dj.status.value if hasattr(dj.status, "value") else str(dj.status),
                "stage": getattr(dj, "stage", "pending") or "pending",
                "mode": getattr(dj, "mode", "auto") or "auto",
                "art_style": getattr(dj, "art_style", "photorealistic") or "photorealistic",
                "voice_preset": getattr(dj, "voice_preset", "default") or "default",
                "created_at": dj.created_at.isoformat() if dj.created_at else "",
                "output_path": dj.output_path,
                "pipeline_data": dj.pipeline_data or {},
                "error": dj.error
            })
        db.close()
        return res
    except Exception:
        return []

col_f1, col_f2 = st.columns([3, 1])
with col_f1:
    filter_stage = st.selectbox(
        "🔍 Lọc theo Giai đoạn (Stage):",
        options=[
            "Tất cả",
            "pending",
            "script_ready",
            "voice_ready",
            "assets_ready",
            "rendering",
            "done",
            "scheduled",
            "published",
            "failed"
        ],
        format_func=lambda s: {
            "Tất cả": "Tất cả các giai đoạn",
            "pending": "⏳ Đang chờ (pending)",
            "script_ready": "📝 Kịch bản xong (script_ready)",
            "voice_ready": "🎙️ Voice xong (voice_ready)",
            "assets_ready": "🖼️ Chờ duyệt ảnh (assets_ready)",
            "rendering": "🎬 Đang render (rendering)",
            "done": "✅ Hoàn thành (done)",
            "scheduled": "📅 Đã lên lịch (scheduled)",
            "published": "🚀 Đã đăng (published)",
            "failed": "❌ Thất bại (failed)"
        }.get(s, s)
    )
with col_f2:
    st.write("")
    if st.button("🔄 Làm mới"):
        st.rerun()

jobs = fetch_jobs_data()

if filter_stage != "Tất cả":
    jobs = [j for j in jobs if j.get("stage") == filter_stage]

if not jobs:
    st.info("ℹ️ Không tìm thấy dự án video nào phù hợp.")
else:
    stage_badges = {
        "pending": "⏳ Đang chờ",
        "script_ready": "📝 Kịch bản xong",
        "voice_ready": "🎙️ Voice xong",
        "assets_ready": "🖼️ Chờ duyệt ảnh (Step-by-Step)",
        "rendering": "🎬 Đang render",
        "done": "✅ Hoàn thành",
        "scheduled": "📅 Đã lên lịch đăng",
        "published": "🚀 Đã đăng",
        "publish_failed": "⚠️ Đăng thất bại (video vẫn xong)",
        "failed": "❌ Thất bại"
    }

    df_records = []
    for j in jobs:
        stg = j.get("stage", "pending")
        mode = j.get("mode", "auto")
        badge = stage_badges.get(stg, stg)
        if mode == "auto" and stg == "assets_ready":
            badge = "🖼️ Storyboard xong (Auto)"

        created_str = str(j.get("created_at", ""))[:19].replace("T", " ")
        publish_info = (j.get("pipeline_data") or {}).get("publish") or {}
        scheduled_str = str(publish_info.get("scheduled_at", ""))[:19].replace("T", " ")

        df_records.append({
            "Job ID": j["id"][:8] + "...",
            "Chủ đề": j.get("topic", "N/A"),
            "Chế độ": "🛠️ Step-by-Step" if mode == "step_by_step" else "⚡ Auto",
            "Giai đoạn": badge,
            "Trạng thái": j.get("status", "pending"),
            "Đăng dự kiến": scheduled_str or "—",
            "Mỹ thuật": j.get("art_style", "photorealistic"),
            "Ngày tạo": created_str,
            "full_id": j["id"]
        })

    display_df = pd.DataFrame(df_records).drop(columns=["full_id"])
    st.dataframe(display_df, use_container_width=True)

    st.subheader("⚡ Thao Tác Nhanh")
    action_job_id = st.selectbox(
        "Chọn dự án để thao tác:",
        options=[r["full_id"] for r in df_records],
        format_func=lambda jid: next(
            (f"{r['Chủ đề']} ({jid[:8]}...) — {r['Giai đoạn']}" for r in df_records if r['full_id'] == jid),
            jid
        )
    )

    if action_job_id:
        sel_job = next(j for j in jobs if j['id'] == action_job_id)
        c_act1, c_act2, c_act3 = st.columns(3)

        with c_act1:
            if st.button("🔍 Soi Quy Trình (Timeline Feed)", type="primary", use_container_width=True):
                st.session_state["selected_job_id"] = action_job_id
                try:
                    st.switch_page("pages/preview_approve.py")
                except Exception:
                    st.info("Vui lòng chọn trang 'Xem Trước & Phê Duyệt' từ menu bên trái.")

        with c_act2:
            if sel_job.get("status") == "failed" or sel_job.get("stage") == "failed":
                if st.button("🔁 Thử lại dự án này", use_container_width=True):
                    try:
                        r = api.post(f"{API_URL}/jobs/{action_job_id}/retry", timeout=5.0)
                        if r.status_code == 200:
                            st.success("Đang kích hoạt thử lại dự án!")
                            st.rerun()
                        else:
                            st.error(f"Lỗi: {r.text}")
                    except Exception as e:
                        st.error(f"Lỗi kết nối: {e}")
            else:
                st.button("🔁 Thử lại (chỉ khi lỗi)", disabled=True, use_container_width=True)

        with c_act3:
            if st.button("🗑️ Xóa dự án", use_container_width=True):
                try:
                    r = api.delete(f"{API_URL}/jobs/{action_job_id}", timeout=5.0)
                    if r.status_code == 200:
                        st.success("Đã xóa dự án thành công!")
                        if st.session_state.get("selected_job_id") == action_job_id:
                            del st.session_state["selected_job_id"]
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {r.text}")
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}")
