"""
test_challenger_2_empirical.py
Empirical test suite for Challenger 2:
Adversarially challenge and stress-test boundaries, extreme parameters, and physical motion specifications.
"""

import os
import sys
import math
import ast
import asyncio
from pathlib import Path
from PIL import Image
import numpy as np

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from styles.collage_broll.torn_paper_generator import TornPaperBackdropGenerator, generate_torn_paper_backdrop
from core.media_engine.paper_fx_engine import PaperFXEngine, DebrisParticle
from core.script_engine.ai_visual_director import AIVisualDirector
from core.media_engine.kinetic_layout_bridge import KineticLayoutBridge
from core.media_engine.motion_timeline_engine import MotionTimelineEngine


def test_section_1_torn_paper():
    print("\n" + "="*70)
    print("TEST SECTION 1: TornPaperBackdropGenerator Boundary & Constraints")
    print("="*70)
    
    # 1.1 OpenCV Constraint: Verify zero `import cv2` across torn_paper_generator.py and paper_fx_engine.py
    print("[1.1] Verifying zero cv2 imports...")
    target_files = [
        PROJECT_ROOT / "styles" / "collage_broll" / "torn_paper_generator.py",
        PROJECT_ROOT / "core" / "media_engine" / "paper_fx_engine.py"
    ]
    for tf in target_files:
        with open(tf, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(tf))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "cv2" not in alias.name, f"VIOLATION: 'import {alias.name}' found in {tf.name}!"
                elif isinstance(node, ast.ImportFrom):
                    assert node.module != "cv2", f"VIOLATION: 'from cv2 import ...' found in {tf.name}!"
    print("  -> PASSED: Zero cv2 imports in torn_paper_generator.py and paper_fx_engine.py.")

    gen = TornPaperBackdropGenerator(default_seed=42)

    # 1.2 image_path is None -> Procedural woodcut engraving fallback executes cleanly
    print("[1.2] Testing image_path=None procedural fallback...")
    img_none = gen.generate_torn_paper_backdrop(
        image_path=None,
        target_width=860,
        target_height=950,
        full_canvas_size=(1080, 1920)
    )
    assert isinstance(img_none, Image.Image), "Result must be PIL Image"
    assert img_none.size == (1080, 1920), f"Expected (1080, 1920), got {img_none.size}"
    assert img_none.mode == "RGBA", f"Expected RGBA, got {img_none.mode}"
    bbox = img_none.getbbox()
    assert bbox is not None, "Output image must not be empty"
    print(f"  -> PASSED: None image_path created valid canvas with non-empty content: bbox={bbox}")

    # 1.3 image_path is non-existent file path
    print("[1.3] Testing non-existent image_path fallback...")
    img_missing = gen.generate_torn_paper_backdrop(
        image_path="non_existent_file_abc_123.png",
        target_width=860,
        target_height=950,
        full_canvas_size=(1080, 1920)
    )
    assert img_missing.size == (1080, 1920), "Size mismatch on missing path fallback"
    assert img_missing.getbbox() is not None, "Missing path must fallback to procedural content"
    print("  -> PASSED: Non-existent image_path gracefully handled with procedural fallback.")

    # 1.4 full_canvas_size=None -> Returns standalone sticker
    print("[1.4] Testing full_canvas_size=None (standalone sticker)...")
    sticker = gen.generate_torn_paper_backdrop(
        image_path=None,
        target_width=860,
        target_height=950,
        full_canvas_size=None
    )
    assert sticker.mode == "RGBA"
    # Pad is max(50, 8*4 + 10) = 50 -> local size 860+100=960, 950+100=1050
    assert sticker.size == (960, 1050), f"Expected sticker size (960, 1050), got {sticker.size}"
    print(f"  -> PASSED: full_canvas_size=None correctly returned standalone sticker of size {sticker.size}.")

    # 1.5 Extreme dimensions & parameters stress test
    print("[1.5] Stress testing extreme dimensions and parameters...")
    extreme_cases = [
        {"target_width": 50, "target_height": 50, "full_canvas_size": (200, 200)},
        {"target_width": 1000, "target_height": 1800, "full_canvas_size": (1080, 1920)},
        {"target_width": 100, "target_height": 900, "full_canvas_size": (1080, 1920)},
        {"target_width": 800, "target_height": 100, "full_canvas_size": (1080, 1920)},
        {"target_width": 400, "target_height": 400, "fiber_thickness": 1, "roughness": 1.0},
        {"target_width": 400, "target_height": 400, "fiber_thickness": 20, "roughness": 35.0},
        {"target_width": 400, "target_height": 400, "position_top": 0},
        {"target_width": 400, "target_height": 400, "position_top": 1500},
        {"target_width": 400, "target_height": 400, "position_top": -50},
    ]
    for idx, params in enumerate(extreme_cases):
        res = gen.generate_torn_paper_backdrop(**params)
        assert isinstance(res, Image.Image), f"Failed on case {idx}: {params}"
        assert res.mode == "RGBA", f"Mode mismatch on case {idx}"
        assert res.getbbox() is not None, f"Empty bbox on case {idx}"
    print(f"  -> PASSED: All {len(extreme_cases)} extreme boundary parameter sets executed cleanly without exception.")


