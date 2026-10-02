"""
DEPRECATED wrapper (Task 1.1) — giờ chỉ gọi pipeline canonical:
core.pipeline.factory.create_video.
Chạy: python scripts/produce_3_random_videos.py
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline.factory import create_video, deprecated_entrypoint

VIDEOS_CONFIG = [
    {"id": "black_hole", "topic": "Vũ trụ & Bí ẩn Hố đen", "title": "Bí Ẩn Hố Đen Và Chân Trời Sự Kiện"},
    {"id": "choice_paradox", "topic": "Tâm lý học hành vi: Nghịch lý lựa chọn", "title": "Nghịch Lý Của Sự Lựa Chọn Trong Cuộc Sống"},
    {"id": "light_bulb", "topic": "Lịch sử phát minh: Chiếc bóng đèn điện", "title": "Chiếc Bóng Đèn Thắp Sáng Văn Minh Nhân Loại"},
]


async def produce_all():
    deprecated_entrypoint("scripts/produce_3_random_videos.py")
    results = []
    for conf in VIDEOS_CONFIG:
        result = await create_video(topic=conf["topic"], style="collage_broll", language="vi", format="shorts")
        results.append({"id": conf["id"], "title": conf["title"], **result})
    return results


if __name__ == "__main__":
    asyncio.run(produce_all())
