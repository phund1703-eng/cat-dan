"""
tests/test_beat_choreographer.py — Stage 6 Step 2: BeatChoreographer.

Phạm vi:
- choreograph(scene, audio_duration) -> timeline/cast/beat_timing/labels.
- Ánh xạ beat -> action đúng vocabulary engine hiện tại.
- Nhịp beat neo theo số từ trên thời lượng audio thật.
- Tương thích MotionTimelineEngine.get_frame_state (không crash, visible đúng).
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.beat_choreographer import (
    HEAD_RESERVE,
    TAIL_RESERVE,
    BeatChoreographer,
)
from core.media_engine.motion_timeline_engine import MotionTimelineEngine

pytestmark = pytest.mark.unit

CHOREO = BeatChoreographer(width=1080, height=1920)


def _scene():
    return {
        "narration": ("Khi vi khuẩn lẻn vào cơ thể, bạch cầu tuần tra lập tức phát hiện kẻ lạ mặt. "
                      "Nó lao tới, vươn tay tóm gọn con mồi."),
        "focal_keyword": "white blood cell",
        "secondary_keyword": "bacterium",
        "duration": 6.0,
        "beats": [
            {"narration_part": "Khi vi khuẩn lẻn vào cơ thể,",
             "elements": [{"role": "focal", "keyword": "white blood cell",
                           "action": "enter", "from": "left"}],
             "emphasis_words": []},
            {"narration_part": "bạch cầu tuần tra lập tức phát hiện kẻ lạ mặt.",
             "elements": [{"role": "secondary", "keyword": "bacterium",
                           "action": "enter", "from": "right"}],
             "emphasis_words": ["kẻ lạ mặt"]},
            {"narration_part": "Nó lao tới, vươn tay tóm gọn con mồi.",
             "elements": [{"role": "focal", "keyword": "white blood cell",
                           "action": "swap_pose", "pose": "grab"},
                          {"role": "secondary", "keyword": "bacterium",
                           "action": "exit", "to": "right"}],
             "emphasis_words": []},
        ],
    }


def _choreo(duration=6.0):
    return CHOREO.choreograph(_scene(), duration)


def test_timeline_targets_match_cast():
    out = _choreo()
    cast_keys = set(out["cast"].keys())
    for a in out["timeline"]:
        assert a["target"] in cast_keys, f"target lạ: {a['target']}"
    assert out["target_by_keyword"]["white blood cell"] == "hero"
    assert out["target_by_keyword"]["bacterium"] == "secondary"


def test_enter_uses_converge_wrap_inside_beat():
    out = _choreo()
    enters = [a for a in out["timeline"] if a["action"] == "CONVERGE_WRAP"]
    assert len(enters) == 2
    beats = out["beat_timing"]
    for a in enters:
        st = a["start_time"]
        assert any(b["start"] <= st <= b["end"] for b in beats)
        ox, oy = a["start_offset"]
        assert abs(ox) >= 1080 * 0.8 or abs(oy) >= 1920 * 0.8


def test_exit_goes_offscreen_and_hides():
    out = _choreo()
    exits = [a for a in out["timeline"] if a["action"] == "EXIT_SLIDE"]
    assert len(exits) == 1
    assert exits[0]["direction"] == "right"
    engine = MotionTimelineEngine(
        timeline=out["timeline"],
        base_configs={k: {"position": v["position"], "visible": v["visible"]}
                      for k, v in out["cast"].items()},
    )
    t0, t1 = exits[0]["time_range"]
    assert engine.get_frame_state(t0 - 0.05)["secondary"]["visible"] is True
    assert engine.get_frame_state(t1 + 0.1)["secondary"]["visible"] is False


def test_emphasize_restores_scale_via_engine():
    scene = _scene()
    scene["beats"] = [
        {"narration_part": "Nhấn mạnh.",
         "elements": [{"role": "focal", "keyword": "white blood cell",
                       "action": "emphasize"}],
         "emphasis_words": []},
    ]
    out = CHOREO.choreograph(scene, 4.0)
    squash = [a for a in out["timeline"] if a["action"] == "COMPRESS_SQUASH"]
    assert len(squash) == 2  # nảy to rồi về 1.0
    engine = MotionTimelineEngine(
        timeline=out["timeline"],
        base_configs={"hero": {"position": [540, 960], "visible": True}},
    )
    t_end = squash[1]["time_range"][1] + 0.2
    st = engine.get_frame_state(t_end)["hero"]
    assert st["scale_x"] == pytest.approx(1.0, abs=0.02)
    assert st["scale_y"] == pytest.approx(1.0, abs=0.02)


def test_swap_pose_emits_placeholder_engine_ignores_safely():
    out = _choreo()
    swaps = [a for a in out["timeline"] if a["action"] == "SWAP_ASSET"]
    assert len(swaps) == 1
    assert swaps[0]["pose"] == "grab"
    assert swaps[0]["target"] == "hero"
    # Engine hiện tại chưa biết SWAP_ASSET -> bỏ qua an toàn, không crash.
    engine = MotionTimelineEngine(
        timeline=out["timeline"],
        base_configs={k: {"position": v["position"], "visible": v["visible"]}
                      for k, v in out["cast"].items()},
    )
    states = engine.get_frame_state(5.0)
    assert "hero" in states and "secondary" in states


def test_hero_hidden_before_enter_and_visible_after():
    out = _choreo()
    engine = MotionTimelineEngine(
        timeline=out["timeline"],
        base_configs={k: {"position": v["position"], "visible": v["visible"]}
                      for k, v in out["cast"].items()},
    )
    assert engine.get_frame_state(0.0)["hero"]["visible"] is False
    assert engine.get_frame_state(2.0)["hero"]["visible"] is True


def test_labels_timing_inside_beats():
    out = _choreo()
    assert len(out["labels"]) == 1
    lb = out["labels"][0]
    assert lb["text"] == "kẻ lạ mặt"
    beats = out["beat_timing"]
    assert any(b["start"] <= lb["start"] <= b["end"] for b in beats)
    assert lb["end"] <= beats[1]["end"] + 0.01


def test_beat_timing_covers_duration_monotonic():
    out = _choreo(duration=6.0)
    beats = out["beat_timing"]
    assert beats[0]["start"] == pytest.approx(HEAD_RESERVE)
    assert beats[-1]["end"] == pytest.approx(6.0 - TAIL_RESERVE)
    for i in range(len(beats) - 1):
        assert beats[i]["end"] <= beats[i + 1]["start"] + 1e-6
        assert beats[i]["start"] < beats[i]["end"]


def test_scene_without_beats_gets_heuristic_timeline():
    scene = {"narration": "Mặt trời mọc mỗi sáng, chim hót véo von trên cành cây xanh.",
             "focal_keyword": "sun", "secondary_keyword": "bird"}
    out = CHOREO.choreograph(scene, 5.0)
    assert len(out["timeline"]) >= 2
    assert len(out["beat_timing"]) >= 2


def test_deterministic():
    a = _choreo()
    b = _choreo()
    assert a == b
