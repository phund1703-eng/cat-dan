"""
DEPRECATED wrapper (Task 1.1) — trước đây là pipeline sản xuất V4 riêng.
Giờ chỉ gọi pipeline canonical: core.pipeline.factory.create_video.
Chạy: python run_pipeline_v4.py
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline.factory import create_video, deprecated_entrypoint

TARGET_VIDEOS_V4 = [
    {"id": "biology", "topic": "Cơ chế bạch cầu săn tìm và tiêu diệt vi khuẩn trong cơ thể"},
    {"id": "geography", "topic": "Bí mật biển sâu và rãnh Mariana"},
    {"id": "history", "topic": "Kỹ thuật ướp xác của các Pharaoh Ai Cập cổ đại"},
]


async def run_production_v4():
    deprecated_entrypoint("run_pipeline_v4.py")
    results = []
    for cfg in TARGET_VIDEOS_V4:
        result = await create_video(topic=cfg["topic"], style="collage_broll", language="vi", format="shorts")
        results.append({"id": cfg["id"], **result})
    return results


if __name__ == "__main__":
    asyncio.run(run_production_v4())
