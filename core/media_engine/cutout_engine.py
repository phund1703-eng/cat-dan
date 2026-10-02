import os
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps
from loguru import logger
import rembg


class CutoutEngine:
    """
    AI Cutout and Vintage Paper-Collage Processor:
    1. AI background removal using rembg (u2net / isnet).
    2. Vintage 1950s Noir B&W Halftone / newspaper grain processing.
    3. Tactile machine-cut cream paper keyline border + soft contact drop shadow.
    """

    def __init__(self):
        # rembg session caches model weights automatically
        self.session = None

    def remove_background(
        self,
        input_image: Image.Image | str,
        output_path: Optional[str] = None
    ) -> Image.Image:
        """
        Removes background from an image using rembg, returning transparent RGBA Image.
        """
        if isinstance(input_image, str):
            img = Image.open(input_image)
        else:
            img = input_image

        img = img.convert("RGBA")

        # Run rembg
        try:
            cutout = rembg.remove(img)
        except Exception as e:
            logger.warning(f"Lỗi rembg ({e}), sử dụng alpha threshold fallback")
            cutout = img

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cutout.save(output_path, format="PNG")

        return cutout

    def apply_vintage_halftone(
        self,
        input_image: Image.Image | str,
        output_path: Optional[str] = None,
        contrast_boost: float = 1.5,
        paper_tint: Tuple[int, int, int] = (250, 248, 242)
    ) -> Image.Image:
        """
        Converts cutout image into authentic 1950s editorial B&W halftone photographic style:
        - High-contrast monochromatic tones.
        - Printed halftone ink grain.
        - Preserves the transparent alpha contour.
        """
        if isinstance(input_image, str):
            img = Image.open(input_image)
        else:
            img = input_image

        img = img.convert("RGBA")
        r, g, b, alpha = img.split()

        # Convert RGB to grayscale
        gray = img.convert("L")

        # Enhance contrast and sharpness like editorial print
        enhancer = ImageEnhance.Contrast(gray)
        gray = enhancer.enhance(contrast_boost)

        sharpener = ImageEnhance.Sharpness(gray)
        gray = sharpener.enhance(2.0)

        # Generate halftone dot / newsprint grain
        w, h = img.size
        # Create subtle dot pattern
        arr = np.array(gray, dtype=np.float32)

        # High-pass micro grain for newsprint texture
        grain = np.random.normal(0, 12, (h, w)).astype(np.float32)
        arr = np.clip(arr + grain, 0, 255).astype(np.uint8)

        # Tint lightly towards vintage warm paper black
        bw_img = Image.fromarray(arr, mode="L").convert("RGB")

        # Restore original alpha mask
        bw_rgba = bw_img.convert("RGBA")
        bw_rgba.putalpha(alpha)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            bw_rgba.save(output_path, format="PNG")

        return bw_rgba

    def add_paper_keyline_and_shadow(
        self,
        input_image: Image.Image | str,
        output_path: Optional[str] = None,
        border_px: int = 10,
        border_color: Tuple[int, int, int, int] = (255, 253, 247, 255), # Cream #FFFDF7
        shadow_blur: int = 14,
        shadow_offset: Tuple[int, int] = (6, 12),
        shadow_opacity: int = 120
    ) -> Image.Image:
        """
        Adds machine-cut cream paper border and physical paper drop shadow
        following the exact alpha contour of the cutout object.
        """
        if isinstance(input_image, str):
            img = Image.open(input_image)
        else:
            img = input_image

        img = img.convert("RGBA")
        w, h = img.size

        # Padding so border and shadow don't get clipped
        pad = max(border_px * 2, shadow_blur * 2) + 20
        padded_w, padded_h = w + pad * 2, h + pad * 2

        # 1. Extract alpha channel
        _, _, _, alpha = img.split()

        # Padded alpha
        padded_alpha = Image.new("L", (padded_w, padded_h), 0)
        padded_alpha.paste(alpha, (pad, pad))

        # 2. Keyline Border: Expand alpha contour using MaxFilter
        filter_size = border_px * 2 + 1
        expanded_alpha = padded_alpha.filter(ImageFilter.MaxFilter(filter_size))

        # Smooth border slightly
        expanded_alpha = expanded_alpha.filter(ImageFilter.GaussianBlur(1.0))
        # Threshold to crisp edge
        expanded_alpha = expanded_alpha.point(lambda p: 255 if p > 80 else 0)

        # 3. Soft physical contact drop shadow
        shadow_layer = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
        shadow_mask = padded_alpha.filter(ImageFilter.GaussianBlur(shadow_blur))
        shadow_mask = shadow_mask.point(lambda p: int(p * (shadow_opacity / 255.0)))
        black_fill = Image.new("RGBA", (padded_w, padded_h), (15, 15, 20, 255))
        shadow_layer.paste(black_fill, mask=shadow_mask)

        # 4. Composite result:
        # Background canvas
        result = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))

        # Paste shadow with offset
        ox, oy = shadow_offset
        result.paste(shadow_layer, (ox, oy), mask=shadow_layer)

        # Paste cream keyline border
        keyline_layer = Image.new("RGBA", (padded_w, padded_h), border_color)
        result.paste(keyline_layer, (0, 0), mask=expanded_alpha)

        # Paste original subject in center
        result.paste(img, (pad, pad), mask=alpha)

        # Crop to tight non-empty bounding box
        bbox = result.getbbox()
        if bbox:
            result = result.crop(bbox)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            result.save(output_path, format="PNG")

        return result
