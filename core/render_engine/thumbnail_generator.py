"""
Thumbnail generator for completed AutoVideoFactory jobs (Task 3.2).

The generator favours the hook scene's own frame/image, frames it as a torn
paper collage sticker, and fits Vietnamese text by measurement instead of
guessing. The preferred BeVietnamPro font belongs to Stage 5 asset packaging;
until it is present we gracefully use DejaVu/other local bold fonts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PORTRAIT_SIZE = (1080, 1920)
LANDSCAPE_SIZE = (1280, 720)

_FONT_CANDIDATES = [
    PROJECT_ROOT / "assets" / "fonts" / "BeVietnamPro-Bold.ttf",
    PROJECT_ROOT / "assets" / "fonts" / "BeVietnamPro-Bold.otf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/seguisb.ttf"),
]


def resolve_thumbnail_font_path() -> Optional[Path]:
    """Return the first usable local bold font, preferring BeVietnamPro."""
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    # A final glob catches a BeVietnamPro file packaged with a variant suffix.
    fonts_dir = PROJECT_ROOT / "assets" / "fonts"
    if fonts_dir.exists():
        for candidate in sorted(fonts_dir.glob("BeVietnamPro*.ttf")):
            return candidate
    return None


def load_thumbnail_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = resolve_thumbnail_font_path()
    if font_path:
        return ImageFont.truetype(str(font_path), size=max(18, int(size)))
    logger.warning("No local bold font found for thumbnail; using PIL default font")
    return ImageFont.load_default()


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def wrap_thumbnail_text(
    text: str,
    *,
    size: Tuple[int, int] = PORTRAIT_SIZE,
    font_size: Optional[int] = None,
    max_lines: int = 3,
) -> Tuple[str, list[str], object, int]:
    """
    Wrap and shrink thumbnail text until every line fits the text panel.

    Returns ``(normalized_text, lines, font, fitted_font_size)``. The geometric
    guarantee used by tests is that every returned line's rendered width is no
    wider than the panel's usable width and the total block fits vertically.
    """
    normalized = " ".join(str(text or "").strip().split()) or "VIDEO MỚI"
    width, height = size
    panel_width = int(width * 0.88)
    usable_width = int(panel_width * 0.90)
    max_block_height = int(height * (0.20 if width > height else 0.19))

    probe = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(probe)
    start_size = font_size or (76 if width > height else 104)
    min_size = 26

    for candidate_size in range(int(start_size), min_size - 1, -2):
        font = load_thumbnail_font(candidate_size)
        words = normalized.split()
        lines: list[str] = []
        current = ""
        overflow = False

        for word in words:
            trial = f"{current} {word}".strip()
            if _text_bbox(draw, trial, font)[0] <= usable_width:
                current = trial
                continue
            if current:
                lines.append(current)
                current = ""
            # Break a single over-long word by characters.
            while word and _text_bbox(draw, word, font)[0] > usable_width:
                cut = max(1, len(word) - 1)
                while cut > 1 and _text_bbox(draw, word[:cut], font)[0] > usable_width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = word
            if len(lines) > max_lines:
                overflow = True
                break

        if current:
            lines.append(current)
        if overflow or len(lines) > max_lines:
            continue

        line_heights = [_text_bbox(draw, line, font)[1] for line in lines]
        spacing = max(6, candidate_size // 5)
        block_height = sum(line_heights) + spacing * max(0, len(lines) - 1)
        if block_height <= max_block_height and all(
            _text_bbox(draw, line, font)[0] <= usable_width for line in lines
        ):
            return normalized, lines, font, candidate_size

    # Last-resort truncation at the minimum size; still guarantees width fit.
    font = load_thumbnail_font(min_size)
    lines = []
    remaining = normalized
    while remaining and len(lines) < max_lines:
        cut = len(remaining)
        suffix = "…" if len(lines) == max_lines - 1 else ""
        while cut > 1 and _text_bbox(draw, remaining[:cut] + suffix, font)[0] > usable_width:
            cut -= 1
        lines.append(remaining[:cut] + suffix)
        remaining = remaining[cut:].strip()
        if not remaining:
            break
    return normalized, lines, font, min_size


def extract_video_frame(video_path: str | Path, output_path: str | Path, timestamp: float = 0.5) -> Optional[str]:
    """Extract an early video frame with FFmpeg when it is available."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not Path(video_path).exists():
        return None
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss",
            str(max(0.0, timestamp)),
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
        return str(output)
    return None


def _cover_rgb_image(source: Optional[str | Path], size: Tuple[int, int]) -> Image.Image:
    """Open/cover-crop a source image, or synthesize a warm paper backdrop."""
    if source and Path(source).exists():
        try:
            with Image.open(source) as opened:
                return ImageOps.fit(opened.convert("RGB"), size, method=Image.Resampling.LANCZOS)
        except Exception as exc:
            logger.warning(f"Could not open thumbnail source {source}: {exc}; using fallback backdrop")

    try:
        from styles.collage_broll.torn_paper_generator import TornPaperBackdropGenerator

        fallback = TornPaperBackdropGenerator(default_seed=42).generate_archival_forest_engraving(
            width=size[0], height=size[1], seed=42
        )
        return fallback.convert("RGB")
    except Exception as exc:
        logger.warning(f"Could not synthesize thumbnail backdrop: {exc}; using plain canvas")
        return Image.new("RGB", size, (36, 42, 54))


