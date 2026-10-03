"""
AutoVideoFactory — Phase 1 Test Script: test_phase1_assets.py
Kiểm thử tạo và bóc tách tự động 6 vật thể đại diện theo chế độ Single Isolated Asset 512x512:
1. "a vintage brass microscope" (Kính hiển vi)
2. "a red microscopic bacteria cell" (Vi khuẩn)
3. "a vintage industrial pressure gauge manometer" (Đồng hồ áp suất)
4. "a yellow retro research submarine" (Tàu ngầm vàng)
5. "an ancient Egyptian canopic jar" (Bình ướp xác)
6. "a mechanical orange juice citrus squeezer" (Máy ép cam)

Yêu cầu nghiệm thu Phase 1:
- 100% 6 vật thể đều PASS Alpha QA Gate (alpha_ratio từ 0.08 đến 0.85).
- Lưu kết quả tại data/test_phase1/.
"""

import sys
import asyncio
from pathlib import Path
from loguru import logger

ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.media_engine.universal_image_generator import UniversalImageGenerator
from core.media_engine.alpha_qa_gate import AlphaQAGate

TEST_OBJECTS = [
    {
        "id": "01_microscope",
        "name": "Kính hiển vi",
        "prompt": "a vintage brass microscope",
        "archetype": "specimen_scientific",
        "seed": 401
    },
    {
        "id": "02_bacteria",
        "name": "Vi khuẩn",
        "prompt": "a red microscopic bacteria cell",
        "archetype": "specimen_scientific",
        "seed": 402
    },
    {
        "id": "03_pressure_gauge",
        "name": "Đồng hồ áp suất",
        "prompt": "a vintage industrial pressure gauge manometer",
        "archetype": "geography_ocean",
        "seed": 403
    },
    {
        "id": "04_submarine",
        "name": "Tàu ngầm vàng",
        "prompt": "a yellow retro research submarine",
        "archetype": "geography_ocean",
        "seed": 404
    },
    {
        "id": "05_canopic_jar",
        "name": "Bình ướp xác",
        "prompt": "an ancient Egyptian canopic jar",
        "archetype": "historical_relic",
        "seed": 405
    },
    {
        "id": "06_citrus_squeezer",
        "name": "Máy ép cam",
        "prompt": "a mechanical orange juice citrus squeezer",
        "archetype": "industrial_social",
        "seed": 406
    }
]


async def run_phase1_test():
    test_dir = Path("data/test_phase1").resolve()
    test_dir.mkdir(parents=True, exist_ok=True)

    generator = UniversalImageGenerator(cache_dir=test_dir / "cache")

    logger.info("=========================================================================")
    logger.info("🚀 BẮT ĐẦU KIỂM THỬ PHASE 1: ISOLATED ASSETS & ALPHA QA GATE")
    logger.info("=========================================================================\n")

    results = []
    all_passed = True

    for idx, item in enumerate(TEST_OBJECTS, start=1):
        obj_id = item["id"]
        obj_name = item["name"]
        prompt = item["prompt"]
        archetype = item["archetype"]
        seed = item["seed"]

        logger.info(f"[{idx}/6] Đang xử lý: {obj_name} ('{prompt}') | Archetype: {archetype}")

        out_prefix = test_dir / f"{obj_id}_{item['prompt'][:10].replace(' ', '_')}"

        cutout_path, qa_res = await generator.generate_isolated_asset(
            concrete_object=prompt,
            output_path=str(out_prefix) + ".png",
            seed=seed,
            archetype=archetype,
            width=512,
            height=512
        )

        passed = qa_res["passed"]
        ratio = qa_res["ratio"]
        status = qa_res["status"]

        if not passed:
            all_passed = False

        results.append({
            "idx": idx,
            "id": obj_id,
            "name": obj_name,
            "prompt": prompt,
            "path": cutout_path,
            "ratio": ratio,
            "status": status,
            "passed": passed
        })

    logger.info("\n=========================================================================")
    logger.info("📊 BẢNG TỔNG HỢP NGHIỆM THU PHASE 1 (ALPHA QA GATE)")
    logger.info("=========================================================================")
    logger.info(f"{'STT':<4} | {'Tên Vật Thể':<18} | {'Tỷ lệ Alpha':<12} | {'Trạng thái':<12} | {'Đường dẫn File Cutout'}")
    logger.info("-" * 90)

    for r in results:
        status_icon = "✅ PASS" if r["passed"] else "❌ FAIL"
        logger.info(
            f"{r['idx']:<4} | {r['name']:<18} | {r['ratio']*100:>8.1f}%   | {status_icon:<12} | {r['path']}"
        )

    logger.info("=" * 90)

    if all_passed:
        logger.success("\n🎉 CHÚC MỪNG: 100% VẬT THỂ THỬ NGHIỆM ĐÃ VƯỢT QUA ALPHA QA GATE (10% - 70%)!")
        logger.success("Hoàn thành trọn vẹn toàn bộ mục tiêu của Phase 1!\n")
    else:
        logger.error("\n❌ Có vật thể không vượt qua kiểm duyệt Alpha QA Gate.")

    return results, all_passed


if __name__ == "__main__":
    results, success = asyncio.run(run_phase1_test())
    sys.exit(0 if success else 1)
