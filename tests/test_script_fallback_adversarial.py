"""
tests/test_script_fallback_adversarial.py

Adversarial Stress Test Suite for core/script_engine/script_generator.py:
1. Topic 1: Biology / Cells ("3 sự thật bất ngờ từ tế bào của con người")
2. Topic 2: Space / Black Holes ("Khám phá bí ẩn hố đen vũ trụ")
3. Topic 3: Technology / AI & Chips ("Cách mạng trí tuệ nhân tạo và chip bán dẫn")
4. Topic 4: History / Pyramids ("Bí mật kim tự tháp ai cập cổ đại")
5. Topic 5: Nature / Ocean ("10 sự thật thú vị về đại dương sâu thẳm")
6. Topic 6: Arbitrary Generic Topic (Dynamic fallback synthesizer)
7. Repo-wide check: Zero occurrences of chessboard/puppet across outputs and in core/script_engine/
8. Edge cases & Stress testing: Empty topics, English language switch, duration scaling, schema completeness.
"""

import sys
import re
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.script_generator import ScriptGenerator


FORBIDDEN_TERMS = ["chessboard", "puppet", "bàn cờ", "con rối"]

REQUIRED_ROOT_KEYS = [
    "title", "description", "topic_domain", "hashtags", "scenes", "estimated_duration"
]

REQUIRED_SCENE_KEYS = [
    "narration", "core_meaning", "visual_metaphor", "topic_domain",
    "focal_keyword", "secondary_keyword", "layout_type", "has_hand",
    "has_camera", "color_field", "color_hex", "assembly_order",
    "still_image_prompt", "visual_description", "duration"
]


def _assert_no_forbidden_terms(data: Any, context: str = ""):
    """Recursively asserts no forbidden terms exist in string representations."""
    if isinstance(data, str):
        data_lower = data.lower()
        for term in FORBIDDEN_TERMS:
            assert term not in data_lower, f"Forbidden term '{term}' found in {context}: {data}"
    elif isinstance(data, dict):
        for k, v in data.items():
            _assert_no_forbidden_terms(k, f"{context}.key({k})")
            _assert_no_forbidden_terms(v, f"{context}[{k}]")
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            _assert_no_forbidden_terms(item, f"{context}[{idx}]")


def _assert_schema_completeness(script: Dict[str, Any]):
    """Asserts that the script and all its scenes satisfy the full schema contract."""
    for key in REQUIRED_ROOT_KEYS:
        assert key in script, f"Missing root key: '{key}'"
    assert isinstance(script["scenes"], list)
    assert len(script["scenes"]) >= 3, f"Expected at least 3 scenes, got {len(script['scenes'])}"
    for idx, scene in enumerate(script["scenes"]):
        for key in REQUIRED_SCENE_KEYS:
            assert key in scene, f"Scene {idx} missing key: '{key}'"
        assert scene["duration"] >= 4.0, f"Scene {idx} duration {scene['duration']} < 4.0s minimum"
        assert scene["topic_domain"] == script["topic_domain"], "Scene domain must match script domain"
    assert script["estimated_duration"] == sum(s["duration"] for s in script["scenes"])


def test_topic_1_biology_cells():
    """Topic 1: '3 sự thật bất ngờ từ tế bào của con người' -> domain biology, cell/dna keywords, no chessboard."""
    gen = ScriptGenerator()
    script = gen._generate_fallback_script(
        topic="3 sự thật bất ngờ từ tế bào của con người",
        style="collage_broll",
        language="vi",
        duration=30
    )

    _assert_schema_completeness(script)
    _assert_no_forbidden_terms(script, "test_topic_1_biology_cells")

    assert script["topic_domain"] == "biology", f"Expected 'biology', got '{script['topic_domain']}'"
    assert "tế bào" in script["title"].lower()

    focal_keywords = [s["focal_keyword"].lower() for s in script["scenes"]]
    secondary_keywords = [s["secondary_keyword"].lower() for s in script["scenes"]]
    all_keywords = focal_keywords + secondary_keywords

    assert any("cell" in kw or "tế bào" in kw for kw in all_keywords), f"Missing cell keyword in {all_keywords}"
    assert any("dna" in kw for kw in all_keywords), f"Missing dna keyword in {all_keywords}"

    narrations_text = " ".join(s["narration"] for s in script["scenes"]).lower()
    assert "tế bào" in narrations_text
    assert "dna" in narrations_text
    print("PASS: test_topic_1_biology_cells")


