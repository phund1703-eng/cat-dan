"""
tests/test_beats_schema.py — Stage 6 Step 1: story beats schema.

Phạm vi:
- normalize_beats: giữ beats LLM đã sanitize; sinh heuristic beats khi thiếu.
- build_heuristic_beats: 2-4 beats, narration_part trích nguyên văn, ngữ pháp
  beat đúng chuẩn (focal enter -> secondary enter -> swap_pose -> exit).
- Không bịa asset: chỉ dùng keyword scene đã có; tôn trọng secondary "none".
- Tương thích ngược: normalize_scene vẫn giữ fact/sources.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.scene_schema import (
    BEAT_ACTIONS,
    BEAT_ROLES,
    build_heuristic_beats,
    normalize_beat,
    normalize_beats,
    normalize_scene,
    normalize_script_scenes,
)

pytestmark = pytest.mark.unit


def _scene(**kw):
    base = {
        "narration": "Khi vi khuẩn lẻn vào cơ thể, bạch cầu tuần tra lập tức phát hiện kẻ lạ mặt. Nó lao tới, vươn tay tóm gọn con mồi.",
        "focal_keyword": "white blood cell",
        "secondary_keyword": "bacterium",
        "core_meaning": "Bạch cầu tiêu diệt vi khuẩn",
    }
    base.update(kw)
    return base


def test_heuristic_beats_cover_narration_verbatim():
    scene = _scene()
    beats = build_heuristic_beats(scene)
    assert 2 <= len(beats) <= 4
    joined = " ".join(b["narration_part"] for b in beats)
    # Mọi từ của narration đều xuất hiện theo đúng thứ tự trong các parts.
    narration_words = scene["narration"].split()
    joined_words = joined.split()
    assert joined_words == narration_words


def test_heuristic_beats_grammar_order():
    scene = _scene()
    beats = build_heuristic_beats(scene)
    actions = [(b["elements"][0]["role"], b["elements"][0]["action"]) for b in beats if b["elements"]]
    assert actions[0] == ("focal", "enter")
    assert actions[1][0] == "secondary" and actions[1][1] == "enter"
    # Beat 3: focal đổi tư thế.
    assert ("focal", "swap_pose") in actions


def test_heuristic_beats_no_secondary_when_none():
    scene = _scene(secondary_keyword="none")
    beats = build_heuristic_beats(scene)
    kws = [e["keyword"] for b in beats for e in b["elements"]]
    assert "bacterium" not in kws
    assert "white blood cell" in kws


def test_heuristic_beats_empty_narration():
    assert build_heuristic_beats(_scene(narration="")) == []
    assert build_heuristic_beats(_scene(narration="   ")) == []


def test_normalize_beats_builds_when_missing():
    scene = _scene()
    normalize_beats(scene)
    assert isinstance(scene["beats"], list) and len(scene["beats"]) >= 2
    for b in scene["beats"]:
        assert set(b.keys()) == {"narration_part", "elements", "emphasis_words"}
        for e in b["elements"]:
            assert e["role"] in BEAT_ROLES
            assert e["action"] in BEAT_ACTIONS


def test_normalize_beats_keeps_llm_beats_sanitized():
    scene = _scene(beats=[
        {"narration_part": "Khi vi khuẩn lẻn vào cơ thể,",
         "elements": [
             {"role": "focal", "keyword": "white blood cell", "action": "enter", "from": "left"},
             {"role": "BOSS", "keyword": "virus", "action": "explode", "from": "up"},
         ],
         "emphasis_words": ["vi khuẩn", 123, ""]},
    ])
    normalize_beats(scene)
    beats = scene["beats"]
    assert len(beats) == 1
    assert beats[0]["narration_part"] == "Khi vi khuẩn lẻn vào cơ thể,"
    assert beats[0]["elements"][0]["action"] == "enter"
    # role/action lạ bị chuẩn hóa về giá trị hợp lệ.
    assert beats[0]["elements"][1]["role"] == "prop"
    assert beats[0]["elements"][1]["action"] == "enter"
    assert beats[0]["elements"][1]["from"] == "left"
    assert beats[0]["emphasis_words"] == ["vi khuẩn"]


def test_normalize_beats_truncates_and_drops_junk():
    scene = _scene(beats=[{"narration_part": f"beat {i}", "elements": []} for i in range(20)]
                  + ["junk", None, {}])
    normalize_beats(scene)
    assert len(scene["beats"]) <= 6


def test_normalize_scene_keeps_fact_sources_and_adds_beats():
    scene = _scene()
    del scene["core_meaning"]
    normalize_scene(scene)
    assert scene["fact"] == ""  # fallback core_meaning rỗng, không bịa
    assert scene["sources"] == []
    assert len(scene["beats"]) >= 2


def test_normalize_script_scenes_applies_to_all():
    script = {"scenes": [_scene(), {"narration": "Một câu ngắn.", "focal_keyword": "sun"}]}
    normalize_script_scenes(script)
    assert all("beats" in s for s in script["scenes"])
    assert all("fact" in s and "sources" in s for s in script["scenes"])
