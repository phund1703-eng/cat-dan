"""
tests/test_fallback_no_hardcoded_stats.py — Task 2.3.

Fallback script (khi không có Gemini key) không được chứa số liệu khoa học
hardcode không nguồn; chỉ dùng câu định tính. Quét bằng chính bộ phát hiện
số liệu của Source Gate trên narration + fact của mọi nhánh domain, 2 ngôn ngữ.
"""

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.script_generator import ScriptGenerator
from core.script_engine.source_gate import contains_numeric_claim

TOPICS = [
    ("3 sự thật bất ngờ từ tế bào của con người", "vi"),
    ("Khám phá bí ẩn hố đen vũ trụ", "vi"),
    ("Cách mạng trí tuệ nhân tạo và chip bán dẫn", "vi"),
    ("Bí mật kim tự tháp ai cập cổ đại", "vi"),
    ("Sự thật thú vị về đại dương sâu thẳm", "vi"),
    ("Nghệ thuật đàm phán hợp đồng thương mại", "vi"),
    ("Human cellular biology secrets", "en"),
    ("Mysteries of cosmic black holes", "en"),
    ("Artificial intelligence and semiconductor chips", "en"),
    ("Ancient Egyptian pyramids", "en"),
    ("Deep ocean marine life", "en"),
    ("Strategic leadership psychology", "en"),
]

# Các cụm số liệu bịa từng hardcode trong fallback (phải biến mất)
BANNED_SNIPPETS = [
    "hai triệu", "two million", "sao diêm vương", "pluto",
    "hai mươi lăm phần trăm", "more than a quarter",
    "hàng tỷ", "billions of",
]


@pytest.fixture(scope="module")
def gen():
    return ScriptGenerator()


@pytest.mark.parametrize("topic,language", TOPICS)
def test_fallback_scenes_have_no_numeric_claims(gen, topic, language):
    script = gen._generate_fallback_script(topic, "collage_broll", language, 30)
    assert script["script_origin"] == "fallback"
    assert len(script["scenes"]) >= 3
    for scene in script["scenes"]:
        claim_text = f"{scene['narration']} {scene.get('fact', '')}"
        assert not contains_numeric_claim(claim_text), (
            f"Fallback scene still contains a numeric claim: {claim_text!r}"
        )
        assert not re.search(r"\d", scene["narration"]), scene["narration"]
        assert scene["sources"] == []


@pytest.mark.parametrize("topic,language", TOPICS)
def test_fallback_banned_snippets_removed(gen, topic, language):
    script = gen._generate_fallback_script(topic, "collage_broll", language, 30)
    all_narration = " ".join(s["narration"] for s in script["scenes"]).lower()
    for snippet in BANNED_SNIPPETS:
        assert snippet not in all_narration, f"Banned hardcoded stat remains: {snippet}"


def test_fallback_biology_still_mentions_cells_and_dna(gen):
    script = gen._generate_fallback_script("3 sự thật bất ngờ từ tế bào của con người", "collage_broll", "vi", 30)
    narrations = " ".join(s["narration"] for s in script["scenes"]).lower()
    assert "tế bào" in narrations
    assert "dna" in narrations
    assert script["topic_domain"] == "biology"
