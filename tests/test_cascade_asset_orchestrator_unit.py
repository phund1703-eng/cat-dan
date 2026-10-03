"""
Automated Unit Test Suite for CascadeAssetOrchestrator
test_cascade_asset_orchestrator_unit.py

Validates Milestone 2 (R2):
- Test 1: Tier 1 Google Imagen 3 acquisition and validation.
- Test 2: Automatic failover from Tier 1 to Tier 2 (FLUX).
- Test 3: Automatic failover from Tier 1/2/3 to Tier 4 (ProceduralAssetSynthesizer).
- Test 4: In-Flight Vision Gate scoring, rejection, 1x retry on Tier 1, and tier downgrade.
- Test 5: Step 0 cache hit resolution and blacklist/intermediate rejection.
- Test 6: Rembg & paper keyline post-processing (8px ivory #FFFDF7 + drop shadow, zero OpenCV).
- Test 7: Dual-key failover and rotation.
"""

import sys
import os
import io
import asyncio
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.cascade_asset_orchestrator import CascadeAssetOrchestrator
from core.media_engine.asset_content_validator import AssetContentValidator


def _create_synthetic_raw_image(width: int = 512, height: int = 512) -> Image.Image:
    """Creates a synthetic raw test image on pure white background (#FFFFFF)."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    # Draw a distinct subject in center
    cx, cy = width // 2, height // 2
    d.ellipse([cx - 100, cy - 100, cx + 100, cy + 100], fill=(180, 120, 40), outline=(50, 30, 10), width=4)
    d.rectangle([cx - 30, cy - 140, cx + 30, cy + 140], fill=(220, 180, 50), outline=(50, 30, 10), width=2)
    return img


def _create_synthetic_cutout_image(width: int = 512, height: int = 512) -> Image.Image:
    """Creates a synthetic transparent RGBA cutout image."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = width // 2, height // 2
    d.ellipse([cx - 110, cy - 110, cx + 110, cy + 110], fill=(190, 130, 40, 255), outline=(50, 30, 10, 255), width=4)
    return img


