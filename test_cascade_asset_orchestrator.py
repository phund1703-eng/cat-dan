"""
End-to-End Automated Test Suite for CascadeAssetOrchestrator & MultiAssetGenerator
test_cascade_asset_orchestrator.py

Milestone 4 (R4):
Automated test suite verifying the 4 mandatory cascade generation and failover scenarios:
- Test 1: Tier 1 Google Imagen 3 generation and valid cutout post-processing.
- Test 2: Tier 1 failure -> graceful, automatic failover to Tier 2 (FLUX).
- Test 3: Tier 1 & 2 failure -> automatic failover to Tier 4 Procedural
          (draw_scale / chemical_flask non-empty RGBA passing AssetContentValidator,
          and MultiAssetGenerator concurrent execution with backwards compatibility).
- Test 4: Gemini Vision Gate scoring accuracy and rejection of unaligned/off-topic images
          (triggering prompt refinement or tier failover).

Offline Determinism Guarantee:
Mocks external HTTP/API endpoints with synthetic 512x512 images so the test suite
runs deterministically in < 5 seconds with zero network flakiness and zero API key quota dependency,
while executing the REAL post-processing (apply_paper_keyline_and_shadow),
AssetContentValidator, and cache mechanics.

Execution:
    .\\venv\\Scripts\\python.exe test_cascade_asset_orchestrator.py
"""

import sys
import os
import io
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple
from unittest.mock import patch, MagicMock, AsyncMock

from PIL import Image, ImageDraw

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.cascade_asset_orchestrator import CascadeAssetOrchestrator
from core.media_engine.multi_asset_generator import MultiAssetGenerator
from core.media_engine.asset_content_validator import AssetContentValidator
from core.media_engine.procedural_asset_synthesizer import ProceduralAssetSynthesizer


def _create_synthetic_raw_image(width: int = 512, height: int = 512, color: Tuple[int, int, int] = (180, 120, 40)) -> Image.Image:
    """
    Creates a synthetic raw test image on pure solid white background (#FFFFFF).
    Has a solid colored subject in the center so that background removal
    (or white-background luminance keying fallback) produces a valid cutout.
    """
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    cx, cy = width // 2, height // 2
    # Draw distinct central subject
    d.ellipse([cx - 100, cy - 100, cx + 100, cy + 100], fill=color, outline=(40, 20, 10), width=4)
    d.rectangle([cx - 30, cy - 140, cx + 30, cy + 140], fill=(220, 180, 50), outline=(40, 20, 10), width=2)
    return img


