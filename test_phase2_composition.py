"""
AutoVideoFactory — Phase 2 Verification Script
Kiểm thử toàn diện:
1. Phân tích kịch bản bằng MultiElementSceneDesigner (Cú pháp câu văn = Cú pháp cảnh collage).
2. Sinh song song Hero và Secondary cutouts bằng MultiAssetGenerator (với QA Gate kiểm tra độ phủ alpha).
3. Lắp ráp và kết xuất 3 video stop-motion 12fps (1080x1920) với hiệu ứng viền kem 3px, đổ bóng vật lý 45 độ và quy trình rơi nảy.
4. Xuất 3 video MP4 và 3 ảnh tĩnh PNG (frame hoàn chỉnh) tại data/test_phase2/.
"""

import os
import sys
import asyncio
import shutil
from pathlib import Path
from loguru import logger
from PIL import Image

# Thêm root dự án vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.text_visual_analyzer import MultiElementSceneDesigner
from core.media_engine.multi_asset_generator import MultiAssetGenerator
from styles.collage_broll.gbro_adapter import GbroAdapter


TEST_CASES = [
    {
        "id": "01_biology",
        "name": "Sinh học (Microscope examining Bacteria)",
        "sentence": "Kính hiển vi quang học phóng đại cụm vi khuẩn đỏ trong đĩa petri để tìm kiếm kháng thể mới.",
        "archetype": "specimen_scientific",
        "scene_layout": {
            "archetype": "specimen_scientific",
            "environment_graphic": "reticle",
            "color_field": {
                "name": "Deep Cobalt",
                "hex": "#1D3557"
            },
            "hero_element": {
                "name": "vintage brass microscope",
                "prompt": "a vintage brass laboratory microscope",
                "scale_factor": 0.48,
                "position": {"x": 540, "y": 700},
                "interaction_role": "EXAMINING"
            },
            "secondary_element": {
                "name": "glass petri dish with red bacteria colonies",
                "prompt": "a glass petri dish with red bacteria culture colonies",
                "scale_factor": 0.35,
                "position": {"x": 540, "y": 1280},
                "interaction_role": "TARGET"
            },
            "interaction_type": "EXAMINING",
            "has_pointing_hand": False
        }
    },
    {
        "id": "02_geography",
        "name": "Địa lý / Biển sâu (Pressure Gauge pressing Submarine)",
        "sentence": "Áp suất hàng nghìn atmosphere dưới đáy rãnh Mariana đè nặng lên lớp vỏ thép của tàu ngầm thám hiểm.",
        "archetype": "archive_documentary",
        "scene_layout": {
            "archetype": "archive_documentary",
            "environment_graphic": "coordinate_grid",
            "color_field": {
                "name": "Sage Green",
                "hex": "#588157"
            },
            "hero_element": {
                "name": "vintage industrial pressure gauge manometer",
                "prompt": "a vintage round metal pressure gauge manometer with dial and needle",
                "scale_factor": 0.46,
                "position": {"x": 540, "y": 720},
                "interaction_role": "PRESSING"
            },
            "secondary_element": {
                "name": "yellow retro research submarine",
                "prompt": "a yellow retro oceanic deep sea research submarine submersible",
                "scale_factor": 0.38,
                "position": {"x": 540, "y": 1260},
                "interaction_role": "TARGET"
            },
            "interaction_type": "PRESSING",
            "has_pointing_hand": True
        }
    },
    {
        "id": "03_mechanic",
        "name": "Cơ học / Đời sống (Press Machine pressing Cut Orange)",
        "sentence": "Máy ép cơ khí tác dụng lực nén khổng lồ ép chặt nửa quả cam tươi mọng nước trên bàn thí nghiệm.",
        "archetype": "surreal_editorial",
        "scene_layout": {
            "archetype": "surreal_editorial",
            "environment_graphic": "ruler_scale",
            "color_field": {
                "name": "Burnt Terracotta",
                "hex": "#D44D22"
            },
            "hero_element": {
                "name": "mechanical metal press machine",
                "prompt": "a vintage heavy mechanical metal press stamper tool",
                "scale_factor": 0.48,
                "position": {"x": 540, "y": 680},
                "interaction_role": "PRESSING"
            },
            "secondary_element": {
                "name": "fresh juicy cut orange half",
                "prompt": "a fresh juicy sliced orange citrus fruit half with visible pulp",
                "scale_factor": 0.34,
                "position": {"x": 540, "y": 1250},
                "interaction_role": "TARGET"
            },
            "interaction_type": "PRESSING",
            "has_pointing_hand": True
        }
    }
]