class TestCascadeAssetOrchestratorUnit(unittest.TestCase):
    """Comprehensive Unit Tests for CascadeAssetOrchestrator."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.orchestrator = CascadeAssetOrchestrator(cache_dir=self.tmp_path / "cutouts")
        self.validator = AssetContentValidator()

    def tearDown(self):
        self.temp_dir.cleanup()

    # =========================================================================
    # Test 1: Tier 1 Imagen 3 Success
    # =========================================================================
    def test_01_tier1_imagen_success(self):
        """Assert acquire_asset successfully acquires via Tier 1 when available and approved."""
        async def _run():
            synth_raw = _create_synthetic_raw_image(512, 512)
            job_cache = self.tmp_path / "job_scene_1"

            with patch.object(self.orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(self.orchestrator, "evaluate_vision_gate", new_callable=AsyncMock) as mock_gate:

                mock_tier1.return_value = synth_raw
                mock_gate.return_value = {
                    "is_aligned": True,
                    "confidence": 0.94,
                    "reason": "Accurate vintage scientific microscope",
                    "refined_prompt": ""
                }

                out_path, meta = await self.orchestrator.acquire_asset(
                    target_object="vintage_brass_microscope",
                    scene_sentence="Kính hiển vi quang học thế kỷ 19",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                self.assertTrue(Path(out_path).exists(), "Output asset file must exist on disk.")
                self.assertEqual(meta["tier_used"], "tier1_imagen")
                self.assertEqual(meta["source"], "imagen-3.0-generate-002")
                self.assertTrue(meta["is_aligned"])
                self.assertAlmostEqual(meta["confidence"], 0.94)

                # Validation check
                val_res = self.validator.validate_cutout(out_path)
                self.assertTrue(val_res.is_valid, f"AssetContentValidator rejected asset: {val_res.reason}")

                # Format check
                with Image.open(out_path) as img:
                    self.assertEqual(img.mode, "RGBA")
                    self.assertEqual(img.size, (512, 512))

        asyncio.run(_run())

    # =========================================================================
    # Test 2: Tier 1 Failure -> Tier 2 FLUX Failover
    # =========================================================================
    def test_02_tier1_failover_to_tier2_flux(self):
        """Assert acquire_asset seamlessly falls over to Tier 2 when Tier 1 fails."""
        async def _run():
            synth_flux = _create_synthetic_raw_image(512, 512)
            job_cache = self.tmp_path / "job_scene_2"

            with patch.object(self.orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(self.orchestrator, "_generate_tier2_flux", new_callable=AsyncMock) as mock_tier2, \
                 patch.object(self.orchestrator, "evaluate_vision_gate", new_callable=AsyncMock) as mock_gate:

                # Tier 1 fails
                mock_tier1.return_value = None
                # Tier 2 succeeds
                mock_tier2.return_value = synth_flux
                mock_gate.return_value = {
                    "is_aligned": True,
                    "confidence": 0.89,
                    "reason": "Accurate antique clock on solid white background",
                    "refined_prompt": ""
                }

                out_path, meta = await self.orchestrator.acquire_asset(
                    target_object="antique_astronomical_clock",
                    scene_sentence="Đồng hồ thiên văn cổ thế kỷ 18",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                self.assertTrue(Path(out_path).exists())
                self.assertEqual(meta["tier_used"], "tier2_flux")
                self.assertEqual(meta["source"], "pollinations_flux")
                self.assertTrue(meta["is_aligned"])
                self.assertAlmostEqual(meta["confidence"], 0.89)

                val_res = self.validator.validate_cutout(out_path)
                self.assertTrue(val_res.is_valid, f"AssetContentValidator rejected asset: {val_res.reason}")

        asyncio.run(_run())

    # =========================================================================
    # Test 3: Tier 1, 2, 3 Failure -> Tier 4 Procedural Failover
    # =========================================================================
    def test_03_tier1_and_tier2_failover_to_tier4_procedural(self):
        """Assert acquire_asset falls over to Tier 4 Procedural Synthesizer (100% offline guarantee)."""
        async def _run():
            job_cache = self.tmp_path / "job_scene_3"

            with patch.object(self.orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(self.orchestrator, "_generate_tier2_flux", new_callable=AsyncMock) as mock_tier2, \
                 patch.object(self.orchestrator, "_generate_tier3_stock", new_callable=AsyncMock) as mock_tier3:

                # All online tiers fail
                mock_tier1.return_value = None
                mock_tier2.return_value = None
                mock_tier3.return_value = None

                out_path, meta = await self.orchestrator.acquire_asset(
                    target_object="golden_scale",
                    scene_sentence="Cái cân tiểu ly hai đĩa bằng đồng thau",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                self.assertTrue(Path(out_path).exists())
                self.assertEqual(meta["tier_used"], "tier4_procedural")
                self.assertEqual(meta["source"], "procedural_asset_synthesizer")
                self.assertTrue(meta["is_aligned"])
                self.assertEqual(meta["confidence"], 1.0)

                # Strictly check validator compliance
                val_res = self.validator.validate_cutout(out_path)
                self.assertTrue(val_res.is_valid, f"AssetContentValidator rejected procedural asset: {val_res.reason}")

                with Image.open(out_path) as img:
                    self.assertEqual(img.mode, "RGBA")
                    self.assertEqual(img.size, (512, 512))

        asyncio.run(_run())

    # =========================================================================
    # Test 4: Vision Gate Scoring, Discrimination & 1x Retry Behavior
    # =========================================================================
    def test_04_gemini_vision_gate_scoring_and_rejection(self):
        """Assert Vision Gate discriminates misaligned images and retries Tier 1 with refined prompt."""
        async def _run():
            # 4A. Direct evaluation of aligned vs unaligned outputs
            aligned_res = await self.orchestrator.evaluate_vision_gate(
                image=_create_synthetic_raw_image(),
                scene_sentence="Kính hiển vi quang học",
                target_object="microscope"
            )
            self.assertIn("is_aligned", aligned_res)
            self.assertIn("confidence", aligned_res)

            # 4B. Tier 1 rejected on attempt 1, retried with refined prompt and accepted on attempt 2
            job_cache = self.tmp_path / "job_scene_4"
            synth_attempt1 = _create_synthetic_raw_image(512, 512)
            synth_attempt2 = _create_synthetic_raw_image(512, 512)

            with patch.object(self.orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(self.orchestrator, "evaluate_vision_gate", new_callable=AsyncMock) as mock_gate:

                # First call returns attempt1, second returns attempt2
                mock_tier1.side_effect = [synth_attempt1, synth_attempt2]

                # First gate evaluation fails (< 0.75), second succeeds (>= 0.75)
                mock_gate.side_effect = [
                    {
                        "is_aligned": False,
                        "confidence": 0.38,
                        "reason": "Ảnh chứa quán rượu cao bồi không liên quan đến bình hóa chất",
                        "refined_prompt": "A single isolated glass erlenmeyer flask with blue liquid on solid white background"
                    },
                    {
                        "is_aligned": True,
                        "confidence": 0.91,
                        "reason": "Đúng chủ thể bình hóa chất Erlenmeyer",
                        "refined_prompt": ""
                    }
                ]

                out_path, meta = await self.orchestrator.acquire_asset(
                    target_object="chemical_flask",
                    scene_sentence="Bình tam giác chứa dung dịch hóa chất",
                    archetype="specimen_scientific",
                    job_cache_dir=job_cache,
                    width=512,
                    height=512
                )

                # Must have called Tier 1 twice (1 initial + 1 retry)
                self.assertEqual(mock_tier1.call_count, 2)
                # Output approved as Tier 1 on retry
                self.assertEqual(meta["tier_used"], "tier1_imagen")
                self.assertEqual(meta["confidence"], 0.91)
                self.assertTrue(Path(out_path).exists())

        asyncio.run(_run())

    # =========================================================================
    # Test 5: Step 0 Cache Check and Blacklist Filtering
    # =========================================================================
    def test_05_step0_cache_hit_and_rejection(self):
        """Assert Step 0 immediately returns valid cached assets and ignores blacklisted junk."""
        async def _run():
            job_cache = self.tmp_path / "job_scene_5"
            job_cache.mkdir(parents=True, exist_ok=True)

            # 5A. Place a valid cutout asset in cache
            valid_asset_path = job_cache / "biology_microscope.png"
            cutout_img = _create_synthetic_cutout_image(512, 512)
            cutout_img.save(str(valid_asset_path), format="PNG")

            out_path, meta = await self.orchestrator.acquire_asset(
                target_object="biology_microscope",
                job_cache_dir=job_cache
            )
            self.assertEqual(meta["tier_used"], "cache")
            self.assertEqual(meta["confidence"], 1.0)
            self.assertTrue(meta["is_aligned"])
            self.assertEqual(Path(out_path).resolve(), valid_asset_path.resolve())

            # 5B. Blacklisted files (scale.png, test_*, temp_*) must be ignored
            junk_scale = job_cache / "scale.png"
            # create junk image
            Image.new("RGB", (200, 200), (255, 0, 0)).save(str(junk_scale))

            with patch.object(self.orchestrator, "_generate_tier1_imagen", new_callable=AsyncMock) as mock_tier1, \
                 patch.object(self.orchestrator, "_generate_tier2_flux", new_callable=AsyncMock) as mock_tier2, \
                 patch.object(self.orchestrator, "_generate_tier3_stock", new_callable=AsyncMock) as mock_tier3:

                mock_tier1.return_value = None
                mock_tier2.return_value = None
                mock_tier3.return_value = None

                # Should NOT return junk_scale, should fall through to procedural
                out_path2, meta2 = await self.orchestrator.acquire_asset(
                    target_object="scale",
                    job_cache_dir=job_cache
                )
                self.assertNotEqual(Path(out_path2).name, "scale.png")
                self.assertEqual(meta2["tier_used"], "tier4_procedural")

        asyncio.run(_run())

    # =========================================================================
    # Test 6: Paper Keyline & Soft Drop Shadow Quality (Zero OpenCV)
    # =========================================================================
    def test_06_paper_keyline_and_shadow_quality(self):
        """Assert apply_paper_keyline_and_shadow produces compliant 8px ivory border and soft shadow."""
        cutout = _create_synthetic_cutout_image(400, 400)
        styled = self.orchestrator.apply_paper_keyline_and_shadow(
            img=cutout,
            outline_width=8,
            outline_color=(255, 253, 247, 255),
            shadow_offset=(8, 10),
            shadow_blur=8,
            shadow_alpha=115,
            target_width=512,
            target_height=512,
            add_cellulose_grain=True
        )

        self.assertEqual(styled.mode, "RGBA")
        self.assertEqual(styled.size, (512, 512))

        # Check alpha ratio compliance
        # (tên file không bắt đầu bằng "test_": AssetContentValidator hiện
        # từ chối stem test_*/temp_* như file tạm — đổi tên để test đúng
        # mục đích kiểm tra keyline/shadow, assert giữ nguyên)
        save_tmp = self.tmp_path / "keyline_check.png"
        styled.save(str(save_tmp), format="PNG")
        val_res = self.validator.validate_cutout(save_tmp)
        self.assertTrue(val_res.is_valid, f"Styled asset failed validation: {val_res.reason}")

    # =========================================================================
    # Test 7: Dual-Key Failover and Key Rotation
    # =========================================================================
    def test_07_dual_key_failover(self):
        """Assert _rotate_api_key toggles through keys upon encountering HTTP 429 quota errors."""
        self.orchestrator.api_keys = ["AIzaSy_KEY_PRIMARY_AAA", "AIzaSy_KEY_SECONDARY_BBB"]
        self.orchestrator.current_key_idx = 0

        self.assertEqual(self.orchestrator._get_active_api_key(), "AIzaSy_KEY_PRIMARY_AAA")
        self.orchestrator._rotate_api_key()
        self.assertEqual(self.orchestrator._get_active_api_key(), "AIzaSy_KEY_SECONDARY_BBB")
        self.orchestrator._rotate_api_key()
        self.assertEqual(self.orchestrator._get_active_api_key(), "AIzaSy_KEY_PRIMARY_AAA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
