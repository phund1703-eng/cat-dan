"""
test_swe_light_bugfix.py
Automated test suite verifying Requirements R1 - R5 and all Acceptance Criteria:
- R1: Strict Asset Resolution in UniversalLLMDirector
- R2: Archetype-Aware Stage Props in GbroAdapter
- R3: Procedural Generation for golden_scale.png in prepare_human_body_assets
- R4: AssetContentValidator Module
- R5: Audit & Migrate Asset Cache to Central Library
"""

import os
import shutil
import pytest
from pathlib import Path
from PIL import Image
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent

# Imports under test
from core.script_engine.universal_llm_director import UniversalLLMDirector
from core.script_engine.ai_visual_director import AIVisualDirector
from styles.collage_broll.gbro_adapter import (
    GbroAdapter,
    generate_scene_appropriate_prop,
    SCENE_PROP_STYLE_MAP
)
from prepare_human_body_assets import draw_procedural_golden_scale
from core.media_engine.asset_content_validator import AssetContentValidator, ValidationResult
from scripts.audit_and_migrate_asset_cache import (
    audit_and_migrate,
    is_blacklisted,
    APPROVED_ASSET_NAMES,
    REJECTED_ASSET_NAMES,
    NEW_LIBRARY,
    OLD_CACHE,
    QUARANTINE_DIR
)


# =============================================================================
# R1 Tests: Strict Asset Resolution
# =============================================================================
class TestR1StrictAssetResolution:
    @pytest.fixture(autouse=True)
    def setup_director(self):
        self.director = UniversalLLMDirector(provider="mock")

    def test_r1_pound_tag_returns_none(self):
        """Acceptance Criterion 3: _resolve_cached_asset('44300_pound_tag', 'prop') accurately returns None."""
        res = self.director._resolve_cached_asset("44300_pound_tag", "prop")
        assert res is None, f"Expected None for '44300_pound_tag', got {res}"

    def test_r1_never_fallback_to_random_asset(self):
        """Never fallback to a random asset for completely unknown keywords."""
        unknown_keywords = [
            "completely_unknown_quantum_device_xyz_123",
            "nonexistent_asset_404",
            "random_gibberish_99999",
            "44300_pound",
            "pound_tag"
        ]
        for kw in unknown_keywords:
            res = self.director._resolve_cached_asset(kw, "prop")
            assert res is None, f"Expected None for '{kw}', got {res}"

    def test_r1_exact_match_level_1(self):
        """Level 1: Exact match finds known asset."""
        res = self.director._resolve_cached_asset("vintage_camera", "prop")
        assert res is not None, "Expected vintage_camera to resolve"
        assert "vintage_camera.png" in res.lower()

    def test_r1_token_match_level_2(self):
        """Level 2: Suffix or prefix match with token length > 3."""
        res = self.director._resolve_cached_asset("microscope", "hero")
        assert res is not None, "Expected microscope to resolve to biology_microscope.png"
        assert "microscope" in res.lower()

    def test_r1_short_token_fallback(self):
        """Level 2: Supports short 3-character tokens like 'dna' and 'axe'."""
        res_dna = self.director._resolve_cached_asset("dna", "hero")
        assert res_dna is not None, "Expected 'dna' to resolve to biology_dna.png"
        assert "dna" in res_dna.lower()

        res_axe = self.director._resolve_cached_asset("axe", "prop")
        assert res_axe is not None, "Expected 'axe' to resolve to real_axe.png"
        assert "axe" in res_axe.lower()

    def test_r1_token_boundary_rejection(self):
        """Rejects arbitrary substring matches that do not follow token boundaries."""
        # 'micro' is a substring of 'microscope' but not a token separated by '_' or '-'
        res_micro = self.director._resolve_cached_asset("micro", "hero")
        assert res_micro is None, f"Expected None for non-token substring 'micro', got {res_micro}"

    def test_r1_search_priority_order(self, tmp_path):
        """Verify priority: job_cutout_dir -> global_cutouts -> data/cache/cutouts."""
        # Create dummy asset in job_cutout_dir
        job_dir = tmp_path / "job_cutouts"
        job_dir.mkdir(parents=True)
        job_file = job_dir / "vintage_camera.png"
        img = Image.new("RGBA", (100, 100), (200, 100, 50, 200))
        img.save(job_file)

        res = self.director._resolve_cached_asset("vintage_camera", "prop", job_cutout_dir=job_dir)
        assert res is not None
        assert Path(res).resolve() == job_file.resolve(), "job_cutout_dir must take precedence over global/cache"

    def test_r1_whitespace_and_empty_returns_none(self):
        """Whitespace and empty keyword must safely return None without filesystem errors."""
        assert self.director._resolve_cached_asset("   ", "hero") is None
        assert self.director._resolve_cached_asset("", "hero") is None
        assert self.director._resolve_cached_asset("   \t\n  ", "prop") is None

    def test_r1_scale_bird_never_resolved(self):
        """'scale' or 'scale.png' must never resolve to bird image in cutouts cache."""
        assert self.director._resolve_cached_asset("scale", "prop") is None
        assert self.director._resolve_cached_asset("scale.png", "prop") is None

    def test_r1_all_blacklisted_junk_never_resolved(self):
        """All blacklisted junk files must return None even if requested explicitly."""
        junk_queries = [
            "scale", "scale.png",
            "test_art_cutout", "test_art_cutout.png",
            "test_axe_flip_v", "test_axe_rot_180",
            "test_knife_dl", "test_knife_flip_v",
            "temp_raw_real_kitchen_knife",
            "real_axe_raw_try1",
            "biology_white_blood_cell_raw_try1"
        ]
        for jq in junk_queries:
            assert self.director._resolve_cached_asset(jq, "prop") is None, f"Expected None for junk query '{jq}'"

    def test_r1_ai_visual_director_synchronization(self):
        """AIVisualDirector must match UniversalLLMDirector strict resolution rules."""
        ai_dir = AIVisualDirector()
        assert ai_dir._resolve_cached_asset("44300_pound_tag", "prop") is None
        assert ai_dir._resolve_cached_asset("scale", "prop") is None
        assert ai_dir._resolve_cached_asset("scale.png", "prop") is None
        assert ai_dir._resolve_cached_asset("   ", "hero") is None
        assert ai_dir._resolve_cached_asset("vintage_camera", "prop") is not None
        assert ai_dir._resolve_cached_asset("dna", "hero") is not None
        assert ai_dir._resolve_cached_asset("micro", "hero") is None


