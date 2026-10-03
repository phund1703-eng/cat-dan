"""
Task 4.2 — Test end-to-end "golden": chủ đề cố định -> MP4 thật.

Chạy pipeline THẬT (dashboard.worker.video_tasks.run_video_pipeline):
- Chỉ mock Gemini bằng fixture kịch bản ghi sẵn (ScriptGenerator.generate).
- Pexels/asset: đi qua CascadeAssetOrchestrator thật (không key -> tự
  degrade xuống tier procedural như production).
- KHÔNG mock TTS/FFmpeg/render: giọng đi qua TTSManager thật (VieNeu ->
  Edge TTS -> fallback tổng hợp của chính pipeline), render FFmpeg thật.

Assert chặt (không hạ chuẩn):
- MP4 tồn tại; ffprobe: 1080x1920, có audio, thời lượng khớp tổng audio
  của các scene +-1.5s.
- Frame tại 50% mỗi scene khác nhau rõ (histogram L1 > 0.05).
- Phụ đề cháy thật: vùng dưới giữa khung hình có chữ sáng tập trung ở
  1/3 giữa (đặc trưng sub căn giữa), không phải sáng nền ngẫu nhiên.
- Export ZIP chứa sources.json khớp đúng nguồn của fixture.
- 9 frame nghiệm thu (3 scene x 25/50/75%) lưu output/golden_frames/.

Đánh dấu integration: cần ffmpeg/ffprobe + ngăn TTS thật (mạng Edge TTS
hoặc VieNeu). Chạy: pytest tests/test_e2e_golden.py -m integration
"""

import json
import shutil
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import dashboard.api.database as db_mod
import dashboard.api.routes.jobs as jobs_mod
import dashboard.worker.video_tasks as worker_mod
from dashboard.api.models import JobStatus

pytestmark = pytest.mark.integration

JOB_ID = "golden-e2e-test"
TOPIC = "Vì sao bạch cầu tiêu diệt được vi khuẩn"
GOLDEN_FRAMES_DIR = PROJECT_ROOT / "output" / "golden_frames"

GOLDEN_SCRIPT = {
    "title": "Vì sao bạch cầu tiêu diệt được vi khuẩn?",
    "description": "Bạch cầu săn và nuốt vi khuẩn như thế nào.",
    "hashtags": ["#khoahoc", "#bachcau"],
    "script_origin": "gemini",
    "scenes": [
        {
            "narration": "Trong mỗi giọt máu của bạn có hàng nghìn bạch cầu tuần tra như những người lính gác.",
            "visual_description": "white blood cells patrolling in bloodstream, red blood cells flowing",
            "fact": "Máu người chứa khoảng 4.000-11.000 bạch cầu trong mỗi microlit.",
            "sources": [{"title": "White blood cell count", "url": "https://medlineplus.gov/ency/article/003643.htm", "publisher": "MedlinePlus", "accessed_date": "2026-10-02"}],
            "focal_keyword": "white blood cell",
            "duration": 4.0,
        },
        {
            "narration": "Khi vi khuẩn xâm nhập, bạch cầu lần theo tín hiệu hóa học và bám chặt lấy kẻ lạ mặt.",
            "visual_description": "white blood cell chasing bacteria, chemotaxis illustration",
            "fact": "Bạch cầu di chuyển về phía vi khuẩn nhờ hiện tượng hóa hướng động (chemotaxis).",
            "sources": [{"title": "Chemotaxis", "url": "https://www.nature.com/scitable/topicpage/chemotaxis-14157154/", "publisher": "Nature Education", "accessed_date": "2026-10-02"}],
            "focal_keyword": "bacteria",
            "duration": 4.0,
        },
        {
            "narration": "Sau đó nó vươn ra ôm trọn con vi khuẩn và nuốt chửng vào bên trong để tiêu hóa.",
            "visual_description": "phagocytosis white blood cell engulfing bacteria",
            "fact": "Quá trình bạch cầu nuốt vi khuẩn được gọi là thực bào (phagocytosis).",
            "sources": [{"title": "Phagocytosis", "url": "https://www.britannica.com/science/phagocytosis", "publisher": "Encyclopaedia Britannica", "accessed_date": "2026-10-02"}],
            "focal_keyword": "phagocytosis",
            "duration": 4.0,
        },
    ],
}


def _ffmpeg_exe() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


@pytest.fixture()
def golden_env(tmp_path, monkeypatch):
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg or not shutil.which("ffprobe"):
        pytest.skip("Cần ffmpeg + ffprobe trên PATH cho e2e render thật")

    monkeypatch.chdir(PROJECT_ROOT)

    engine = create_engine(
        f"sqlite:///{tmp_path}/golden.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_mod.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(jobs_mod, "SessionLocal", TestingSession)
    monkeypatch.setattr(worker_mod, "SessionLocal", TestingSession)

    # Chỉ mock Gemini: trả fixture kịch bản ghi sẵn.
    from core.script_engine.script_generator import ScriptGenerator

    async def fake_generate(self, topic, style, language, duration=60):
        assert topic == TOPIC
        return json.loads(json.dumps(GOLDEN_SCRIPT))

    monkeypatch.setattr(ScriptGenerator, "generate", fake_generate)

    # Dọn output của lần chạy trước để test lặp lại được.
    job_dir = PROJECT_ROOT / "data" / "output" / JOB_ID
    if job_dir.exists():
        shutil.rmtree(job_dir)

    db = TestingSession()
    try:
        db.add(db_mod.VideoJob(
            id=JOB_ID, topic=TOPIC, style="collage_broll", language="vi",
            status=JobStatus.pending, stage="pending", mode="auto",
        ))
        db.commit()
    finally:
        db.close()

    return TestingSession, ffmpeg


def _extract_frame(ffmpeg: str, video: Path, t: float, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video),
         "-frames:v", "1", str(out)],
        check=True,
    )
    assert out.exists() and out.stat().st_size > 0
    return out


