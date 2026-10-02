"""
DEPRECATED wrapper (Task 1.1) — trước đây là script sản xuất riêng cho video Cơ Thể Người.
Giờ chỉ gọi pipeline canonical: core.pipeline.factory.create_video.
Asset tĩnh dùng cho kịch bản này nằm ở core/media_engine/human_body_assets.py
(trước đây: prepare_human_body_assets.py).
Chạy: python produce_human_body_video.py
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline.factory import create_video, deprecated_entrypoint

HUMAN_BODY_TOPIC = "Giá trị nguyên liệu thô cấu tạo nên cơ thể người"


async def produce_human_body_video():
    deprecated_entrypoint("produce_human_body_video.py")
    result = await create_video(topic=HUMAN_BODY_TOPIC, style="collage_broll", language="vi", format="shorts")
    print(f"DONE_MASTER:{result['output_path']}")
    return result


if __name__ == "__main__":
    asyncio.run(produce_human_body_video())