# =============================================================================
# R2 Tests: Archetype-Aware Stage Props
# =============================================================================
class TestR2ArchetypeAwareProps:
    def test_r2_generate_scene_appropriate_prop_5_archetypes(self):
        """Acceptance Criterion 4: Successfully generates valid size images for 5 archetypes."""
        archetypes = [
            "specimen_scientific",
            "oxford_library",
            "bank_teller",
            "historical_relic",
            "default"
        ]
        for arch in archetypes:
            img = generate_scene_appropriate_prop(
                archetype_or_style=arch,
                target_width=702,
                target_height=310
            )
            assert isinstance(img, Image.Image), f"Failed to generate Image for {arch}"
            assert img.mode == "RGBA", f"Expected RGBA mode for {arch}, got {img.mode}"
            # Due to padding pad=55 added on both sides, size >= (702 + 110, 310 + 110)
            assert img.width >= 702, f"Width {img.width} too small for {arch}"
            assert img.height >= 310, f"Height {img.height} too small for {arch}"

    def test_r2_scene_prop_style_map(self):
        """Verify SCENE_PROP_STYLE_MAP contains required styles and archetypes."""
        expected_styles = {
            "lab_bench", "stone_plinth", "reading_desk",
            "teller_counter", "display_plinth", "harbor_deck", "classic_plinth"
        }
        for s in expected_styles:
            assert s in SCENE_PROP_STYLE_MAP
            assert SCENE_PROP_STYLE_MAP[s] == s

        assert SCENE_PROP_STYLE_MAP["specimen_scientific"] == "lab_bench"
        assert SCENE_PROP_STYLE_MAP["oxford_library"] == "reading_desk"
        assert SCENE_PROP_STYLE_MAP["bank_teller"] == "teller_counter"
        assert SCENE_PROP_STYLE_MAP["historical_relic"] == "stone_plinth"
        assert SCENE_PROP_STYLE_MAP["default"] == "classic_plinth"

    def test_r2_workbench_delegates_to_classic_plinth(self):
        """generate_procedural_workbench delegates to generate_scene_appropriate_prop without carpenter vice."""
        adapter = GbroAdapter()
        prop = adapter.generate_procedural_workbench(target_width=500, target_height=200)
        assert isinstance(prop, Image.Image)
        assert prop.mode == "RGBA"
        assert prop.width > 500

    def test_r2_float_and_tiny_dimensions_safe(self):
        """Props must handle float and small dimensions gracefully without Pillow errors."""
        # Float dimensions test
        img_float = generate_scene_appropriate_prop(
            archetype_or_style="bank_teller",
            target_width=702.5,
            target_height=310.5
        )
        assert isinstance(img_float, Image.Image)
        assert img_float.mode == "RGBA"

        # Tiny dimensions test (tests coordinate clamping across all styles)
        for s in ["teller_counter", "stone_plinth", "lab_bench", "reading_desk", "display_plinth", "classic_plinth"]:
            img_tiny = generate_scene_appropriate_prop(
                archetype_or_style=s,
                target_width=100,
                target_height=80
            )
            assert isinstance(img_tiny, Image.Image)
            assert img_tiny.mode == "RGBA"

    def test_r2_to_legacy_scene_layout_preserves_7_layer_keys(self):
        """to_legacy_scene_layout must preserve stage_prop, archival_backdrop, and is_floating."""
        director = UniversalLLMDirector(provider="mock")
        blueprint = {
            "spatial_context": {"archetype": "oxford_library", "color_field": "Deep Cobalt", "color_hex": "1D3557"},
            "archival_backdrop": {"keyword": "oxford_library", "zoom_rate": 1.05},
            "stage_prop": {"name": "wooden_library_desk", "style": "reading_desk", "is_floating": False},
            "is_floating": False,
            "kinetic_cast": {
                "hero_actor": {"name": "bryson_book"},
                "secondary_target": {"name": "elements_59_chart"}
            },
            "cause_and_effect_fx": {"engine": "ENGINE_EMIT_SLIDE"},
            "director_accents": {"has_hand": False}
        }
        legacy = director.to_legacy_scene_layout(blueprint)
        assert legacy["archetype"] == "oxford_library"
        assert "stage_prop" in legacy
        assert legacy["stage_prop"]["name"] == "wooden_library_desk"
        assert "archival_backdrop" in legacy
        assert legacy["archival_backdrop"]["keyword"] == "oxford_library"
        assert legacy["is_floating"] is False


