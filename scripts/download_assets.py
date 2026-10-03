#!/usr/bin/env python3
"""
download_assets.py — Tải lại tài nguyên tĩnh (font + nhạc nền) cho AutoVideoFactory.

Dùng khi clone repo mà thiếu file trong `assets/fonts/` hoặc `assets/music/`
(install.bat tự gọi script này khi phát hiện thiếu). Mọi nguồn đều là nguồn
chính thức, license rõ ràng:

- Font Be Vietnam Pro Bold (SIL OFL 1.1): Google Fonts (github.com/google/fonts).
- Nhạc nền Kevin MacLeod (CC BY, bắt buộc ghi credit): Wikimedia Commons.
  File tải về được re-encode 128kbps nếu có ffmpeg, giống bản đã commit.

Cách dùng:
    python scripts/download_assets.py            # chỉ tải file còn thiếu
    python scripts/download_assets.py --force    # tải lại tất cả
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FONT_URL = (
    "https://github.com/google/fonts/raw/main/ofl/bevietnampro/BeVietnamPro-Bold.ttf"
)
FONT_LICENSE_URL = "https://github.com/google/fonts/raw/main/ofl/bevietnampro/OFL.txt"

# (tên file đích, URL nguồn, tác phẩm, giấy phép)
MUSIC_TRACKS = [
    (
        "kevin_macleod_cattails.mp3",
        "https://upload.wikimedia.org/wikipedia/commons/4/4c/Kevin_MacLeod_-_Cattails.mp3",
        "Cattails — Kevin MacLeod",
        "CC BY 3.0",
    ),
    (
        "kevin_macleod_holiday_weasel.mp3",
        "https://upload.wikimedia.org/wikipedia/commons/c/ce/"
        "Kevin_MacLeod_-_Holiday_Weasel_%28cc-by%29_%28filmmusic%29.mp3",
        "Holiday Weasel — Kevin MacLeod",
        "CC BY 2.0",
    ),
    (
        "kevin_macleod_stay_the_course.mp3",
        "https://upload.wikimedia.org/wikipedia/commons/7/74/"
        "Kevin_MacLeod_-_Stay_The_Course_%28cc-by%29_%28filmmusic%29.mp3",
        "Stay The Course — Kevin MacLeod",
        "CC BY 4.0",
    ),
]

MIN_FONT_BYTES = 50_000  # font thật ~140KB; nhỏ hơn = tải lỗi
MIN_MUSIC_BYTES = 500_000


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "cat-dan/download_assets"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def _ensure(target: Path, url: str, min_bytes: int, force: bool, label: str) -> bool:
    if target.exists() and target.stat().st_size >= min_bytes and not force:
        print(f"  [=] Đã có: {label}")
        return True
    print(f"  [>] Đang tải {label} ...")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        _download(url, tmp)
    except Exception as exc:  # noqa: BLE001 - báo lỗi rõ cho người dùng
        print(f"  [!] Tải thất bại {label}: {exc}")
        tmp.unlink(missing_ok=True)
        return False
    if tmp.stat().st_size < min_bytes:
        print(f"  [!] File tải về quá nhỏ (tải lỗi?): {label}")
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(target)
    print(f"  [✓] Xong: {label} ({target.stat().st_size / 1e6:.2f} MB)")
    return True


def _reencode_128k(path: Path) -> None:
    """Re-encode MP3 về 128kbps cho nhẹ repo (nếu có ffmpeg); giữ ID3 credit."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print(f"  [i] Không có ffmpeg — giữ nguyên bản gốc: {path.name}")
        return
    tmp = path.with_suffix(".tmp.mp3")
    result = subprocess.run(
        [
            ffmpeg, "-y", "-v", "error", "-i", str(path),
            "-codec:a", "libmp3lame", "-b:a", "128k", "-id3v2_version", "3",
            "-metadata", "artist=Kevin MacLeod",
            "-metadata", "composer=Kevin MacLeod",
            str(tmp),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and tmp.exists() and tmp.stat().st_size > MIN_MUSIC_BYTES:
        tmp.replace(path)
        print(f"  [i] Đã re-encode 128kbps: {path.name}")
    else:
        tmp.unlink(missing_ok=True)
        print(f"  [i] Re-encode thất bại — giữ nguyên bản gốc: {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Tải font + nhạc nền cho AutoVideoFactory")
    parser.add_argument("--force", action="store_true", help="tải lại kể cả khi file đã có")
    args = parser.parse_args()

    ok = True
    fonts_dir = PROJECT_ROOT / "assets" / "fonts"
    music_dir = PROJECT_ROOT / "assets" / "music"

    print("[Font] Be Vietnam Pro Bold (OFL 1.1, Google Fonts)")
    ok &= _ensure(fonts_dir / "BeVietnamPro-Bold.ttf", FONT_URL, MIN_FONT_BYTES, args.force, "BeVietnamPro-Bold.ttf")
    ok &= _ensure(fonts_dir / "OFL.txt", FONT_LICENSE_URL, 1_000, args.force, "OFL.txt")

    print("[Music] Kevin MacLeod qua Wikimedia Commons (CC BY — nhớ ghi credit)")
    for filename, url, title, license_name in MUSIC_TRACKS:
        target = music_dir / filename
        existed = target.exists() and not args.force
        if _ensure(target, url, MIN_MUSIC_BYTES, args.force, f"{filename} ({title}, {license_name})"):
            if not existed:
                _reencode_128k(target)
        else:
            ok = False

    print("\nHoàn tất." if ok else "\nCó file tải thất bại — kiểm tra mạng và chạy lại.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
