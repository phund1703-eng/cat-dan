"""
DEPRECATED wrapper (Task 1.1) — trước đây là pipeline sản xuất V2 riêng cho
video "Chi phí nguyên liệu thô cơ thể người".
Giờ chỉ gọi pipeline canonical: core.pipeline.factory.create_video.
Chạy: python produce_human_body_v2.py
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline.factory import create_video, deprecated_entrypoint

HUMAN_BODY_TOPIC = "Chi phí nguyên liệu thô cấu tạo nên cơ thể người"


async def produce_human_body_v2() -> None:
    deprecated_entrypoint("produce_human_body_v2.py")
    result = await create_video(topic=HUMAN_BODY_TOPIC, style="collage_broll", language="vi", format="shorts")
    print(f"DONE_MASTER:{result['output_path']}")


if __name__ == "__main__":
    asyncio.run(produce_human_body_v2())