# =============================================================================
# R3 Tests: Procedural golden_scale.png
# =============================================================================
class TestR3ProceduralGoldenScale:
    def test_r3_draw_procedural_golden_scale(self, tmp_path):
        """Acceptance Criterion 5: Produces valid RGBA golden_scale.png."""
        save_path = tmp_path / "golden_scale.png"
        img = draw_procedural_golden_scale(save_path)

        assert save_path.exists(), "golden_scale.png was not saved"
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA", f"Expected RGBA mode, got {img.mode}"
        assert img.size == (480, 460), f"Expected (480, 460), got {img.size}"

        # Check alpha channel transparency ratio
        alpha = np.array(img.getchannel("A"))
        trans_ratio = float(np.sum(alpha < 128)) / float(alpha.size)
        assert 0.08 <= trans_ratio <= 0.95, (
            f"Alpha transparent ratio {trans_ratio:.1%} outside expected cutout range [8%, 95%]"
        )

        # Check color bands contain gold/brass values
        rgb_arr = np.array(img)
        # Gold RGB: (212, 168, 40)
        has_gold = np.any((rgb_arr[:, :, 0] > 180) & (rgb_arr[:, :, 1] > 120) & (rgb_arr[:, :, 2] < 80))
        assert has_gold, "Image does not appear to contain golden/brass colors"