def _histogram(path: Path):
    import numpy as np
    from PIL import Image

    im = Image.open(path).convert("L").resize((270, 480))
    hist = np.histogram(np.asarray(im), bins=32, range=(0, 256))[0].astype(float)
    return hist / hist.sum()


def _subtitle_signal(path: Path) -> float:
    """Độ tập trung chữ sáng ở 1/3 giữa vùng dưới khung hình.

    Sub cháy căn giữa -> bright-pixel fraction ở cột giữa cao hơn hẳn hai
    cột biên. Trả (center_frac, center_frac - max(edge_frac)).
    """
    import numpy as np
    from PIL import Image

    im = Image.open(path).convert("L")
    w, h = im.size
    band = np.asarray(im.crop((0, int(h * 0.60), w, int(h * 0.97))), dtype=float)
    bright = band > 200
    center = float(bright[:, w // 3: 2 * w // 3].mean())
    edges = max(float(bright[:, : w // 3].mean()), float(bright[:, 2 * w // 3:].mean()))
    return center, center - edges


def test_e2e_golden_pipeline(golden_env):
    TestingSession, ffmpeg = golden_env
    from core.render_engine.ffmpeg_utils import get_video_info

    # --- Chạy pipeline thật từ đầu tới cuối -------------------------------
    worker_mod.run_video_pipeline(JOB_ID)

    db = TestingSession()
    try:
        job = worker_mod.get_job(db, JOB_ID)
        assert job.status == JobStatus.done, f"job không done: {job.status}/{job.stage} err={job.error}"
        assert job.stage == "done"
        pipeline_data = job.pipeline_data or {}
        scenes = pipeline_data.get("scenes") or []
        assert len(scenes) == 3
        audio_durations = [float(s.get("audio_duration") or s.get("duration") or 0) for s in scenes]
        assert all(d > 0 for d in audio_durations)
        output_path = Path(job.output_path) if job.output_path else None
    finally:
        db.close()

    # --- MP4 thật: tồn tại, đúng chuẩn dọc, có audio -----------------------
    assert output_path is not None and output_path.exists(), "Chưa có file MP4 đầu ra"
    info = get_video_info(str(output_path))
    assert info["width"] == 1080 and info["height"] == 1920, f"Sai độ phân giải: {info}"
    assert info["has_audio"], "Video không có audio stream"
    total_audio = sum(audio_durations)
    assert abs(info["duration"] - total_audio) <= 1.5, (
        f"Thời lượng video {info['duration']:.2f}s lệch tổng audio {total_audio:.2f}s quá 1.5s"
    )

    # --- 9 frame nghiệm thu + frame 50% mỗi scene --------------------------
    starts = [0.0]
    for d in audio_durations[:-1]:
        starts.append(starts[-1] + d)

    mid_frames = []
    for i, (start, dur) in enumerate(zip(starts, audio_durations)):
        scene_frames = []
        for frac in (0.25, 0.50, 0.75):
            frame = _extract_frame(
                ffmpeg, output_path, start + dur * frac,
                GOLDEN_FRAMES_DIR / f"scene{i + 1}_{int(frac * 100)}.png",
            )
            scene_frames.append(frame)
        mid_frames.append(scene_frames[1])

        # Phụ đề cháy: ít nhất 1 frame trong scene có chữ sáng căn giữa.
        signals = [_subtitle_signal(f) for f in scene_frames]
        best_center, best_contrast = max(signals, key=lambda s: s[0])
        assert best_center > 0.002 and best_contrast > 0.001, (
            f"Scene {i + 1}: không thấy phụ đề cháy (center={best_center:.4f}, contrast={best_contrast:.4f})"
        )

    # --- Frame giữa các scene phải khác nhau rõ ----------------------------
    import numpy as np

    hists = [_histogram(f) for f in mid_frames]
    for i in range(len(hists)):
        for j in range(i + 1, len(hists)):
            dist = float(np.abs(hists[i] - hists[j]).sum())
            assert dist > 0.05, f"Frame scene {i + 1} và {j + 1} quá giống nhau (L1={dist:.3f})"

    # --- sources.json trong export ZIP khớp fixture ------------------------
    from fastapi.testclient import TestClient
    from dashboard.api.main import app

    with TestClient(app) as client:
        r = client.get(f"/jobs/{JOB_ID}/export-zip")
        assert r.status_code == 200, r.text

    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        assert "sources.json" in zf.namelist()
        payload = json.loads(zf.read("sources.json").decode("utf-8"))

    exported_urls = {s["url"] for s in payload["sources"]}
    expected_urls = {s["sources"][0]["url"] for s in GOLDEN_SCRIPT["scenes"]}
    assert exported_urls == expected_urls, f"sources.json lệch fixture: {exported_urls} vs {expected_urls}"
