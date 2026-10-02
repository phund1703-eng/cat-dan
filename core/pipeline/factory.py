"""
AutoVideoFactory — Canonical Pipeline Factory (Task 1.1)

Đây là ĐIỂM VÀO DUY NHẤT để tạo video từ chủ đề. Mọi entrypoint cũ
(run_pipeline_v4/v5, produce_human_body_*, scripts/produce_*) chỉ là
wrapper mỏng gọi về đây — không cài đặt logic pipeline riêng nữa.

Đường Dashboard (DB-driven, 5 stage + step-by-step halt ở assets_ready)
vẫn chạy qua dashboard/worker/video_tasks.py và dùng chung engine render
styles/collage_broll (CollageEngine) với hàm này.
"""

import asyncio
import warnings
from typing import Optional

from loguru import logger


async def create_video(
    topic: str,
    style: str = "collage_broll",
    language: str = "vi",
    format: str = "shorts",
    mode: str = "auto",
    art_style: Optional[str] = None,
    voice_preset: Optional[str] = None,
    job_id: Optional[str] = None,
) -> dict:
    """
    Tạo video hoàn chỉnh từ chủ đề qua pipeline canonical.

    Args:
        topic: Chủ đề video.
        style: Phong cách (hiện hỗ trợ thật: 'collage_broll').
        language: 'vi' | 'en' | 'both'.
        format: 'shorts' (9:16) | 'landscape' (16:9).
        mode: 'auto' | 'step_by_step' (chỉ áp dụng cho Dashboard worker).
        art_style / voice_preset: preset tùy chọn (Dashboard worker dùng).
        job_id: ID job (tự tạo nếu None).

    Returns:
        dict của VideoFactory.create_video: {job_id, output_path, script, ...}
    """
    # Import lười để tránh vòng lặp import (root pipeline.py là cài đặt gốc)
    from pipeline import VideoFactory

    logger.info(
        f"[canonical pipeline] topic='{topic}' style={style} language={language} "
        f"format={format} mode={mode} job_id={job_id}"
    )
    factory = VideoFactory()
    return await factory.create_video(
        topic=topic,
        style=style,
        language=language,
        video_format=format,
        job_id=job_id,
    )


def run_create_video(*args, **kwargs) -> dict:
    """Hàm đồng bộ tiện ích: chạy create_video() bằng asyncio.run."""
    return asyncio.run(create_video(*args, **kwargs))


def deprecated_entrypoint(old_name: str) -> None:
    """Phát cảnh báo deprecated cho các entrypoint cũ đã chuyển thành wrapper."""
    msg = (
        f"{old_name} is deprecated: it now delegates to the canonical pipeline "
        f"(core.pipeline.factory.create_video). Please use that entrypoint directly."
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=3)
    logger.warning(f"⚠️ DEPRECATED: {msg}")