def _draw_gradient_overlay(base: Image.Image) -> Image.Image:
    """Darken the lower image area so the cream text panel reads cleanly."""
    width, height = base.size
    overlay = Image.new("L", (1, height))
    for y in range(height):
        ratio = y / max(1, height - 1)
        overlay.putpixel((0, y), int(28 + 92 * max(0.0, ratio - 0.45) / 0.55))
    alpha = overlay.resize((width, height))
    black = Image.new("RGB", (width, height), (12, 14, 20))
    return Image.composite(black, base, alpha.point(lambda p: int(p * 0.42)))


def create_thumbnail_image(
    output_path: str | Path,
    thumbnail_text: str,
    *,
    source_image_path: Optional[str | Path] = None,
    video_path: Optional[str | Path] = None,
    size: Tuple[int, int] = PORTRAIT_SIZE,
) -> str:
    """
    Create one thumbnail JPEG at ``output_path``.

    ``video_path`` is used to extract the hook frame when no explicit source
    image is supplied. A scene image can be provided directly by workers that
    already have a snapshot/hook frame on disk.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    source = source_image_path
    temp_frame: Optional[Path] = None
    if (not source or not Path(source).exists()) and video_path:
        temp_frame = output.parent / f".{output.stem}_frame.jpg"
        source = extract_video_frame(video_path, temp_frame) or source

    base = _draw_gradient_overlay(_cover_rgb_image(source, size))

    # Collage treatment: lay the same hook image inside a torn-paper sticker.
    if source and Path(source).exists():
        try:
            from styles.collage_broll.torn_paper_generator import TornPaperBackdropGenerator

            width, height = size
            sticker = TornPaperBackdropGenerator(default_seed=42).generate_torn_paper_backdrop(
                image_path=str(source),
                target_width=int(width * 0.84),
                target_height=int(height * (0.46 if height >= width else 0.48)),
                full_canvas_size=size,
                position_top=int(height * (0.07 if height >= width else 0.06)),
                seed=42,
            )
            base.paste(sticker, (0, 0), sticker)
        except Exception as exc:
            logger.warning(f"Torn-paper thumbnail framing failed: {exc}; keeping cover image")

    draw = ImageDraw.Draw(base, "RGBA")
    width, height = size
    _, lines, font, font_size = wrap_thumbnail_text(
        str(thumbnail_text or "VIDEO MỚI").upper(), size=size
    )

    panel_x0 = int(width * 0.06)
    panel_x1 = int(width * 0.94)
    panel_y1 = int(height * 0.93)
    spacing = max(6, font_size // 5)
    line_dimensions = [_text_bbox(draw, line, font) for line in lines]
    block_height = sum(h for _, h in line_dimensions) + spacing * max(0, len(lines) - 1)
    panel_y0 = max(int(height * 0.58), panel_y1 - block_height - int(height * 0.075))

    draw.rounded_rectangle(
        [panel_x0, panel_y0, panel_x1, panel_y1],
        radius=max(16, int(width * 0.025)),
        fill=(245, 239, 229, 246),
        outline=(52, 42, 34, 255),
        width=max(3, int(width * 0.004)),
    )

    y = panel_y0 + (panel_y1 - panel_y0 - block_height) // 2
    for line, (line_width, line_height) in zip(lines, line_dimensions):
        x = (width - line_width) // 2
        draw.text((x + 3, y + 3), line, font=font, fill=(245, 216, 90, 255))
        draw.text((x, y), line, font=font, fill=(36, 30, 25, 255))
        y += line_height + spacing

    base.save(output, "JPEG", quality=92)
    if temp_frame and temp_frame.exists():
        try:
            temp_frame.unlink()
        except OSError:
            pass
    return str(output)


def generate_job_thumbnails(
    output_dir: str | Path,
    thumbnail_text: str,
    *,
    source_image_path: Optional[str | Path] = None,
    video_path: Optional[str | Path] = None,
    video_format: str = "shorts",
) -> Dict[str, str]:
    """
    Generate the canonical portrait thumbnail and, for landscape jobs, the
    additional 1280x720 version. Both live beside ``final_video.mp4``.
    """
    out_dir = Path(output_dir)
    portrait = create_thumbnail_image(
        out_dir / "thumbnail.jpg",
        thumbnail_text,
        source_image_path=source_image_path,
        video_path=video_path,
        size=PORTRAIT_SIZE,
    )
    result = {
        "thumbnail_path": str(out_dir / "thumbnail.jpg"),
        "thumbnail_portrait_path": portrait,
        "thumbnail_text": " ".join(str(thumbnail_text or "").strip().split()),
        "thumbnail_font": str(resolve_thumbnail_font_path() or "PIL default"),
    }
    if str(video_format or "shorts").lower() == "landscape":
        landscape = create_thumbnail_image(
            out_dir / "thumbnail_landscape.jpg",
            thumbnail_text,
            source_image_path=source_image_path,
            video_path=video_path,
            size=LANDSCAPE_SIZE,
        )
        result["thumbnail_landscape_path"] = landscape
    return result
