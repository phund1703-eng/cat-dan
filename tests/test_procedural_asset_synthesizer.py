"""
Automated Test Suite for ProceduralAssetSynthesizer
test_procedural_asset_synthesizer.py

Validates Milestone 1 (R1):
- Mode strictly 'RGBA'
- Correct dimensions & dimension clamping
- Valid alpha ratios:
  * AssetContentValidator: 0.08 <= transparent_ratio <= 0.95
  * AlphaQAGate: 0.08 <= opaque_ratio <= 0.85
- Dispatcher routing in synthesize()
- File persistence with save_path
- Edge cases: tiny/huge dimensions, None/empty/overlong strings
"""

import sys
import tempfile
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.procedural_asset_synthesizer import ProceduralAssetSynthesizer
from core.media_engine.asset_content_validator import AssetContentValidator
from core.media_engine.alpha_qa_gate import AlphaQAGate


def _assert_image_validity(img: Image.Image, expected_w: int, expected_h: int, label: str):
    """Common assertions for generated procedural images."""
    assert img is not None, f"[{label}] Image is None"
    assert img.mode == "RGBA", f"[{label}] Mode must be 'RGBA', got {img.mode}"
    assert img.size == (expected_w, expected_h), f"[{label}] Size mismatch: expected {(expected_w, expected_h)}, got {img.size}"

    # Alpha ratios
    metrics = ProceduralAssetSynthesizer.get_alpha_metrics(img)
    tr = metrics["transparent_ratio"]
    op = metrics["opaque_ratio"]

    # AssetContentValidator check
    assert 0.08 <= tr <= 0.95, f"[{label}] AssetContentValidator failed: transparent_ratio={tr:.4f} not in [0.08, 0.95]"

    # AlphaQAGate check
    assert 0.08 <= op <= 0.85, f"[{label}] AlphaQAGate failed: opaque_ratio={op:.4f} not in [0.08, 0.85]"

    # External validator check
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        img.save(str(tmp_path), format="PNG")
        val_res = AssetContentValidator().validate_cutout(tmp_path)
        assert val_res.is_valid, f"[{label}] AssetContentValidator.validate_cutout failed: {val_res.reason}"

        qa_res = AlphaQAGate.verify(tmp_path)
        assert qa_res["passed"] is True, f"[{label}] AlphaQAGate.verify failed: {qa_res['message']}"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    print(f"  PASS: {label} (trans={tr:.1%}, opaque={op:.1%})")


def test_draw_scale():
    print("Testing draw_scale...")
    synth = ProceduralAssetSynthesizer()
    img_512 = synth.draw_scale(width=512, height=512)
    _assert_image_validity(img_512, 512, 512, "draw_scale(512, 512)")

    img_custom = synth.draw_scale(width=400, height=500)
    _assert_image_validity(img_custom, 400, 500, "draw_scale(400, 500)")


def test_draw_chemical_flask():
    print("Testing draw_chemical_flask...")
    synth = ProceduralAssetSynthesizer()
    # Oxygen
    img_oxy = synth.draw_chemical_flask(element_name="Oxygen", formula="O2", price="$120", width=512, height=512)
    _assert_image_validity(img_oxy, 512, 512, "draw_chemical_flask(Oxygen)")

    # Hydrogen
    img_hyd = synth.draw_chemical_flask(element_name="Hydrogen", formula="H2", price="$95", width=512, height=512)
    _assert_image_validity(img_hyd, 512, 512, "draw_chemical_flask(Hydrogen)")

    # Sulfur
    img_sul = synth.draw_chemical_flask(element_name="Sulfur", formula="S8", price="$45", width=512, height=512)
    _assert_image_validity(img_sul, 512, 512, "draw_chemical_flask(Sulfur)")


def test_draw_microscope():
    print("Testing draw_microscope...")
    synth = ProceduralAssetSynthesizer()
    img = synth.draw_microscope(width=512, height=512)
    _assert_image_validity(img, 512, 512, "draw_microscope(512, 512)")