# =============================================================================
# Test 1: Tier 1 Google Imagen 3 Success & Real Post-Processing
# =============================================================================
def test_01_tier1_imagen_success():
    """
    Test 1: Tier 1 Google Imagen 3 generation and valid cutout post-processing.
    Asserts acquire_asset successfully acquires via Tier 1 when available and approved by Vision Gate.
    Verifies output PNG exists, metadata matches tier1_imagen, REAL apply_paper_keyline_and_shadow
    is executed, and AssetContentValidator confirms valid RGBA alpha ratio (8% - 95%).
    """
    async def _async_test():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            job_cache = tmp_path / "job_scene_1"
            orchestrator = CascadeAssetOrchestrator(cache_dir=tmp_path / "cutouts")
            validator = AssetContentValidator()

            synth_raw = _create_synthetic_raw_image(512, 512, color=(180, 120, 40))

            with patch.object(orchestrator, "_check_cache", return_value=None), \
                 patch.object(orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(orchestrator, "evaluate_vision_gate", new_callable=AsyncMock) as mock_gate:

                mock_tier1.return_value = synth_raw
                mock_gate.return_value = {
                    "is_aligned": True,
                    "confidence": 0.95,
                    "reason": "Accurate vintage brass laboratory microscope on pure white background",
                    "refined_prompt": ""
                }

                out_path, meta = await orchestrator.acquire_asset(
                    target_object="vintage_brass_microscope",
                    scene_sentence="Kính hiển vi quang học phòng thí nghiệm thế kỷ 19",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                # 1. File existence
                p = Path(out_path)
                assert p.exists(), f"Output asset file must exist at {out_path}"
                assert p.is_file(), f"Output asset must be a regular file: {out_path}"

                # 2. Metadata verification
                assert meta["tier_used"] == "tier1_imagen", f"Expected tier1_imagen, got {meta.get('tier_used')}"
                assert meta["source"] == "imagen-3.0-generate-002", f"Expected imagen-3.0-generate-002, got {meta.get('source')}"
                assert meta["is_aligned"] is True, "Expected is_aligned to be True"
                assert meta["confidence"] >= 0.75, f"Expected confidence >= 0.75, got {meta.get('confidence')}"

                # 3. Real AssetContentValidator verification
                val_res = validator.validate_cutout(p)
                assert val_res.is_valid, f"AssetContentValidator rejected tier 1 asset: {val_res.reason}"

                # 4. Image properties verification
                with Image.open(p) as img:
                    assert img.mode == "RGBA", f"Expected RGBA mode, got {img.mode}"
                    assert img.size == (512, 512), f"Expected (512, 512), got {img.size}"

    asyncio.run(_async_test())


# =============================================================================
# Test 2: Tier 1 Failure -> Failover to Tier 2 (FLUX)
# =============================================================================
def test_02_tier1_failover_to_tier2_flux():
    """
    Test 2: Tier 1 failure -> graceful, automatic failover to Tier 2 (FLUX).
    Simulates Tier 1 failure (e.g. HTTP 429 quota exhaustion or API error),
    asserts acquire_asset automatically falls over to Tier 2 Pollinations FLUX without crashing,
    and produces a valid RGBA cutout passing AssetContentValidator.
    """
    async def _async_test():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            job_cache = tmp_path / "job_scene_2"
            orchestrator = CascadeAssetOrchestrator(cache_dir=tmp_path / "cutouts")
            validator = AssetContentValidator()

            synth_flux = _create_synthetic_raw_image(512, 512, color=(160, 100, 200))

            with patch.object(orchestrator, "_check_cache", return_value=None), \
                 patch.object(orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(orchestrator, "_generate_tier2_flux", new_callable=AsyncMock) as mock_tier2, \
                 patch.object(orchestrator, "evaluate_vision_gate", new_callable=AsyncMock) as mock_gate:

                # Tier 1 fails (simulating API failure or quota exhaustion)
                mock_tier1.return_value = None
                # Tier 2 succeeds
                mock_tier2.return_value = synth_flux
                # Vision Gate approves Tier 2
                mock_gate.return_value = {
                    "is_aligned": True,
                    "confidence": 0.88,
                    "reason": "Accurate antique astronomical clock on solid white background",
                    "refined_prompt": ""
                }

                out_path, meta = await orchestrator.acquire_asset(
                    target_object="antique_astronomical_clock",
                    scene_sentence="Đồng hồ thiên văn cổ thế kỷ 18 với các bánh răng đồng",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                # 1. File existence
                p = Path(out_path)
                assert p.exists(), f"Output asset must exist at {out_path}"

                # 2. Metadata verification
                assert meta["tier_used"] == "tier2_flux", f"Expected tier2_flux, got {meta.get('tier_used')}"
                assert meta["source"] == "pollinations_flux", f"Expected pollinations_flux, got {meta.get('source')}"
                assert meta["is_aligned"] is True, "Expected is_aligned to be True"
                assert meta["confidence"] >= 0.75, f"Expected confidence >= 0.75, got {meta.get('confidence')}"

                # 3. Real AssetContentValidator verification
                val_res = validator.validate_cutout(p)
                assert val_res.is_valid, f"AssetContentValidator rejected tier 2 asset: {val_res.reason}"

                # 4. Image properties
                with Image.open(p) as img:
                    assert img.mode == "RGBA", f"Expected RGBA mode, got {img.mode}"
                    assert img.size == (512, 512), f"Expected (512, 512), got {img.size}"

    asyncio.run(_async_test())


# =============================================================================
# Test 3: Tier 1 & 2 Failure -> Failover to Tier 4 Procedural
# =============================================================================
def test_03_tier1_and_tier2_failover_to_tier4_procedural():
    """
    Test 3: Tier 1 & 2 failure -> automatic failover to Tier 4 Procedural
    (draw_scale / chemical_flask non-empty RGBA passing AssetContentValidator).
    Also validates MultiAssetGenerator concurrent execution and backwards compatibility.
    """
    async def _async_test():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            job_cache = tmp_path / "job_scene_3"
            orchestrator = CascadeAssetOrchestrator(cache_dir=tmp_path / "cutouts")
            validator = AssetContentValidator()

            with patch.object(orchestrator, "_check_cache", return_value=None), \
                 patch.object(orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock, return_value=None), \
                 patch.object(orchestrator, "_generate_tier2_flux", new_callable=AsyncMock, return_value=None), \
                 patch.object(orchestrator, "_generate_tier3_stock", new_callable=AsyncMock, return_value=None):

                # 3A. Golden Scale Procedural Fallback
                scale_path, scale_meta = await orchestrator.acquire_asset(
                    target_object="golden_scale",
                    scene_sentence="Chiếc cân tiểu ly hai đĩa bằng đồng thau chuẩn xác",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                p_scale = Path(scale_path)
                assert p_scale.exists(), f"Scale asset must exist at {scale_path}"
                assert scale_meta["tier_used"] == "tier4_procedural", f"Expected tier4_procedural, got {scale_meta.get('tier_used')}"
                assert scale_meta["source"] == "procedural_asset_synthesizer"
                assert scale_meta["confidence"] == 1.0

                val_scale = validator.validate_cutout(p_scale)
                assert val_scale.is_valid, f"AssetContentValidator rejected procedural scale: {val_scale.reason}"
                assert 0.08 <= val_scale.transparent_ratio <= 0.95, f"Invalid alpha ratio: {val_scale.transparent_ratio}"

                with Image.open(p_scale) as img:
                    assert img.mode == "RGBA"
                    assert img.size == (512, 512)

                # 3B. Chemical Flask Procedural Fallback
                flask_path, flask_meta = await orchestrator.acquire_asset(
                    target_object="chemical_flask",
                    scene_sentence="Bình tam giác Erlenmeyer chứa dung dịch hóa chất và nhãn dán",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                p_flask = Path(flask_path)
                assert p_flask.exists(), f"Flask asset must exist at {flask_path}"
                assert flask_meta["tier_used"] == "tier4_procedural", f"Expected tier4_procedural, got {flask_meta.get('tier_used')}"
                assert flask_meta["source"] == "procedural_asset_synthesizer"

                val_flask = validator.validate_cutout(p_flask)
                assert val_flask.is_valid, f"AssetContentValidator rejected procedural flask: {val_flask.reason}"
                assert 0.08 <= val_flask.transparent_ratio <= 0.95, f"Invalid alpha ratio: {val_flask.transparent_ratio}"

                with Image.open(p_flask) as img:
                    assert img.mode == "RGBA"
                    assert img.size == (512, 512)

                # 3C. MultiAssetGenerator Integration & Backwards Compatibility
                generator = MultiAssetGenerator(cache_dir=tmp_path / "cutouts")
                generator.orchestrator = orchestrator

                scene_layout = {
                    "archetype": "specimen_scientific",
                    "narration": "Đo lường dung tích và khối lượng chất hóa học trên chiếc cân tiểu ly",
                    "hero_element": {
                        "name": "golden_scale",
                        "prompt": "a brass two-pan balance scale"
                    },
                    "secondary_element": {
                        "name": "chemical_flask",
                        "prompt": "an erlenmeyer glass flask with colored liquid"
                    }
                }

                scene_res = await generator.generate_scene_assets(
                    scene_layout=scene_layout,
                    output_dir=job_cache / "scene_concurrent"
                )

                # Check all 6 backwards-compatible keys
                assert "hero_path" in scene_res, "Missing hero_path in scene_res"
                assert "secondary_path" in scene_res, "Missing secondary_path in scene_res"
                assert "sec_path" in scene_res, "Missing sec_path in scene_res"
                assert "hero_qa" in scene_res, "Missing hero_qa in scene_res"
                assert "secondary_qa" in scene_res, "Missing secondary_qa in scene_res"
                assert "sec_qa" in scene_res, "Missing sec_qa in scene_res"

                assert scene_res["secondary_path"] == scene_res["sec_path"]
                assert Path(scene_res["hero_path"]).exists()
                assert Path(scene_res["sec_path"]).exists()

                assert scene_res["hero_qa"]["passed"] is True
                assert scene_res["sec_qa"]["passed"] is True
                assert scene_res["hero_qa"]["tier_used"] == "tier4_procedural"
                assert scene_res["sec_qa"]["tier_used"] == "tier4_procedural"

    asyncio.run(_async_test())


# =============================================================================
# Test 4: Gemini Vision Gate Scoring, Discrimination & 1x Retry Behavior
# =============================================================================
def test_04_gemini_vision_gate_scoring_and_rejection():
    """
    Test 4: Gemini Vision Gate scoring accuracy and rejection of unaligned/off-topic images
    (triggering prompt refinement or tier failover).
    Verifies that:
    1. Direct evaluate_vision_gate produces correct schema with confidence & alignment.
    2. An off-topic image (< 0.75) is rejected and triggers 1x retry with refined prompt.
    3. Persistent rejection triggers graceful tier failover to Tier 2 FLUX.
    """
    async def _async_test():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            orchestrator = CascadeAssetOrchestrator(cache_dir=tmp_path / "cutouts")

            # -----------------------------------------------------------------
            # 4A. Scoring accuracy and schema verification
            # -----------------------------------------------------------------
            mock_json_resp = json.dumps({
                "is_aligned": False,
                "confidence": 0.35,
                "reason": "Ảnh chứa quán bar cao bồi không liên quan đến kính hiển vi",
                "refined_prompt": "A single isolated vintage brass microscope on pure solid white background"
            })
            with patch.object(orchestrator, "_get_active_api_key", return_value="mock_key"), \
                 patch.object(orchestrator, "api_keys", ["mock_key_1"]), \
                 patch("core.media_engine.cascade_asset_orchestrator.legacy_genai") as mock_leg:
                mock_model = MagicMock()
                mock_leg.GenerativeModel.return_value = mock_model
                mock_resp = MagicMock()
                mock_resp.text = mock_json_resp
                mock_model.generate_content.return_value = mock_resp

                synth_sample = _create_synthetic_raw_image(512, 512)
                eval_res = await orchestrator.evaluate_vision_gate(
                    image=synth_sample,
                    scene_sentence="Kính hiển vi quang học phòng thí nghiệm",
                    target_object="microscope"
                )
                assert "is_aligned" in eval_res, "Missing 'is_aligned' in Vision Gate result"
                assert "confidence" in eval_res, "Missing 'confidence' in Vision Gate result"
                assert eval_res["is_aligned"] is False, "Vision Gate should have rejected unaligned image"
                assert eval_res["confidence"] == 0.35, f"Expected confidence 0.35, got {eval_res['confidence']}"
                assert "quán bar" in eval_res["reason"], "Reason should mention why image was rejected"
                assert "microscope" in eval_res["refined_prompt"], "Refined prompt should mention target object"

            # -----------------------------------------------------------------
            # 4B. In-Flight Rejection & 1x Prompt Refinement Retry
            # -----------------------------------------------------------------
            job_cache_4b = tmp_path / "job_scene_4b"
            synth_attempt1 = _create_synthetic_raw_image(512, 512, color=(100, 50, 50))
            synth_attempt2 = _create_synthetic_raw_image(512, 512, color=(200, 150, 50))

            with patch.object(orchestrator, "_check_cache", return_value=None), \
                 patch.object(orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(orchestrator, "evaluate_vision_gate", new_callable=AsyncMock) as mock_gate:

                # First call returns off-topic attempt 1; second call returns corrected attempt 2
                mock_tier1.side_effect = [synth_attempt1, synth_attempt2]

                # Attempt 1 rejected (confidence 0.35 < 0.75), attempt 2 approved (confidence 0.93 >= 0.75)
                mock_gate.side_effect = [
                    {
                        "is_aligned": False,
                        "confidence": 0.35,
                        "reason": "Ảnh chứa quán bar cao bồi không liên quan đến bình hóa chất",
                        "refined_prompt": "A single isolated vintage glass chemical flask with blue liquid on solid white background"
                    },
                    {
                        "is_aligned": True,
                        "confidence": 0.93,
                        "reason": "Đúng chủ thể bình hóa chất Erlenmeyer phòng thí nghiệm",
                        "refined_prompt": ""
                    }
                ]

                out_path, meta = await orchestrator.acquire_asset(
                    target_object="chemical_flask",
                    scene_sentence="Bình tam giác chứa dung dịch hóa chất phòng thí nghiệm",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache_4b,
                    width=512,
                    height=512
                )

                # Tier 1 must have been called exactly 2 times (1 initial + 1 retry)
                assert mock_tier1.call_count == 2, f"Expected 2 Tier 1 calls, got {mock_tier1.call_count}"
                assert meta["tier_used"] == "tier1_imagen", f"Expected tier1_imagen on retry, got {meta.get('tier_used')}"
                assert meta["confidence"] == 0.93
                assert meta["is_aligned"] is True
                assert Path(out_path).exists()

            # -----------------------------------------------------------------
            # 4C. Persistent Rejection -> Automatic Failover to Tier 2
            # -----------------------------------------------------------------
            job_cache_4c = tmp_path / "job_scene_4c"
            synth_flux = _create_synthetic_raw_image(512, 512, color=(50, 150, 200))

            with patch.object(orchestrator, "_check_cache", return_value=None), \
                 patch.object(orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1_fail, \
                 patch.object(orchestrator, "_generate_tier2_flux", new_callable=AsyncMock) as mock_tier2_succ, \
                 patch.object(orchestrator, "evaluate_vision_gate", new_callable=AsyncMock) as mock_gate_failover:

                # Tier 1 returns images for both attempts
                mock_tier1_fail.side_effect = [synth_attempt1, synth_attempt2]
                # Tier 2 returns FLUX image
                mock_tier2_succ.return_value = synth_flux

                # Both Tier 1 attempts fail Vision Gate, Tier 2 succeeds
                mock_gate_failover.side_effect = [
                    {"is_aligned": False, "confidence": 0.20, "reason": "Lạc đề", "refined_prompt": "refine 1"},
                    {"is_aligned": False, "confidence": 0.40, "reason": "Vẫn lạc đề", "refined_prompt": "refine 2"},
                    {"is_aligned": True, "confidence": 0.89, "reason": "Tier 2 FLUX đạt chuẩn", "refined_prompt": ""}
                ]

                out_path_c, meta_c = await orchestrator.acquire_asset(
                    target_object="microscope",
                    scene_sentence="Kính hiển vi quang học",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache_4c,
                    width=512,
                    height=512
                )

                assert mock_tier1_fail.call_count == 2, "Tier 1 should have retried once before failover"
                assert mock_tier2_succ.call_count == 1, "Tier 2 FLUX should have been invoked after Tier 1 failover"
                assert meta_c["tier_used"] == "tier2_flux", f"Expected tier2_flux, got {meta_c.get('tier_used')}"
                assert meta_c["confidence"] == 0.89
                assert Path(out_path_c).exists()

    asyncio.run(_async_test())


# =============================================================================
# Direct Runner Entry Point
# =============================================================================
if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main(["-v", __file__]))
    except Exception as e:
        print(f"Pytest invocation error ({e}), executing test functions directly...")
        test_01_tier1_imagen_success()
        print("✅ PASS: test_01_tier1_imagen_success")
        test_02_tier1_failover_to_tier2_flux()
        print("✅ PASS: test_02_tier1_failover_to_tier2_flux")
        test_03_tier1_and_tier2_failover_to_tier4_procedural()
        print("✅ PASS: test_03_tier1_and_tier2_failover_to_tier4_procedural")
        test_04_gemini_vision_gate_scoring_and_rejection()
        print("✅ PASS: test_04_gemini_vision_gate_scoring_and_rejection")
        print("\nAll 4 test cases passed successfully.")
        sys.exit(0)
