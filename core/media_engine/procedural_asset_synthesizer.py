"""
AutoVideoFactory — Procedural Asset Synthesizer
core/media_engine/procedural_asset_synthesizer.py

Tier 4 Procedural Asset Synthesizer: 100% offline procedural graphic generator.
Generates authentic, high-detail 19th-century editorial and archival engraving-style
illustrations directly into transparent RGBA images using Pillow.

Guarantees:
1. Zero crashes: Dimension clamping, safe font cascade, string sanitization.
2. Compliance: Strictly satisfies AssetContentValidator (0.08 <= transparent_ratio <= 0.95)
   and AlphaQAGate (0.08 <= opaque_ratio <= 0.85).
3. Rich visual quality: Multi-tone shading, copperplate hatching, specular glints,
   physical volumetric details, and archival cartouches/typography.
"""

import math
from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _get_safe_font(size: int = 14, bold: bool = False, prefer_serif: bool = True) -> ImageFont.ImageFont:
    """
    Zero-crash multi-tier font loader:
    Tier 1: OS TrueType fonts (Windows/Fonts or system font path).
    Tier 2: Pillow 10+ scalable FreeType font via ImageFont.load_default(size=size).
    Tier 3: Pillow legacy bitmap default font.
    """
    size = max(6, int(size))
    candidates = []
    if prefer_serif:
        if bold:
            candidates.extend(["timesbd.ttf", "georgiab.ttf", "arialbd.ttf", "times.ttf", "georgia.ttf", "arial.ttf"])
        else:
            candidates.extend(["georgia.ttf", "times.ttf", "arial.ttf", "calibri.ttf"])
    else:
        if bold:
            candidates.extend(["arialbd.ttf", "calibrib.ttf", "tahomabd.ttf", "arial.ttf", "timesbd.ttf"])
        else:
            candidates.extend(["arial.ttf", "calibri.ttf", "tahoma.ttf", "georgia.ttf"])

    win_fonts = Path("C:/Windows/Fonts")
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
        if win_fonts.exists():
            fp = win_fonts / name
            if fp.exists():
                try:
                    return ImageFont.truetype(str(fp), size)
                except Exception:
                    pass

    try:
        return ImageFont.load_default(size=size)
    except Exception:
        pass

    return ImageFont.load_default()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: Tuple[int, int, int, int],
    fill: Tuple[int, int, int, int],
    max_font_size: int = 22,
    min_font_size: int = 8,
    prefer_serif: bool = True,
    bold: bool = False
) -> None:
    """
    Renders text centered inside bounding box [x1, y1, x2, y2].
    Dynamically auto-shrinks font size to prevent overflow. Safe against empty/long strings.
    """
    if not text:
        return
    text_str = str(text).strip()
    if not text_str:
        return
    if len(text_str) > 60:
        text_str = text_str[:57] + "..."

    x1, y1, x2, y2 = box
    max_w = max(10, x2 - x1 - 4)
    max_h = max(6, y2 - y1 - 2)

    best_font = None
    best_w, best_h = 0, 0
    best_offset_x, best_offset_y = 0, 0

    for sz in range(int(max_font_size), int(min_font_size) - 1, -1):
        f = _get_safe_font(sz, bold=bold, prefer_serif=prefer_serif)
        try:
            bb = draw.textbbox((0, 0), text_str, font=f)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            if tw <= max_w and th <= max_h:
                best_font = f
                best_w, best_h = tw, th
                best_offset_x = bb[0]
                best_offset_y = bb[1]
                break
        except Exception:
            pass

    if best_font is None:
        best_font = _get_safe_font(min_font_size, bold=bold, prefer_serif=prefer_serif)
        try:
            bb = draw.textbbox((0, 0), text_str, font=best_font)
            best_w = bb[2] - bb[0]
            best_h = bb[3] - bb[1]
            best_offset_x = bb[0]
            best_offset_y = bb[1]
        except Exception:
            best_w = len(text_str) * 6
            best_h = 10
            best_offset_x = 0
            best_offset_y = 0

    tx = x1 + (x2 - x1 - best_w) // 2 - best_offset_x
    ty = y1 + (y2 - y1 - best_h) // 2 - best_offset_y
    draw.text((tx, ty), text_str, font=best_font, fill=fill)


def _draw_specular_glint(
    draw: ImageDraw.ImageDraw,
    center_xy: Tuple[int, int],
    radius_long: int = 18,
    radius_short: int = 3,
    flare_color: Tuple[int, int, int, int] = (255, 255, 255, 255)
) -> None:
    """Draws an authentic multi-point optical diamond star sparkle flare."""
    gx, gy = center_xy
    rl = max(4, int(radius_long))
    rs = max(1, int(radius_short))

    # Horizontal flare spike
    draw.polygon([
        (gx - rl, gy), (gx, gy - rs),
        (gx + rl, gy), (gx, gy + rs)
    ], fill=flare_color)
    # Vertical flare spike
    draw.polygon([
        (gx - rs, gy), (gx, gy - rl),
        (gx + rs, gy), (gx, gy + rl)
    ], fill=flare_color)
    # Diagonal micro spikes
    r_diag = max(2, int(rl * 0.45))
    draw.polygon([
        (gx - r_diag, gy - r_diag), (gx + 1, gy - 1),
        (gx + r_diag, gy + r_diag), (gx - 1, gy + 1)
    ], fill=flare_color)
    draw.polygon([
        (gx - r_diag, gy + r_diag), (gx - 1, gy - 1),
        (gx + r_diag, gy - r_diag), (gx + 1, gy + 1)
    ], fill=flare_color)
    # Central intense glowing core
    draw.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=(255, 255, 255, 255))