def test_draw_crystal():
    print("Testing draw_crystal...")
    synth = ProceduralAssetSynthesizer()
    for name, color in [
        ("Diamond", "cyan"),
        ("Carbon", "carbon"),
        ("Emerald", "emerald"),
        ("Ruby", "ruby"),
        ("Sapphire", "sapphire"),
        ("Topaz", "gold")
    ]:
        img = synth.draw_crystal(name=name, color=color, width=512, height=512)
        _assert_image_validity(img, 512, 512, f"draw_crystal({name}, {color})")


def test_draw_book():
    print("Testing draw_book...")
    synth = ProceduralAssetSynthesizer()
    img_enc = synth.draw_book(title="ENCYCLOPEDIA", author="BRITANNICA", width=512, height=512)
    _assert_image_validity(img_enc, 512, 512, "draw_book(ENCYCLOPEDIA)")

    img_bry = synth.draw_book(title="SHORT HISTORY", author="BILL BRYSON", width=512, height=512)
    _assert_image_validity(img_bry, 512, 512, "draw_book(SHORT HISTORY)")


def test_draw_generic_symbol():
    print("Testing draw_generic_symbol...")
    synth = ProceduralAssetSynthesizer()
    archetypes = [
        "specimen_scientific",
        "oxford_library",
        "bank_teller",
        "historical_relic",
        "geography_ocean",
        "industrial_social",
        "luxury_treasure",
        "default"
    ]
    for arch in archetypes:
        img = synth.draw_generic_symbol(keyword=arch[:10], archetype=arch, width=512, height=512)
        _assert_image_validity(img, 512, 512, f"draw_generic_symbol({arch})")


def test_synthesize_dispatcher():
    print("Testing synthesize dispatcher...")
    synth = ProceduralAssetSynthesizer()
    test_queries = [
        ("golden_scale", 512, 512),
        ("vintage_balance", 512, 512),
        ("oxygen_chemical_flask", 512, 512),
        ("biology_microscope", 512, 512),
        ("carbon_crystal", 512, 512),
        ("antique_book", 512, 512),
        ("unknown_guild_insignia", 512, 512)
    ]
    for target, w, h in test_queries:
        img = synth.synthesize(target_object=target, width=w, height=h)
        _assert_image_validity(img, w, h, f"synthesize({target})")


def test_dimension_clamping():
    print("Testing dimension clamping...")
    synth = ProceduralAssetSynthesizer()
    # Below MIN_DIMENSION (60)
    img_tiny = synth.draw_scale(width=30, height=30)
    assert img_tiny.size == (60, 60), f"Expected (60, 60), got {img_tiny.size}"

    # String & float dimensions
    img_float = synth.draw_chemical_flask(width=512.6, height=512.2)
    assert img_float.size == (512, 512), f"Expected (512, 512), got {img_float.size}"

    # OverflowError handling: float('inf') and float('-inf') gracefully fall back to DEFAULT_SIZE
    img_inf = synth.draw_scale(width=float('inf'), height=512)
    assert img_inf.size == (512, 512), f"Expected (512, 512), got {img_inf.size}"
    _assert_image_validity(img_inf, 512, 512, "draw_scale(inf, 512)")

    img_neginf = synth.draw_scale(width=512, height=float('-inf'))
    assert img_neginf.size == (512, 512), f"Expected (512, 512), got {img_neginf.size}"

    img_nan = synth.draw_scale(width=float('nan'), height=512)
    assert img_nan.size == (512, 512), f"Expected (512, 512), got {img_nan.size}"

    # Aspect ratio protection (max(w, h) / min(w, h) <= 2.2)
    # 100x800 clamped to 100x220
    img_tall = synth.draw_scale(width=100, height=800)
    assert img_tall.size == (100, 220), f"Expected (100, 220), got {img_tall.size}"
    _assert_image_validity(img_tall, 100, 220, "draw_scale(100, 800) -> (100, 220)")

    # 800x200 clamped to 440x200
    img_wide = synth.draw_scale(width=800, height=200)
    assert img_wide.size == (440, 200), f"Expected (440, 200), got {img_wide.size}"
    _assert_image_validity(img_wide, 440, 200, "draw_scale(800, 200) -> (440, 200)")



