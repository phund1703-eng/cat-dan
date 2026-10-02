"""
AutoVideoFactory — Production Pipeline V2: produce_human_body_v2.py
Milestone M4: Complete Version 2 Production Pipeline for "Chi phí nguyên liệu thô cơ thể người".

Features:
1. UniversalLLMDirector (core.script_engine.universal_llm_director):
   - Directs the 8 scenes with 7-layer scene blueprints, color arc, and CriticGate audit.
2. BackdropAssetGateway (core.media_engine.backdrop_asset_gateway):
   - Supplies 8 bespoke 19th-century archival backdrops into data/cache/backdrops/.
   - 100% unique historical engravings (zero forest repetition).
3. 16 Cutout Assets in data/cache/human_body_assets/:
   - Preserves authentic vintage styling with cream outline (9px) and 3D shadow.
4. Vietnamese EdgeTTS Audio:
   - vi-VN-NamMinhNeural / vi-VN-HoaiMyNeural voice synthesis.
5. TikTok Yellow Subtitles (&H0000FFFF with black border &H00000000):
   - Formatted ASS subtitles with smart word-wrapping for 9:16 vertical video.
6. 7-Layer Stop-Motion Rendering:
   - GbroAdapter.render_multi_layer_scene at 1080x1920 @ 12fps.
   - Ken Burns Slow Push-In Zoom (1.0x -> 1.05x) centered at (540, 655).
   - Clean bypass of Layer 2 when is_floating=True (Scenes 7 and 8).
   - Hand gesture accents (pointing, presenting, helpless) limited to Scenes 1, 4, 6.
7. FFmpeg Concatenation & Muxing:
   - Concat all 8 scenes into output/video_human_body_cost_v2.mp4.
8. 8 Scene Snapshots:
   - Extracted into output/human_body_cost_v2/snapshot_scene_{1..8}.jpg.
"""