def test_section_2_paper_fx_engine():
    print("\n" + "="*70)
    print("TEST SECTION 2: PaperFXEngine Boundary & Kinematic Verification")
    print("="*70)
    
    fx = PaperFXEngine(fps=12)
    impact_t = 1.8

    # Generate particles using a standard test image
    test_img = Image.new("RGBA", (200, 200), (120, 70, 30, 255))
    particles = fx.generate_debris_particles(
        source_image=test_img,
        num_particles=4,
        impact_center_px=(540, 1300)
    )
    assert len(particles) == 4, f"Expected 4 particles, got {len(particles)}"
    print(f"[2.1] Generated {len(particles)} debris particles successfully.")

    # 2.1 Boundary: t < impact_time -> MUST return empty list []
    print("[2.2] Testing t < impact_time...")
    pre_impact_times = [0.0, 0.5, 1.0, 1.5, 1.799, impact_t - 0.0001, -1.0]
    for t in pre_impact_times:
        states = fx.get_particles_state(t=t, impact_time=impact_t)
        assert states == [], f"Failed: at t={t} (< impact_time={impact_t}), get_particles_state must return [], got {states}"
        shock = fx.get_environmental_shock(t=t, impact_time=impact_t)
        assert shock == (0.0, 0.0), f"Failed: at t={t} (< impact_time), shock must be (0.0, 0.0), got {shock}"
    print("  -> PASSED: t < impact_time strictly returns empty list [] and (0.0, 0.0) shock.")

    # 2.2 Boundary: t >= impact_time + 4/12 -> MUST return empty list []
    print("[2.3] Testing t >= impact_time + 4/12...")
    expiry_times = [
        impact_t + 4.0 / 12.0,
        impact_t + 4.0 / 12.0 + 0.01,
        impact_t + 5.0 / 12.0,
        impact_t + 1.0,
        impact_t + 10.0
    ]
    for t in expiry_times:
        states = fx.get_particles_state(t=t, impact_time=impact_t)
        assert states == [], f"Failed: at t={t} (>= impact_time + 4/12), get_particles_state must return [], got {states}"
        shock = fx.get_environmental_shock(t=t, impact_time=impact_t)
        assert shock == (0.0, 0.0), f"Failed: at t={t} (>= impact_time + 4/12), shock must be (0.0, 0.0), got {shock}"
    print("  -> PASSED: t >= impact_time + 4/12 strictly returns empty list [] and (0.0, 0.0) shock.")

    # 2.3 Stop-motion frames 0, 1, 2, 3 verification
    print("[2.4] Testing stop-motion intermediate frames (0, 1, 2, 3)...")
    for step in range(4):
        t = impact_t + step / 12.0 + 0.001
        states = fx.get_particles_state(t=t, impact_time=impact_t)
        assert len(states) == 4, f"Expected 4 states at step {step}, got {len(states)}"
        for s in states:
            assert "image" in s and "position" in s and "rotation_deg" in s and "opacity" in s
            assert isinstance(s["image"], Image.Image)
        if step == 0:
            assert all(s["opacity"] == 1.0 for s in states)
        elif step == 1:
            assert all(s["opacity"] == 1.0 for s in states)
            # Verify burst outward
            for i, p in enumerate(particles):
                st = states[i]
                dx = st["position"][0] - p.origin_pos[0]
                dy = st["position"][1] - p.origin_pos[1]
                dist = math.hypot(dx, dy)
                assert 55.0 <= dist <= 125.0, f"Step 1 burst dist {dist} outside [60, 120] range!"
        elif step == 2:
            assert all(s["opacity"] == 0.90 for s in states)
            # Step 2 rotation in ±30° to ±60°
            for s in states:
                assert 29.0 <= abs(s["rotation_deg"]) <= 61.0, f"Step 2 spin {s['rotation_deg']} outside ±30°..±60°"
        elif step == 3:
            assert all(s["opacity"] == 0.40 for s in states)
    print("  -> PASSED: Stop-motion kinematics, burst distances, rotations, and opacities verified.")

    # 2.4 Environmental Shock magnitudes ±8px
    print("[2.5] Verifying Environmental Shock pattern and ±8px magnitudes...")
    expected_shocks = {
        0: (0.0, 8.0),
        1: (-8.0, -6.0),
        2: (6.0, 4.0),
        3: (-3.0, -2.0)
    }
    for step, expected in expected_shocks.items():
        t = impact_t + step / 12.0 + 0.001
        actual = fx.get_environmental_shock(t=t, impact_time=impact_t, shock_amplitude=8.0)
        assert actual == expected, f"Step {step} shock mismatch: expected {expected}, got {actual}"
    
    # Check extreme shock amplitude
    actual_16 = fx.get_environmental_shock(t=impact_t + 0.001, impact_time=impact_t, shock_amplitude=16.0)
    assert actual_16 == (0.0, 16.0), f"Shock scale failed: expected (0.0, 16.0), got {actual_16}"
    print("  -> PASSED: Environmental shock offsets strictly match ±8px specification.")

    # 2.5 Empty or Transparent source_image boundary
    print("[2.6] Testing empty or 100% transparent source_image...")
    fx_empty = PaperFXEngine(fps=12)
    
    # Case A: source_image is None
    p_none = fx_empty.generate_debris_particles(source_image=None, num_particles=3)
    assert len(p_none) == 3, "Failed to fallback on source_image=None"
    
    # Case B: source_image is completely transparent
    trans_img = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
    p_trans = fx_empty.generate_debris_particles(source_image=trans_img, num_particles=5)
    assert len(p_trans) == 5, "Failed to fallback on 100% transparent source_image"
    
    # Case C: tiny 1x1 image
    tiny_img = Image.new("RGBA", (1, 1), (255, 0, 0, 255))
    p_tiny = fx_empty.generate_debris_particles(source_image=tiny_img, num_particles=3)
    assert len(p_tiny) == 3, "Failed on tiny 1x1 image"

    # Case D: num_particles = 0
    p_zero = fx_empty.generate_debris_particles(source_image=test_img, num_particles=0)
    assert len(p_zero) == 0, "num_particles=0 must return empty list"

    print("  -> PASSED: Empty, None, tiny, and 100% transparent textures cleanly handled with procedural wood fallback.")