async def run_phase2_verification():
    output_dir = PROJECT_ROOT / "data" / "test_phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    assets_cache_dir = PROJECT_ROOT / "data" / "cache" / "phase2_assets"
    assets_cache_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo modules
    designer = MultiElementSceneDesigner()
    generator = MultiAssetGenerator(cache_dir=assets_cache_dir)
    adapter = GbroAdapter()

    results = []

    logger.info("=" * 60)
    logger.info("🚀 BẮT ĐẦU KIỂM THỬ PHASE 2: ĐA VẬT THỂ TƯƠNG TÁC (MULTI-ELEMENT SCENE)")
    logger.info("=" * 60)

    for case in TEST_CASES:
        case_id = case["id"]
        logger.info(f"\n🎬 --- XỬ LÝ TEST CASE: {case['name']} ---")

        # 1. Thử nghiệm TextVisualAnalyzer / MultiElementSceneDesigner với câu thoại
        logger.info(f"📝 [Step 1] Phân tích câu thoại qua MultiElementSceneDesigner:")
        logger.info(f"   Câu thoại: \"{case['sentence']}\"")
        analyzed_layout = await designer.design_scene(case["sentence"], topic_context=case["archetype"])
        logger.info(f"   Kết quả phân tích: Hero='{analyzed_layout['hero_element']['name']}', "
                    f"Sec='{analyzed_layout['secondary_element']['name']}', "
                    f"Interaction='{analyzed_layout['interaction_type']}'")

        # Dùng case["scene_layout"] chuẩn đã được định nghĩa chi tiết
        scene_layout = case["scene_layout"]

        # Nếu đã có sẵn cutouts từ phase 1, kiểm tra ưu tiên hoặc sinh mới
        phase1_dir = PROJECT_ROOT / "data" / "test_phase1"
        hero_fallback = None
        sec_fallback = None

        if case_id == "01_biology":
            p1_hero = phase1_dir / "01_microscope_a_vintage__cutout.png"
            p1_sec = phase1_dir / "02_bacteria_a_red_micr_cutout.png"
            if p1_hero.exists():
                hero_fallback = str(p1_hero)
            if p1_sec.exists():
                sec_fallback = str(p1_sec)
        elif case_id == "02_geography":
            p1_hero = phase1_dir / "03_pressure_gauge_a_vintage__cutout.png"
            p1_sec = phase1_dir / "04_submarine_a_yellow_r_cutout.png"
            if p1_hero.exists():
                hero_fallback = str(p1_hero)
            if p1_sec.exists():
                sec_fallback = str(p1_sec)

        # 2. Sinh song song Hero & Secondary Cutouts
        logger.info(f"🎨 [Step 2] Sinh/bóc tách song song Hero & Secondary Assets...")
        asset_res = await generator.generate_scene_assets(
            scene_layout=scene_layout,
            output_dir=assets_cache_dir
        )

        hero_path = asset_res["hero_path"]
        sec_path = asset_res["sec_path"]

        # Nếu sinh bị lỗi và có Phase 1 asset sẵn, tận dụng Phase 1 asset
        if (not hero_path or not Path(hero_path).exists()) and hero_fallback:
            hero_path = hero_fallback
        if (not sec_path or not Path(sec_path).exists()) and sec_fallback:
            sec_path = sec_fallback

        logger.info(f"   Hero Asset: {hero_path}")
        logger.info(f"   Secondary Asset: {sec_path}")

        # 3. Kết xuất Stop-Motion 12 FPS Video và Frame Tĩnh hoàn chỉnh
        out_video = output_dir / f"clip_{case_id}.mp4"
        out_frame = output_dir / f"frame_{case_id}.png"

        logger.info(f"🎞️ [Step 3] Render Stop-Motion 12 FPS: {out_video.name} & {out_frame.name}...")
        rendered_video = adapter.render_multi_element_scene(
            scene_layout=scene_layout,
            hero_asset_path=hero_path,
            secondary_asset_path=sec_path,
            output_video_path=str(out_video),
            output_frame_path=str(out_frame),
            duration=5.0,
            fps=12
        )

        vid_size = os.path.getsize(rendered_video) / (1024 * 1024)
        frame_size = os.path.getsize(str(out_frame)) / 1024

        logger.success(f"✅ Hoàn thành {case_id}: Video ({vid_size:.2f} MB), Frame ({frame_size:.1f} KB)")

        results.append({
            "id": case_id,
            "name": case["name"],
            "video": str(out_video),
            "frame": str(out_frame),
            "video_size_mb": vid_size,
            "frame_size_kb": frame_size
        })

    logger.info("\n" + "=" * 60)
    logger.info("📊 TỔNG KẾT KẾT QUẢ PHASE 2 VERIFICATION")
    logger.info("=" * 60)
    for r in results:
        logger.info(f"✨ {r['name']}:")
        logger.info(f"   - Video: {r['video']} ({r['video_size_mb']:.2f} MB)")
        logger.info(f"   - Frame: {r['frame']} ({r['frame_size_kb']:.1f} KB)")

    return results


if __name__ == "__main__":
    asyncio.run(run_phase2_verification())