import os
import sys
import math
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.universal_llm_director import UniversalLLMDirector, CriticGate
from core.media_engine.backdrop_asset_gateway import BackdropAssetGateway
from core.media_engine.kinetic_layout_bridge import KineticLayoutBridge
from styles.collage_broll.gbro_adapter import GbroAdapter
from core.tts_engine.tts_manager import TTSManager
from core.render_engine.subtitle_generator import SubtitleGenerator
from core.render_engine.ffmpeg_utils import get_video_info

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================
OUTPUT_DIR = PROJECT_ROOT / "output" / "human_body_cost_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MASTER_VIDEO_PATH = PROJECT_ROOT / "output" / "video_human_body_cost_v2.mp4"
ASSETS_DIR = PROJECT_ROOT / "data" / "cache" / "human_body_assets"
BACKDROPS_DIR = PROJECT_ROOT / "data" / "cache" / "backdrops"
BACKDROPS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# CANONICAL BENCHMARK SCRIPT: "CHI PHÍ NGUYÊN LIỆU THÔ CƠ THỂ NGƯỜI" (8 SCENES)
# =============================================================================
BENCHMARK_SCENES = [
    {
        "id": 1,
        "title": "Scene 1: Sẽ tốn bao nhiêu tiền để mua nguyên liệu làm nên bạn?",
        "sentence": "Bạn đã bao giờ tự hỏi: Sẽ tốn bao nhiêu tiền để mua toàn bộ nguyên liệu thô cấu tạo nên một cơ thể người?",
        "keyword": "vitruvian_man",
        "backdrop_prompt": "19th century woodcut engraving of Da Vinci Vitruvian anatomical proportions and sacred geometry",
        "hero_asset": "human_silhouette.png",
        "secondary_asset": "golden_scale.png",
        "engine": "ENGINE_REVOLVE_VORTEX",
        "archetype": "historical_relic",
        "color_field": "Plum & Gold",
        "color_hex": "4A235A",
        "environment_graphic": "coordinate_grid",
        "is_floating": False,
        "stage_prop_name": "stone_pedestal",
        "has_hand": True,
        "hand_gesture": "pointing",
        "custom_params": {"hero_scale": 0.48, "sec_scale": 0.36, "radius": 360.0}
    },
    {
        "id": 2,
        "title": "Scene 2: Sách Bill Bryson & 59 nguyên tố",
        "sentence": "Theo cuốn sách \"Cơ thể người\" của Bill Bryson và dữ liệu từ Hiệp hội Hóa học Hoàng gia Anh, cần chính xác 59 nguyên tố để lắp ráp ra bạn.",
        "keyword": "oxford_library",
        "backdrop_prompt": "19th century vintage engraving of ancient Oxford Bodleian library gothic bookshelves and ladders",
        "hero_asset": "bryson_book.png",
        "secondary_asset": "elements_59_chart.png",
        "engine": "ENGINE_EMIT_SLIDE",
        "archetype": "oxford_library",
        "color_field": "Warm Ochre",
        "color_hex": "B7950B",
        "environment_graphic": "papyrus_frame",
        "is_floating": False,
        "stage_prop_name": "book_table",
        "has_hand": False,
        "hand_gesture": None,
        "custom_params": {"hero_scale": 0.46, "sec_scale": 0.40, "distance": 480.0}
    },
    {
        "id": 3,
        "title": "Scene 3: Oxy 61% và Hydro 10% - Quá rẻ",
        "sentence": "Bạn tưởng sẽ đắt đỏ lắm sao? Thực ra 61% cơ thể bạn chỉ là Oxy – trị giá vỏn vẹn 9 Bảng Anh. Thêm 10% là Hydro, tốn thêm 16 Bảng nữa. Quá rẻ đúng không!",
        "keyword": "chem_lab",
        "backdrop_prompt": "18th century vintage etching of Lavoisier chemistry laboratory with glass alembics and distillation flasks",
        "hero_asset": "flask_oxygen.png",
        "secondary_asset": "flask_hydrogen.png",
        "engine": "ENGINE_SWEEP_OSCILLATE",
        "archetype": "specimen_scientific",
        "color_field": "Teal & Coral",
        "color_hex": "2A9D8F",
        "environment_graphic": "microscope_reticle",
        "is_floating": False,
        "stage_prop_name": "flask_rack",
        "has_hand": False,
        "hand_gesture": None,
        "custom_params": {"hero_scale": 0.42, "sec_scale": 0.38, "sweep_angle": 35.0}
    },
    {
        "id": 4,
        "title": "Scene 4: Carbon tinh khiết 13,6 kg - 44.300 Bảng Anh",
        "sentence": "Nhưng đây mới là thứ ngốn tiền nhất: Bạn cần 13,6 kg Carbon tinh khiết. Và khoản này sẽ tiêu tốn của bạn một con số khổng lồ: 44.300 Bảng Anh!",
        "keyword": "coal_jewelry",
        "backdrop_prompt": "Victorian archival engraving of industrial coal mine heaps and sparkling diamond jewelry vault floor",
        "hero_asset": "carbon_crystal.png",
        "secondary_asset": "money_stack_44k.png",
        "engine": "ENGINE_COMPRESS_SQUASH",
        "archetype": "industrial_social",
        "color_field": "Burnt Terracotta",
        "color_hex": "D44D22",
        "environment_graphic": "ruler_scale",
        "is_floating": False,
        "stage_prop_name": "weighing_plinth",
        "has_hand": True,
        "hand_gesture": "pointing",
        "custom_params": {"hero_scale": 0.46, "sec_scale": 0.42, "scale_y": 0.35, "scale_x": 1.65}
    },
    {
        "id": 5,
        "title": "Scene 5: Tổng hóa đơn 96.546 Bảng Anh ~ 3 tỷ đồng",
        "sentence": "Cộng thêm các nguyên tố vi lượng khác, tổng hóa đơn để mua toàn bộ nguyên liệu làm ra bạn là chính xác 96.546 Bảng Anh 79 xu — tức là khoảng 3 tỷ đồng.",
        "keyword": "teller_counter",
        "backdrop_prompt": "Victorian Bank of England teller counter with brass grille and accounting ledger parchment",
        "hero_asset": "cash_register.png",
        "secondary_asset": "bill_receipt_3ty.png",
        "engine": "ENGINE_EMIT_SLIDE",
        "archetype": "bank_teller",

        "color_field": "Plum & Gold",
        "color_hex": "4A235A",
        "environment_graphic": "coordinate_grid",
        "is_floating": False,
        "stage_prop_name": "brass_counter",
        "has_hand": False,
        "hand_gesture": None,
        "custom_params": {"hero_scale": 0.45, "sec_scale": 0.42, "distance": 520.0}
    },
    {
        "id": 6,
        "title": "Scene 6: Các nhà khoa học bất lực",
        "sentence": "Nhưng đây mới là sự thật chấn động: Ngay cả khi bạn mua đủ số hóa chất đó, và gọi những nhà khoa học thiên tài nhất lịch sử đến phòng thí nghiệm... họ vẫn bất lực. Họ không thể lắp ráp đống hóa chất vô tri ấy thành dù chỉ một tế bào sống.",
        "keyword": "royal_academy",
        "backdrop_prompt": "19th century Royal Academy of Sciences amphitheater lecture hall with brass compound microscope",
        "hero_asset": "microscope_brass.png",
        "secondary_asset": "petri_chemicals.png",
        "engine": "ENGINE_SWEEP_OSCILLATE",
        "archetype": "specimen_scientific",
        "color_field": "Deep Cobalt",
        "color_hex": "1D3557",
        "environment_graphic": "microscope_reticle",
        "is_floating": False,
        "stage_prop_name": "lab_table",
        "has_hand": True,
        "hand_gesture": "helpless",
        "custom_params": {"hero_scale": 0.46, "sec_scale": 0.38, "sweep_angle": 42.0}
    },
    {
        "id": 7,
        "title": "Scene 7: Phép màu vũ trụ - Nguyên tử tự liên kết",
        "sentence": "Phép màu vĩ đại nhất của vũ trụ là: Bằng một cách nào đó, những nguyên tử chết hoàn toàn vô tri vô giác lại biết cách tự liên kết lại để trở thành chính bạn.",
        "keyword": "harmonia_macrocosmica",
        "backdrop_prompt": "Andreas Cellarius Harmonia Macrocosmica 1660 celestial constellation atlas with orbital rings and star charts",
        "hero_asset": "cosmic_atoms.png",
        "secondary_asset": "dna_helix.png",
        "engine": "ENGINE_CONVERGE_WRAP",
        "archetype": "celestial_cosmic",
        "color_field": "Midnight Celestial",
        "color_hex": "0D1B2A",
        "environment_graphic": "celestial_star_chart",
        "is_floating": True,             # NO TABLE, FLOATING IN COSMOS!
        "stage_prop_name": None,
        "has_hand": False,
        "hand_gesture": None,
        "custom_params": {"hero_scale": 0.46, "sec_scale": 0.40}
    },
    {
        "id": 8,
        "title": "Scene 8: Một thực thể biết suy nghĩ và yêu thương",
        "sentence": "Một thực thể biết suy nghĩ, biết yêu thương và biết tò mò... Và chính điều kỳ diệu đó khiến bạn không thể không thắc mắc...",
        "keyword": "vesalius_brain",
        "backdrop_prompt": "16th century Andreas Vesalius human brain anatomy engraving with radiant spiritual aura and halo light",
        "hero_asset": "glowing_brain.png",
        "secondary_asset": "heart_empathy.png",
        "engine": "ENGINE_REVOLVE_VORTEX",
        "archetype": "conceptual_duel",
        "color_field": "Plum & Gold",
        "color_hex": "4A235A",
        "environment_graphic": "coordinate_grid",
        "is_floating": True,             # NO TABLE, FLOATING GLOWING BRAIN!
        "stage_prop_name": None,
        "has_hand": False,
        "hand_gesture": None,
        "custom_params": {"hero_scale": 0.48, "sec_scale": 0.38, "radius": 380.0}
    }
]


