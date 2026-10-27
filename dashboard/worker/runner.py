"""
AutoVideoFactory — Durable DB-polling worker (Task 4.1, thay Celery/Redis).

Chạy như một tiến trình riêng:

    python -m dashboard.worker.runner [--once] [--poll-interval 2.0]
                                      [--max-concurrent N]

Cơ chế:
- Poll bảng video_jobs, nhận job theo FIFO (created_at tăng dần):
  * status 'pending'                         -> chạy từ đầu
  * status 'processing' ở stage trung gian   -> resume từ stage đã lưu
    (script_ready / voice_ready / assets_ready / rendering), artifact đã
    có trên đĩa (audio/ảnh từng scene) được stage tự dùng lại.
- KHÔNG tự vượt điểm dừng duyệt: job ở 'source_review' hoặc
  'assets_ready' của mode 'step_by_step' luôn chờ thao tác người dùng.
- Tối đa `queue.max_concurrent_jobs` job chạy đồng thời (config ở
  config/settings.yaml; biến môi trường CATDAN_MAX_CONCURRENT_JOBS ghi đè).
- API chỉ tạo job (status 'pending'); tiến trình này là nơi duy nhất
  thực thi pipeline tạo video.

Mặc định chạy vòng lặp vô hạn; `--once` xử lý tới khi hết job claim được
rồi thoát (dùng cho test/smoke). Chỉ nên chạy MỘT instance worker cho
mỗi DB — claim được ghi vào pipeline_data["worker_claim"] để truy vết.
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from loguru import logger

import dashboard.api.database as db_module
from dashboard.api.models import JobStatus
from dashboard.worker import video_tasks

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"

# Stage trung gian có thể resume tự động (assets_ready chỉ khi mode auto,
# kiểm tra riêng trong find_claimable_jobs).
RESUMABLE_STAGES = {"pending", "script_ready", "voice_ready", "assets_ready", "rendering"}
TERMINAL_STATUSES = {
    JobStatus.done.value,
    JobStatus.failed.value,
    JobStatus.approved.value,
    JobStatus.scheduled.value,
    JobStatus.published.value,
    JobStatus.publish_failed.value,
    JobStatus.rejected.value,
}


def load_max_concurrent_jobs(config_path: Optional[Path] = None) -> int:
    """
    Đọc số job chạy đồng thời tối đa.

    Thứ tự ưu tiên: biến môi trường CATDAN_MAX_CONCURRENT_JOBS →
    `queue.max_concurrent_jobs` trong cấu hình. Mặc định an toàn = 2.

    Khi truyền `config_path` (test/smoke), đọc trực tiếp file đó;
    không truyền thì dùng nguồn cấu hình duy nhất core.config
    (config/settings.yaml qua CATDAN_SETTINGS_FILE nếu có).
    """
    env_val = os.environ.get("CATDAN_MAX_CONCURRENT_JOBS", "").strip()
    if env_val:
        try:
            return max(1, int(env_val))
        except ValueError:
            logger.warning(f"CATDAN_MAX_CONCURRENT_JOBS không hợp lệ: {env_val!r}; bỏ qua")

    if config_path is None:
        from core.config import get_queue_max_concurrent_jobs

        return get_queue_max_concurrent_jobs()

    path = Path(config_path)
    try:
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            value = (data.get("queue") or {}).get("max_concurrent_jobs")
            if value is not None:
                return max(1, int(value))
    except Exception as e:
        logger.warning(f"Không đọc được {path} ({e}); dùng mặc định 2")
    return 2


def _status_value(job) -> str:
    status = getattr(job, "status", "")
    return status.value if hasattr(status, "value") else str(status)


def is_claimable(job, in_flight_ids: Set[str]) -> bool:
    """Job này có được worker nhận chạy (tiếp) ngay bây giờ không?"""
    if job.id in in_flight_ids:
        return False
    status = _status_value(job)
    if status in TERMINAL_STATUSES:
        return False
    stage = (getattr(job, "stage", None) or "pending").strip() or "pending"
    if status == JobStatus.pending.value:
        return True
    if status != JobStatus.processing.value:
        return False
    if stage not in RESUMABLE_STAGES:
        # 'source_review' và các stage chờ duyệt khác: chờ người dùng.
        return False
    pipeline_data = getattr(job, "pipeline_data", {}) or {}
    if pipeline_data.get("manual_studio_lock"):
        return False
    if stage == "assets_ready" and (getattr(job, "mode", "auto") or "auto") == "step_by_step":
        # Điểm dừng duyệt storyboard của Step-by-Step Studio.
        return False
    return True


def find_claimable_jobs(db, in_flight_ids: Set[str]) -> List:
    """Danh sách job claim được, sắp FIFO theo created_at."""
    jobs = db_module.list_jobs(db)
    claimable = [j for j in jobs if is_claimable(j, in_flight_ids)]
    claimable.sort(key=lambda j: (j.created_at or datetime.min, j.id))
    return claimable


def _claim_job(db, job) -> None:
    """Ghi dấu claim vào pipeline_data để truy vết (không đổi stage/status)."""
    try:
        pipeline_data = dict(job.pipeline_data or {})
        pipeline_data["worker_claim"] = {
            "pid": os.getpid(),
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "stage": job.stage,
        }
        db_module.update_job_stage(
            db, job.id, job.stage or "pending", pipeline_data=pipeline_data
        )
    except Exception as e:
        logger.warning(f"Không ghi được worker_claim cho job {job.id}: {e}")


def _run_one(job_id: str) -> Dict[str, Any]:
    """Chạy/resume một job; lỗi đã được pipeline tự ghi vào DB."""
    try:
        result = video_tasks.resume_video_pipeline(job_id)
        logger.info(f"Worker xử lý xong job {job_id}: {result}")
        return result
    except Exception as e:
        # resume_video_pipeline/run_video_pipeline đã đánh dấu failed trong
        # DB ở hầu hết đường lỗi; ở đây chỉ log để worker không chết theo.
        logger.exception(f"Worker lỗi khi chạy job {job_id}: {e}")
        return {"job_id": job_id, "action": "error", "error": str(e)}


class WorkerRunner:
    """Vòng lặp poll DB + ThreadPoolExecutor giới hạn đồng thời."""

    def __init__(
        self,
        max_concurrent_jobs: Optional[int] = None,
        poll_interval: float = 2.0,
        once: bool = False,
    ):
        self.max_concurrent_jobs = max_concurrent_jobs or load_max_concurrent_jobs()
        self.poll_interval = max(0.05, float(poll_interval))
        self.once = once
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def run(self) -> int:
        logger.info(
            f"🚀 Video worker khởi động (max_concurrent={self.max_concurrent_jobs}, "
            f"poll={self.poll_interval}s, once={self.once})"
        )
        processed = 0
        with ThreadPoolExecutor(max_workers=self.max_concurrent_jobs) as executor:
            futures: Dict[Any, str] = {}
            while not self._stopped:
                # Thu hồi future đã xong
                done = [f for f in futures if f.done()]
                for f in done:
                    futures.pop(f, None)
                    processed += 1

                slots = self.max_concurrent_jobs - len(futures)
                submitted = 0
                if slots > 0:
                    db = db_module.SessionLocal()
                    try:
                        candidates = find_claimable_jobs(db, set(futures.values()))
                        for job in candidates[:slots]:
                            _claim_job(db, job)
                            futures[executor.submit(_run_one, job.id)] = job.id
                            submitted += 1
                            logger.info(
                                f"Worker nhận job {job.id} (stage={job.stage}, "
                                f"status={_status_value(job)})"
                            )
                    finally:
                        db.close()

                if self.once and not futures and submitted == 0:
                    # Hết việc claim được ở cả vòng này -> thoát.
                    break
                if not self.once or futures:
                    time.sleep(self.poll_interval)
        logger.info(f"🛑 Video worker dừng. Đã xử lý {processed} job trong phiên này.")
        return processed


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dashboard.worker.runner",
        description="Durable DB-polling video worker (thay Celery/Redis).",
    )
    parser.add_argument("--once", action="store_true",
                        help="Xử lý tới khi hết job claim được rồi thoát")
    parser.add_argument("--poll-interval", type=float, default=2.0,
                        help="Giây giữa hai lần poll DB (mặc định 2.0)")
    parser.add_argument("--max-concurrent", type=int, default=None,
                        help="Ghi đè queue.max_concurrent_jobs trong config")
    args = parser.parse_args(argv)

    runner = WorkerRunner(
        max_concurrent_jobs=args.max_concurrent,
        poll_interval=args.poll_interval,
        once=args.once,
    )
    try:
        runner.run()
    except KeyboardInterrupt:
        logger.info("Nhận Ctrl+C — worker dừng.")
        runner.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