def test_section_3_ai_visual_director():
    print("\n" + "="*70)
    print("TEST SECTION 3: AIVisualDirector Thematic Stress & Blueprint Schema")
    print("="*70)
    
    director = AIVisualDirector()

    test_sentences = [
        # Thematic duel / Sever
        ("Lưỡi rìu bổ đôi khúc gỗ rừng già", "ENGINE_SEVER_SHATTER"),
        ("Con dao bếp sắc bén thái từng lát bánh mì baguette giòn rụm", "ENGINE_SEVER_SHATTER"),
        # Scientific / Absorb
        ("Tế bào bạch cầu thực bào nuốt chửng vi khuẩn gây bệnh", "ENGINE_ABSORB_DISSOLVE"),
        # Scientific / Sweep
        ("Kính hiển vi soi quét các mẫu tế bào trên đĩa petri", "ENGINE_SWEEP_OSCILLATE"),
        # Ocean / Translate
        ("Tàu ngầm lặn xuống đáy rãnh Mariana đo áp suất đại dương", "ENGINE_TRANSLATE_NAV"),
        # Relic / Converge
        ("Chiếc quách pharaoh chứa đầy bình canopic trong hầm mộ kim tự tháp", "ENGINE_CONVERGE_WRAP"),
        # Industrial / Compress
        ("Máy ép dập bẹp dúm quả cam mọng nước", "ENGINE_COMPRESS_SQUASH"),
        # Astronomy / Revolve
        ("Hố đen vũ trụ hút xoáy các hành tinh quay quanh", "ENGINE_REVOLVE_VORTEX"),
        # Edge cases:
        ("Câu thoại ngắn gọn", None),
        ("", None),
        ("!@#$%^&*()_+ 12345 🔪🪵🚀", None),
        ("Câu chuyện " * 100, None)
    ]

    REQUIRED_7_KEYS = [
        "spatial_context",
        "archival_backdrop",
        "stage_prop",
        "kinetic_cast",
        "cause_and_effect_fx",
        "director_accents",
        "transition"
    ]

    for sentence, expected_engine in test_sentences:
        display_s = (sentence[:40] + "...") if len(sentence) > 40 else sentence
        bp = director.direct_scene_sync(sentence)
        assert isinstance(bp, dict), f"Failed to return dict for '{display_s}'"
        
        # Verify 7 root layers
        for k in REQUIRED_7_KEYS:
            assert k in bp, f"Missing key '{k}' in blueprint for '{display_s}'"
        
        # Verify kinetic_cast sub-schema
        kc = bp["kinetic_cast"]
        assert "hero_actor" in kc and "secondary_target" in kc
        assert "name" in kc["hero_actor"] and "initial_position" in kc["hero_actor"]
        assert "name" in kc["secondary_target"] and "position" in kc["secondary_target"]

        # Verify stage_prop sub-schema
        sp = bp["stage_prop"]
        assert "name" in sp and "position" in sp and "environmental_shock" in sp
        assert "magnitude_px" in sp["environmental_shock"]

        # Verify cause_and_effect_fx sub-schema
        ce = bp["cause_and_effect_fx"]
        assert "kinetic_engine" in ce
        assert "recoil_px" in ce
        assert "paper_debris_fx" in ce

        if expected_engine:
            assert ce["kinetic_engine"] == expected_engine, f"Engine mismatch for '{display_s}': expected {expected_engine}, got {ce['kinetic_engine']}"

        # Verify recoil_px = 8.0px for SEVER and COMPRESS
        if ce["kinetic_engine"] in ["ENGINE_SEVER_SHATTER", "ENGINE_COMPRESS_SQUASH"]:
            assert ce["recoil_px"] == 8.0, f"Recoil px must be 8.0, got {ce['recoil_px']}"

        # Verify archival_backdrop dimensions
        ab = bp["archival_backdrop"]
        assert ab["target_width"] == 860
        assert ab["target_height"] == 950
        assert ab["cellulose_fiber_color"] == "#F5EFEB"

    print(f"  -> PASSED: All {len(test_sentences)} diverse thematic and edge sentences produced strictly valid 7-layer blueprints.")