def test_topic_2_space_blackhole():
    """Topic 2: 'Khám phá bí ẩn hố đen vũ trụ' -> domain space."""
    gen = ScriptGenerator()
    script = gen._generate_fallback_script(
        topic="Khám phá bí ẩn hố đen vũ trụ",
        style="collage_broll",
        language="vi",
        duration=30
    )

    _assert_schema_completeness(script)
    _assert_no_forbidden_terms(script, "test_topic_2_space_blackhole")

    assert script["topic_domain"] == "space", f"Expected 'space', got '{script['topic_domain']}'"
    assert "vũ trụ" in script["title"].lower()

    focal_keywords = [s["focal_keyword"].lower() for s in script["scenes"]]
    assert "galaxy" in focal_keywords
    assert "planet" in focal_keywords
    assert "astronaut" in focal_keywords
    print("PASS: test_topic_2_space_blackhole")


def test_topic_3_tech_ai_chips():
    """Topic 3: 'Cách mạng trí tuệ nhân tạo và chip bán dẫn' -> domain technology."""
    gen = ScriptGenerator()
    script = gen._generate_fallback_script(
        topic="Cách mạng trí tuệ nhân tạo và chip bán dẫn",
        style="collage_broll",
        language="vi",
        duration=30
    )

    _assert_schema_completeness(script)
    _assert_no_forbidden_terms(script, "test_topic_3_tech_ai_chips")

    assert script["topic_domain"] == "technology", f"Expected 'technology', got '{script['topic_domain']}'"
    assert "công nghệ" in script["title"].lower()

    focal_keywords = [s["focal_keyword"].lower() for s in script["scenes"]]
    assert "microchip" in focal_keywords
    assert "neural network" in focal_keywords
    assert "digital portal" in focal_keywords
    print("PASS: test_topic_3_tech_ai_chips")


def test_topic_4_history_pyramids():
    """Topic 4: 'Bí mật kim tự tháp ai cập cổ đại' -> domain history."""
    gen = ScriptGenerator()
    script = gen._generate_fallback_script(
        topic="Bí mật kim tự tháp ai cập cổ đại",
        style="collage_broll",
        language="vi",
        duration=30
    )

    _assert_schema_completeness(script)
    _assert_no_forbidden_terms(script, "test_topic_4_history_pyramids")

    assert script["topic_domain"] == "history", f"Expected 'history', got '{script['topic_domain']}'"
    assert "lịch sử" in script["title"].lower()

    focal_keywords = [s["focal_keyword"].lower() for s in script["scenes"]]
    assert "papyrus scroll" in focal_keywords
    assert "pyramid" in focal_keywords
    assert "marble column" in focal_keywords
    print("PASS: test_topic_4_history_pyramids")


def test_topic_5_nature_ocean():
    """Topic 5: '10 sự thật thú vị về đại dương sâu thẳm' -> domain geography (nature/ocean)."""
    gen = ScriptGenerator()
    script = gen._generate_fallback_script(
        topic="10 sự thật thú vị về đại dương sâu thẳm",
        style="collage_broll",
        language="vi",
        duration=30
    )

    _assert_schema_completeness(script)
    _assert_no_forbidden_terms(script, "test_topic_5_nature_ocean")

    assert script["topic_domain"] in ("geography", "nature", "ocean"), f"Expected geography/nature/ocean, got '{script['topic_domain']}'"
    assert "thiên nhiên" in script["title"].lower() or "đại dương" in script["title"].lower()

    focal_keywords = [s["focal_keyword"].lower() for s in script["scenes"]]
    assert "submarine" in focal_keywords
    assert "coral reef" in focal_keywords
    assert "mountain peak" in focal_keywords

    narrations_text = " ".join(s["narration"] for s in script["scenes"]).lower()
    assert "đại dương" in narrations_text or "san hô" in narrations_text
    print("PASS: test_topic_5_nature_ocean")


