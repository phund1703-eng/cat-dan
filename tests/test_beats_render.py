"""
tests/test_beats_render.py — Stage 6 Step 4: beats render path (offline).

Phạm vi:
- GbroAdapter.render_beats_clip: dựng clip từ choreo (timeline + labels +
  pose variants) bằng asset procedural, không mạng.
- SWAP_ASSET đổi ảnh thật sự trên frame (kiểm bằng màu pixel).
- Kinetic labels xuất hiện đúng cửa sổ thời gian.
- render_paper_wipe: clip chuyển cảnh có đủ 2 màu scene.
- CollageEngine._render_beats_scene: nối asset mock -> render_beats_clip.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.media_engine.beat_choreographer import BeatChoreographer
from styles.collage_broll.gbro_adapter import GbroAdapter

pytestmark = pytest.mark.unit

W, H = 540, 960
TMP = Path("/tmp/beats_render_test")


def _rgba_square(path: Path, rgb, shape="square", size=200):
    im = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shape == "square":
        d.rectangle([20, 20, size + 20, size + 20], fill=rgb + (255,))
    else:
        d.ellipse([20, 20, size + 20, size + 20], fill=rgb + (255,))
    im.save(path)
    return str(path)


@pytest.fixture(scope="module")
def assets():
    TMP.mkdir(parents=True, exist_ok=True)
    return {
        "hero": _rgba_square(TMP / "hero.png", (255, 0, 0)),
        "secondary": _rgba_square(TMP / "sec.png", (0, 0, 255), "circle"),
        "prop": _rgba_square(TMP / "prop.png", (0, 180, 0)),
        "hero_alt": _rgba_square(TMP / "hero_alt.png", (255, 255, 0)),
    }


def _scene():
    return {
        "color_field": "Deep Cobalt",
        "color_hex": "1D3557",
        "beats": [
            {"narration_part": "Vi khuẩn xuất hiện.",
             "elements": [{"role": "focal", "keyword": "white blood cell",
                           "action": "enter", "from": "left"}],
             "emphasis_words": []},
            {"narration_part": "Bạch cầu lao tới.",
             "elements": [{"role": "secondary", "keyword": "bacterium",
                           "action": "enter", "from": "right"}],
             "emphasis_words": ["lao tới"]},
            {"narration_part": "Đổi tư thế tóm gọn.",
             "elements": [{"role": "focal", "keyword": "white blood cell",
                           "action": "swap_pose", "pose": "alt"}],
             "emphasis_words": []},
        ],
    }


def _choreo(duration=4.0):
    return BeatChoreographer(width=W, height=H).choreograph(_scene(), duration)


def _probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip().split("=")[1])


def _frame_mean_rgb(video, t, box):
    png = TMP / f"probe_{t}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video,
                    "-vframes", "1", str(png)], check=True)
    im = Image.open(png).convert("RGB").crop(box)
    px = list(im.get_flattened_data())
    n = len(px)
    return tuple(sum(c[i] for c in px) / n for i in range(3))


def test_render_beats_clip_produces_video(assets):
    adapter = GbroAdapter()
    out = str(TMP / "beats.mp4")
    got = adapter.render_beats_clip(
        scene=_scene(), choreo=_choreo(),
        assets={"hero": assets["hero"], "secondary": assets["secondary"]},
        output_path=out, work_dir=TMP / "w1", width=W, height=H,
        duration=4.0, fps=12,
        pose_assets={"hero": {"alt": assets["hero_alt"]}},
    )
    assert Path(got).exists()
    assert _probe_duration(got) == pytest.approx(4.0, abs=0.3)


def test_swap_asset_changes_pixels(assets):
    adapter = GbroAdapter()
    out = str(TMP / "beats_swap.mp4")
    choreo = _choreo()
    swap_t = next(a["swap_time"] for a in choreo["timeline"]
                  if a["action"] == "SWAP_ASSET")
    adapter.render_beats_clip(
        scene=_scene(), choreo=choreo,
        assets={"hero": assets["hero"], "secondary": assets["secondary"]},
        output_path=out, work_dir=TMP / "w2", width=W, height=H,
        duration=4.0, fps=12,
        pose_assets={"hero": {"alt": assets["hero_alt"]}},
    )
    # Vùng hero nghỉ (0.36W, 0.58H), crop 90x90.
    box = (int(0.36 * W) - 45, int(0.58 * H) - 45,
           int(0.36 * W) + 45, int(0.58 * H) + 45)
    before = _frame_mean_rgb(out, max(0.1, swap_t - 0.6), box)
    after = _frame_mean_rgb(out, min(3.9, swap_t + 0.6), box)
    # trước swap: đỏ trội; sau swap: vàng (đỏ+xanh lá đều cao)
    assert before[0] > before[1] + 20
    assert after[1] > before[1] + 20


def test_labels_appear_in_window(assets):
    adapter = GbroAdapter()
    out = str(TMP / "beats_label.mp4")
    choreo = _choreo()
    lb = choreo["labels"][0]
    adapter.render_beats_clip(
        scene=_scene(), choreo=choreo,
        assets={"hero": assets["hero"], "secondary": assets["secondary"]},
        output_path=out, work_dir=TMP / "w3", width=W, height=H,
        duration=4.0, fps=12,
    )
    box = (int(0.5 * W) - 80, int(0.16 * H) - 40,
           int(0.5 * W) + 80, int(0.16 * H) + 40)
    inside = _frame_mean_rgb(out, (lb["start"] + lb["end"]) / 2, box)
    outside = _frame_mean_rgb(out, 0.1, box)
    # nền Deep Cobalt tối; khi label hiện, vùng sáng hơn rõ rệt (chữ trắng viền)
    bright_in = sum(inside) / 3
    bright_out = sum(outside) / 3
    assert bright_in > bright_out + 15


def test_paper_wipe_blends_two_scenes(assets):
    adapter = GbroAdapter()
    a = str(TMP / "wipe_src_a.mp4")
    b = str(TMP / "wipe_src_b.mp4")
    for path, color in ((a, "red"), (b, "blue")):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                        "-i", f"color=c={color}:s={W}x{H}:d=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", path], check=True)
    out = str(TMP / "wipe.mp4")
    got = adapter.render_paper_wipe(a, b, out, width=W, height=H)
    assert Path(got).exists()
    assert _probe_duration(got) == pytest.approx(0.5, abs=0.15)
    mid = _frame_mean_rgb(out, 0.25, (0, 0, W, H))
    # giữa wipe: có cả đỏ (A) và xanh (B) trong khung
    assert mid[0] > 40 and mid[2] > 40


def test_collage_engine_beats_wiring(assets):
    from styles.collage_broll.collage_engine import CollageEngine

    async def fake_sticker(keyword, domain="general", is_character=False,
                          fallback_scene_index=0):
        return {"white blood cell": assets["hero"],
                "bacterium": assets["secondary"]}.get(keyword, "")

    engine = CollageEngine.__new__(CollageEngine)
    engine.gbro_adapter = GbroAdapter()

    class FakeCutoutMgr:
        async def get_cutout_sticker(self, keyword, domain="general",
                                     is_character=False, fallback_scene_index=0):
            return await fake_sticker(keyword)

    engine.cutout_mgr = FakeCutoutMgr()
    out = str(TMP / "wired.mp4")
    got = asyncio.run(engine._render_beats_scene(
        scene=_scene(), scene_duration=4.0, width=W, height=H,
        scene_dir=TMP / "w4", scene_index=0, topic_domain="biology",
        focal_sticker_path=assets["hero"],
        secondary_sticker_path=assets["secondary"],
        output_path=out,
    ))
    assert Path(got).exists()
    assert _probe_duration(got) == pytest.approx(4.0, abs=0.3)