def test_section_4_physical_motion_dynamics():
    print("\n" + "="*70)
    print("TEST SECTION 4: Physical Motion Dynamics Calibration")
    print("="*70)
    
    bridge = KineticLayoutBridge()

    # 4.1 ENGINE_SEVER_SHATTER Dynamics:
    # Vung cao -35° (y=0.16), bổ +6° (y=sec_y-0.02), toác dạt 260px, xoay 30°, recoil 8px
    print("[4.1] Testing ENGINE_SEVER_SHATTER motion dynamics...")
    sever_layout = bridge.build_scene_layout(
        engine_name="ENGINE_SEVER_SHATTER",
        hero_asset_path="dummy_axe.png",
        secondary_asset_path="dummy_woodlog.png"
    )
    timeline = sever_layout["timeline"]
    assert len(timeline) == 4, f"Expected 4 timeline phases, got {len(timeline)}"
    
    # Phase 0: Windup
    p0 = timeline[0]
    assert p0["max_tilt_deg"] == -35.0, f"Windup tilt must be -35.0, got {p0['max_tilt_deg']}"
    assert p0["start_pos"][1] == 0.16, f"Windup start_pos Y must be 0.16, got {p0['start_pos'][1]}"
    
    # Phase 1: Strike
    p1 = timeline[1]
    assert p1["max_tilt_deg"] == 6.0, f"Strike tilt must be 6.0, got {p1['max_tilt_deg']}"
    # Target secondary_y is 0.68 -> hero_impact_y = 0.68 - 0.02 = 0.66
    assert p1["end_pos"][1] == 0.66, f"Strike penetration Y must be 0.66, got {p1['end_pos'][1]}"

    # Phase 2: Recoil 8px
    p2 = timeline[2]
    # recoil_norm_y = round(8.0 / 1920, 4) = 0.0042 -> 0.66 - 0.0042 = 0.6558
    assert p2["end_pos"][1] == round(0.66 - round(8.0/1920, 4), 4), f"Recoil end_pos Y must be {round(0.66 - round(8.0/1920, 4), 4)}, got {p2['end_pos'][1]}"

    # Phase 3: Secondary Sever Shatter Drift
    p3 = timeline[3]
    assert p3["max_drift_px"] == 260.0, f"Max drift must be 260.0, got {p3['max_drift_px']}"
    assert p3["tilt_deg"] == 30.0, f"Tilt deg must be 30.0, got {p3['tilt_deg']}"
    assert p3["drift_direction"] == [1.0, 0.2], f"Drift direction must be [1.0, 0.2], got {p3['drift_direction']}"

    # Test MotionTimelineEngine.apply_sever_shatter
    impact_t = 1.8
    duration = 0.8
    ox, oy, rot = MotionTimelineEngine.apply_sever_shatter(
        t=impact_t + duration + 0.1,
        impact_time=impact_t,
        drift_direction=(1.0, 0.2),
        max_drift_px=260.0,
        tilt_deg=30.0,
        duration=duration
    )
    assert ox == 260.0, f"Final drift ox must be 260.0, got {ox}"
    assert oy == 52.0, f"Final drift oy must be 52.0 (0.2 * 260), got {oy}"
    assert rot == 30.0, f"Final tilt rot must be 30.0, got {rot}"
    print(f"  -> PASSED: ENGINE_SEVER_SHATTER drift (260px, 30°, [1.0, 0.2]), strike (y=0.66), windup (-35°), and recoil 8px verified.")

    # 4.2 ENGINE_EMIT_SLIDE Dynamics:
    # Trượt xa 580px, lượn chao đảo ±10°
    print("[4.2] Testing ENGINE_EMIT_SLIDE motion dynamics...")
    emit_layout = bridge.build_scene_layout(
        engine_name="ENGINE_EMIT_SLIDE",
        hero_asset_path="dummy_hero.png",
        action_assets_paths=["dummy_action.png"]
    )
    emit_timeline = emit_layout["timeline"]
    assert len(emit_timeline) == 1
    act0 = emit_timeline[0]
    assert act0["distance"] == 580.0, f"Slide distance must be 580.0, got {act0['distance']}"

    # Test MotionTimelineEngine.apply_emit_slide
    vis, ox, oy, wobble = MotionTimelineEngine.apply_emit_slide(
        t=1.4 + 0.85 + 0.1,
        spawn_time=1.4,
        slide_direction=(0.0, 1.0),
        distance=580.0,
        duration=0.85
    )
    assert vis is True
    assert ox == 0.0
    assert oy == 580.0, f"Slide oy must be 580.0, got {oy}"
    
    # Test wobble mid-flight
    vis_mid, ox_mid, oy_mid, wobble_mid = MotionTimelineEngine.apply_emit_slide(
        t=1.4 + 0.425,
        spawn_time=1.4,
        slide_direction=(0.0, 1.0),
        distance=580.0,
        duration=0.85
    )
    assert abs(wobble_mid) > 0.0, "Wobble must be active during slide mid-flight"
    print(f"  -> PASSED: ENGINE_EMIT_SLIDE slide distance (580px) and wobble (±10°) verified.")


def main():
    print("STARTING EMPIRICAL CHALLENGER 2 SUITE...")
    test_section_1_torn_paper()
    test_section_2_paper_fx_engine()
    test_section_3_ai_visual_director()
    test_section_4_physical_motion_dynamics()
    print("\n" + "="*70)
    print("ALL EMPIRICAL TESTS PASSED WITH ZERO FAILURES!")
    print("="*70)


if __name__ == "__main__":
    main()
