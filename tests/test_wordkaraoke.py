"""
tests/test_wordkaraoke.py — Stage 6 Step 5: phụ đề karaoke word-level.

Phạm vi (offline, Whisper giả — không tải model):
- transcribe_words: model None -> [] (fallback an toàn).
- _map_script_words_to_timings: khớp 1:1 và nội suy khi lệch số từ.
- generate_wordkaraoke_ass: tag {\k} theo timing thật, chữ từ kịch bản,
  scene thiếu audio -> fallback chia đều, tôn trọng scene_start_times.
- CollageEngine._scene_start_times: tính mốc gồm wipe chuyển cảnh.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.render_engine.subtitle_generator import SubtitleGenerator

pytestmark = pytest.mark.unit


class _FakeWord:
    def __init__(self, word, start, end):
        self.word = word
        self.start = start
        self.end = end


class _FakeSeg:
    def __init__(self, words):
        self.words = words


class _FakeModel:
    def __init__(self, timed_words):
        self.timed_words = timed_words

    def transcribe(self, audio_path, language="vi", word_timestamps=True):
        words = [_FakeWord(w, s, e) for w, s, e in self.timed_words]
        return [_FakeSeg(words)], None


def _gen():
    g = SubtitleGenerator.__new__(SubtitleGenerator)
    g.model = None
    g.model_size = "base"
    return g


def test_transcribe_words_no_model_returns_empty():
    g = _gen()
    assert g.transcribe_words("/tmp/khong_co_file.wav") == []
    assert g.transcribe_words("") == []


def test_map_words_one_to_one():
    heard = [{"word": "x", "start": s, "end": e}
             for _, s, e in [("a", 0.0, 0.2), ("b", 0.2, 0.5)]]
    out = SubtitleGenerator._map_script_words_to_timings(["xin", "chào"], heard)
    assert out[0] == {"word": "xin", "start": 0.0, "end": 0.2}
    assert out[1] == {"word": "chào", "start": 0.2, "end": 0.5}


def test_map_words_interpolates_when_counts_differ():
    heard = [{"word": f"w{i}", "start": i * 0.3, "end": i * 0.3 + 0.25} for i in range(6)]
    out = SubtitleGenerator._map_script_words_to_timings(["một", "hai", "ba"], heard)
    assert out[0]["start"] == pytest.approx(0.0)
    assert out[2]["start"] == pytest.approx(1.5)
    assert [w["word"] for w in out] == ["một", "hai", "ba"]


def test_wordkaraoke_ass_uses_real_timings(tmp_path):
    import subprocess
    wav = str(tmp_path / "fake.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=16000:cl=mono", "-t", "2",
                    wav], check=True)
    g = _gen()
    g.model = _FakeModel([("xin", 0.0, 0.3), ("chào", 0.3, 0.6),
                          ("các", 0.6, 0.9), ("bạn", 0.9, 1.2)])
    script = {"scenes": [{"narration": "xin chào các bạn"}]}
    out = str(tmp_path / "k.ass")
    g.generate_wordkaraoke_ass(
        script, scene_audios=[wav], scene_durations=[5.0],
        output_path=out, format="shorts", language="vi",
        scene_start_times=[2.0],
    )
    content = Path(out).read_text(encoding="utf-8")
    assert "{\\k30}xin" in content
    assert "{\\k30}chào" in content
    # chunk bắt đầu đúng mốc scene (2.0 + 0.0)
    assert "Dialogue: 0,0:00:02.00," in content
    assert "TikTokKaraoke" in content


def test_wordkaraoke_fallback_when_no_audio(tmp_path):
    g = _gen()
    script = {"scenes": [{"narration": "một hai ba bốn năm"}]}
    out = str(tmp_path / "k2.ass")
    g.generate_wordkaraoke_ass(
        script, scene_audios=[""], scene_durations=[4.0],
        output_path=out, format="shorts",
    )
    content = Path(out).read_text(encoding="utf-8")
    # fallback: cụm 4 từ chia đều, chữ hoa như generate_tiktok_ass
    assert "MỘT HAI BA BỐN" in content
    assert "{\\k" not in content


def test_scene_start_times_with_wipes():
    from styles.collage_broll.collage_engine import CollageEngine
    clips = ["clip_00.mp4", "wipe_00_01.mp4", "clip_01.mp4",
             "wipe_01_02.mp4", "clip_02.mp4"]
    starts = CollageEngine._scene_start_times(clips, [5.0, 6.0, 4.0])
    assert starts == [0.0, 5.5, 12.0]


def test_scene_start_times_no_wipes():
    from styles.collage_broll.collage_engine import CollageEngine
    starts = CollageEngine._scene_start_times(["a.mp4", "b.mp4"], [5.0, 6.0])
    assert starts == [0.0, 5.0]