def test_blank_and_overlong_strings():
    print("Testing blank and overlong strings...")
    synth = ProceduralAssetSynthesizer()
    # None and empty
    img_blank_flask = synth.draw_chemical_flask(element_name="", formula="", price="")
    _assert_image_validity(img_blank_flask, 512, 512, "draw_chemical_flask(empty strings)")

    img_blank_book = synth.draw_book(title="", author="")
    _assert_image_validity(img_blank_book, 512, 512, "draw_book(empty strings)")

    # Overlong strings
    long_title = "AN EXCEEDINGLY COMPREHENSIVE AND MONUMENTAL HISTORICAL TREATISE ON THE PHILOSOPHY OF NATURE"
    long_author = "PROFESSOR DOCTOR BARTHOLOMEW ALEXANDER MONTGOMERY ESQUIRE OF CAMBRIDGE"
    img_long_book = synth.draw_book(title=long_title, author=long_author)
    _assert_image_validity(img_long_book, 512, 512, "draw_book(long strings)")


def test_save_path_persistence():
    print("Testing save_path persistence...")
    synth = ProceduralAssetSynthesizer()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "nested" / "dir" / "test_scale.png"
        img = synth.draw_scale(width=512, height=512, save_path=out_path)
        assert out_path.exists(), "File was not saved to save_path"
        assert out_path.stat().st_size > 0, "Saved file is empty"
        with Image.open(out_path) as saved_img:
            assert saved_img.mode == "RGBA"
            assert saved_img.size == (512, 512)
    print("  PASS: save_path persistence")


def test_draw_book_ribbon_fishtail():
    print("Testing draw_book ribbon fishtail notch...")
    synth = ProceduralAssetSynthesizer()
    img = synth.draw_book(width=512, height=512)
    _assert_image_validity(img, 512, 512, "draw_book(512, 512) ribbon check")

    # Verify the inverted V-notch fishtail geometry
    # tip is at (352, 492), notch apex at (352, 482), bottom corners at (344, 492) and (360, 492)
    # The center notch cutout at (352, 490) must be transparent (alpha == 0)
    alpha_ch = img.getchannel("A")
    notch_center_alpha = alpha_ch.getpixel((352, 490))
    assert notch_center_alpha == 0, f"Expected transparent ribbon notch cutout at (352, 490), got alpha={notch_center_alpha}"

    # The ribbon tail points on either side should have ribbon opacity
    left_tail_alpha = alpha_ch.getpixel((346, 490))
    right_tail_alpha = alpha_ch.getpixel((358, 490))
    assert left_tail_alpha > 0, f"Expected left ribbon tail opacity at (346, 490), got alpha={left_tail_alpha}"
    assert right_tail_alpha > 0, f"Expected right ribbon tail opacity at (358, 490), got alpha={right_tail_alpha}"
    print(f"  PASS: ribbon fishtail notch verified (notch_center=0, left_tail={left_tail_alpha}, right_tail={right_tail_alpha})")


def run_all_tests():
    print("=" * 60)
    print("RUNNING ALL PROCEDURAL ASSET SYNTHESIZER TESTS")
    print("=" * 60)
    test_draw_scale()
    test_draw_chemical_flask()
    test_draw_microscope()
    test_draw_crystal()
    test_draw_book()
    test_draw_book_ribbon_fishtail()
    test_draw_generic_symbol()
    test_synthesize_dispatcher()
    test_dimension_clamping()
    test_blank_and_overlong_strings()
    test_save_path_persistence()
    print("=" * 60)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
