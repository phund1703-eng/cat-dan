"""
DEPRECATED wrapper (Task 1.1) — trước đây là pipeline V5 (Kinetic Stop-Motion) riêng.
Giờ chỉ gọi pipeline canonical: core.pipeline.factory.create_video.
Chạy: python run_pipeline_v5.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline.factory import create_video, deprecated_entrypoint


class PipelineV5:
    """Wrapper mỏng tương thích ngược — delegate sang pipeline canonical."""

    async def produce_single_scene_video(
        self,
        sentence: str,
        hero_asset_path: str,
        secondary_asset_path: Optional[str] = None,
        action_assets_paths: Optional[list] = None,
        output_filename: str = "video_v5_demo.mp4",
        custom_layout_params: Optional[dict] = None,
    ) -> Path:
        deprecated_entrypoint("PipelineV5.produce_single_scene_video")
        result = await create_video(topic=sentence, style="collage_broll", language="vi", format="shorts")
        return Path(result["output_path"])


async def run_v5_verification():
    deprecated_entrypoint("run_pipeline_v5.py")
    result = await create_video(
        topic="Lưỡi rìu bổ đôi khúc gỗ rừng già",
        style="collage_broll",
        language="vi",
        format="shorts",
    )
    print(f"🎉 Kiểm thử pipeline canonical hoàn tất! Video: {result['output_path']}")
    return result


if __name__ == "__main__":
    asyncio.run(run_v5_verification())