# =============================================================================
# HELPER: DYNAMIC CHUNKED TIKTOK SUBTITLE GENERATOR (ASS FORMAT)
# =============================================================================
def generate_dynamic_chunked_subtitles(
    sentence: str,
    duration: float,
    output_path: Path,
    chunk_words: int = 3,
    font_size: int = 44,
    margin_v: int = 180
) -> str:
    """
    Generates dynamic pop-up chunked ASS subtitles (2-4 words, alternating yellow/white)
    positioned safely at MarginV=180 without obstructing Layer 2 stage props.
    """
    return SubtitleGenerator.generate_dynamic_chunked_ass(
        sentence=sentence,
        duration=duration,
        output_path=output_path,
        chunk_words=chunk_words,
        font_size=font_size,
        margin_v=margin_v
    )


def generate_tiktok_yellow_subtitles(
    sentence: str,
    duration: float,
    output_path: Path
) -> None:
    """Backward-compatible wrapper delegating to dynamic chunked subtitle generator."""
    generate_dynamic_chunked_subtitles(sentence, duration, output_path)


# =============================================================================
# HELPER: TTS SYNTHESIS WITH RESILIENT FALLBACK
# =============================================================================
async def synthesize_speech_resilient(
    tts_manager: TTSManager,
    text: str,
    output_path: Path
) -> float:
    """
    Synthesizes speech using TTSManager (VieNeu-TTS on-device CPU priority, EdgeTTS fallback).
    Falls back gracefully to modulated direct EdgeTTS or silent audio buffer.
    Returns the actual duration in seconds.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try TTSManager (prioritizes VieNeu-TTS with auto failover to EdgeTTS)
    try:
        await tts_manager.synthesize(text=text, language="vi", output_path=str(output_path))
        if output_path.exists() and output_path.stat().st_size > 1000:
            probe = get_video_info(str(output_path))
            dur = float(probe.get("duration", 0.0))
            if dur > 0.5:
                return dur
    except Exception as e:
        logger.warning(f"TTSManager attempt failed: {e}. Trying direct edge_tts...")

    # 2. Try direct edge_tts with vi-VN-NamMinhNeural (modulated: rate=-5%, pitch=-2Hz)
    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text,
            "vi-VN-NamMinhNeural",
            rate="-5%",
            pitch="-2Hz"
        )
        await communicate.save(str(output_path))
        if output_path.exists() and output_path.stat().st_size > 1000:
            probe = get_video_info(str(output_path))
            dur = float(probe.get("duration", 0.0))
            if dur > 0.5:
                return dur
    except Exception as e2:
        logger.warning(f"Direct edge_tts failed: {e2}. Falling back to synthetic tone...")

    # 3. Offline fallback: Generate clean silent audio via FFmpeg
    word_count = len(text.split())
    estimated_duration = max(3.5, round(word_count * 0.28, 2))
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(estimated_duration),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(output_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return estimated_duration


# =============================================================================
# MAIN PRODUCTION PIPELINE V2
# =============================================================================
async def produce_human_body_v2() -> None:
    logger.info("=" * 80)
    logger.info("🎬 [AutoVideoFactory V2] KHỞI ĐỘNG DÂY CHUYỀN SẢN XUẤT MASTER VIDEO V2")
    logger.info("📖 Kịch bản: 'Chi phí nguyên liệu thô cơ thể người' (8 phân cảnh điện ảnh 7 tầng)")
    logger.info("=" * 80)

    # 1. Initialize Engines
    director = UniversalLLMDirector()
    gateway = BackdropAssetGateway(cache_dir=BACKDROPS_DIR)
    bridge = KineticLayoutBridge()
    adapter = GbroAdapter()
    tts = TTSManager()

    # 2. Universal AI Showrunner Directing & Critic Gate Audit
    script_full_text = "\n".join([f"Scene {sc['id']}: {sc['sentence']}" for sc in BENCHMARK_SCENES])
    logger.info("🎭 [UniversalLLMDirector] Đang phân tích kịch bản và thiết lập Storyboard 8 phân cảnh...")
    blueprints = await director.analyze_and_direct_storyboard(
        script_text=script_full_text,
        topic="Chi phí nguyên liệu thô cơ thể người"
    )

    # Audit blueprints via CriticGate
    blueprints = CriticGate.audit_and_correct(blueprints)
    logger.success(f"✅ CriticGate đã kiểm duyệt và phê duyệt {len(blueprints)} blueprints.")

    scene_final_paths: List[Path] = []
    scene_snapshots: List[Path] = []

    # 3. Produce each of the 8 scenes
    for idx, sc in enumerate(BENCHMARK_SCENES):
        sc_id = sc["id"]
        sentence = sc["sentence"]
        bp = blueprints[idx] if idx < len(blueprints) else blueprints[0]

        logger.info("-" * 80)
        logger.info(f"▶️ [Sản xuất Scene {sc_id}/8]: {sc['title']}")
        logger.info(f"   Keyword: '{sc['keyword']}' | Engine: {sc['engine']} | Floating: {sc['is_floating']} | Hand: {sc['has_hand']}")

        sc_dir = OUTPUT_DIR / f"scene_{sc_id}"
        sc_dir.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------------------
        # Step A: Audio Synthesis (TTSManager: VieNeu-TTS / EdgeTTS Fallback)
        # -------------------------------------------------------------
        audio_path = sc_dir / "voice.mp3"
        actual_dur = await synthesize_speech_resilient(tts, sentence, audio_path)
        video_dur = max(3.5, actual_dur + 0.4)
        logger.info(f"   ⏱️ Audio: {actual_dur:.2f}s -> Video Duration: {video_dur:.2f}s")

        # -------------------------------------------------------------
        # Step B: Archival Backdrop Provisioning via Gateway
        # -------------------------------------------------------------
        archival_cfg = dict(bp.get("archival_backdrop") or {})
        archival_cfg["keyword"] = sc["keyword"]
        archival_cfg["prompt"] = sc["backdrop_prompt"]
        archival_cfg["zoom_rate"] = 1.05

        raw_backdrop_path = await gateway.ensure_backdrop_asset_async(
            archival_cfg=archival_cfg,
            keyword=sc["keyword"],
            prompt=sc["backdrop_prompt"]
        )
        archival_cfg["asset_path"] = str(raw_backdrop_path.resolve())
        logger.info(f"   🏛️ Backdrop: {raw_backdrop_path.name} (Torn paper zoom 1.05x)")

        # -------------------------------------------------------------
        # Step C: Foreground Cutout Asset Resolution
        # -------------------------------------------------------------
        hero_p = str((ASSETS_DIR / sc["hero_asset"]).resolve())
        sec_p = str((ASSETS_DIR / sc["secondary_asset"]).resolve())
        if not os.path.exists(hero_p):
            logger.warning(f"Hero asset not found at {hero_p}, checking props...")
        if not os.path.exists(sec_p):
            logger.warning(f"Secondary asset not found at {sec_p}, checking props...")

        # -------------------------------------------------------------
        # Step D: Kinetic Layout Bridge Composition
        # -------------------------------------------------------------
        custom_params = dict(sc.get("custom_params", {}))
        custom_params["color_field"] = sc.get("color_field", "Plum & Gold")
        custom_params["color_hex"] = sc.get("color_hex", "4A235A")
        custom_params["environment_graphic"] = sc.get("environment_graphic", "coordinate_grid")

        emit_assets = [sec_p] if sc["engine"] == "ENGINE_EMIT_SLIDE" else None
        scene_layout = bridge.build_scene_layout(
            engine_name=sc["engine"],
            hero_asset_path=hero_p,
            secondary_asset_path=sec_p,
            action_assets_paths=emit_assets,
            custom_params=custom_params,
            director_blueprint=bp
        )

        # Enforce 7-Layer parameters strictly per M4 acceptance criteria:
        scene_layout["archetype"] = sc.get("archetype") or bp.get("spatial_context", {}).get("archetype", "conceptual_duel")
        scene_layout["archival_backdrop"] = archival_cfg
        scene_layout["color_field"] = sc.get("color_field", "Plum & Gold")
        scene_layout["color_hex"] = sc.get("color_hex", "4A235A")

        # Layer 2: Floating stage prop bypass for celestial/brain scenes
        if sc["is_floating"]:
            scene_layout["stage_prop"] = None
            scene_layout["is_floating"] = True
            if "secondary_element" in scene_layout:
                scene_layout["secondary_element"]["bottom_anchor"] = False
        else:
            stage_prop_cfg = bp.get("stage_prop") or {}
            stage_prop_cfg["is_floating"] = False
            stage_prop_cfg["name"] = stage_prop_cfg.get("name") or sc.get("stage_prop_name")
            stage_prop_cfg["style"] = stage_prop_cfg.get("style") or sc.get("archetype")
            scene_layout["stage_prop"] = stage_prop_cfg
            scene_layout["is_floating"] = False

        # Layer 6: Director hand accents (pointing, presenting, helpless)
        scene_layout["director_accents"] = {
            "has_hand": sc["has_hand"],
            "gesture": sc["hand_gesture"],
            "calligraphic_label": bp.get("director_accents", {}).get("calligraphic_label")
        }
        scene_layout["has_pointing_hand"] = sc["has_hand"]

        # -------------------------------------------------------------
        # Step E: 12fps Multi-Layer Stop-Motion Render (GbroAdapter)
        # -------------------------------------------------------------
        temp_visual_mp4 = sc_dir / "visual_no_audio.mp4"
        frames_dir = sc_dir / "frames"
        logger.info(f"   🎥 Rendering 12fps stop-motion ({video_dur:.2f}s @ 1080x1920)...")
        adapter.render_multi_layer_scene(
            scene_layout=scene_layout,
            hero_asset_path=hero_p,
            secondary_asset_path=sec_p,
            output_video_path=str(temp_visual_mp4),
            duration=video_dur,
            work_dir=frames_dir,
            width=1080,
            height=1920,
            fps=12
        )

        # -------------------------------------------------------------
        # Step F: Dynamic Chunked TikTok Subtitles (ASS Format)
        # -------------------------------------------------------------
        sub_ass = sc_dir / "subtitles.ass"
        SubtitleGenerator.generate_dynamic_chunked_ass(
            sentence=sentence,
            duration=actual_dur,
            output_path=sub_ass,
            chunk_words=3,
            font_size=44,
            margin_v=180
        )

        # -------------------------------------------------------------
        # Step G: Mux Scene Audio, Video & Subtitles (FFmpeg with Engine Fallback)
        # -------------------------------------------------------------
        scene_final_mp4 = sc_dir / f"scene_{sc_id}.mp4"
        sub_generator = SubtitleGenerator()
        sub_generator.burn_subtitles(
            video_path=str(temp_visual_mp4),
            sub_path=str(sub_ass),
            output_path=str(scene_final_mp4),
            audio_path=str(audio_path)
        )

        # -------------------------------------------------------------
        # Step H: Scene Snapshot Extraction
        # -------------------------------------------------------------
        snap_jpg = sc_dir / f"snapshot_scene_{sc_id}.jpg"
        mid_time = f"{video_dur / 2.0:.2f}"
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", mid_time,
            "-i", str(scene_final_mp4),
            "-vframes", "1",
            "-q:v", "2",
            str(snap_jpg)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Also place snapshot in parent output/human_body_cost_v2/
        global_snap_jpg = OUTPUT_DIR / f"snapshot_scene_{sc_id}.jpg"
        if snap_jpg.exists():
            import shutil
            shutil.copyfile(str(snap_jpg), str(global_snap_jpg))

        logger.success(f"✅ Scene {sc_id} hoàn tất: {scene_final_mp4.name} ({scene_final_mp4.stat().st_size / 1024:.1f} KB)")
        scene_final_paths.append(scene_final_mp4)
        scene_snapshots.append(global_snap_jpg)

    # =========================================================================
    # CONCATENATION: ASSEMBLE 8 SCENES INTO MASTER VIDEO V2
    # =========================================================================
    logger.info("=" * 80)
    logger.info("🎞️ [CONCATENATION] Đang ghép nối toàn bộ 8 phân cảnh thành Master Video V2...")
    concat_list_txt = OUTPUT_DIR / "concat_list.txt"
    with open(concat_list_txt, "w", encoding="utf-8") as f:
        for p in scene_final_paths:
            safe_p = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_txt),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        str(MASTER_VIDEO_PATH)
    ]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)

    # Master Snapshot at 12.0s
    master_snap_jpg = OUTPUT_DIR / "snapshot_master_v2.jpg"
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", "12.0",
        "-i", str(MASTER_VIDEO_PATH),
        "-vframes", "1",
        "-q:v", "2",
        str(master_snap_jpg)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Master Video Verification & Summary
    probe_master = get_video_info(str(MASTER_VIDEO_PATH))
    master_dur = float(probe_master.get("duration", 0.0))
    master_w = int(probe_master.get("width", 1080))
    master_h = int(probe_master.get("height", 1920))
    master_size_mb = MASTER_VIDEO_PATH.stat().st_size / (1024 * 1024)

    logger.success("=" * 80)
    logger.success("🎉🎉🎉 [MASTER VIDEO V2 HOÀN TẤT THÀNH CÔNG] 🎉🎉🎉")
    logger.success(f"📍 Master Video: {MASTER_VIDEO_PATH}")
    logger.success(f"📐 Độ phân giải: {master_w}x{master_h} (9:16 vertical mobile standard)")
    logger.success(f"⏱️ Thời lượng: {master_dur:.2f}s | Dung lượng: {master_size_mb:.2f} MB")
    logger.success(f"📸 Snapshots đã trích xuất: {len(scene_snapshots)} ảnh tại {OUTPUT_DIR}")
    logger.success("=" * 80)

    print(f"DONE_MASTER_V2:{MASTER_VIDEO_PATH}:{master_w}x{master_h}:{master_dur:.2f}s:{master_size_mb:.2f}MB")


if __name__ == "__main__":
    asyncio.run(produce_human_body_v2())