# =============================================================================
# R4 Tests: AssetContentValidator Module
# =============================================================================
class TestR4AssetContentValidator:
    @pytest.fixture(autouse=True)
    def setup_validator(self):
        self.validator = AssetContentValidator()

    def test_r4_rejects_scale_png(self):
        """Acceptance Criterion 2a: AssetContentValidator successfully rejects scale.png."""
        res = self.validator.validate_cutout("scale.png")
        assert not res.is_valid, "scale.png must be rejected"
        assert not bool(res), "ValidationResult must evaluate to False"
        assert "scale.png" in res.reason.lower() or "alpha" in res.reason.lower()

        # validate_and_reject_if_invalid must return empty string
        rejected_path = self.validator.validate_and_reject_if_invalid("scale.png")
        assert rejected_path == "", f"Expected empty string for scale.png, got '{rejected_path}'"

    def test_r4_approves_biology_microscope(self):
        """Acceptance Criterion 2b: AssetContentValidator approves biology_microscope.png."""
        micro_cand = PROJECT_ROOT / "data" / "cache" / "cutouts" / "biology_microscope.png"
        if not micro_cand.exists():
            micro_cand = PROJECT_ROOT / "data" / "asset_library" / "global_cutouts" / "biology_microscope.png"

        assert micro_cand.exists(), f"biology_microscope.png must exist at {micro_cand}"
        res = self.validator.validate_cutout(micro_cand)
        assert res.is_valid, f"biology_microscope.png must be approved, reason: {res.reason}"
        assert bool(res)

        approved_path = self.validator.validate_and_reject_if_invalid(micro_cand)
        assert approved_path != ""
        assert Path(approved_path).exists()

    def test_r4_rejects_missing_and_non_rgba(self, tmp_path):
        """Rejects non-existent files and non-RGBA files."""
        assert not self.validator.validate_cutout("totally_nonexistent_file_xyz.png").is_valid
        assert self.validator.validate_and_reject_if_invalid("totally_nonexistent_file_xyz.png") == ""

        # RGB mode image without alpha
        rgb_path = tmp_path / "rgb_no_alpha.png"
        Image.new("RGB", (100, 100), (255, 0, 0)).save(rgb_path)
        res_rgb = self.validator.validate_cutout(rgb_path)
        assert not res_rgb.is_valid
        assert "rgba" in res_rgb.reason.lower() or "missing alpha" in res_rgb.reason.lower()

    def test_r4_rejects_solid_image(self, tmp_path):
        """Rejects solid background image (alpha ratio < 8%)."""
        solid_path = tmp_path / "solid_image.png"
        img = Image.new("RGBA", (200, 200), (255, 255, 255, 255)) # Solid white
        img.save(solid_path)

        res = self.validator.validate_cutout(solid_path)
        assert not res.is_valid
        assert "solid background" in res.reason.lower() or "below minimum" in res.reason.lower()
        assert self.validator.validate_and_reject_if_invalid(solid_path) == ""

    def test_r4_rejects_empty_image(self, tmp_path):
        """Rejects empty/nearly empty image (alpha ratio > 95%)."""
        empty_path = tmp_path / "empty_image.png"
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 0)) # Completely transparent
        img.save(empty_path)

        res = self.validator.validate_cutout(empty_path)
        assert not res.is_valid
        assert "empty" in res.reason.lower() or "exceeds maximum" in res.reason.lower()
        assert self.validator.validate_and_reject_if_invalid(empty_path) == ""

    def test_r4_rejects_invalid_dimensions(self, tmp_path):
        """Rejects dimensions outside 60x60 to 4096x4096."""
        tiny_path = tmp_path / "tiny.png"
        Image.new("RGBA", (40, 40), (100, 100, 100, 128)).save(tiny_path)
        assert not self.validator.validate_cutout(tiny_path).is_valid

        huge_path = tmp_path / "huge.png"
        Image.new("RGBA", (4097, 100), (100, 100, 100, 128)).save(huge_path)
        assert not self.validator.validate_cutout(huge_path).is_valid

    def test_r4_rejects_directory_path(self, tmp_path):
        """Directories must not be treated as valid image cutouts."""
        assert not self.validator.validate_cutout(tmp_path).is_valid
        assert self.validator.validate_and_reject_if_invalid(tmp_path) == ""

    def test_r4_handles_non_string_types(self):
        """Non-string/non-Path types must return ValidationResult(False, ...) without raising exceptions."""
        for invalid_input in [12345, 99.9, {}, [], object()]:
            res = self.validator.validate_cutout(invalid_input)
            assert not res.is_valid
            assert "invalid asset path type" in res.reason.lower()
            assert self.validator.validate_and_reject_if_invalid(invalid_input) == ""


# =============================================================================
# R5 Tests: Audit and Migrate Asset Cache
# =============================================================================
class TestR5AuditAndMigrate:
    def test_r5_blacklist_filtering(self):
        """Blacklist rejects scale.png, test_*, temp_*, and _raw_try files."""
        assert is_blacklisted(Path("scale.png"))[0]
        assert is_blacklisted(Path("test_art_cutout.png"))[0]
        assert is_blacklisted(Path("test_axe_flip_v.png"))[0]
        assert is_blacklisted(Path("temp_raw_real_kitchen_knife.png"))[0]
        assert is_blacklisted(Path("real_axe_raw_try1.png"))[0]

        # Valid assets must not be blacklisted
        assert not is_blacklisted(Path("biology_microscope.png"))[0]
        assert not is_blacklisted(Path("vintage_camera.png"))[0]
        assert not is_blacklisted(Path("real_axe.png"))[0]

    def test_r5_audit_and_migrate_execution(self):
        """Acceptance Criterion 1: Run audit_and_migrate successfully, creating global_cutouts."""
        results = audit_and_migrate()
        assert NEW_LIBRARY.exists(), f"Target directory {NEW_LIBRARY} was not created"
        assert isinstance(results, dict)
        assert "approved" in results
        assert "rejected" in results

        # Ensure no blacklisted file ended up in NEW_LIBRARY
        for f in NEW_LIBRARY.glob("*.png"):
            assert not is_blacklisted(f)[0], f"Blacklisted junk file found in global library: {f.name}"
            assert f.name.lower() != "scale.png", "scale.png (bird image) must NEVER be in global library"

        # Ensure procedural golden_scale.png is migrated and is 480x460 (authentic balance scale)
        golden_migrated = NEW_LIBRARY / "golden_scale.png"
        assert golden_migrated.exists(), "golden_scale.png must be present in NEW_LIBRARY"
        with Image.open(golden_migrated) as g_img:
            assert g_img.size == (480, 460), (
                f"golden_scale.png in NEW_LIBRARY must be procedural (480, 460), got {g_img.size}"
            )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
