"""
DEPRECATED wrapper (Task 1.1) — giờ chỉ gọi pipeline canonical:
core.pipeline.factory.create_video.
Chạy: python scripts/produce_domain_test_videos.py
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline.factory import create_video, deprecated_entrypoint

VIDEOS_CONFIG = [
    {"id": "biology", "topic": "Hành trình tế bào bạch cầu tiêu diệt vi khuẩn", "title": "Cuộc Chiến Vô Hình Của Tế Bào Bạch Cầu"},
    {"id": "geography", "topic": "Bí mật rãnh Mariana - Vực sâu tăm tối nhất hành tinh", "title": "Bí Mật Rãnh Mariana - Vực Sâu Tăm Tối Nhất Hành Tinh"},
    {"id": "history", "topic": "Bí mật kỹ thuật ướp xác của các Pharaoh Ai Cập", "title": "Bí Mật Kỹ Thuật Ướp Xác Của Các Pharaoh Ai Cập"},
]


async def produce_all():
    deprecated_entrypoint("scripts/produce_domain_test_videos.py")
    results = []
    for conf in VIDEOS_CONFIG:
        result = await create_video(topic=conf["topic"], style="collage_broll", language="vi", format="shorts")
        results.append({"id": conf["id"], "title": conf["title"], **result})
    return results


if __name__ == "__main__":
    asyncio.run(produce_all())
