"""
tests/test_verb_beat_enrich.py — Stage 6: từ điển động từ -> beats.

Phạm vi:
- enrich_beats_with_verbs: tự chèn beat_action còn thiếu từ narration_part.
- pulse/divide/emphasize gắn vào focal; absorb gắn vào secondary.
- Idempotent; động từ quan hệ (attack/approach/block/flow) không tự chèn;
  động từ cơ khí cũ (không có beat_action) bị bỏ qua.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.scene_schema import normalize_scene, enrich_beats_with_verbs
from core.script_engine.verb_semantic_matcher import suggest_beat_action

pytestmark = pytest.mark.unit


def test_suggest_beat_action_physiology():
    s = suggest_beat_action("Trái tim đập thình thịch không ngừng.")
    assert s and s["beat_action"] == "pulse"
    assert s["verb_vi"] == "tim đập"


def test_suggest_beat_action_ignores_mechanical():
    assert suggest_beat_action("Cỗ máy ép mạnh xuống.") is None
    assert suggest_beat_action("Hôm nay trời đẹp.") is None


def test_enrich_adds_pulse_to_focal():
    scene = {"narration": "Trái tim đập thình thịch.",
             "focal_keyword": "heart",
             "beats": [{"narration_part": "Trái tim đập thình thịch.",
                        "elements": [{"role": "focal", "keyword": "heart",
                                      "action": "enter", "from": "left",
                                      "to": "right", "pose": "", "target": "",
                                      "rate": ""}],
                        "emphasis_words": []}]}
    normalize_scene(scene)
    actions = [e["action"] for e in scene["beats"][0]["elements"]]
    assert "enter" in actions and "pulse" in actions
    pulse_el = next(e for e in scene["beats"][0]["elements"] if e["action"] == "pulse")
    assert pulse_el["keyword"] == "heart"


def test_enrich_absorb_attaches_to_secondary():
    scene = {"narration": "Bạch cầu thực bào vi khuẩn.",
             "focal_keyword": "white blood cell",
             "secondary_keyword": "bacterium",
             "beats": [{"narration_part": "Bạch cầu thực bào vi khuẩn.",
                        "elements": [
                            {"role": "focal", "keyword": "white blood cell",
                             "action": "enter", "from": "left", "to": "right",
                             "pose": "", "target": "", "rate": ""},
                            {"role": "secondary", "keyword": "bacterium",
                             "action": "enter", "from": "right", "to": "left",
                             "pose": "", "target": "", "rate": ""}],
                        "emphasis_words": []}]}
    normalize_scene(scene)
    absorb_els = [e for e in scene["beats"][0]["elements"] if e["action"] == "absorb"]
    assert len(absorb_els) == 1
    assert absorb_els[0]["keyword"] == "bacterium"


def test_enrich_is_idempotent():
    scene = {"narration": "Tim đập.",
             "focal_keyword": "heart",
             "beats": [{"narration_part": "Tim đập.",
                        "elements": [{"role": "focal", "keyword": "heart",
                                      "action": "enter", "from": "left",
                                      "to": "right", "pose": "", "target": "",
                                      "rate": ""}],
                        "emphasis_words": []}]}
    normalize_scene(scene)
    n1 = len(scene["beats"][0]["elements"])
    enrich_beats_with_verbs(scene)
    assert len(scene["beats"][0]["elements"]) == n1


def test_enrich_skips_relational_verbs():
    scene = {"narration": "Bạch cầu tấn công vi khuẩn.",
             "focal_keyword": "white blood cell",
             "secondary_keyword": "bacterium",
             "beats": [{"narration_part": "Bạch cầu tấn công vi khuẩn.",
                        "elements": [{"role": "focal", "keyword": "white blood cell",
                                      "action": "enter", "from": "left",
                                      "to": "right", "pose": "", "target": "",
                                      "rate": ""}],
                        "emphasis_words": []}]}
    normalize_scene(scene)
    actions = [e["action"] for e in scene["beats"][0]["elements"]]
    assert "attack" not in actions  # để LLM quyết định chủ/khách


def test_enrich_heuristic_beats_end_to_end():
    # Không có beats từ LLM: heuristic + enrich phải sinh pulse cho tim.
    scene = {"narration": "Trái tim đập thình thịch để bơm máu đi khắp cơ thể.",
             "focal_keyword": "heart", "secondary_keyword": "blood"}
    normalize_scene(scene)
    all_actions = [e["action"] for b in scene["beats"] for e in b["elements"]]
    assert "pulse" in all_actions