class ProceduralAssetSynthesizer:
    """
    Tier 4 Procedural Asset Synthesizer: 100% offline graphic generation engine.
    Produces authentic vintage engravings on transparent RGBA canvases.
    """
    MIN_DIMENSION: int = 60
    MAX_DIMENSION: int = 4096
    DEFAULT_SIZE: int = 512

    # Color Constants
    INK_DEEP = (36, 26, 16, 255)
    BRONZE_DARK = (115, 80, 22, 255)
    BRASS_CLASSIC = (185, 138, 32, 255)
    GOLD_POLISHED = (225, 178, 48, 255)
    CHAMPAGNE_SPEC = (255, 245, 205, 255)
    HATCH_INK = (75, 52, 20, 180)

    def __init__(self):
        pass

    @classmethod
    def _clamp_dimensions(cls, width: Union[int, float], height: Union[int, float]) -> Tuple[int, int]:
        """Safely normalizes and clamps canvas dimensions into [MIN_DIMENSION, MAX_DIMENSION],
        enforcing aspect ratio <= 2.2 to prevent isotropic letterboxing from exceeding 95% transparent ratio."""
        try:
            w = int(width)
            h = int(height)
        except (TypeError, ValueError, OverflowError):
            w = cls.DEFAULT_SIZE
            h = cls.DEFAULT_SIZE

        w = max(cls.MIN_DIMENSION, min(cls.MAX_DIMENSION, w))
        h = max(cls.MIN_DIMENSION, min(cls.MAX_DIMENSION, h))

        # Enforce maximum aspect ratio max(w, h) / min(w, h) <= 2.2
        # to ensure letterboxing never exceeds the 95% transparent threshold of AssetContentValidator
        min_dim = min(w, h)
        max_dim = max(w, h)
        if min_dim > 0 and (max_dim / min_dim) > 2.2:
            clamped_larger = int(min_dim * 2.2)
            if w > h:
                w = clamped_larger
            else:
                h = clamped_larger

        return w, h

    @staticmethod
    def get_alpha_metrics(image: Image.Image) -> Dict[str, float]:
        """Calculates transparent and opaque ratios according to project QA gates."""
        rgba = image.convert("RGBA")
        alpha_arr = np.array(rgba.getchannel("A"))
        total = alpha_arr.size
        if total == 0:
            return {"transparent_ratio": 1.0, "opaque_ratio": 0.0}
        trans_count = np.sum(alpha_arr < 128)
        opaque_count = np.sum(alpha_arr > 20)
        return {
            "transparent_ratio": float(trans_count) / float(total),
            "opaque_ratio": float(opaque_count) / float(total)
        }

    @classmethod
    def verify_compliance(cls, image: Image.Image) -> Tuple[bool, str]:
        """Verifies if an image satisfies both AssetContentValidator and AlphaQAGate bounds."""
        metrics = cls.get_alpha_metrics(image)
        tr = metrics["transparent_ratio"]
        op = metrics["opaque_ratio"]
        if tr < 0.08:
            return False, f"Solid background violation: transparent_ratio {tr:.4f} < 0.08"
        if tr > 0.95:
            return False, f"Empty image violation: transparent_ratio {tr:.4f} > 0.95"
        if op < 0.08:
            return False, f"AlphaQAGate empty violation: opaque_ratio {op:.4f} < 0.08"
        if op > 0.85:
            return False, f"AlphaQAGate not removed violation: opaque_ratio {op:.4f} > 0.85"
        return True, f"Compliant: trans={tr:.1%}, opaque={op:.1%}"

    def save_image(self, image: Image.Image, output_path: Union[str, Path]) -> Path:
        """Saves a PIL Image to disk, guaranteeing parent directory creation."""
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(p), format="PNG")
        return p

    # =========================================================================
    # Object 1: draw_scale
    # =========================================================================
    def draw_scale(
        self,
        width: int = 512,
        height: int = 512,
        save_path: Optional[Union[str, Path]] = None
    ) -> Image.Image:
        """
        Renders an authentic 19th-century Victorian brass/gold 2-pan balance scale.
        Includes stepped base plinth, turned column, truss beam, rider notches,
        degree index plate, pointer, and dual suspended pans with brass counterweights.
        """
        w, h = self._clamp_dimensions(width, height)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        s = min(w, h) / 512.0
        ox = (w - 512.0 * s) / 2.0
        oy = (h - 512.0 * s) / 2.0

        def pt(x: float, y: float) -> Tuple[int, int]:
            return int(ox + x * s), int(oy + y * s)

        cx = pt(256, 256)[0]

        ink = self.INK_DEEP
        dark_bronze = self.BRONZE_DARK
        brass = self.BRASS_CLASSIC
        gold = self.GOLD_POLISHED
        champagne = self.CHAMPAGNE_SPEC
        hatch_ink = self.HATCH_INK

        # 1. Base Plinth (Multi-Tiered Stepped Pedestal)
        # Bottom tier plinth
        b1 = [pt(256 - 95, 436)[0], pt(256 - 95, 436)[1], pt(256 + 95, 458)[0], pt(256 + 95, 458)[1]]
        d.rounded_rectangle(b1, radius=max(2, int(4 * s)), fill=dark_bronze, outline=ink, width=max(1, int(2 * s)))
        # Leveling feet
        d.rectangle([pt(256 - 88, 456)[0], pt(256 - 88, 456)[1], pt(256 - 72, 464)[0], pt(256 - 72, 464)[1]], fill=brass, outline=ink)
        d.rectangle([pt(256 + 72, 456)[0], pt(256 + 72, 456)[1], pt(256 + 88, 464)[0], pt(256 + 88, 464)[1]], fill=brass, outline=ink)
        # Middle tier
        b2 = [pt(256 - 75, 420)[0], pt(256 - 75, 420)[1], pt(256 + 75, 436)[0], pt(256 + 75, 436)[1]]
        d.rectangle(b2, fill=brass, outline=ink, width=max(1, int(2 * s)))
        # Molded dome
        b3 = [pt(256 - 52, 404)[0], pt(256 - 52, 404)[1], pt(256 + 52, 424)[0], pt(256 + 52, 424)[1]]
        d.ellipse(b3, fill=gold, outline=dark_bronze, width=max(1, int(2 * s)))

        # Base cross-hatching
        for bx in range(256 - 85, 256 + 85, 8):
            d.line([pt(bx, 438), pt(bx + 6, 456)], fill=hatch_ink, width=1)

        # 2. Turned Central Pillar
        col_w = max(3, int(9 * s))
        col_top = pt(256, 120)[1]
        col_bot = pt(256, 406)[1]
        d.rectangle([cx - col_w, col_top, cx, col_bot], fill=dark_bronze)
        d.rectangle([cx, col_top, cx + col_w, col_bot], fill=gold)
        d.line([(cx - col_w, col_top), (cx - col_w, col_bot)], fill=ink, width=max(1, int(2 * s)))
        d.line([(cx + col_w, col_top), (cx + col_w, col_bot)], fill=ink, width=max(1, int(2 * s)))
        d.line([(cx + max(1, int(2 * s)), col_top + int(10 * s)), (cx + max(1, int(2 * s)), col_bot - int(10 * s))], fill=champagne, width=max(1, int(2 * s)))
        for hy in range(120 + 20, 406 - 20, 10):
            d.line([(cx - col_w + 1, pt(256, hy)[1]), (cx - 1, pt(256, hy)[1])], fill=hatch_ink, width=1)

        # Balusters & Collars
        d.ellipse([pt(256 - 16, 388)[0], pt(256 - 16, 388)[1], pt(256 + 16, 406)[0], pt(256 + 16, 406)[1]], fill=brass, outline=ink, width=1)
        d.ellipse([pt(256 - 14, 252)[0], pt(256 - 14, 252)[1], pt(256 + 14, 274)[0], pt(256 + 14, 274)[1]], fill=gold, outline=ink, width=1)
        d.ellipse([pt(256 - 14, 136)[0], pt(256 - 14, 136)[1], pt(256 + 14, 152)[0], pt(256 + 14, 152)[1]], fill=brass, outline=ink, width=1)

        # Bearing & Acorn Finial
        d.rectangle([pt(256 - 16, 112)[0], pt(256 - 16, 112)[1], pt(256 + 16, 134)[0], pt(256 + 16, 134)[1]], fill=dark_bronze, outline=ink, width=max(1, int(2 * s)))
        finial_box = [pt(256 - 11, 78)[0], pt(256 - 11, 78)[1], pt(256 + 11, 104)[0], pt(256 + 11, 104)[1]]
        d.ellipse(finial_box, fill=gold, outline=ink, width=1)
        d.polygon([pt(256 - 4, 80), pt(256 + 4, 80), pt(256, 66)], fill=gold, outline=ink)

        # 3. Graduated Degree Index Arc & Pointer Needle
        idx_box = [pt(256 - 26, 145)[0], pt(256 - 26, 145)[1], pt(256 + 26, 176)[0], pt(256 + 26, 176)[1]]
        d.arc(idx_box, 20, 160, fill=dark_bronze, width=max(1, int(6 * s)))
        d.arc(idx_box, 20, 160, fill=(245, 240, 225, 255), width=max(1, int(4 * s)))
        for deg in range(40, 150, 15):
            rad = math.radians(deg)
            tx1 = cx + int(24 * s * math.cos(rad))
            ty1 = pt(256, 160)[1] + int(18 * s * math.sin(rad))
            tx2 = cx + int(20 * s * math.cos(rad))
            ty2 = pt(256, 160)[1] + int(14 * s * math.sin(rad))
            d.line([(tx1, ty1), (tx2, ty2)], fill=ink, width=1)
        d.polygon([pt(256 - 2, 124), pt(256 + 2, 124), pt(256, 173)], fill=ink)

        # 4. Symmetrical Equal-Arm Balance Beam
        beam_pts = [pt(70, 122), pt(256, 114), pt(442, 122), pt(256, 130)]
        d.polygon(beam_pts, fill=gold, outline=ink)
        d.line([pt(72, 121), pt(256, 115), pt(440, 121)], fill=champagne, width=max(1, int(2 * s)))
        d.ellipse([pt(256 - 10, 116)[0], pt(256 - 10, 116)[1], pt(256 + 10, 128)[0], pt(256 + 10, 128)[1]], fill=dark_bronze, outline=ink, width=1)
        d.ellipse([pt(256 - 3, 120)[0], pt(256 - 3, 120)[1], pt(256 + 3, 124)[0], pt(256 + 3, 124)[1]], fill=champagne)
        for rx in range(95, 420, 16):
            if abs(rx - 256) > 22:
                d.line([pt(rx, 116), pt(rx, 120)], fill=ink, width=1)
        d.ellipse([pt(66, 118)[0], pt(66, 118)[1], pt(78, 130)[0], pt(78, 130)[1]], fill=brass, outline=ink, width=1)
        d.ellipse([pt(434, 118)[0], pt(434, 118)[1], pt(446, 130)[0], pt(446, 130)[1]], fill=brass, outline=ink, width=1)

        # 5. Dual Suspended Pans & Cords
        pan_w = int(54 * s)
        pan_h = int(18 * s)
        cord_w = max(1, int(2 * s))

        # Left Pan Assembly
        hook_l = pt(72, 128)
        pan_l_cx, pan_l_cy = pt(75, 286)
        d.line([hook_l, (pan_l_cx - pan_w + int(6 * s), pan_l_cy - int(8 * s))], fill=dark_bronze, width=cord_w)
        d.line([hook_l, (pan_l_cx + pan_w - int(6 * s), pan_l_cy - int(8 * s))], fill=dark_bronze, width=cord_w)
        d.line([hook_l, (pan_l_cx, pan_l_cy + int(10 * s))], fill=brass, width=cord_w)
        pan_l_outer = [pan_l_cx - pan_w, pan_l_cy - pan_h, pan_l_cx + pan_w, pan_l_cy + pan_h]
        d.ellipse(pan_l_outer, fill=dark_bronze, outline=ink, width=max(1, int(2 * s)))
        pan_l_inner = [pan_l_cx - pan_w + int(4 * s), pan_l_cy - pan_h + int(3 * s), pan_l_cx + pan_w - int(4 * s), pan_l_cy + pan_h - int(5 * s)]
        d.ellipse(pan_l_inner, fill=gold, outline=dark_bronze, width=1)
        d.arc(pan_l_inner, 0, 180, fill=champagne, width=max(1, int(2 * s)))

        # Counterweights on Left Pan
        d.rectangle([pt(75 - 16, 286 - 24)[0], pt(75 - 16, 286 - 24)[1], pt(75 - 2, 286 - 4)[0], pt(75 - 2, 286 - 4)[1]], fill=brass, outline=ink, width=1)
        d.ellipse([pt(75 - 12, 286 - 28)[0], pt(75 - 12, 286 - 28)[1], pt(75 - 6, 286 - 22)[0], pt(75 - 6, 286 - 22)[1]], fill=gold, outline=ink)
        d.rectangle([pt(75 + 2, 286 - 18)[0], pt(75 + 2, 286 - 18)[1], pt(75 + 14, 286 - 4)[0], pt(75 + 14, 286 - 4)[1]], fill=brass, outline=ink, width=1)
        d.ellipse([pt(75 + 5, 286 - 21)[0], pt(75 + 5, 286 - 21)[1], pt(75 + 11, 286 - 16)[0], pt(75 + 11, 286 - 16)[1]], fill=gold, outline=ink)

        # Right Pan Assembly
        hook_r = pt(440, 128)
        pan_r_cx, pan_r_cy = pt(437, 286)
        d.line([hook_r, (pan_r_cx - pan_w + int(6 * s), pan_r_cy - int(8 * s))], fill=dark_bronze, width=cord_w)
        d.line([hook_r, (pan_r_cx + pan_w - int(6 * s), pan_r_cy - int(8 * s))], fill=dark_bronze, width=cord_w)
        d.line([hook_r, (pan_r_cx, pan_r_cy + int(10 * s))], fill=brass, width=cord_w)
        pan_r_outer = [pan_r_cx - pan_w, pan_r_cy - pan_h, pan_r_cx + pan_w, pan_r_cy + pan_h]
        d.ellipse(pan_r_outer, fill=dark_bronze, outline=ink, width=max(1, int(2 * s)))
        pan_r_inner = [pan_r_cx - pan_w + int(4 * s), pan_r_cy - pan_h + int(3 * s), pan_r_cx + pan_w - int(4 * s), pan_r_cy + pan_h - int(5 * s)]
        d.ellipse(pan_r_inner, fill=gold, outline=dark_bronze, width=1)
        d.arc(pan_r_inner, 0, 180, fill=champagne, width=max(1, int(2 * s)))

        if save_path:
            self.save_image(img, save_path)
        return img

    # =========================================================================
    # Object 2: draw_chemical_flask
    # =========================================================================
    def draw_chemical_flask(
        self,
        element_name: str = "Oxygen",
        formula: str = "O2",
        price: str = "$120",
        width: int = 512,
        height: int = 512,
        save_path: Optional[Union[str, Path]] = None
    ) -> Image.Image:
        """
        Renders an authentic 19th-century Erlenmeyer conical flask with liquid,
        curved meniscus, rising bubbles, volumetric graduation, and apothecary label.
        """
        w, h = self._clamp_dimensions(width, height)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        s = min(w, h) / 512.0
        ox = (w - 512.0 * s) / 2.0
        oy = (h - 512.0 * s) / 2.0

        def pt(x: float, y: float) -> Tuple[int, int]:
            return int(ox + x * s), int(oy + y * s)

        cx = pt(256, 256)[0]

        # Colors
        glass_ink = (48, 72, 95, 245)
        glass_fill = (220, 240, 252, 75)
        glass_spec = (255, 255, 255, 200)
        cork_fill = (168, 120, 72, 255)
        cork_dark = (105, 70, 36, 255)

        # Liquid color by element
        name_clean = str(element_name or "Oxygen").lower()
        form_clean = str(formula or "O2").lower()
        if "oxy" in name_clean or "o2" in form_clean:
            liq_top = (45, 155, 210, 215)
            liq_bot = (18, 78, 122, 235)
            meniscus_c = (150, 220, 255, 230)
        elif "hydro" in name_clean:
            liq_top = (40, 185, 140, 215)
            liq_bot = (15, 95, 70, 235)
            meniscus_c = (140, 245, 205, 230)
        elif "sulf" in name_clean or "gold" in name_clean:
            liq_top = (225, 165, 45, 215)
            liq_bot = (135, 90, 18, 235)
            meniscus_c = (255, 235, 150, 230)
        else:
            liq_top = (35, 145, 110, 215)
            liq_bot = (16, 82, 58, 235)
            meniscus_c = (145, 235, 195, 230)

        # 1. Natural Bark Cork Stopper
        cork_poly = [
            pt(256 - 42, 54),
            pt(256 + 42, 54),
            pt(256 + 36, 94),
            pt(256 - 36, 94)
        ]
        d.polygon(cork_poly, fill=cork_fill, outline=cork_dark, width=max(1, int(2 * s)))
        for cy_pos in [64, 74, 84]:
            d.line([pt(256 - 30, cy_pos), pt(256 - 8, cy_pos)], fill=cork_dark, width=1)
            d.line([pt(256 + 6, cy_pos), pt(256 + 30, cy_pos)], fill=cork_dark, width=1)

        # 2. Conical Flask Glass Body Outline
        neck_w = int(38 * s)
        neck_y1 = pt(256, 94)[1]
        neck_y2 = pt(256, 190)[1]
        base_w = int(152 * s)
        base_y = pt(256, 444)[1]

        outer_flask_poly = [
            (cx - neck_w, neck_y1),
            (cx + neck_w, neck_y1),
            (cx + neck_w, neck_y2),
            (cx + base_w, base_y),
            (cx - base_w, base_y),
            (cx - neck_w, neck_y2)
        ]
        d.polygon(outer_flask_poly, fill=glass_fill)

        # 3. Liquid Solution Fill & Meniscus
        y_surf = pt(256, 315)[1]
        w_surf = int(neck_w + (base_w - neck_w) * (315 - 190) / (444 - 190))
        liquid_poly = [
            (cx - w_surf, y_surf),
            (cx + w_surf, y_surf),
            (cx + base_w - int(6 * s), base_y - int(3 * s)),
            (cx - base_w + int(6 * s), base_y - int(3 * s))
        ]
        d.polygon(liquid_poly, fill=liq_top)
        d.polygon([
            (cx - int(w_surf * 0.9), pt(256, 390)[1]),
            (cx + int(w_surf * 0.9), pt(256, 390)[1]),
            (cx + base_w - int(6 * s), base_y - int(3 * s)),
            (cx - base_w + int(6 * s), base_y - int(3 * s))
        ], fill=liq_bot)

        # Concave Meniscus Curve
        meniscus_box = [cx - w_surf, y_surf - int(7 * s), cx + w_surf, y_surf + int(7 * s)]
        d.ellipse(meniscus_box, fill=liq_top, outline=glass_ink, width=1)
        d.arc(meniscus_box, 0, 180, fill=meniscus_c, width=max(1, int(2 * s)))

        # 4. Effervescent Bubbles
        bubble_data = [
            (-25, 410, 5), (15, 395, 4), (-8, 380, 6), (32, 365, 3),
            (-38, 350, 4), (0, 340, 5), (24, 330, 4), (-18, 325, 3),
            (45, 420, 4), (-50, 415, 5), (10, 430, 3), (-5, 400, 4)
        ]
        for bx_off, by_val, br in bubble_data:
            bx, by = pt(256 + bx_off, by_val)
            rad = max(2, int(br * s))
            d.ellipse([bx - rad, by - rad, bx + rad, by + rad], outline=(255, 255, 255, 190), fill=meniscus_c)
            d.point((bx - rad // 2, by - rad // 2), fill=(255, 255, 255, 255))

        # 5. Volumetric Graduation Tick Marks
        for ml, gy in [("500", 335), ("400", 360), ("300", 385), ("200", 410), ("100", 435)]:
            gw = int(neck_w + (base_w - neck_w) * (gy - 190) / (444 - 190))
            gx1 = cx - gw + int(8 * s)
            gx2 = gx1 + int(18 * s)
            d.line([(gx1, pt(256, gy)[1]), (gx2, pt(256, gy)[1])], fill=(240, 248, 255, 210), width=max(1, int(2 * s)))
            d.line([(gx1, pt(256, gy - 12)[1]), (gx1 + int(10 * s), pt(256, gy - 12)[1])], fill=(240, 248, 255, 160), width=1)

        # 6. Glass Outlines & Specular Highlight Streaks
        d.line([(cx - neck_w, neck_y1), (cx - neck_w, neck_y2), (cx - base_w, base_y)], fill=glass_ink, width=max(1, int(3 * s)))
        d.line([(cx + neck_w, neck_y1), (cx + neck_w, neck_y2), (cx + base_w, base_y)], fill=glass_ink, width=max(1, int(3 * s)))
        d.line([(cx - base_w, base_y), (cx + base_w, base_y)], fill=glass_ink, width=max(1, int(4 * s)))
        d.line([(cx - neck_w + int(6 * s), neck_y2), (cx - base_w + int(12 * s), base_y - int(4 * s))], fill=(255, 255, 255, 140), width=max(1, int(2 * s)))
        d.line([(cx - neck_w + int(4 * s), neck_y1 + int(10 * s)), (cx - neck_w + int(4 * s), neck_y2)], fill=glass_spec, width=max(1, int(2 * s)))
        d.line([(cx - neck_w + int(10 * s), neck_y2 + int(6 * s)), (cx - int(125 * s), base_y - int(15 * s))], fill=glass_spec, width=max(1, int(3 * s)))
        d.ellipse([pt(256 - 46, 86)[0], pt(256 - 46, 86)[1], pt(256 + 46, 102)[0], pt(256 + 46, 102)[1]], outline=glass_ink, fill=glass_fill, width=max(1, int(2 * s)))
        d.arc([pt(256 - 44, 88)[0], pt(256 - 44, 88)[1], pt(256 + 44, 98)[0], pt(256 + 44, 98)[1]], 190, 350, fill=glass_spec, width=max(1, int(2 * s)))

        # 7. Archival Apothecary Paper Label
        lbl_w = int(82 * s)
        lbl_h = int(45 * s)
        lbl_cy = pt(256, 380)[1]
        label_box = [cx - lbl_w, lbl_cy - lbl_h, cx + lbl_w, lbl_cy + lbl_h]
        d.rounded_rectangle(label_box, radius=max(2, int(3 * s)), fill=(248, 242, 226, 250), outline=(38, 28, 22, 255), width=max(1, int(2 * s)))
        inner_box = [cx - lbl_w + int(4 * s), lbl_cy - lbl_h + int(4 * s), cx + lbl_w - int(4 * s), lbl_cy + lbl_h - int(4 * s)]
        d.rectangle(inner_box, outline=(155, 105, 65, 200), width=1)

        # 8. Typographic Layout
        name_val = str(element_name or "Oxygen").upper()
        form_val = str(formula or "O2")
        price_val = str(price or "$120")

        _draw_centered_text(
            d, name_val,
            (label_box[0] + int(4 * s), lbl_cy - int(38 * s), label_box[2] - int(4 * s), lbl_cy - int(12 * s)),
            fill=(32, 25, 20, 255), max_font_size=max(9, int(15 * s)), min_font_size=8, bold=True, prefer_serif=True
        )
        _draw_centered_text(
            d, form_val,
            (label_box[0] + int(4 * s), lbl_cy - int(12 * s), label_box[2] - int(4 * s), lbl_cy + int(12 * s)),
            fill=(165, 42, 28, 255), max_font_size=max(8, int(13 * s)), min_font_size=7, bold=False, prefer_serif=True
        )
        _draw_centered_text(
            d, price_val,
            (label_box[0] + int(4 * s), lbl_cy + int(12 * s), label_box[2] - int(4 * s), lbl_cy + int(38 * s)),
            fill=(24, 92, 48, 255), max_font_size=max(8, int(12 * s)), min_font_size=7, bold=True, prefer_serif=False
        )

        if save_path:
            self.save_image(img, save_path)
        return img

    # =========================================================================
    # Object 3: draw_microscope
    # =========================================================================
    def draw_microscope(
        self,
        width: int = 512,
        height: int = 512,
        save_path: Optional[Union[str, Path]] = None
    ) -> Image.Image:
        """
        Renders an authentic 19th-century Victorian brass optical microscope.
        Includes japanned horseshoe foot, compass inclination knuckle, limb,
        substage gimbal mirror, mechanical stage with specimen slide and clips,
        optical body tube, draw-tube graduations, eyepiece, and dual objectives.
        """
        w, h = self._clamp_dimensions(width, height)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        s = min(w, h) / 512.0
        ox = (w - 512.0 * s) / 2.0
        oy = (h - 512.0 * s) / 2.0

        def pt(x: float, y: float) -> Tuple[int, int]:
            return int(ox + x * s), int(oy + y * s)

        cx = pt(246, 256)[0]

        ink = (32, 24, 22, 255)
        japanned_black = (34, 30, 32, 255)
        dark_bronze = (115, 82, 25, 255)
        brass = (188, 142, 34, 255)
        gold = (232, 185, 52, 255)
        champagne = (255, 246, 210, 255)
        hatch_ink = (75, 52, 20, 180)

        # 1. Cast-Iron Horseshoe Base (Japanned Black Finish)
        heel_box = [pt(246 - 88, 414)[0], pt(246 - 88, 414)[1], pt(246 + 88, 448)[0], pt(246 + 88, 448)[1]]
        d.ellipse(heel_box, fill=japanned_black, outline=ink, width=max(1, int(2 * s)))
        l_toe = [pt(246 - 96, 436)[0], pt(246 - 96, 436)[1], pt(246 - 60, 464)[0], pt(246 - 60, 464)[1]]
        d.rounded_rectangle(l_toe, radius=max(2, int(6 * s)), fill=japanned_black, outline=ink, width=max(1, int(2 * s)))
        r_toe = [pt(246 + 60, 436)[0], pt(246 + 60, 436)[1], pt(246 + 96, 464)[0], pt(246 + 96, 464)[1]]
        d.rounded_rectangle(r_toe, radius=max(2, int(6 * s)), fill=japanned_black, outline=ink, width=max(1, int(2 * s)))
        d.arc(heel_box, 190, 350, fill=dark_bronze, width=max(1, int(3 * s)))
        d.line([pt(246 - 92, 440), pt(246 - 64, 460)], fill=dark_bronze, width=max(1, int(2 * s)))
        d.line([pt(246 + 64, 460), pt(246 + 92, 440)], fill=dark_bronze, width=max(1, int(2 * s)))

        # 2. Brass Upright Pillar & Compass Inclination Joint
        d.rectangle([pt(246 - 16, 346)[0], pt(246 - 16, 346)[1], pt(246 + 16, 424)[0], pt(246 + 16, 424)[1]], fill=brass, outline=ink, width=max(1, int(2 * s)))
        d.line([pt(246 + 2, 350), pt(246 + 2, 420)], fill=gold, width=max(1, int(2 * s)))
        for hy in range(360, 420, 8):
            d.line([pt(246 - 14, hy), pt(246 - 4, hy)], fill=hatch_ink, width=1)
        knuckle_box = [pt(246 - 22, 336)[0], pt(246 - 22, 336)[1], pt(246 + 22, 374)[0], pt(246 + 22, 374)[1]]
        d.ellipse(knuckle_box, fill=brass, outline=ink, width=max(1, int(2 * s)))
        d.ellipse([pt(246 - 9, 347)[0], pt(246 - 9, 347)[1], pt(246 + 9, 363)[0], pt(246 + 9, 363)[1]], fill=dark_bronze, outline=ink, width=1)
        d.ellipse([pt(246 - 4, 351)[0], pt(246 - 4, 351)[1], pt(246 + 4, 359)[0], pt(246 + 4, 359)[1]], fill=champagne)

        # 3. Substage Swiveling Concave Mirror
        d.line([pt(246 - 8, 366), pt(246 - 38, 392)], fill=brass, width=max(1, int(3 * s)))
        mirror_box = [pt(246 - 62, 382)[0], pt(246 - 62, 382)[1], pt(246 - 24, 414)[0], pt(246 - 24, 414)[1]]
        d.ellipse(mirror_box, fill=dark_bronze, outline=ink, width=max(1, int(2 * s)))
        mirror_face = [pt(246 - 59, 385)[0], pt(246 - 59, 385)[1], pt(246 - 27, 411)[0], pt(246 - 27, 411)[1]]
        d.ellipse(mirror_face, fill=(215, 235, 248, 255), outline=ink, width=1)
        d.arc(mirror_face, 210, 360, fill=(255, 255, 255, 255), width=max(1, int(2 * s)))

        # 4. Heavy Curved Brass Limb (Arm)
        limb_pts = [
            pt(246 - 12, 346),
            pt(246 + 48, 300),
            pt(246 + 56, 210),
            pt(246 + 24, 176),
            pt(246 + 8, 184),
            pt(246 + 36, 220),
            pt(246 + 28, 294),
            pt(246 + 4, 346)
        ]
        d.polygon(limb_pts, fill=brass, outline=ink)
        d.line([pt(246 + 24, 178), pt(246 + 48, 220), pt(246 + 38, 296)], fill=gold, width=max(1, int(2 * s)))

        # 5. Blackened Mechanical Stage & Specimen Slide
        d.rectangle([pt(246 - 44, 292)[0], pt(246 - 44, 292)[1], pt(246 - 6, 310)[0], pt(246 - 6, 310)[1]], fill=brass, outline=ink, width=1)
        stage_box = [pt(246 - 84, 274)[0], pt(246 - 84, 274)[1], pt(246 + 52, 292)[0], pt(246 + 52, 292)[1]]
        d.rounded_rectangle(stage_box, radius=max(1, int(2 * s)), fill=japanned_black, outline=ink, width=max(1, int(2 * s)))
        d.line([pt(246 - 82, 276), pt(246 + 50, 276)], fill=dark_bronze, width=1)
        slide_box = [pt(246 - 56, 270)[0], pt(246 - 56, 270)[1], pt(246 + 24, 275)[0], pt(246 + 24, 275)[1]]
        d.rectangle(slide_box, fill=(235, 245, 255, 200), outline=(255, 255, 255, 240), width=1)
        d.ellipse([pt(246 - 22, 270)[0], pt(246 - 22, 270)[1], pt(246 - 10, 275)[0], pt(246 - 10, 275)[1]], outline=(180, 210, 230, 255), width=1)
        d.line([pt(246 - 54, 272), pt(246 - 38, 270)], fill=gold, width=max(1, int(2 * s)))
        d.line([pt(246 + 22, 272), pt(246 + 6, 270)], fill=gold, width=max(1, int(2 * s)))

        # 6. Optical Body Tube
        tube_x1 = pt(246 - 8, 136)[0]
        tube_x2 = pt(246 + 38, 136)[0]
        tube_y1 = pt(246, 136)[1]
        tube_y2 = pt(246, 246)[1]
        d.rectangle([tube_x1, tube_y1, cx + int(15 * s), tube_y2], fill=brass)
        d.rectangle([cx + int(15 * s), tube_y1, tube_x2, tube_y2], fill=dark_bronze)
        d.line([(tube_x1, tube_y1), (tube_x1, tube_y2)], fill=ink, width=max(1, int(2 * s)))
        d.line([(tube_x2, tube_y1), (tube_x2, tube_y2)], fill=ink, width=max(1, int(2 * s)))
        d.line([(cx + int(4 * s), tube_y1 + int(4 * s)), (cx + int(4 * s), tube_y2 - int(4 * s))], fill=champagne, width=max(1, int(3 * s)))
        for hx in [tube_x2 - int(6 * s), tube_x2 - int(3 * s)]:
            d.line([(hx, tube_y1 + int(10 * s)), (hx, tube_y2 - int(10 * s))], fill=hatch_ink, width=1)

        # Upper Sliding Draw-Tube
        dt_x1 = pt(246 - 2, 88)[0]
        dt_x2 = pt(246 + 32, 88)[0]
        dt_y1 = pt(246, 88)[1]
        dt_y2 = pt(246, 136)[1]
        d.rectangle([dt_x1, dt_y1, dt_x2, dt_y2], fill=gold, outline=ink, width=max(1, int(2 * s)))
        for my in range(88 + 8, 136 - 6, 6):
            d.line([(dt_x1 + 1, pt(246, my)[1]), (dt_x1 + int(6 * s), pt(246, my)[1])], fill=ink, width=1)

        # 7. Eyepiece (Ocular)
        d.rectangle([pt(246 - 4, 76)[0], pt(246 - 4, 76)[1], pt(246 + 34, 88)[0], pt(246 + 34, 88)[1]], fill=brass, outline=ink, width=1)
        eyecup_poly = [
            pt(246 - 2, 76),
            pt(246 + 32, 76),
            pt(246 + 28, 64),
            pt(246 + 2, 64)
        ]
        d.polygon(eyecup_poly, fill=japanned_black, outline=ink)
        d.ellipse([pt(246 + 5, 64)[0], pt(246 + 5, 64)[1], pt(246 + 25, 68)[0], pt(246 + 25, 68)[1]], fill=(200, 230, 250, 255), outline=ink)

        # 8. Revolving Nosepiece & Objectives
        d.rectangle([pt(246 - 12, 246)[0], pt(246 - 12, 246)[1], pt(246 + 34, 258)[0], pt(246 + 34, 258)[1]], fill=dark_bronze, outline=ink, width=1)
        obj1_box = [pt(246 - 4, 258)[0], pt(246 - 4, 258)[1], pt(246 + 14, 272)[0], pt(246 + 14, 272)[1]]
        d.rectangle(obj1_box, fill=gold, outline=ink, width=max(1, int(2 * s)))
        d.line([pt(246 - 4, 264), pt(246 + 14, 264)], fill=dark_bronze, width=1)
        d.line([pt(246 - 2, 271), pt(246 + 12, 271)], fill=(220, 240, 255, 255), width=1)
        obj2_poly = [
            pt(246 + 20, 256),
            pt(246 + 36, 264),
            pt(246 + 31, 273),
            pt(246 + 15, 265)
        ]
        d.polygon(obj2_poly, fill=brass, outline=ink)

        # 9. Focusing Knobs
        kw_cx, kw_cy = pt(246 + 52, 202)
        kw_r = int(20 * s)
        d.ellipse([kw_cx - kw_r, kw_cy - kw_r, kw_cx + kw_r, kw_cy + kw_r], fill=brass, outline=ink, width=max(1, int(2 * s)))
        d.ellipse([kw_cx - int(kw_r * 0.65), kw_cy - int(kw_r * 0.65), kw_cx + int(kw_r * 0.65), kw_cy + int(kw_r * 0.65)], fill=dark_bronze, outline=ink, width=1)
        d.ellipse([kw_cx - int(4 * s), kw_cy - int(4 * s), kw_cx + int(4 * s), kw_cy + int(4 * s)], fill=gold)
        for deg in range(0, 360, 30):
            rad = math.radians(deg)
            x1 = kw_cx + int(kw_r * 0.7 * math.cos(rad))
            y1 = kw_cy + int(kw_r * 0.7 * math.sin(rad))
            x2 = kw_cx + int(kw_r * math.cos(rad))
            y2 = kw_cy + int(kw_r * math.sin(rad))
            d.line([(x1, y1), (x2, y2)], fill=ink, width=1)

        fk_cx, fk_cy = pt(246 + 18, 152)
        fk_r = int(10 * s)
        d.ellipse([fk_cx - fk_r, fk_cy - fk_r, fk_cx + fk_r, fk_cy + fk_r], fill=gold, outline=ink, width=max(1, int(2 * s)))
        d.ellipse([fk_cx - int(3 * s), fk_cy - int(3 * s), fk_cx + int(3 * s), fk_cy + int(3 * s)], fill=champagne)

        if save_path:
            self.save_image(img, save_path)
        return img

    # =========================================================================
    # Object 4: draw_crystal
    # =========================================================================
    def draw_crystal(
        self,
        name: str = "Diamond",
        color: str = "cyan",
        width: int = 512,
        height: int = 512,
        save_path: Optional[Union[str, Path]] = None
    ) -> Image.Image:
        """
        Renders a 3D faceted mineral/gemstone crystal specimen.
        Includes table facet, star facets, kite/bezel facets, culet apex,
        specular ridge highlights, optical star glints, and museum archival plaque.
        """
        w, h = self._clamp_dimensions(width, height)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        s = min(w, h) / 512.0
        ox = (w - 512.0 * s) / 2.0
        oy = (h - 512.0 * s) / 2.0

        def pt(x: float, y: float) -> Tuple[int, int]:
            return int(ox + x * s), int(oy + y * s)

        c_lower = str(color or "cyan").lower().strip()
        if any(k in c_lower for k in ["carbon", "graphite", "black", "gray", "grey", "coal"]):
            c_highlight = (210, 220, 235, 255)
            c_mid = (115, 125, 140, 255)
            c_base = (70, 75, 88, 255)
            c_shadow = (42, 46, 56, 255)
            c_deep = (22, 25, 32, 255)
        elif any(k in c_lower for k in ["emerald", "green", "jade"]):
            c_highlight = (200, 252, 225, 255)
            c_mid = (65, 195, 125, 255)
            c_base = (30, 155, 90, 255)
            c_shadow = (18, 95, 55, 255)
            c_deep = (8, 50, 30, 255)
        elif any(k in c_lower for k in ["ruby", "red", "crimson", "garnet"]):
            c_highlight = (255, 205, 215, 255)
            c_mid = (235, 75, 105, 255)
            c_base = (195, 35, 65, 255)
            c_shadow = (125, 18, 38, 255)
            c_deep = (65, 8, 20, 255)
        elif any(k in c_lower for k in ["amethyst", "purple", "violet", "quartz"]):
            c_highlight = (245, 215, 255, 255)
            c_mid = (185, 105, 235, 255)
            c_base = (145, 65, 195, 255)
            c_shadow = (85, 30, 130, 255)
            c_deep = (45, 12, 75, 255)
        elif any(k in c_lower for k in ["amber", "gold", "yellow", "topaz", "pyrite"]):
            c_highlight = (255, 248, 200, 255)
            c_mid = (245, 195, 75, 255)
            c_base = (215, 155, 35, 255)
            c_shadow = (140, 95, 18, 255)
            c_deep = (80, 52, 10, 255)
        elif any(k in c_lower for k in ["sapphire", "blue", "lapis"]):
            c_highlight = (210, 230, 255, 255)
            c_mid = (75, 145, 240, 255)
            c_base = (35, 95, 205, 255)
            c_shadow = (18, 55, 135, 255)
            c_deep = (10, 28, 75, 255)
        else:  # Ice Cyan / Diamond
            c_highlight = (225, 250, 255, 255)
            c_mid = (115, 210, 240, 255)
            c_base = (65, 175, 215, 255)
            c_shadow = (25, 95, 135, 255)
            c_deep = (14, 55, 85, 255)

        c_ridge_light = (255, 255, 255, 220)
        c_ridge_dark = (25, 30, 42, 230)

        # Key 3D Vertices
        T = [pt(220, 95), pt(256, 90), pt(292, 95), pt(325, 120),
             pt(292, 145), pt(256, 150), pt(220, 145), pt(187, 120)]
        G_back = [pt(135, 185), pt(200, 175), pt(312, 175), pt(377, 185)]
        G_left = pt(90, 205)
        G_right = pt(422, 205)
        G_front = [pt(132, 225), pt(192, 235), pt(256, 240), pt(320, 235), pt(380, 225)]
        V_culet = pt(256, 355)

        # Base Back Body Fill
        back_poly = [G_left, G_back[0], G_back[1], G_back[2], G_back[3], G_right, V_culet]
        draw.polygon(back_poly, fill=c_shadow)

        # Upper Back Star Facets
        draw.polygon([T[0], T[1], G_back[1]], fill=c_mid)
        draw.polygon([T[1], T[2], G_back[2]], fill=c_base)
        draw.polygon([T[7], T[0], G_back[0]], fill=c_highlight)
        draw.polygon([T[2], T[3], G_back[3]], fill=c_shadow)

        # Lower Pavilion Main Facets
        draw.polygon([G_left, G_front[0], V_culet], fill=c_mid)
        draw.polygon([G_front[0], G_front[1], V_culet], fill=c_highlight)
        draw.polygon([G_front[1], G_front[2], V_culet], fill=c_base)
        draw.polygon([G_front[2], G_front[3], V_culet], fill=c_shadow)
        draw.polygon([G_front[3], G_front[4], V_culet], fill=c_deep)
        draw.polygon([G_front[4], G_right, V_culet], fill=c_deep)

        # Front Kite / Bezel Facets
        draw.polygon([T[7], G_left, G_front[0], T[6]], fill=c_highlight)
        draw.polygon([T[6], G_front[0], G_front[1], T[5]], fill=c_mid)
        draw.polygon([T[5], G_front[1], G_front[2], T[4]], fill=c_base)
        draw.polygon([T[4], G_front[2], G_front[3], T[3]], fill=c_shadow)
        draw.polygon([T[3], G_front[3], G_front[4], T[2]], fill=c_deep)
        draw.polygon([T[2], G_front[4], G_right, G_back[3]], fill=c_deep)

        # Front Star Facets
        draw.polygon([T[6], T[5], G_front[1]], fill=c_highlight)
        draw.polygon([T[5], T[4], G_front[2]], fill=c_mid)
        draw.polygon([T[4], T[3], G_front[3]], fill=c_shadow)

        # Table Facet
        draw.polygon(T, fill=c_highlight)

        # Engraved Hatching Lines on Shadow Pavilion Facets
        for hy in range(pt(256, 245)[1], pt(256, 350)[1], max(3, int(5 * s))):
            hx1 = int(ox + (256 + (hy - pt(256, 240)[1]) * 0.35) * s)
            hx2 = int(ox + (380 - (hy - pt(256, 225)[1]) * 0.75) * s)
            if hx1 < hx2:
                draw.line([(hx1, hy), (hx2, hy)], fill=(20, 25, 35, 140), width=1)

        # Crisp Facet Ridge Lines
        for i in range(len(T)):
            draw.line([T[i], T[(i + 1) % len(T)]], fill=c_ridge_light, width=max(1, int(2 * s)))
        for g_pt in [G_front[0], G_front[1]]:
            draw.line([g_pt, V_culet], fill=c_ridge_light, width=1)
        for g_pt in [G_front[2], G_front[3], G_front[4]]:
            draw.line([g_pt, V_culet], fill=c_ridge_dark, width=1)
        draw.line([G_left, V_culet], fill=c_ridge_light, width=max(1, int(2 * s)))
        draw.line([G_right, V_culet], fill=c_ridge_dark, width=max(1, int(2 * s)))

        # Specular Glints
        _draw_specular_glint(draw, T[7], radius_long=int(22 * s), radius_short=int(4 * s))
        _draw_specular_glint(draw, T[1], radius_long=int(15 * s), radius_short=int(3 * s))
        _draw_specular_glint(draw, G_front[0], radius_long=int(12 * s), radius_short=int(3 * s))

        # Museum Specimen Cartouche
        plaque_box = (pt(95, 395)[0], pt(95, 395)[1], pt(417, 472)[0], pt(417, 472)[1])
        draw.rectangle(plaque_box, fill=(246, 240, 226, 255), outline=(58, 46, 34, 255), width=max(1, int(2 * s)))
        inner_box = (plaque_box[0] + 4, plaque_box[1] + 4, plaque_box[2] - 4, plaque_box[3] - 4)
        draw.rectangle(inner_box, outline=(180, 145, 60, 200), width=1)

        # Corner Rivets
        for rx, ry in [(plaque_box[0] + 8, plaque_box[1] + 8), (plaque_box[2] - 8, plaque_box[1] + 8),
                       (plaque_box[0] + 8, plaque_box[3] - 8), (plaque_box[2] - 8, plaque_box[3] - 8)]:
            draw.ellipse([rx - 3, ry - 3, rx + 3, ry + 3], fill=(212, 168, 40, 255), outline=(90, 65, 15, 255), width=1)

        _draw_centered_text(
            draw, "MINERALOGICAL SPECIMEN",
            (plaque_box[0] + 12, plaque_box[1] + 6, plaque_box[2] - 12, plaque_box[1] + 24),
            fill=(75, 60, 48, 255), max_font_size=max(8, int(11 * s)), min_font_size=7, bold=True, prefer_serif=True
        )
        crystal_name = str(name or "Diamond").upper()
        _draw_centered_text(
            draw, crystal_name,
            (plaque_box[0] + 12, plaque_box[1] + 24, plaque_box[2] - 12, plaque_box[1] + 50),
            fill=(25, 20, 16, 255), max_font_size=max(11, int(18 * s)), min_font_size=9, bold=True, prefer_serif=True
        )
        subtext = "FORMULA: C • HARDNESS: 10 MOHS • CUBIC" if any(k in crystal_name.lower() for k in ["carbon", "diamond"]) else "SYSTEM: HEXAGONAL / ISOMETRIC • REFRACTIVE"
        _draw_centered_text(
            draw, subtext,
            (plaque_box[0] + 12, plaque_box[1] + 50, plaque_box[2] - 12, plaque_box[3] - 6),
            fill=(115, 95, 75, 255), max_font_size=max(7, int(10 * s)), min_font_size=6, bold=False, prefer_serif=False
        )

        if save_path:
            self.save_image(canvas, save_path)
        return canvas

    # =========================================================================
    # Object 5: draw_book
    # =========================================================================
    def draw_book(
        self,
        title: str = "ENCYCLOPEDIA",
        author: str = "BRITANNICA",
        width: int = 512,
        height: int = 512,
        save_path: Optional[Union[str, Path]] = None
    ) -> Image.Image:
        """
        Renders an antique leather-bound folio with convex spine, 5 raised gilded hubs,
        embossed borders, aged deckled vellum fore-edge, silk bookmark ribbon, and title cartouche.
        """
        w, h = self._clamp_dimensions(width, height)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        s = min(w, h) / 512.0
        ox = (w - 512.0 * s) / 2.0
        oy = (h - 512.0 * s) / 2.0

        def pt(x: float, y: float) -> Tuple[int, int]:
            return int(ox + x * s), int(oy + y * s)

        # Palette
        c_leather_base = (95, 30, 24, 255)
        c_leather_dark = (60, 18, 14, 255)
        c_leather_ridge = (125, 45, 35, 255)
        c_gold_leaf = (220, 170, 42, 255)
        c_gold_bright = (248, 215, 95, 255)
        c_gold_shadow = (140, 95, 18, 255)
        c_page_block = (244, 238, 222, 255)
        c_page_line = (195, 180, 155, 190)
        c_ribbon_base = (185, 28, 38, 255)
        c_ribbon_light = (235, 85, 95, 255)

        # 1. Deckled Fore-Edge (Parchment Paper Block on Right)
        f_x1, f_y1 = pt(415, 60)
        f_x2, f_y2 = pt(438, 452)
        draw.rectangle([f_x1, f_y1, f_x2, f_y2], fill=c_page_block, outline=(160, 140, 115, 255), width=1)
        for py in range(f_y1 + 4, f_y2 - 3, max(2, int(3 * s))):
            draw.line([(f_x1 + 1, py), (f_x2 - 2, py)], fill=c_page_line, width=1)
        draw.line([(f_x2, f_y1), (f_x2, f_y2)], fill=c_gold_shadow, width=max(1, int(2 * s)))

        # 2. Main Front Board
        b_x1, b_y1 = pt(135, 52)
        b_x2, b_y2 = pt(415, 460)
        draw.rectangle([b_x1, b_y1, b_x2, b_y2], fill=c_leather_base, outline=(45, 14, 10, 255), width=max(1, int(2 * s)))

        # 3. Spine
        sp_x1, sp_y1 = pt(75, 48)
        sp_x2, sp_y2 = pt(135, 464)
        draw.rectangle([sp_x1, sp_y1, pt(88, 464)[0], sp_y2], fill=c_leather_dark)
        draw.rectangle([pt(88, 48)[0], sp_y1, pt(112, 464)[0], sp_y2], fill=c_leather_ridge)
        draw.rectangle([pt(112, 48)[0], sp_y1, pt(126, 464)[0], sp_y2], fill=c_leather_base)
        draw.rectangle([pt(126, 48)[0], sp_y1, sp_x2, sp_y2], fill=c_leather_dark)

        # Headcap & Tailcap
        draw.ellipse([sp_x1, pt(75, 38)[1], sp_x2, pt(135, 54)[1]], fill=c_leather_base, outline=c_leather_dark, width=1)
        draw.ellipse([sp_x1, pt(75, 458)[1], sp_x2, pt(135, 474)[1]], fill=c_leather_dark, outline=(30, 8, 6, 255), width=1)

        # 4. Five Raised Spine Hubs
        for hy in [105, 175, 245, 315, 385]:
            hub_top = pt(75, hy - 6)[1]
            hub_bot = pt(135, hy + 6)[1]
            draw.rectangle([sp_x1, hub_top, sp_x2, hub_bot], fill=c_leather_ridge, outline=c_leather_dark, width=1)
            draw.line([(sp_x1 + 3, hub_top + 2), (sp_x2 - 3, hub_top + 2)], fill=c_gold_bright, width=max(1, int(1.5 * s)))
            draw.line([(sp_x1 + 3, hub_bot - 2), (sp_x2 - 3, hub_bot - 2)], fill=c_gold_shadow, width=max(1, int(1.5 * s)))
            cx_hub = (sp_x1 + sp_x2) // 2
            cy_hub = (hub_top + hub_bot) // 2
            draw.ellipse([cx_hub - 2, cy_hub - 2, cx_hub + 2, cy_hub + 2], fill=c_gold_leaf)

        # 5. Front Board Tooling
        blind_box = (pt(143, 60)[0], pt(143, 60)[1], pt(407, 452)[0], pt(407, 452)[1])
        draw.rectangle(blind_box, outline=c_leather_dark, width=max(1, int(2 * s)))

        gold_box = (pt(149, 66)[0], pt(149, 66)[1], pt(401, 446)[0], pt(401, 446)[1])
        draw.rectangle(gold_box, outline=c_gold_leaf, width=max(1, int(2.5 * s)))
        inner_gold_box = (gold_box[0] + 4, gold_box[1] + 4, gold_box[2] - 4, gold_box[3] - 4)
        draw.rectangle(inner_gold_box, outline=c_gold_shadow, width=1)

        # Arabesque Corner Flourishes
        for cx_corner, cy_corner in [(gold_box[0], gold_box[1]), (gold_box[2], gold_box[1]),
                                     (gold_box[0], gold_box[3]), (gold_box[2], gold_box[3])]:
            draw.ellipse([cx_corner - 4, cy_corner - 4, cx_corner + 4, cy_corner + 4], fill=c_gold_bright)

        # 6. Central Gilded Title Cartouche
        c_x1, c_y1 = pt(175, 140)
        c_x2, c_y2 = pt(375, 370)
        draw.rectangle([c_x1, c_y1, c_x2, c_y2], fill=c_leather_dark, outline=c_gold_leaf, width=max(1, int(2 * s)))
        draw.rectangle([c_x1 + 3, c_y1 + 3, c_x2 - 3, c_y2 - 3], outline=c_gold_shadow, width=1)

        _draw_centered_text(
            draw, "— TOMUS I —",
            (c_x1 + 8, c_y1 + 10, c_x2 - 8, c_y1 + 32),
            fill=c_gold_shadow, max_font_size=max(8, int(11 * s)), min_font_size=7, bold=True, prefer_serif=True
        )
        book_title = str(title or "ENCYCLOPEDIA").upper()
        _draw_centered_text(
            draw, book_title,
            (c_x1 + 8, c_y1 + 38, c_x2 - 8, c_y1 + 95),
            fill=c_gold_bright, max_font_size=max(12, int(22 * s)), min_font_size=9, bold=True, prefer_serif=True
        )
        mid_cx = (c_x1 + c_x2) // 2
        mid_cy = (c_y1 + c_y2) // 2 + 10
        draw.polygon([
            (mid_cx - 12, mid_cy), (mid_cx, mid_cy - 7),
            (mid_cx + 12, mid_cy), (mid_cx, mid_cy + 7)
        ], fill=c_gold_leaf, outline=c_gold_bright)

        book_author = str(author or "BRITANNICA").upper()
        _draw_centered_text(
            draw, book_author,
            (c_x1 + 8, c_y1 + 135, c_x2 - 8, c_y1 + 175),
            fill=c_gold_leaf, max_font_size=max(10, int(15 * s)), min_font_size=8, bold=True, prefer_serif=True
        )
        _draw_centered_text(
            draw, "EDINBURGH • MDCCLXVIII",
            (c_x1 + 8, c_y2 - 30, c_x2 - 8, c_y2 - 8),
            fill=c_gold_shadow, max_font_size=max(7, int(9 * s)), min_font_size=6, bold=False, prefer_serif=True
        )

        # 7. Crimson Silk Bookmark Ribbon
        ribbon_pts = [
            pt(115, 42), pt(122, 68), pt(162, 160), pt(225, 275),
            pt(305, 385), pt(345, 452), pt(352, 492)
        ]
        rw = max(8, int(16 * s))
        shadow_offset = int(4 * s)
        for i in range(len(ribbon_pts) - 1):
            p1 = (ribbon_pts[i][0] + shadow_offset, ribbon_pts[i][1] + shadow_offset)
            p2 = (ribbon_pts[i + 1][0] + shadow_offset, ribbon_pts[i + 1][1] + shadow_offset)
            draw.line([p1, p2], fill=(20, 8, 6, 90), width=rw)

        for i in range(len(ribbon_pts) - 1):
            draw.line([ribbon_pts[i], ribbon_pts[i + 1]], fill=c_ribbon_base, width=rw)
            draw.line([ribbon_pts[i], ribbon_pts[i + 1]], fill=c_ribbon_light, width=max(1, rw // 4))

        tip_x, tip_y = ribbon_pts[-1]
        half_w = rw // 2
        draw.polygon([
            (tip_x - half_w, tip_y),
            (tip_x, tip_y - max(4, int(10 * s))),
            (tip_x + half_w, tip_y)
        ], fill=(0, 0, 0, 0))

        if save_path:
            self.save_image(canvas, save_path)
        return canvas

    # =========================================================================
    # Object 6: draw_generic_symbol
    # =========================================================================
    def draw_generic_symbol(
        self,
        keyword: str = "prop",
        archetype: str = "specimen_scientific",
        width: int = 512,
        height: int = 512,
        save_path: Optional[Union[str, Path]] = None
    ) -> Image.Image:
        """
        Renders a dignified geometric academy crest/insignia tailored to archetype.
        Includes concentric guilloché frames, gold studs, botanical laurel wreath,
        radiant star crest, archetype-adaptive central charge, and parchment ribbon banner.
        """
        w, h = self._clamp_dimensions(width, height)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        s = min(w, h) / 512.0
        ox = (w - 512.0 * s) / 2.0
        oy = (h - 512.0 * s) / 2.0

        def pt(x: float, y: float) -> Tuple[int, int]:
            return int(ox + x * s), int(oy + y * s)

        cx, cy = pt(256, 230)
        R_outer = int(165 * s)
        R_mid = int(155 * s)
        R_inner = int(125 * s)

        c_gold = (218, 165, 32, 255)
        c_gold_light = (248, 220, 105, 255)
        c_bronze = (130, 90, 20, 255)
        c_navy = (22, 35, 60, 255)
        c_vellum = (248, 244, 232, 255)
        c_laurel = (48, 82, 54, 255)
        c_laurel_light = (92, 142, 98, 255)
        c_ink = (28, 24, 20, 255)

        # 1. Concentric Outer Guilloché Seal Rings
        draw.ellipse([cx - R_outer, cy - R_outer, cx + R_outer, cy + R_outer], fill=c_bronze, outline=c_gold, width=max(1, int(2 * s)))
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            bx = cx + int((R_outer - 5 * s) * math.cos(rad))
            by = cy + int((R_outer - 5 * s) * math.sin(rad))
            r_stud = max(2, int(2.5 * s))
            draw.ellipse([bx - r_stud, by - r_stud, bx + r_stud, by + r_stud], fill=c_gold_light)

        draw.ellipse([cx - R_mid, cy - R_mid, cx + R_mid, cy + R_mid], fill=c_navy, outline=c_gold, width=max(1, int(2 * s)))
        draw.ellipse([cx - R_inner, cy - R_inner, cx + R_inner, cy + R_inner], fill=c_vellum, outline=c_gold, width=max(1, int(2 * s)))

        # Sunburst Rays
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            rx2 = cx + int((R_inner - 2 * s) * math.cos(rad))
            ry2 = cy + int((R_inner - 2 * s) * math.sin(rad))
            draw.line([(cx, cy), (rx2, ry2)], fill=(210, 180, 130, 120), width=1)

        # 2. Flanking Laurel Wreath
        for deg in range(100, 260, 14):
            rad = math.radians(deg)
            lx = cx + int((R_outer + 12 * s) * math.cos(rad))
            ly = cy + int((R_outer + 12 * s) * math.sin(rad))
            draw.ellipse([lx - int(10 * s), ly - int(5 * s), lx + int(10 * s), ly + int(5 * s)], fill=c_laurel, outline=c_laurel_light, width=1)
        for deg in range(-80, 80, 14):
            rad = math.radians(deg)
            rx = cx + int((R_outer + 12 * s) * math.cos(rad))
            ry = cy + int((R_outer + 12 * s) * math.sin(rad))
            draw.ellipse([rx - int(10 * s), ry - int(5 * s), rx + int(10 * s), ry + int(5 * s)], fill=c_laurel, outline=c_laurel_light, width=1)

        knot_x, knot_y = pt(256, 385)
        draw.ellipse([knot_x - int(8 * s), knot_y - int(5 * s), knot_x + int(8 * s), knot_y + int(5 * s)], fill=c_gold, outline=c_bronze, width=1)

        # 3. Top Crest: 8-Pointed Star
        star_cx, star_cy = pt(256, 72)
        _draw_specular_glint(draw, (star_cx, star_cy), radius_long=int(20 * s), radius_short=int(5 * s), flare_color=c_gold_light)

        # 4. Central Charge (Archetype-Specific)
        arch_norm = str(archetype or "specimen_scientific").lower().strip()
        if "sci" in arch_norm or "specimen" in arch_norm or "bio" in arch_norm:
            r_orb = int(58 * s)
            draw.ellipse([cx - r_orb, cy - int(22 * s), cx + r_orb, cy + int(22 * s)], outline=c_navy, width=max(1, int(2 * s)))
            draw.ellipse([cx - int(22 * s), cy - r_orb, cx + int(22 * s), cy + r_orb], outline=c_navy, width=max(1, int(2 * s)))
            draw.line([(cx - r_orb, cy), (cx + r_orb, cy)], fill=c_bronze, width=1)
            draw.line([(cx, cy - r_orb), (cx, cy + r_orb)], fill=c_bronze, width=1)
            draw.ellipse([cx - int(10 * s), cy - int(10 * s), cx + int(10 * s), cy + int(10 * s)], fill=c_gold, outline=c_bronze, width=max(1, int(2 * s)))
        elif "lib" in arch_norm or "oxford" in arch_norm or "book" in arch_norm:
            bk_w, bk_h = int(45 * s), int(30 * s)
            draw.polygon([(cx - bk_w, cy - bk_h), (cx, cy - int(15 * s)), (cx, cy + bk_h), (cx - bk_w, cy + int(15 * s))], fill=c_vellum, outline=c_ink, width=max(1, int(2 * s)))
            draw.polygon([(cx + bk_w, cy - bk_h), (cx, cy - int(15 * s)), (cx, cy + bk_h), (cx + bk_w, cy + int(15 * s))], fill=c_vellum, outline=c_ink, width=max(1, int(2 * s)))
            draw.line([(cx - int(35 * s), cy - int(35 * s)), (cx + int(35 * s), cy + int(35 * s))], fill=c_bronze, width=max(1, int(2 * s)))
            draw.line([(cx + int(35 * s), cy - int(35 * s)), (cx - int(35 * s), cy + int(35 * s))], fill=c_bronze, width=max(1, int(2 * s)))
        elif "bank" in arch_norm or "teller" in arch_norm or "money" in arch_norm:
            draw.line([(cx - int(45 * s), cy - int(15 * s)), (cx + int(45 * s), cy - int(15 * s))], fill=c_gold, width=max(2, int(4 * s)))
            draw.line([(cx, cy - int(30 * s)), (cx, cy + int(35 * s))], fill=c_bronze, width=max(1, int(3 * s)))
            draw.ellipse([cx - int(55 * s), cy + int(10 * s), cx - int(35 * s), cy + int(20 * s)], fill=c_gold, outline=c_bronze)
            draw.ellipse([cx + int(35 * s), cy + int(10 * s), cx + int(55 * s), cy + int(20 * s)], fill=c_gold, outline=c_bronze)
        elif "hist" in arch_norm or "relic" in arch_norm:
            draw.polygon([(cx - int(50 * s), cy - int(10 * s)), (cx, cy - int(40 * s)), (cx + int(50 * s), cy - int(10 * s))], fill=c_vellum, outline=c_ink, width=max(1, int(2 * s)))
            for col_x in [-35, -12, 12, 35]:
                draw.line([(cx + int(col_x * s), cy - int(10 * s)), (cx + int(col_x * s), cy + int(30 * s))], fill=c_bronze, width=max(1, int(3 * s)))
            draw.rectangle([cx - int(55 * s), cy + int(30 * s), cx + int(55 * s), cy + int(38 * s)], fill=c_vellum, outline=c_ink, width=max(1, int(2 * s)))
        elif "ocean" in arch_norm or "geo" in arch_norm or "sea" in arch_norm:
            cr_r = int(55 * s)
            for deg in [0, 90, 180, 270]:
                rad = math.radians(deg)
                rad_l = math.radians(deg + 45)
                draw.polygon([
                    (cx, cy),
                    (cx + int(cr_r * math.cos(rad)), cy + int(cr_r * math.sin(rad))),
                    (cx + int(cr_r * 0.4 * math.cos(rad_l)), cy + int(cr_r * 0.4 * math.sin(rad_l)))
                ], fill=c_navy, outline=c_gold)
        elif "ind" in arch_norm or "social" in arch_norm:
            draw.ellipse([cx - int(42 * s), cy - int(42 * s), cx + int(42 * s), cy + int(42 * s)], fill=c_gold, outline=c_bronze, width=max(1, int(2 * s)))
            for deg in range(0, 360, 30):
                rad = math.radians(deg)
                gx = cx + int(42 * s * math.cos(rad))
                gy = cy + int(42 * s * math.sin(rad))
                draw.rectangle([gx - int(5 * s), gy - int(5 * s), gx + int(5 * s), gy + int(5 * s)], fill=c_bronze)
            draw.ellipse([cx - int(20 * s), cy - int(20 * s), cx + int(20 * s), cy + int(20 * s)], fill=c_vellum, outline=c_bronze, width=max(1, int(2 * s)))
        elif "lux" in arch_norm or "treasure" in arch_norm:
            draw.polygon([
                (cx - int(45 * s), cy + int(25 * s)), (cx - int(45 * s), cy - int(10 * s)),
                (cx - int(22 * s), cy + int(5 * s)), (cx, cy - int(25 * s)),
                (cx + int(22 * s), cy + int(5 * s)), (cx + int(45 * s), cy - int(10 * s)),
                (cx + int(45 * s), cy + int(25 * s))
            ], fill=c_gold, outline=c_bronze, width=max(1, int(2 * s)))
        else:
            draw.polygon([
                (cx - int(40 * s), cy - int(35 * s)), (cx + int(40 * s), cy - int(35 * s)),
                (cx + int(40 * s), cy + int(10 * s)), (cx, cy + int(45 * s)),
                (cx - int(40 * s), cy + int(10 * s))
            ], fill=c_navy, outline=c_gold, width=max(1, int(2 * s)))
            _draw_specular_glint(draw, (cx, cy), radius_long=int(16 * s), radius_short=int(4 * s), flare_color=c_gold_light)

        # 5. Lower Floating Parchment Ribbon Banner
        rb_y1, rb_y2 = pt(76, 396)[1], pt(436, 444)[1]
        draw.polygon([pt(110, 412), pt(135, 412), pt(135, 444)], fill=(120, 85, 45, 255))
        draw.polygon([pt(402, 412), pt(377, 412), pt(377, 444)], fill=(120, 85, 45, 255))
        draw.polygon([pt(76, 415), pt(120, 415), pt(120, 452), pt(76, 452), pt(92, 433)], fill=c_vellum, outline=c_bronze, width=1)
        draw.polygon([pt(436, 415), pt(392, 415), pt(392, 452), pt(436, 452), pt(420, 433)], fill=c_vellum, outline=c_bronze, width=1)

        c_banner_box = (pt(120, 396)[0], rb_y1, pt(392, 444)[0], rb_y2)
        draw.rectangle(c_banner_box, fill=c_vellum, outline=c_bronze, width=max(1, int(2 * s)))
        inner_banner = (c_banner_box[0] + 3, c_banner_box[1] + 3, c_banner_box[2] - 3, c_banner_box[3] - 3)
        draw.rectangle(inner_banner, outline=(210, 175, 100, 180), width=1)

        banner_text = str(keyword or "PROP").upper()
        _draw_centered_text(
            draw, banner_text,
            (c_banner_box[0] + 6, c_banner_box[1] + 4, c_banner_box[2] - 6, c_banner_box[3] - 4),
            fill=c_ink, max_font_size=max(11, int(18 * s)), min_font_size=8, bold=True, prefer_serif=True
        )

        if save_path:
            self.save_image(canvas, save_path)
        return canvas

    # =========================================================================
    # High-Level Keyword Router: synthesize
    # =========================================================================
    def synthesize(
        self,
        target_object: str,
        archetype: str = "specimen_scientific",
        width: int = 512,
        height: int = 512,
        save_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Image.Image:
        """
        High-level dispatcher for Tier 4 procedural generation.
        Maps any keyword query to the most appropriate authentic procedural drawing.
        Guarantees 100% offline generation success and strict alpha compliance.
        """
        target = str(target_object or "").lower().strip()

        # 1. Scales / Balance
        if any(k in target for k in ["scale", "balance", "weigh", "golden_scale", "pan"]):
            return self.draw_scale(width=width, height=height, save_path=save_path)

        # 2. Chemical Flask / Erlenmeyer / Liquids
        if any(k in target for k in ["flask", "chemical", "potion", "beaker", "erlenmeyer", "acid", "oxygen", "hydrogen", "solution", "reagent"]):
            element = kwargs.get("element_name")
            if not element:
                if "oxygen" in target:
                    element = "Oxygen"
                elif "hydrogen" in target:
                    element = "Hydrogen"
                elif "sulfur" in target:
                    element = "Sulfur"
                elif "gold" in target:
                    element = "Gold Reagent"
                else:
                    element = target.replace("_", " ").title() or "Oxygen"

            formula = kwargs.get("formula")
            if not formula:
                if "oxygen" in target:
                    formula = "O2"
                elif "hydrogen" in target:
                    formula = "H2"
                elif "sulfur" in target:
                    formula = "S8"
                elif "gold" in target:
                    formula = "Au(aq)"
                else:
                    formula = "O2"

            price = kwargs.get("price", "$120")
            return self.draw_chemical_flask(
                element_name=element,
                formula=formula,
                price=price,
                width=width,
                height=height,
                save_path=save_path
            )

        # 3. Microscope / Biology / Lenses
        if any(k in target for k in ["microscope", "biology", "specimen_lens", "optical", "magnif", "slide"]):
            return self.draw_microscope(width=width, height=height, save_path=save_path)

        # 4. Crystal / Diamond / Carbon / Gems
        if any(k in target for k in ["crystal", "diamond", "carbon", "gem", "mineral", "jewel", "emerald", "ruby", "sapphire", "amethyst", "topaz"]):
            name = kwargs.get("name")
            if not name:
                if "diamond" in target:
                    name = "Diamond"
                elif "carbon" in target:
                    name = "Carbon"
                elif "emerald" in target:
                    name = "Emerald"
                elif "ruby" in target:
                    name = "Ruby"
                elif "sapphire" in target:
                    name = "Sapphire"
                else:
                    name = target.replace("_", " ").title() or "Diamond"

            color = kwargs.get("color")
            if not color:
                if "carbon" in target:
                    color = "carbon"
                elif "emerald" in target:
                    color = "emerald"
                elif "ruby" in target:
                    color = "ruby"
                elif "sapphire" in target:
                    color = "sapphire"
                else:
                    color = "cyan"

            return self.draw_crystal(
                name=name,
                color=color,
                width=width,
                height=height,
                save_path=save_path
            )

        # 5. Book / Folio / Encyclopedia
        if any(k in target for k in ["book", "encyclopedia", "folio", "tome", "volume", "manuscript", "journal", "bryson"]):
            title = kwargs.get("title")
            if not title:
                if "bryson" in target:
                    title = "SHORT HISTORY"
                elif "encyclopedia" in target:
                    title = "ENCYCLOPEDIA"
                else:
                    title = target.replace("_", " ").title() or "ENCYCLOPEDIA"

            author = kwargs.get("author")
            if not author:
                if "bryson" in target:
                    author = "BILL BRYSON"
                else:
                    author = "BRITANNICA"

            return self.draw_book(
                title=title,
                author=author,
                width=width,
                height=height,
                save_path=save_path
            )

        # 6. Fallback Generic Symbol / Emblem
        kw = kwargs.get("keyword", target_object or "prop")
        return self.draw_generic_symbol(
            keyword=kw,
            archetype=archetype,
            width=width,
            height=height,
            save_path=save_path
        )
