"""
styles/collage_broll/torn_paper_generator.py

Procedural Torn Paper Backdrop Generator for Cinematic Collage Theatre (Requirement R2 & R6).
Generates authentic torn-edge archival backdrops with cellulose fiber fraying borders
and soft drop shadows using pure Pillow (PIL) and NumPy.

Strict constraint: Does NOT use OpenCV (cv2).
"""

import os
import math
import random
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps
from loguru import logger


class TornPaperBackdropGenerator:
    """
    Generates procedural torn paper archival backdrops for Layer 1 compositing.
    Features:
    - 4-edge procedural contour with 3-harmonic sinusoidal waves + random micro-jitter.
    - Linear corner attenuation window (B ≈ 25px) guaranteeing zero corner discontinuity.
    - Ivory white cellulose fiber border (#F5EFEB, 4-6px) via morphological min-filtering erosion.
    - Soft physical drop shadow (Gaussian blur 8, offset (8, 10), opacity 35%).
    - Automatic procedural fallback synthesizing an authentic antique primeval forest woodcut
      engraving with aged parchment tones and fine hatching lines when image_path is None or missing.
    - Positioning on full 1080x1920 canvas centered horizontally at top=180.
    """

    def __init__(self, default_seed: Optional[int] = None):
        self.default_seed = default_seed

    def _generate_edge_displacements(
        self,
        length: float,
        roughness: float,
        rng: np.random.RandomState,
        step: float = 2.0,
        corner_buffer: float = 25.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes sample coordinates along an edge and normal procedural displacements D(s).
        Uses 3-harmonic sine decomposition + random micro-jitter + corner attenuation window:
        D(s) = [sum(A_k * sin(2*pi*f_k*s/L + phi_k)) + U(-eps, eps)] * T(s)
        where T(s) = min(1.0, s / B, (L - s) / B) strictly ensures D(0) = D(L) = 0.
        """
        scale = max(0.1, roughness / 12.0)
        s_coords = np.arange(0.0, length + step * 0.5, step)
        if s_coords[-1] < length:
            s_coords = np.append(s_coords, length)
        s_coords[-1] = length

        # Harmonic 1: Macro-curvature (f in [1.0, 2.2], A in [4.0, 7.0] * scale)
        f1 = rng.uniform(1.0, 2.2)
        a1 = scale * rng.uniform(4.0, 7.0)
        p1 = rng.uniform(0.0, 2.0 * math.pi)

        # Harmonic 2: Mid-frequency tearing (f in [3.5, 6.5], A in [2.0, 4.0] * scale)
        f2 = rng.uniform(3.5, 6.5)
        a2 = scale * rng.uniform(2.0, 4.0)
        p2 = rng.uniform(0.0, 2.0 * math.pi)

        # Harmonic 3: Micro-creases (f in [10.0, 16.0], A in [1.0, 2.5] * scale)
        f3 = rng.uniform(10.0, 16.0)
        a3 = scale * rng.uniform(1.0, 2.5)
        p3 = rng.uniform(0.0, 2.0 * math.pi)

        wave = (
            a1 * np.sin(2.0 * math.pi * f1 * s_coords / length + p1) +
            a2 * np.sin(2.0 * math.pi * f2 * s_coords / length + p2) +
            a3 * np.sin(2.0 * math.pi * f3 * s_coords / length + p3)
        )

        # Random micro-jitter (+- 1.5px) simulating individual paper fiber tears
        jitter = rng.uniform(-1.5, 1.5, size=len(s_coords)) * min(scale, 1.5)

        # Corner attenuation window T(s)
        # Guarantees D(0) = 0 and D(length) = 0 so adjacent edges connect perfectly
        t_window = np.minimum(1.0, np.minimum(s_coords / corner_buffer, (length - s_coords) / corner_buffer))
        t_window = np.maximum(0.0, t_window)

        displacements = (wave + jitter) * t_window
        return s_coords, displacements

    def generate_torn_edge_contour(
        self,
        width: int,
        height: int,
        roughness: float = 12.0,
        pad: int = 50,
        seed: Optional[int] = None
    ) -> List[Tuple[float, float]]:
        """
        Generates a closed polygon representing a torn paper sheet of nominal size (width, height),
        offset by (pad, pad) inside a padded canvas.
        Returns a list of (x, y) tuples ordered clockwise.
        """
        rng = np.random.RandomState(seed if seed is not None else self.default_seed)
        W = float(width)
        H = float(height)

        # 1. Top Edge: from (pad, pad) to (pad + W, pad)
        s_top, d_top = self._generate_edge_displacements(W, roughness, rng)
        top_pts = [(pad + float(s), pad + float(d)) for s, d in zip(s_top, d_top)]

        # 2. Right Edge: from (pad + W, pad) to (pad + W, pad + H)
        s_right, d_right = self._generate_edge_displacements(H, roughness, rng)
        right_pts = [(pad + W + float(d), pad + float(s)) for s, d in zip(s_right, d_right)]

        # 3. Bottom Edge: from (pad + W, pad + H) to (pad, pad + H)
        s_bot, d_bot = self._generate_edge_displacements(W, roughness, rng)
        bot_pts = [(pad + W - float(s), pad + H + float(d)) for s, d in zip(s_bot, d_bot)]

        # 4. Left Edge: from (pad, pad + H) to (pad, pad)
        s_left, d_left = self._generate_edge_displacements(H, roughness, rng)
        left_pts = [(pad + float(d), pad + H - float(s)) for s, d in zip(s_left, d_left)]

        # Assemble clockwise polygon, omitting duplicate corner vertices
        polygon = []
        polygon.extend(top_pts[:-1])
        polygon.extend(right_pts[:-1])
        polygon.extend(bot_pts[:-1])
        polygon.extend(left_pts[:-1])
        return polygon

    def generate_archival_forest_engraving(
        self,
        width: int,
        height: int,
        seed: Optional[int] = 42
    ) -> Image.Image:
        """
        Procedurally synthesizes an authentic 19th-century primeval forest ("rừng già")
        botanical woodcut engraving with sepia tones, aged paper grain, and fine hatching lines.
        Used as automatic fallback when image_path is None or missing.
        """
        rng = np.random.RandomState(seed if seed is not None else 42)

        # Base antique paper canvas
        paper_tone = (241, 233, 218, 255)  # Warm cream / aged vellum
        img = Image.new("RGBA", (width, height), paper_tone)
        draw = ImageDraw.Draw(img)

        # Soft sepia vignette (darker towards corners)
        vignette = Image.new("L", (width, height), 0)
        v_draw = ImageDraw.Draw(vignette)
        cx, cy = width / 2.0, height / 2.0
        max_r = math.hypot(cx, cy)
        for r_step in range(12):
            r = max_r * (1.0 - r_step / 12.0)
            alpha_val = int(35 * (1.0 - r_step / 12.0))
            bbox = [cx - r, cy - r, cx + r, cy + r]
            v_draw.ellipse(bbox, fill=alpha_val)
        vignette_layer = Image.new("RGBA", (width, height), (160, 135, 105, 0))
        vignette_layer.putalpha(vignette)
        img = Image.alpha_composite(img, vignette_layer)
        draw = ImageDraw.Draw(img)

        # Ink colors for woodcut engraving
        dark_ink = (35, 28, 24, 235)      # Deep woodcut charcoal
        mid_sepia = (82, 68, 54, 210)     # Midtone sepia
        light_sepia = (135, 116, 95, 180) # Distant ridge / soft hatch
        forest_ink = (44, 52, 38, 225)    # Ancient deep woodland olive

        # 1. Sky Hatching (fine horizontal woodcut lines in upper 38% of canvas)
        sky_limit = int(height * 0.38)
        for y_line in range(25, sky_limit, 6):
            rel_y = y_line / sky_limit
            line_alpha = int(190 * (1.0 - rel_y * 0.75))
            stroke_col = (dark_ink[0], dark_ink[1], dark_ink[2], line_alpha)
            # Wavy horizontal stroke
            line_pts = []
            for x in range(20, width - 20, 12):
                wave_y = y_line + 1.2 * math.sin(x * 0.02 + y_line * 0.1)
                line_pts.append((x, wave_y))
            if len(line_pts) >= 2:
                draw.line(line_pts, fill=stroke_col, width=1)

        # 2. Celestial Light Halo (vintage radiant sun / moon etching behind canopy)
        sun_cx, sun_cy = int(width * 0.52), int(height * 0.22)
        sun_radius = 55
        for ray_angle in range(0, 360, 10):
            rad = math.radians(ray_angle)
            r_start = sun_radius + 4
            r_end = sun_radius + 24 + (ray_angle % 20) * 2
            x1 = sun_cx + r_start * math.cos(rad)
            y1 = sun_cy + r_start * math.sin(rad)
            x2 = sun_cx + r_end * math.cos(rad)
            y2 = sun_cy + r_end * math.sin(rad)
            draw.line([(x1, y1), (x2, y2)], fill=light_sepia, width=1)
        draw.ellipse([sun_cx - sun_radius, sun_cy - sun_radius, sun_cx + sun_radius, sun_cy + sun_radius],
                     outline=mid_sepia, width=1)

        # 3. Distant Mountain Ridges (layered background silhouettes with vertical hatching)
        for ridge_idx, (base_y_ratio, amp, freq, ridge_col) in enumerate([
            (0.42, 35.0, 0.006, light_sepia),
            (0.48, 45.0, 0.009, mid_sepia)
        ]):
            base_y = int(height * base_y_ratio)
            ridge_pts = [(0, height)]
            for x in range(0, width + 10, 10):
                y = base_y - amp * math.sin(x * freq + ridge_idx * 1.5) - (amp * 0.4) * math.cos(x * freq * 2.1)
                ridge_pts.append((x, y))
            ridge_pts.append((width, height))
            # Dense vertical hatching on mountain slopes
            for hx in range(30, width - 30, 4):
                hy_top = base_y - amp * math.sin(hx * freq + ridge_idx * 1.5) - (amp * 0.4) * math.cos(hx * freq * 2.1)
                draw.line([(hx, hy_top), (hx, hy_top + 30)], fill=(ridge_col[0], ridge_col[1], ridge_col[2], 120), width=1)

        # 4. Midground Primeval Ancient Trees (Majestic Oaks / Pines)
        tree_specs = [
            {"base_x": 0.18 * width, "top_x": 0.22 * width, "base_w": 58, "top_w": 28, "canopy_y": 0.14 * height},
            {"base_x": 0.82 * width, "top_x": 0.78 * width, "base_w": 64, "top_w": 32, "canopy_y": 0.12 * height},
            {"base_x": 0.46 * width, "top_x": 0.48 * width, "base_w": 46, "top_w": 22, "canopy_y": 0.18 * height},
            {"base_x": 0.33 * width, "top_x": 0.35 * width, "base_w": 32, "top_w": 16, "canopy_y": 0.22 * height},
            {"base_x": 0.66 * width, "top_x": 0.64 * width, "base_w": 34, "top_w": 18, "canopy_y": 0.20 * height}
        ]

        ground_y = int(height * 0.78)

        # Draw tree trunks and bark hatching
        for t in tree_specs:
            bx, tx = t["base_x"], t["top_x"]
            bw, tw = t["base_w"], t["top_w"]
            cy_tree = t["canopy_y"]

            # Trunk polygon
            trunk_poly = [
                (bx - bw * 0.6, ground_y + 30),
                (bx - bw * 0.4, ground_y),
                (tx - tw * 0.5, cy_tree),
                (tx + tw * 0.5, cy_tree),
                (bx + bw * 0.4, ground_y),
                (bx + bw * 0.6, ground_y + 30)
            ]
            draw.polygon(trunk_poly, fill=mid_sepia)

            # Woodcut bark texture: closely spaced vertical contour lines
            num_bark_lines = int(bw // 3.5)
            for bi in range(num_bark_lines):
                u = bi / max(1, num_bark_lines - 1)
                x_b = (bx - bw * 0.4) * (1.0 - u) + (bx + bw * 0.4) * u
                x_t = (tx - tw * 0.5) * (1.0 - u) + (tx + tw * 0.5) * u
                bark_pts = []
                for step_y in range(int(cy_tree), ground_y, 14):
                    factor = (step_y - cy_tree) / (ground_y - cy_tree)
                    x_mid = x_t * (1.0 - factor) + x_b * factor + math.sin(step_y * 0.08 + bi) * 1.5
                    bark_pts.append((x_mid, step_y))
                if len(bark_pts) >= 2:
                    draw.line(bark_pts, fill=dark_ink, width=1)

            # Prominent branches spreading outward
            for branch_dir in [-1.0, 1.0]:
                br_start_y = cy_tree + (ground_y - cy_tree) * rng.uniform(0.1, 0.45)
                factor = (br_start_y - cy_tree) / (ground_y - cy_tree)
                br_start_x = tx * (1.0 - factor) + bx * factor
                br_end_x = br_start_x + branch_dir * rng.uniform(60, 120)
                br_end_y = br_start_y - rng.uniform(30, 70)
                draw.line([(br_start_x, br_start_y), (br_end_x, br_end_y)], fill=dark_ink, width=4)
                # Sub-branch
                sub_end_x = br_end_x + branch_dir * rng.uniform(30, 60)
                sub_end_y = br_end_y - rng.uniform(15, 35)
                draw.line([(br_end_x, br_end_y), (sub_end_x, sub_end_y)], fill=dark_ink, width=2)

        # 5. Botanical Foliage Clusters (Canopy leaf clumps with woodcut hatching)
        for t in tree_specs:
            tx = t["top_x"]
            cy_tree = t["canopy_y"]
            num_clumps = 14
            for ci in range(num_clumps):
                clump_x = tx + rng.uniform(-110, 110)
                clump_y = cy_tree + rng.uniform(-50, 70)
                clump_r = rng.uniform(22, 42)
                # Clump base tone
                draw.ellipse(
                    [clump_x - clump_r, clump_y - clump_r * 0.75, clump_x + clump_r, clump_y + clump_r * 0.75],
                    fill=forest_ink
                )
                # Woodcut interior hatching arcs
                for arc_r in range(int(clump_r * 0.3), int(clump_r), 6):
                    bbox = [clump_x - arc_r, clump_y - arc_r * 0.7, clump_x + arc_r, clump_y + arc_r * 0.7]
                    draw.arc(bbox, start=160, end=350, fill=dark_ink, width=1)

        # 6. Forest Floor, Fallen Log & Botanical Flora
        # Earthen ground base
        ground_poly = [(0, ground_y), (width, ground_y), (width, height), (0, height)]
        draw.polygon(ground_poly, fill=(215, 202, 180, 255))

        # Horizontal soil hatching
        for gy in range(ground_y, height - 20, 5):
            hatch_pts = []
            for gx in range(25, width - 25, 15):
                hy = gy + math.sin(gx * 0.03) * 1.5
                hatch_pts.append((gx, hy))
            draw.line(hatch_pts, fill=mid_sepia, width=1)

        # Thematic Fallen Wood Log across forest floor
        log_x1, log_y1 = int(width * 0.25), int(height * 0.83)
        log_x2, log_y2 = int(width * 0.75), int(height * 0.86)
        log_thickness = 22
        # Log body
        draw.line([(log_x1, log_y1), (log_x2, log_y2)], fill=dark_ink, width=log_thickness)
        # Tree rings at cut end
        draw.ellipse([log_x1 - 12, log_y1 - 11, log_x1 + 12, log_y1 + 11], fill=mid_sepia, outline=dark_ink, width=2)
        draw.ellipse([log_x1 - 6, log_y1 - 6, log_x1 + 6, log_y1 + 6], outline=dark_ink, width=1)
        # Log cross-hatching
        for lx in range(log_x1 + 15, log_x2 - 10, 8):
            factor = (lx - log_x1) / (log_x2 - log_x1)
            ly = log_y1 * (1.0 - factor) + log_y2 * factor
            draw.line([(lx - 4, ly - 9), (lx + 4, ly + 9)], fill=dark_ink, width=1)

        # Foreground Victorian Botanical Ferns (left and right edges)
        for fern_side, fx_base in [(-1, 0.12 * width), (1, 0.88 * width)]:
            for fern_idx in range(4):
                f_angle = fern_side * (35 + fern_idx * 15)
                f_len = 110 + fern_idx * 18
                f_rad = math.radians(f_angle - 90)
                fx_end = fx_base + f_len * math.cos(f_rad)
                fy_end = ground_y + 45 + f_len * math.sin(f_rad)
                # Central frond stem
                draw.line([(fx_base, ground_y + 45), (fx_end, fy_end)], fill=dark_ink, width=2)
                # Pinnae (side leaflets)
                num_pinnae = 12
                for pi in range(1, num_pinnae):
                    u = pi / num_pinnae
                    px = fx_base * (1.0 - u) + fx_end * u
                    py = (ground_y + 45) * (1.0 - u) + fy_end * u
                    p_len = (1.0 - u * 0.6) * 22
                    for p_dir in [-1, 1]:
                        p_rad = f_rad + p_dir * math.radians(65)
                        draw.line([(px, py), (px + p_len * math.cos(p_rad), py + p_len * math.sin(p_rad))],
                                  fill=dark_ink, width=1)

        # 7. Archival Double Framing Border & Cartouche Plate
        border_pad = 22
        # Outer thin rule
        draw.rectangle([border_pad, border_pad, width - border_pad, height - border_pad],
                       outline=dark_ink, width=2)
        # Inner fine rule
        draw.rectangle([border_pad + 5, border_pad + 5, width - border_pad - 5, height - border_pad - 5],
                       outline=mid_sepia, width=1)
        # Corner accent flourishes
        for cx_b, cy_b in [
            (border_pad, border_pad),
            (width - border_pad, border_pad),
            (border_pad, height - border_pad),
            (width - border_pad, height - border_pad)
        ]:
            draw.ellipse([cx_b - 4, cy_b - 4, cx_b + 4, cy_b + 4], fill=dark_ink)

        # Archival plate inscription cartouche at bottom center
        label_w, label_h = 240, 20
        label_x = (width - label_w) // 2
        label_y = height - border_pad - 16
        draw.rectangle([label_x, label_y, label_x + label_w, label_y + label_h],
                       fill=paper_tone, outline=dark_ink, width=1)
        # Classic small text representation / line accent
        draw.line([(label_x + 15, label_y + 10), (label_x + label_w - 15, label_y + 10)],
                  fill=mid_sepia, width=1)
        draw.line([(label_x + 35, label_y + 6), (label_x + label_w - 35, label_y + 6)],
                  fill=dark_ink, width=1)

        # 8. Subtle Uncoated Paper Grain (monochromatic noise overlay)
        grain_arr = rng.normal(128, 14, (height, width)).astype(np.uint8)
        grain_img = Image.fromarray(grain_arr, mode="L")
        grain_layer = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        grain_layer.putalpha(grain_img.point(lambda p: int(abs(p - 128) * 0.4)))
        img = Image.alpha_composite(img, grain_layer)

        return img

    def generate_torn_paper_backdrop(
        self,
        image_path: Optional[str] = None,
        target_width: int = 860,
        target_height: int = 950,
        full_canvas_size: Optional[Tuple[int, int]] = (1080, 1920),
        position_top: int = 180,
        fiber_thickness: int = 5,
        fiber_color: Tuple[int, int, int, int] = (245, 239, 235, 255),
        shadow_offset: Tuple[int, int] = (8, 10),
        shadow_blur: int = 8,
        shadow_opacity: float = 0.35,
        roughness: float = 12.0,
        seed: Optional[int] = None
    ) -> Image.Image:
        """
        Main entry point. Generates a torn paper backdrop with:
        1. Procedural torn edge contour (multi-harmonic sine waves + random micro-jitter + corner window).
        2. Base torn polygon filled with ivory cellulose fiber color #F5EFEB (245, 239, 235).
        3. Inner image mask eroded by fiber_thickness (default 5px) via ImageFilter.MinFilter(11),
           exposing the raw cellulose fibers along all 4 jagged borders.
        4. Soft physical drop shadow (blur 8, offset (8, 10), opacity 35%).
        5. Procedural fallback antique woodcut engraving if image_path is None or missing.
        6. Centered horizontally at (1080 - 860) // 2 = 110, y = 180 on 1080x1920 canvas.
        """
        effective_seed = seed if seed is not None else self.default_seed

        # Generous padding to accommodate torn edge excursions, drop shadow offset and blur
        pad = max(50, shadow_blur * 4 + max(abs(shadow_offset[0]), abs(shadow_offset[1])))
        local_w = target_width + pad * 2
        local_h = target_height + pad * 2

        # Step 1: Generate procedural torn edge closed polygon
        polygon_pts = self.generate_torn_edge_contour(
            width=target_width,
            height=target_height,
            roughness=roughness,
            pad=pad,
            seed=effective_seed
        )

        # Step 2: Create binary paper mask
        paper_mask = Image.new("L", (local_w, local_h), 0)
        draw_mask = ImageDraw.Draw(paper_mask)
        draw_mask.polygon(polygon_pts, fill=255)

        # Step 3: Morphological erosion to create inner image mask
        # MinFilter(fiber_thickness * 2 + 1) erodes white mask by fiber_thickness pixels
        filter_kernel_size = max(3, int(fiber_thickness * 2 + 1))
        inner_mask = paper_mask.filter(ImageFilter.MinFilter(filter_kernel_size))

        # Step 4: Prepare the Inner Image (photograph or procedural engraving fallback)
        # Sized slightly larger than (target_width, target_height) so outward edge crests are covered
        img_margin = 30
        crop_w = target_width + img_margin * 2
        crop_h = target_height + img_margin * 2

        inner_content_img: Optional[Image.Image] = None
        if image_path is not None and os.path.isfile(image_path):
            try:
                with Image.open(image_path) as opened_img:
                    inner_content_img = opened_img.convert("RGBA")
            except Exception as e:
                logger.warning(f"Failed to load archival image from {image_path}: {e}. Using procedural woodcut fallback.")

        if inner_content_img is None:
            # High quality procedural woodcut fallback
            inner_content_img = self.generate_archival_forest_engraving(
                width=crop_w,
                height=crop_h,
                seed=effective_seed
            )
        else:
            # Aspect-ratio preserving cover crop to (crop_w, crop_h)
            src_w, src_h = inner_content_img.size
            target_aspect = crop_w / crop_h
            src_aspect = src_w / src_h

            if src_aspect > target_aspect:
                new_h = crop_h
                new_w = int(src_w * (crop_h / src_h))
            else:
                new_w = crop_w
                new_h = int(src_h * (crop_w / src_w))

            resized = inner_content_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - crop_w) // 2
            top = (new_h - crop_h) // 2
            inner_content_img = resized.crop((left, top, left + crop_w, top + crop_h))

        # Position inner image on local padded canvas centered with img_margin
        inner_canvas = Image.new("RGBA", (local_w, local_h), (0, 0, 0, 0))
        inner_canvas.paste(inner_content_img, (pad - img_margin, pad - img_margin))

        # Step 5: Base paper layer (cellulose fibers)
        base_paper = Image.new("RGBA", (local_w, local_h), fiber_color)
        # Monochromatic paper grain on cellulose border
        rng_local = np.random.RandomState(effective_seed if effective_seed is not None else 101)
        fiber_grain_arr = rng_local.normal(128, 10, (local_h, local_w)).astype(np.uint8)
        fiber_grain = Image.fromarray(fiber_grain_arr, mode="L")
        fiber_grain_layer = Image.new("RGBA", (local_w, local_h), (255, 255, 255, 0))
        fiber_grain_layer.putalpha(fiber_grain.point(lambda p: int(abs(p - 128) * 0.25)))
        base_paper = Image.alpha_composite(base_paper, fiber_grain_layer)

        # Step 6: Soft physical drop shadow
        shadow_mask = paper_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
        shadow_alpha = int(255 * max(0.0, min(1.0, shadow_opacity)))
        shadow_layer = Image.new("RGBA", (local_w, local_h), (0, 0, 0, shadow_alpha))

        # Step 7: Assemble local torn paper sticker
        sticker = Image.new("RGBA", (local_w, local_h), (0, 0, 0, 0))
        # 1. Shadow at offset
        sticker.paste(shadow_layer, shadow_offset, mask=shadow_mask)
        # 2. Base cellulose paper masked by full torn paper contour
        sticker.paste(base_paper, (0, 0), mask=paper_mask)
        # 3. Inner image masked by eroded mask, leaving exposed ivory border
        sticker.paste(inner_canvas, (0, 0), mask=inner_mask)

        # Step 8: Positioning on full canvas or return standalone sticker
        if full_canvas_size is not None:
            canvas_w, canvas_h = full_canvas_size
            # Center horizontally: (canvas_w - target_width) // 2
            x_target = (canvas_w - target_width) // 2
            y_target = position_top

            # The nominal top-left of the torn paper in local canvas is at (pad, pad).
            # To place nominal top-left at (x_target, y_target):
            paste_x = x_target - pad
            paste_y = y_target - pad

            full_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            full_canvas.paste(sticker, (paste_x, paste_y), mask=sticker)
            return full_canvas
        else:
            return sticker


def generate_torn_paper_backdrop(
    image_path: Optional[str] = None,
    target_width: int = 860,
    target_height: int = 950,
    full_canvas_size: Optional[Tuple[int, int]] = (1080, 1920),
    position_top: int = 180,
    fiber_thickness: int = 5,
    fiber_color: Tuple[int, int, int, int] = (245, 239, 235, 255),
    shadow_offset: Tuple[int, int] = (8, 10),
    shadow_blur: int = 8,
    shadow_opacity: float = 0.35,
    roughness: float = 12.0,
    seed: Optional[int] = None
) -> Image.Image:
    """
    Convenience function instantiating TornPaperBackdropGenerator and generating the backdrop.
    """
    generator = TornPaperBackdropGenerator()
    return generator.generate_torn_paper_backdrop(
        image_path=image_path,
        target_width=target_width,
        target_height=target_height,
        full_canvas_size=full_canvas_size,
        position_top=position_top,
        fiber_thickness=fiber_thickness,
        fiber_color=fiber_color,
        shadow_offset=shadow_offset,
        shadow_blur=shadow_blur,
        shadow_opacity=shadow_opacity,
        roughness=roughness,
        seed=seed
    )