def test_topic_6_arbitrary_generic():
    """Topic 6: Arbitrary generic topic -> dynamic generic synthesizer works without chessboard."""
    generic_topic = "Nghệ thuật đàm phán hợp đồng thương mại quốc tế 2026"
    gen = ScriptGenerator()
    script = gen._generate_fallback_script(
        topic=generic_topic,
        style="collage_broll",
        language="vi",
        duration=30
    )

    _assert_schema_completeness(script)
    _assert_no_forbidden_terms(script, "test_topic_6_arbitrary_generic")

    assert script["topic_domain"] == "science"
    assert generic_topic in script["title"]
    assert generic_topic in script["description"]

    # Assert dynamic injection of generic topic in all scene narrations
    for scene in script["scenes"]:
        assert generic_topic in scene["narration"]

    # Verify focal keywords are tangible collage objects, NOT chessboard/puppet
    focal_keywords = [s["focal_keyword"].lower() for s in script["scenes"]]
    assert "leather notebook" in focal_keywords
    assert "hourglass" in focal_keywords
    assert "light bulb" in focal_keywords
    print("PASS: test_topic_6_arbitrary_generic")


def test_zero_chessboard_puppet_in_core_script_engine():
    """Asserts 0 occurrences of 'chessboard' or 'puppet' across all python code in core/script_engine/."""
    engine_dir = PROJECT_ROOT / "core" / "script_engine"
    py_files = list(engine_dir.glob("*.py"))
    assert len(py_files) > 0, "No python files found in core/script_engine"

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        # Check forbidden keywords in executable code (excluding docstrings/comments)
        for line_num, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            # If line is not a comment/docstring line
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            line_lower = stripped.lower()
            for term in FORBIDDEN_TERMS:
                assert term not in line_lower, (
                    f"Forbidden term '{term}' found in {py_file.name}:{line_num}: {line}"
                )
    print("PASS: test_zero_chessboard_puppet_in_core_script_engine")


def test_stress_edge_cases():
    """Adversarial stress testing of edge cases, inputs, and boundaries."""
    gen = ScriptGenerator()

    # Edge Case 1: Empty and whitespace topic
    script_empty = gen._generate_fallback_script("", "collage_broll", "vi", 30)
    _assert_schema_completeness(script_empty)
    _assert_no_forbidden_terms(script_empty, "script_empty")

    script_ws = gen._generate_fallback_script("    ", "collage_broll", "vi", 30)
    _assert_schema_completeness(script_ws)
    _assert_no_forbidden_terms(script_ws, "script_ws")

    # Edge Case 2: Uppercase topic
    script_upper = gen._generate_fallback_script(
        "3 SỰ THẬT BẤT NGỜ TỪ TẾ BÀO CON NGƯỜI",
        "collage_broll",
        "vi",
        30
    )
    _assert_schema_completeness(script_upper)
    assert script_upper["topic_domain"] == "biology"
    _assert_no_forbidden_terms(script_upper, "script_upper")

    # Edge Case 3: English language switch across all domains
    test_cases_en = [
        ("Human cellular biology secrets", "biology"),
        ("Mysteries of cosmic black holes", "space"),
        ("Artificial intelligence and semiconductor chips", "technology"),
        ("Ancient Egyptian pyramids", "history"),
        ("Deep ocean marine life", "geography"),
        ("Strategic leadership psychology", "science"),
    ]
    for topic_en, expected_domain in test_cases_en:
        script_en = gen._generate_fallback_script(topic_en, "collage_broll", "en", 45)
        _assert_schema_completeness(script_en)
        _assert_no_forbidden_terms(script_en, f"script_en_{topic_en}")
        assert script_en["topic_domain"] == expected_domain, (
            f"Expected {expected_domain} for '{topic_en}', got '{script_en['topic_domain']}'"
        )
        assert all(s["duration"] == 15.0 for s in script_en["scenes"])

    # Edge Case 4: Extreme durations
    script_dur_0 = gen._generate_fallback_script("Test", "collage_broll", "vi", 0)
    assert all(s["duration"] >= 4.0 for s in script_dur_0["scenes"])

    script_dur_neg = gen._generate_fallback_script("Test", "collage_broll", "vi", -100)
    assert all(s["duration"] >= 4.0 for s in script_dur_neg["scenes"])

    script_dur_huge = gen._generate_fallback_script("Test", "collage_broll", "vi", 300)
    assert all(s["duration"] == 100.0 for s in script_dur_huge["scenes"])

    print("PASS: test_stress_edge_cases")


if __name__ == "__main__":
    test_topic_1_biology_cells()
    test_topic_2_space_blackhole()
    test_topic_3_tech_ai_chips()
    test_topic_4_history_pyramids()
    test_topic_5_nature_ocean()
    test_topic_6_arbitrary_generic()
    test_zero_chessboard_puppet_in_core_script_engine()
    test_stress_edge_cases()
    print("\nALL 8 ADVERSARIAL STRESS TESTS PASSED EMPIRICALLY!")
