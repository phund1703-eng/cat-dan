"""
tests/test_motion_primitives.py — Stage 6 Step 3: 3 động cơ mới.

Phạm vi:
- SWAP_ASSET: đổi asset_variant theo beat (renderer dùng để vẽ pose khác).
- EXIT_SLIDE: trượt ra theo hướng rồi visible=False.
- POP_IN: nảy overshoot 0 -> 1 theo nấc stop-motion.
- tactile_jitter_from / amplitude cấu hình được; không crash khi có __screen_shake__.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.motion_timeline_engine import MotionTimelineEngine

pytestmark = pytest.mark.unit

BASE = {"hero": {"position": [540, 960], "visible": True}}


def _engine(timeline, **kw):
    return MotionTimelineEngine(timeline=timeline, base_configs=dict(BASE), **kw)


def test_swap_asset_sets_variant_after_time():
    tl = [{"target": "hero", "action": "SWAP_ASSET", "swap_time": 2.0, "pose": "grab"}]
    e = _engine(tl)
    assert e.get_frame_state(1.9)["hero"]["asset_variant"] == ""
    assert e.get_frame_state(2.0)["hero"]["asset_variant"] == "grab"
    assert e.get_frame_state(9.9)["hero"]["asset_variant"] == "grab"


def test_swap_asset_last_wins_and_default_pose():
    tl = [
        {"target": "hero", "action": "SWAP_ASSET", "swap_time": 1.0, "pose": "point"},
        {"target": "hero", "action": "SWAP_ASSET", "swap_time": 3.0},  # pose rỗng -> "alt"
    ]
    e = _engine(tl)
    assert e.get_frame_state(2.0)["hero"]["asset_variant"] == "point"
    assert e.get_frame_state(3.5)["hero"]["asset_variant"] == "alt"


def test_exit_slide_moves_then_hides():
    tl = [{"target": "hero", "action": "EXIT_SLIDE",
           "time_range": [2.0, 2.8], "direction": "right", "steps": 4}]
    e = _engine(tl)
    before = e.get_frame_state(1.9)["hero"]
    assert before["visible"] is True
    assert before["position"][0] == pytest.approx(540)
    mid = e.get_frame_state(2.4)["hero"]
    assert mid["visible"] is True
    assert mid["position"][0] > 540  # đang trượt ra phải
    after = e.get_frame_state(2.9)["hero"]
    assert after["visible"] is False
    assert after["position"][0] > 1080  # đã ra khỏi khung


def test_exit_slide_explicit_end_pos():
    tl = [{"target": "hero", "action": "EXIT_SLIDE",
           "time_range": [1.0, 2.0], "end_pos": [2000, 960]}]
    e = _engine(tl)
    assert e.get_frame_state(2.5)["hero"]["visible"] is False


def test_pop_in_hidden_before_overshoot_mid_settled_after():
    tl = [{"target": "hero", "action": "POP_IN",
           "start_time": 1.0, "duration": 0.6, "steps": 3}]
    e = _engine(tl)
    assert e.get_frame_state(0.9)["hero"]["visible"] is False
    mid_scale = max(
        e.get_frame_state(1.0 + i * 0.05)["hero"]["scale_x"] for i in range(1, 12)
    )
    assert mid_scale > 1.0  # có overshoot nảy quá cỡ
    end = e.get_frame_state(1.8)["hero"]
    assert end["visible"] is True
    assert end["scale_x"] == pytest.approx(1.0)
    assert end["scale_y"] == pytest.approx(1.0)


def test_tactile_jitter_configurable():
    tl = []
    e_default = _engine(tl)
    p0 = e_default.get_frame_state(4.0, frame_idx=0)["hero"]["position"]
    p1 = e_default.get_frame_state(4.0, frame_idx=1)["hero"]["position"]
    assert p0 != p1  # mặc định vẫn rung ở t >= 3.8
    e_off = _engine(tl, tactile_jitter_from=999.0)
    q0 = e_off.get_frame_state(4.0, frame_idx=0)["hero"]["position"]
    q1 = e_off.get_frame_state(4.0, frame_idx=1)["hero"]["position"]
    assert q0 == q1 == [540.0, 960.0]


def test_screen_shake_flag_does_not_crash_jitter():
    tl = [{"target": "hero", "action": "COMPRESS_SQUASH",
           "time_range": [3.6, 4.4], "screen_shake": True,
           "scale_x": 1.2, "scale_y": 0.9}]
    e = _engine(tl)
    states = e.get_frame_state(3.9, frame_idx=2)  # vừa shake vừa jitter
    assert states.get("__screen_shake__") is True
    assert "position" in states["hero"]


def test_pulse_beats_and_rests():
    tl = [{"target": "hero", "action": "PULSE",
           "time_range": [1.0, 3.0], "pulses_per_sec": 1.0,
           "scale_max": 1.2, "steps": 4}]
    e = _engine(tl)
    assert e.get_frame_state(0.5)["hero"]["scale_x"] == pytest.approx(1.0)
    scales = [e.get_frame_state(1.0 + i * 0.1)["hero"]["scale_x"] for i in range(20)]
    assert max(scales) > 1.05  # có nhịp phồng
    assert min(scales) == pytest.approx(1.0, abs=0.01)  # có nhịp xẹp về gốc
    assert e.get_frame_state(3.5)["hero"]["scale_x"] == pytest.approx(1.0)


def test_pulse_alias_engine_constant():
    tl = [{"target": "hero", "action": "ENGINE_PULSE",
           "time_range": [0.5, 2.5]}]
    e = _engine(tl)
    assert e.get_frame_state(1.0)["hero"]["scale_x"] >= 1.0
