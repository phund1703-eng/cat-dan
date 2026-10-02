"""
AutoVideoFactory — MultiAssetGenerator
core/media_engine/multi_asset_generator.py

Milestone 3 (R3):
Điều phối sinh song song các vật thể đa thành phần (Hero & Secondary) cho một cảnh:
- Sử dụng CascadeAssetOrchestrator làm bộ điều phối đa tầng bậc thang.
- Cả Hero Element và Secondary Target đều được điều phối qua CascadeAssetOrchestrator.acquire_asset().
- Gọi sinh đồng thời qua asyncio.gather().
- Tương thích ngược 100% với các vị trí gọi (run_pipeline_v4.py, test_phase2_composition.py).
- Trả về dictionary:
  {
      "hero_path": hero_path,
      "secondary_path": sec_path,
      "sec_path": sec_path,
      "hero_qa": hero_qa,
      "secondary_qa": sec_qa,
      "sec_qa": sec_qa
  }
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Union
from loguru import logger

from .cascade_asset_orchestrator import CascadeAssetOrchestrator
from .alpha_qa_gate import AlphaQAGate
from .fallback_asset_library import FallbackAssetLibrary


class MultiAssetGenerator:
    """
    Sinh và kiểm duyệt song song các vật thể cho một cảnh Collage đa tầng
    sử dụng CascadeAssetOrchestrator (Tier 1 Imagen 3 -> Tier 2 FLUX -> Tier 3 Stock -> Tier 4 Procedural).
    """

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        self.cache_dir = Path(cache_dir).resolve() if cache_dir else None
        self.orchestrator = CascadeAssetOrchestrator(cache_dir=self.cache_dir)
        self.fallback_lib = FallbackAssetLibrary()

    async def generate_scene_assets(
        self,
        scene_layout: Dict[str, Any],
        output_dir: Optional[Union[str, Path]] = None,
        width: int = 512,
        height: int = 512
    ) -> Dict[str, Any]:
        """
        Sinh song song cả Hero Element và Secondary Element cho cảnh thông qua CascadeAssetOrchestrator.
        """
        out_dir = Path(output_dir).resolve() if output_dir else Path("data/cache/scene_assets").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        archetype = scene_layout.get("archetype", "specimen_scientific")
        scene_sentence = (
            scene_layout.get("narration")
            or scene_layout.get("sentence")
            or scene_layout.get("scene_sentence")
            or ""
        )

        hero = scene_layout.get("hero_element", {})
        hero_name = str(hero.get("name", "")).strip()
        hero_prompt = str(hero.get("prompt", "")).strip()
        if hero_name and hero_name.lower() not in ["hero", "hero_element", "element", "actor"]:
            hero_target = hero_name
        elif hero_prompt:
            hero_target = hero_prompt
        else:
            hero_target = "vintage central object"

        sec = scene_layout.get("secondary_element", {})
        sec_name = str(sec.get("name", "")).strip()
        sec_prompt = str(sec.get("prompt", "")).strip()
        if sec_name and sec_name.lower() not in ["sec", "secondary", "secondary_element", "target"]:
            sec_target = sec_name
        elif sec_prompt:
            sec_target = sec_prompt
        else:
            sec_target = "vintage target object"

        logger.info(
            f"⚡ [MultiAssetGenerator] Bắt đầu sinh song song qua CascadeAssetOrchestrator: "
            f"Hero ('{hero_target[:30]}...') & Secondary ('{sec_target[:30]}...')..."
        )

        # Điều phối sinh đồng thời cả 2 vật thể qua asyncio.gather
        task_hero = self.orchestrator.acquire_asset(
            target_object=hero_target,
            scene_sentence=scene_sentence,
            archetype=archetype,
            job_cache_dir=out_dir,
            width=width,
            height=height
        )
        task_sec = self.orchestrator.acquire_asset(
            target_object=sec_target,
            scene_sentence=scene_sentence,
            archetype=archetype,
            job_cache_dir=out_dir,
            width=width,
            height=height
        )

        (hero_path, hero_meta), (sec_path, sec_meta) = await asyncio.gather(task_hero, task_sec)

        # Kiểm tra chất lượng Alpha và kết hợp metadata từ CascadeAssetOrchestrator
        hero_qa = AlphaQAGate.verify(hero_path)
        hero_qa.update({
            "tier_used": hero_meta.get("tier_used"),
            "source": hero_meta.get("source"),
            "confidence": hero_meta.get("confidence", 1.0),
            "is_aligned": hero_meta.get("is_aligned", True),
            "reason": hero_meta.get("reason", "")
        })

        sec_qa = AlphaQAGate.verify(sec_path)
        sec_qa.update({
            "tier_used": sec_meta.get("tier_used"),
            "source": sec_meta.get("source"),
            "confidence": sec_meta.get("confidence", 1.0),
            "is_aligned": sec_meta.get("is_aligned", True),
            "reason": sec_meta.get("reason", "")
        })

        # Safeguard fallback nếu file không đạt QA hoặc không tồn tại
        if not hero_qa.get("passed", False) or not Path(hero_path).exists():
            logger.warning(f"🛡️ Hero asset không đạt QA, kích hoạt Fallback Library...")
            fallback_hero = self.fallback_lib.get_fallback(archetype, hero_target)
            hero_path = str(fallback_hero)
            hero_qa = AlphaQAGate.verify(hero_path)
            hero_qa.update({"tier_used": "fallback_library", "source": "fallback_asset_library"})

        if not sec_qa.get("passed", False) or not Path(sec_path).exists():
            logger.warning(f"🛡️ Secondary asset không đạt QA, kích hoạt Fallback Library...")
            fallback_sec = self.fallback_lib.get_fallback(archetype, sec_target)
            sec_path = str(fallback_sec)
            sec_qa = AlphaQAGate.verify(sec_path)
            sec_qa.update({"tier_used": "fallback_library", "source": "fallback_asset_library"})

        logger.success(
            f"🎯 [MultiAssetGenerator] Đã hoàn tất 2 vật thể: "
            f"Hero ({hero_qa.get('ratio', 0)*100:.1f}%, Tier: {hero_meta.get('tier_used')}) & "
            f"Secondary ({sec_qa.get('ratio', 0)*100:.1f}%, Tier: {sec_meta.get('tier_used')})"
        )

        return {
            "hero_path": str(hero_path),
            "secondary_path": str(sec_path),
            "sec_path": str(sec_path),
            "hero_qa": hero_qa,
            "secondary_qa": sec_qa,
            "sec_qa": sec_qa
        }
