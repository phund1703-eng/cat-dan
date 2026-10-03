"""
Automated Empirical Adversarial Stress Test Suite for ProceduralAssetSynthesizer
test_challenge_stress_m1.py

Adversarially stress-tests:
1. Extreme dimensions (boundary 60x60, 4096x4096, rectangular 100x800, 800x200, float, nan, inf).
2. Malformed / extreme text inputs (empty strings, None, Unicode/CJK/emoji, 500+ chars, null bytes, special symbols).
3. Unknown colors and archetypes (unrecognized color names in draw_crystal, novel archetypes in draw_generic_symbol).
4. Dual-gate alpha compliance:
   - AssetContentValidator: 0.08 <= transparent_ratio <= 0.95
   - AlphaQAGate: 0.08 <= opaque_ratio <= 0.85
"""

import sys
import math
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.procedural_asset_synthesizer import ProceduralAssetSynthesizer
from core.media_engine.asset_content_validator import AssetContentValidator
from core.media_engine.alpha_qa_gate import AlphaQAGate


class StressTestResult:
    def __init__(self, name: str, passed: bool, details: Dict[str, Any], error: str = ""):
        self.name = name
        self.passed = passed
        self.details = details
        self.error = error

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.details} {self.error}"


class EmpiricalStressTester:
    def __init__(self):
        self.synth = ProceduralAssetSynthesizer()
        self.validator = AssetContentValidator()
        self.results: List[StressTestResult] = []

    def evaluate_image(self, img: Image.Image, test_name: str, expected_size: Tuple[int, int] = None) -> StressTestResult:
        """Thoroughly checks PIL Image against all contractual constraints."""
        details = {}
        if img is None:
            return StressTestResult(test_name, False, {}, "Returned None image")

        if img.mode != "RGBA":
            return StressTestResult(test_name, False, {"mode": img.mode}, f"Invalid mode: {img.mode} != RGBA")

        w, h = img.size
        details["size"] = (w, h)
        if expected_size and (w, h) != expected_size:
            return StressTestResult(test_name, False, details, f"Size mismatch: expected {expected_size}, got {(w, h)}")

        # Calculate exact alpha ratios
        alpha_arr = np.array(img.getchannel("A"))
        total = alpha_arr.size
        if total == 0:
            return StressTestResult(test_name, False, details, "Image has 0 total pixels")

        trans_pixels = np.sum(alpha_arr < 128)
        opaque_pixels = np.sum(alpha_arr > 20)
        tr = float(trans_pixels) / float(total)
        op = float(opaque_pixels) / float(total)
        details["transparent_ratio"] = round(tr, 4)
        details["opaque_ratio"] = round(op, 4)

        # AssetContentValidator criteria: 0.08 <= tr <= 0.95
        acv_passed = (0.08 <= tr <= 0.95)
        details["acv_bounds_passed"] = acv_passed

        # AlphaQAGate criteria: 0.08 <= op <= 0.85
        alpha_qa_passed = (0.08 <= op <= 0.85)
        details["alpha_qa_bounds_passed"] = alpha_qa_passed

        # File validation with AssetContentValidator
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            img.save(str(tmp_path), format="PNG")
            val_res = self.validator.validate_cutout(tmp_path)
            details["validator_is_valid"] = val_res.is_valid
            details["validator_reason"] = val_res.reason
            qa_res = AlphaQAGate.verify(tmp_path)
            details["alpha_gate_passed"] = qa_res["passed"]
            details["alpha_gate_status"] = qa_res["status"]
        except Exception as e:
            return StressTestResult(test_name, False, details, f"Exception during validation: {e}")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        overall_passed = acv_passed and alpha_qa_passed and details["validator_is_valid"] and details["alpha_gate_passed"]
        error_msg = ""
        if not overall_passed:
            reasons = []
            if not acv_passed:
                reasons.append(f"transparent_ratio={tr:.1%} outside [8%, 95%]")
            if not alpha_qa_passed:
                reasons.append(f"opaque_ratio={op:.1%} outside [8%, 85%]")
            if not details["validator_is_valid"]:
                reasons.append(f"Validator rejected: {details['validator_reason']}")
            if not details["alpha_gate_passed"]:
                reasons.append(f"AlphaQAGate rejected: {details['alpha_gate_status']}")
            error_msg = "; ".join(reasons)

        return StressTestResult(test_name, overall_passed, details, error_msg)

    def test_dimensions(self):
        print("\n--- Running Test Category 1: Extreme Dimensions ---")
        dim_cases = [
            ("min_boundary_60x60_scale", lambda: self.synth.draw_scale(60, 60), (60, 60)),
            ("min_boundary_60x60_flask", lambda: self.synth.draw_chemical_flask(width=60, height=60), (60, 60)),
            ("min_boundary_60x60_microscope", lambda: self.synth.draw_microscope(60, 60), (60, 60)),
            ("min_boundary_60x60_crystal", lambda: self.synth.draw_crystal(width=60, height=60), (60, 60)),
            ("min_boundary_60x60_book", lambda: self.synth.draw_book(width=60, height=60), (60, 60)),
            ("min_boundary_60x60_generic", lambda: self.synth.draw_generic_symbol(width=60, height=60), (60, 60)),

            ("max_boundary_4096x4096_scale", lambda: self.synth.draw_scale(4096, 4096), (4096, 4096)),
            ("max_boundary_4096x4096_flask", lambda: self.synth.draw_chemical_flask(width=4096, height=4096), (4096, 4096)),
            ("max_boundary_4096x4096_microscope", lambda: self.synth.draw_microscope(4096, 4096), (4096, 4096)),
            ("max_boundary_4096x4096_crystal", lambda: self.synth.draw_crystal(width=4096, height=4096), (4096, 4096)),
            ("max_boundary_4096x4096_book", lambda: self.synth.draw_book(width=4096, height=4096), (4096, 4096)),
            ("max_boundary_4096x4096_generic", lambda: self.synth.draw_generic_symbol(width=4096, height=4096), (4096, 4096)),

            ("sub_minimum_clamped_30x30", lambda: self.synth.draw_scale(30, 30), (60, 60)),
            ("super_maximum_clamped_5000x5000", lambda: self.synth.draw_scale(5000, 5000), (4096, 4096)),

            ("float_dimensions_scale", lambda: self.synth.draw_scale(512.7, 512.3), (512, 512)),
            ("float_dimensions_boundary", lambda: self.synth.draw_chemical_flask(width=60.9, height=60.1), (60, 60)),

            # Rectangular Dimensions (Stress-testing aspect ratios clamped to <= 2.2)
            ("rectangular_100x800_scale", lambda: self.synth.draw_scale(100, 800), (100, 220)),
            ("rectangular_100x800_flask", lambda: self.synth.draw_chemical_flask(width=100, height=800), (100, 220)),
            ("rectangular_100x800_microscope", lambda: self.synth.draw_microscope(100, 800), (100, 220)),
            ("rectangular_100x800_crystal", lambda: self.synth.draw_crystal(width=100, height=800), (100, 220)),
            ("rectangular_100x800_book", lambda: self.synth.draw_book(width=100, height=800), (100, 220)),
            ("rectangular_100x800_generic", lambda: self.synth.draw_generic_symbol(width=100, height=800), (100, 220)),

            ("rectangular_800x200_scale", lambda: self.synth.draw_scale(800, 200), (440, 200)),
            ("rectangular_800x200_flask", lambda: self.synth.draw_chemical_flask(width=800, height=200), (440, 200)),
            ("rectangular_800x200_microscope", lambda: self.synth.draw_microscope(800, 200), (440, 200)),
            ("rectangular_800x200_crystal", lambda: self.synth.draw_crystal(width=800, height=200), (440, 200)),
            ("rectangular_800x200_book", lambda: self.synth.draw_book(width=800, height=200), (440, 200)),
            ("rectangular_800x200_generic", lambda: self.synth.draw_generic_symbol(width=800, height=200), (440, 200)),

            # Special float values: NaN and Inf
            ("nan_dimension_handling", lambda: self.synth.draw_scale(float('nan'), 512), (512, 512)),
            ("inf_dimension_handling", lambda: self.synth.draw_scale(float('inf'), 512), (512, 512)),
        ]

        for label, fn, expected_sz in dim_cases:
            try:
                img = fn()
                res = self.evaluate_image(img, label, expected_sz)
            except Exception as e:
                res = StressTestResult(label, False, {}, f"Crashed with exception: {type(e).__name__}: {e}")
            self.results.append(res)
            print(res)

    def test_malformed_text_inputs(self):
        print("\n--- Running Test Category 2: Malformed / Extreme Text Inputs ---")
        text_cases = [
            ("empty_flask", lambda: self.synth.draw_chemical_flask(element_name="", formula="", price="")),
            ("none_flask", lambda: self.synth.draw_chemical_flask(element_name=None, formula=None, price=None)),
            ("empty_book", lambda: self.synth.draw_book(title="", author="")),
            ("none_book", lambda: self.synth.draw_book(title=None, author=None)),
            ("empty_generic", lambda: self.synth.draw_generic_symbol(keyword="", archetype="")),
            ("none_generic", lambda: self.synth.draw_generic_symbol(keyword=None, archetype=None)),
            ("empty_crystal", lambda: self.synth.draw_crystal(name="", color="")),
            ("none_crystal", lambda: self.synth.draw_crystal(name=None, color=None)),

            ("long_500_chars_flask", lambda: self.synth.draw_chemical_flask(
                element_name="A" * 550, formula="F" * 520, price="$" + "9" * 500
            )),
            ("long_500_chars_book", lambda: self.synth.draw_book(
                title="HISTORIA_NATURALIS_" * 40, author="ARISTOTELES_PLINIUS_" * 30
            )),
            ("long_500_chars_generic", lambda: self.synth.draw_generic_symbol(
                keyword="EMBLEM_" * 80, archetype="specimen_scientific"
            )),
            ("long_500_chars_crystal", lambda: self.synth.draw_crystal(
                name="OCTAHEDRON_CARBON_" * 40, color="cyan"
            )),

            ("unicode_vietnamese_flask", lambda: self.synth.draw_chemical_flask(
                element_name="Dung Dịch Axit Sunfuric Đậm Đặc", formula="H2SO4 (98%)", price="150.000₫"
            )),
            ("unicode_cjk_book", lambda: self.synth.draw_book(
                title="帝国大百科全书 第一卷", author="大英帝国皇家科学院"
            )),
            ("unicode_arabic_generic", lambda: self.synth.draw_generic_symbol(
                keyword="الأكاديمية الملكية", archetype="oxford_library"
            )),
            ("unicode_emojis_generic", lambda: self.synth.draw_generic_symbol(
                keyword="✨⚗️🔬💎📖⚖️✨", archetype="default"
            )),

            ("special_symbols_flask", lambda: self.synth.draw_chemical_flask(
                element_name="<script>alert('XSS')</script>", formula="O2 & S8 -> SO2", price="$100 & 50¢"
            )),
            ("newlines_tabs_book", lambda: self.synth.draw_book(
                title="Line1\nLine2\tLine3\rLine4", author="Dr.\nAuthor"
            )),
            ("null_byte_flask", lambda: self.synth.draw_chemical_flask(
                element_name="Oxygen\x00Explosion", formula="O2\x00", price="$100\x00"
            )),
            ("null_byte_book", lambda: self.synth.draw_book(
                title="Encyclopedia\x00Secret", author="Britannica\x00Ghost"
            )),
            ("quotes_slashes_generic", lambda: self.synth.draw_generic_symbol(
                keyword="\"''\\\\//--==++", archetype="historical_relic"
            )),
        ]

        for label, fn in text_cases:
            try:
                img = fn()
                res = self.evaluate_image(img, label, (512, 512))
            except Exception as e:
                res = StressTestResult(label, False, {}, f"Crashed with exception: {type(e).__name__}: {e}")
            self.results.append(res)
            print(res)

    def test_unknown_colors_and_archetypes(self):
        print("\n--- Running Test Category 3: Unknown Colors & Archetypes ---")
        unknown_cases = [
            ("crystal_unknown_color_neon_magenta", lambda: self.synth.draw_crystal(name="Alien Gem", color="neon_magenta")),
            ("crystal_unknown_color_holographic", lambda: self.synth.draw_crystal(name="Bismuth", color="holographic_rainbow")),
            ("crystal_unknown_color_numeric", lambda: self.synth.draw_crystal(name="Test", color="123456")),
            ("crystal_unknown_color_empty", lambda: self.synth.draw_crystal(name="Clear", color="")),

            ("generic_unknown_arch_cyberpunk", lambda: self.synth.draw_generic_symbol(keyword="cyber", archetype="cyberpunk_neon")),
            ("generic_unknown_arch_steampunk", lambda: self.synth.draw_generic_symbol(keyword="steam", archetype="steampunk_clockwork")),
            ("generic_unknown_arch_empty", lambda: self.synth.draw_generic_symbol(keyword="test", archetype="")),
            ("generic_unknown_arch_gibberish", lambda: self.synth.draw_generic_symbol(keyword="test", archetype="xyz_9999_gibberish")),

            ("synthesize_unknown_alien_object", lambda: self.synth.synthesize("alien_quantum_device", archetype="sci_fi")),
            ("synthesize_empty_string", lambda: self.synth.synthesize("")),
            ("synthesize_none", lambda: self.synth.synthesize(None)),
            ("synthesize_numeric", lambda: self.synth.synthesize(12345)),
        ]

        for label, fn in unknown_cases:
            try:
                img = fn()
                res = self.evaluate_image(img, label, (512, 512))
            except Exception as e:
                res = StressTestResult(label, False, {}, f"Crashed with exception: {type(e).__name__}: {e}")
            self.results.append(res)
            print(res)

    def generate_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        failures = [r for r in self.results if not r.passed]

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
            "failures": failures
        }


def run_stress_suite():
    tester = EmpiricalStressTester()
    tester.test_dimensions()
    tester.test_malformed_text_inputs()
    tester.test_unknown_colors_and_archetypes()
    summary = tester.generate_summary()
    print("\n" + "=" * 60)
    print(f"STRESS TEST SUMMARY: {summary['passed']}/{summary['total']} PASSED ({summary['pass_rate']}%)")
    print(f"FAILURES COUNT: {summary['failed']}")
    for f in summary["failures"]:
        print(f"  FAILED: {f.name} -> {f.error}")
    print("=" * 60)
    return summary


if __name__ == "__main__":
    run_stress_suite()
