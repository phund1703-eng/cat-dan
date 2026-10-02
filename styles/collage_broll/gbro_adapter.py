import os
import sys
import math
import random
import subprocess
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageChops, ImageOps
from loguru import logger

# Add omni_scripts to path
omni_scripts_dir = Path(__file__).parent / "omni_scripts"
if str(omni_scripts_dir) not in sys.path:
    sys.path.insert(0, str(omni_scripts_dir))

try:
    from generate_video import generate_video, parse_and_validate_duration
except ImportError:
    generate_video = None

from .multi_layer_compositor import MultiLayerCollageCompositor, apply_paper_cutout_styling
from core.media_engine.motion_timeline_engine import MotionTimelineEngine
from styles.collage_broll.torn_paper_generator import TornPaperBackdropGenerator
from core.media_engine.paper_fx_engine import PaperFXEngine
try:
    from core.media_engine.asset_content_validator import AssetContentValidator
except ImportError:
    AssetContentValidator = None


def split_image_into_halves(
    target_image: Image.Image,
    split_axis: str = "vertical",
    angle_deg: Optional[float] = None,
    apply_styling: bool = True,
    compositor: Optional[MultiLayerCollageCompositor] = None
) -> Tuple[Image.Image, Image.Image]:
    """
    Toán tử Cắt đa chiều thuần túy cho BẤT KỲ ảnh PNG RGBA nào:
    1. Tìm bounding box của vật thể thực tế (alpha > 0).
    2. Hỗ trợ cắt dọc (vertical), cắt ngang (horizontal), hoặc góc chém bất kỳ (angle_deg).
    3. Tách làm 2 Image độc lập (part_1, part_2), tự động tính toán tâm hình học
       và natural_offset để khi ghép lại khớp đúng 100% vị trí ban đầu.
    4. Áp dụng viền kem giấy 9px (#FFFDF7) + bóng đổ vật lý 3D compositor.apply_paper_cutout_styling cho cả 2 mảnh mới sinh.
    Returns: (part_1, part_2)
    """
    img = target_image.convert("RGBA")
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return img.copy(), img.copy()

    w, h = img.size
    min_x, min_y, max_x, max_y = bbox
    xc = (min_x + max_x) / 2.0
    yc = (min_y + max_y) / 2.0

    # Xác định góc cắt (độ)
    if angle_deg is not None:
        cut_angle = float(angle_deg)
    elif str(split_axis).lower() in ["horizontal", "h"]:
        cut_angle = 90.0
    else:
        cut_angle = 0.0

    theta = np.radians(cut_angle)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    x = np.arange(w)
    y = np.arange(h)
    xx, yy = np.meshgrid(x, y)
    d = (xx - xc) * cos_t + (yy - yc) * sin_t

    m1 = Image.fromarray((d <= 0).astype(np.uint8) * 255, mode="L")
    m2 = Image.fromarray((d > 0).astype(np.uint8) * 255, mode="L")

    alpha_1 = ImageChops.multiply(alpha, m1)
    alpha_2 = ImageChops.multiply(alpha, m2)

    part_1 = img.copy()
    part_1.putalpha(alpha_1)
    bbox_1 = alpha_1.getbbox()
    if bbox_1:
        part_1 = part_1.crop(bbox_1)
        cx_1 = (bbox_1[0] + bbox_1[2]) / 2.0
        cy_1 = (bbox_1[1] + bbox_1[3]) / 2.0
    else:
        cx_1, cy_1 = w / 4.0, h / 2.0

    part_2 = img.copy()
    part_2.putalpha(alpha_2)
    bbox_2 = alpha_2.getbbox()
    if bbox_2:
        part_2 = part_2.crop(bbox_2)
        cx_2 = (bbox_2[0] + bbox_2[2]) / 2.0
        cy_2 = (bbox_2[1] + bbox_2[3]) / 2.0
    else:
        cx_2, cy_2 = 3.0 * w / 4.0, h / 2.0

    off_1 = (cx_1 - w / 2.0, cy_1 - h / 2.0)
    off_2 = (cx_2 - w / 2.0, cy_2 - h / 2.0)

    # 4. Áp dụng viền kem 3px và bóng đổ vật lý cho cả 2 mảnh
    if apply_styling:
        if compositor is None:
            compositor = MultiLayerCollageCompositor()
        part_1 = compositor.apply_paper_cutout_styling(part_1)
        part_2 = compositor.apply_paper_cutout_styling(part_2)

    part_1.natural_offset = off_1
    part_2.natural_offset = off_2
    return part_1, part_2


dynamic_sever_split = split_image_into_halves


def rotate_with_fixed_pivot(img: Image.Image, angle_deg: float, pivot_norm: Tuple[float, float] = (0.5, 1.0)) -> Tuple[Image.Image, int, int]:
    """
    Xoay ảnh quanh tâm neo pivot cố định (ví dụ chân đế [0.5, 1.0] của kính hiển vi).
    Tâm neo không bị dịch chuyển dù ở bất kỳ góc nghiêng nào.
    Returns: (rotated_canvas, pivot_canvas_x, pivot_canvas_y)
    """
    w, h = img.size
    p_x = int(w * pivot_norm[0])
    p_y = int(h * pivot_norm[1])
    diag = int(math.hypot(w, h) * 1.35)
    canvas = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    canvas.paste(img, (diag // 2 - p_x, diag // 2 - p_y), mask=img)
    rot_canvas = canvas.rotate(angle_deg, resample=Image.Resampling.BICUBIC)
    return rot_canvas, diag // 2, diag // 2


# =============================================================================
# BẢN ĐỒ PHONG CÁCH BỆ ĐỠ SÂN KHẤU (R2: SCENE_PROP_STYLE_MAP)
# =============================================================================
SCENE_PROP_STYLE_MAP: Dict[str, str] = {
    # Archetypes
    "specimen_scientific": "lab_bench",
    "oxford_library": "reading_desk",
    "bank_teller": "teller_counter",
    "historical_relic": "stone_plinth",
    "geography_ocean": "harbor_deck",
    "industrial_social": "classic_plinth",
    "conceptual_duel": "classic_plinth",
    "luxury_treasure": "display_plinth",
    "default": "classic_plinth",

    # Direct style keys
    "lab_bench": "lab_bench",
    "stone_plinth": "stone_plinth",
    "reading_desk": "reading_desk",
    "teller_counter": "teller_counter",
    "display_plinth": "display_plinth",
    "harbor_deck": "harbor_deck",
    "classic_plinth": "classic_plinth",

    # Prop name aliases
    "stone_pedestal": "stone_plinth",
    "book_table": "reading_desk",
    "flask_rack": "lab_bench",
    "weighing_plinth": "classic_plinth",
    "cash_counter": "teller_counter",
    "brass_counter": "teller_counter",
    "lab_table": "lab_bench",
    "carpenter_workbench": "classic_plinth",
}


def generate_scene_appropriate_prop(
    archetype_or_style: str = "default",
    target_width: int = 702,
    target_height: int = 310,
    outline_width: int = 9,
    shadow_offset: Tuple[int, int] = (12, 14),
    shadow_blur: int = 10,
    pad: int = 55,
    compositor: Optional[MultiLayerCollageCompositor] = None
) -> Image.Image:
    """
    Sinh bệ đỡ sân khấu (Context-Specific Stage Prop) thích ứng theo từng phân cảnh:
    - lab_bench: Bàn đá đen phòng thí nghiệm hóa học có vân đá granite.
    - stone_plinth: Bệ đá sa thạch/cẩm thạch cổ điển La Mã/Hy Lạp.
    - reading_desk: Bàn đọc sách gỗ gụ phủ da xanh thư viện Anh.
    - teller_counter: Quầy ngân hàng Victoria với chấn song và thanh ngang bằng đồng.
    - display_plinth: Bệ trưng bày nhung tím viền vàng sang trọng.
    - harbor_deck: Sàn ván gỗ bến cảng có đinh tán.
    - classic_plinth: Bệ gỗ tối giản cổ điển (fallback an toàn, không có ê-tô thợ mộc).
    """
    raw_w = max(300, int(target_width))
    raw_h = max(180, int(target_height))
    canvas = Image.new("RGBA", (raw_w, raw_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    style = SCENE_PROP_STYLE_MAP.get(str(archetype_or_style).lower().strip(), "classic_plinth")

    if style == "lab_bench":
        # 1. Bàn đá đen phòng thí nghiệm hóa học có vân đá granite
        top_y1 = max(4, int(raw_h * 0.08))
        top_y2 = max(top_y1 + 15, int(raw_h * 0.28))
        draw.rectangle([int(raw_w * 0.05), top_y1, int(raw_w * 0.95), top_y2], fill=(36, 40, 46, 255), outline=(20, 22, 26, 255), width=2)
        draw.rectangle([int(raw_w * 0.05) + 2, top_y1 + 2, int(raw_w * 0.95) - 2, min(top_y2 - 2, top_y1 + 6)], fill=(75, 82, 92, 255))
        rng = np.random.RandomState(42)
        for _ in range(160):
            gx = int(rng.randint(int(raw_w * 0.06), int(raw_w * 0.94)))
            gy = int(rng.randint(top_y1 + 2, max(top_y1 + 3, top_y2 - 2)))
            c = int(rng.choice([160, 200, 240, 15]))
            draw.point((gx, gy), fill=(c, c, c, 180))
        cab_y1 = top_y2
        cab_y2 = max(cab_y1 + 20, raw_h - 15)
        draw.rectangle([int(raw_w * 0.10), cab_y1, int(raw_w * 0.90), cab_y2], fill=(52, 58, 66, 255), outline=(26, 30, 35, 255), width=2)
        mid_y = int(cab_y1 + (cab_y2 - cab_y1) * 0.35)
        draw.line([(int(raw_w * 0.10), mid_y), (int(raw_w * 0.90), mid_y)], fill=(26, 30, 35, 255), width=2)
        draw.line([(raw_w // 2, mid_y), (raw_w // 2, cab_y2)], fill=(26, 30, 35, 255), width=2)
        draw.rectangle([raw_w // 2 - 45, int((cab_y1 + mid_y) / 2) - 3, raw_w // 2 - 15, int((cab_y1 + mid_y) / 2) + 3], fill=(190, 200, 210, 255))
        draw.rectangle([raw_w // 2 + 15, int((cab_y1 + mid_y) / 2) - 3, raw_w // 2 + 45, int((cab_y1 + mid_y) / 2) + 3], fill=(190, 200, 210, 255))
        draw.ellipse([raw_w // 2 - 30, int((mid_y + cab_y2) / 2) - 6, raw_w // 2 - 18, int((mid_y + cab_y2) / 2) + 6], fill=(190, 200, 210, 255))
        draw.ellipse([raw_w // 2 + 18, int((mid_y + cab_y2) / 2) - 6, raw_w // 2 + 30, int((mid_y + cab_y2) / 2) + 6], fill=(190, 200, 210, 255))

    elif style == "stone_plinth":
        # 2. Bệ đá sa thạch/cẩm thạch cổ điển La Mã/Hy Lạp
        t1_y1, t1_y2 = max(4, int(raw_h * 0.06)), max(15, int(raw_h * 0.16))
        t2_y1, t2_y2 = t1_y2, max(t1_y2 + 15, int(raw_h * 0.26))
        draw.rectangle([int(raw_w * 0.08), t1_y1, int(raw_w * 0.92), t1_y2], fill=(232, 224, 210, 255), outline=(160, 150, 132, 255), width=2)
        draw.rectangle([int(raw_w * 0.12), t2_y1, int(raw_w * 0.88), t2_y2], fill=(218, 208, 192, 255), outline=(160, 150, 132, 255), width=2)
        shaft_x1, shaft_x2 = int(raw_w * 0.16), int(raw_w * 0.84)
        shaft_y1 = t2_y2
        base_h = max(25, int(raw_h * 0.24))
        shaft_y2 = max(shaft_y1 + 20, raw_h - base_h)
        draw.rectangle([shaft_x1, shaft_y1, shaft_x2, shaft_y2], fill=(225, 217, 202, 255), outline=(155, 145, 128, 255), width=2)
        for fx in range(shaft_x1 + 18, shaft_x2 - 15, 20):
            draw.line([(fx, shaft_y1 + 4), (fx, shaft_y2 - 4)], fill=(185, 175, 158, 255), width=2)
            draw.line([(fx + 2, shaft_y1 + 4), (fx + 2, shaft_y2 - 4)], fill=(245, 240, 230, 255), width=1)
        b1_y1 = shaft_y2
        b1_y2 = int(shaft_y2 + base_h * 0.45)
        draw.rectangle([int(raw_w * 0.12), b1_y1, int(raw_w * 0.88), b1_y2], fill=(218, 208, 192, 255), outline=(160, 150, 132, 255), width=2)
        draw.rectangle([int(raw_w * 0.08), b1_y2, int(raw_w * 0.92), max(b1_y2 + 8, raw_h - 15)], fill=(205, 195, 178, 255), outline=(150, 140, 122, 255), width=2)

    elif style == "reading_desk":
        # 3. Bàn đọc sách gỗ gụ phủ da xanh thư viện Anh
        top_y1 = max(4, int(raw_h * 0.08))
        top_y2 = max(top_y1 + 25, int(raw_h * 0.28))
        draw.rectangle([int(raw_w * 0.05), top_y1, int(raw_w * 0.95), top_y2], fill=(85, 38, 22, 255), outline=(50, 20, 10, 255), width=2)
        draw.rectangle([int(raw_w * 0.10), top_y1 + 4, int(raw_w * 0.90), top_y2 - 4], fill=(32, 75, 50, 255), outline=(20, 50, 32, 255), width=1)
        draw.rectangle([int(raw_w * 0.11), top_y1 + 6, int(raw_w * 0.89), top_y2 - 6], outline=(218, 165, 32, 255), width=2)
        apron_h = max(15, int(raw_h * 0.16))
        draw.rectangle([int(raw_w * 0.18), top_y2, int(raw_w * 0.82), top_y2 + apron_h], fill=(70, 30, 16, 255), outline=(45, 18, 8, 255), width=2)
        leg_bottom = max(top_y2 + 20, raw_h - 15)
        draw.rectangle([int(raw_w * 0.12), top_y2, int(raw_w * 0.18), leg_bottom], fill=(75, 32, 18, 255), outline=(48, 18, 8, 255), width=2)
        draw.rectangle([int(raw_w * 0.82), top_y2, int(raw_w * 0.88), leg_bottom], fill=(75, 32, 18, 255), outline=(48, 18, 8, 255), width=2)
        stretcher_y = max(top_y2 + apron_h + 10, raw_h - 38)
        draw.rectangle([int(raw_w * 0.12), stretcher_y, int(raw_w * 0.88), stretcher_y + 12], fill=(62, 26, 14, 255), outline=(40, 15, 6, 255), width=1)

    elif style == "teller_counter":
        # 4. Quầy ngân hàng Victoria với chấn song và thanh ngang bằng đồng
        counter_y1 = max(40, int(raw_h * 0.38))
        counter_y2 = max(counter_y1 + 18, int(raw_h * 0.54))
        draw.rectangle([int(raw_w * 0.05), counter_y1, int(raw_w * 0.95), counter_y2], fill=(78, 45, 26, 255), outline=(45, 24, 12, 255), width=2)
        draw.rectangle([int(raw_w * 0.05) + 2, counter_y1 + 2, int(raw_w * 0.95) - 2, counter_y1 + 6], fill=(120, 72, 42, 255))
        counter_base = max(counter_y2 + 15, raw_h - 15)
        draw.rectangle([int(raw_w * 0.10), counter_y2, int(raw_w * 0.90), counter_base], fill=(62, 34, 18, 255), outline=(40, 20, 10, 255), width=2)
        draw.rectangle([int(raw_w * 0.15), counter_y2 + 8, int(raw_w * 0.46), max(counter_y2 + 15, raw_h - 25)], outline=(95, 55, 30, 255), width=2)
        draw.rectangle([int(raw_w * 0.54), counter_y2 + 8, int(raw_w * 0.85), max(counter_y2 + 15, raw_h - 25)], outline=(95, 55, 30, 255), width=2)
        rail_top = max(8, int(raw_h * 0.08))
        rail_bar_bottom = max(rail_top + 8, counter_y1 - 10)
        draw.rectangle([int(raw_w * 0.08), rail_top, int(raw_w * 0.92), rail_top + 8], fill=(212, 172, 55, 255), outline=(148, 115, 32, 255), width=1)
        draw.rectangle([int(raw_w * 0.08), rail_bar_bottom, int(raw_w * 0.92), counter_y1], fill=(212, 172, 55, 255), outline=(148, 115, 32, 255), width=1)
        for bx in range(int(raw_w * 0.10), int(raw_w * 0.90), 20):
            if int(raw_w * 0.42) <= bx <= int(raw_w * 0.58):
                continue
            draw.line([(bx, rail_top + 8), (bx, rail_bar_bottom)], fill=(195, 155, 45, 255), width=3)
            draw.line([(bx - 1, rail_top + 8), (bx - 1, rail_bar_bottom)], fill=(245, 210, 95, 255), width=1)
        arc_top = max(rail_top + 10, int(counter_y1 * 0.45))
        arc_bottom = max(arc_top + 8, counter_y1 - 4)
        draw.arc([int(raw_w * 0.40), arc_top, int(raw_w * 0.60), arc_bottom], start=180, end=360, fill=(212, 172, 55, 255), width=3)

    elif style == "display_plinth":
        # 5. Bệ trưng bày nhung tím viền vàng sang trọng
        cushion_x1, cushion_x2 = int(raw_w * 0.10), int(raw_w * 0.90)
        cushion_y1 = max(6, int(raw_h * 0.08))
        cushion_y2 = max(cushion_y1 + 25, int(raw_h * 0.36))
        draw.rectangle([cushion_x1, cushion_y1, cushion_x2, cushion_y2], fill=(78, 22, 90, 255), outline=(48, 10, 56, 255), width=2)
        mid_cy = (cushion_y1 + cushion_y2) // 2
        draw.polygon([(raw_w // 2, cushion_y1 + 4), (raw_w // 2 + 55, mid_cy), (raw_w // 2, cushion_y2 - 4), (raw_w // 2 - 55, mid_cy)], outline=(115, 45, 130, 160), width=1)
        draw.ellipse([raw_w // 2 - 4, mid_cy - 4, raw_w // 2 + 4, mid_cy + 4], fill=(235, 195, 60, 255))
        trim_h = max(10, int(raw_h * 0.06))
        draw.rectangle([int(raw_w * 0.08), cushion_y2, int(raw_w * 0.92), cushion_y2 + trim_h], fill=(225, 180, 45, 255), outline=(150, 115, 25, 255), width=2)
        ped_y1 = cushion_y2 + trim_h
        base_h = max(18, int(raw_h * 0.12))
        ped_y2 = max(ped_y1 + 20, raw_h - base_h - 15)
        draw.rectangle([int(raw_w * 0.12), ped_y1, int(raw_w * 0.88), ped_y2], fill=(48, 14, 56, 255), outline=(28, 8, 34, 255), width=2)
        plinth_bottom = max(ped_y2 + 8, raw_h - 15)
        draw.rectangle([int(raw_w * 0.08), ped_y2, int(raw_w * 0.92), plinth_bottom], fill=(215, 170, 40, 255), outline=(145, 110, 25, 255), width=2)

    elif style == "harbor_deck":
        # 6. Sàn ván gỗ bến cảng có đinh tán
        deck_x1, deck_x2 = int(raw_w * 0.04), int(raw_w * 0.96)
        draw.rectangle([deck_x1, 15, deck_x2, max(25, raw_h - 15)], fill=(112, 98, 82, 255), outline=(58, 48, 38, 255), width=2)
        plank_ys = [int(raw_h * 0.28), int(raw_h * 0.50), int(raw_h * 0.72)]
        for py in plank_ys:
            draw.line([(deck_x1, py), (deck_x2, py)], fill=(48, 40, 32, 255), width=3)
            for rx in [int(raw_w * 0.12), int(raw_w * 0.32), int(raw_w * 0.52), int(raw_w * 0.72), int(raw_w * 0.88)]:
                draw.ellipse([rx - 4, py - 10, rx + 4, py - 2], fill=(45, 48, 54, 255), outline=(24, 26, 30, 255))
                draw.point((rx - 1, py - 6), fill=(160, 170, 180, 255))
                draw.ellipse([rx - 4, py + 2, rx + 4, py + 10], fill=(45, 48, 54, 255), outline=(24, 26, 30, 255))
                draw.point((rx - 1, py + 6), fill=(160, 170, 180, 255))

    else:
        # 7. classic_plinth: Bệ gỗ tối giản cổ điển (fallback an toàn, không có ê-tô thợ mộc)
        top_x1 = int(raw_w * 0.06)
        top_x2 = int(raw_w * 0.94)
        top_y1 = max(6, int(raw_h * 0.08))
        top_y2 = max(top_y1 + 25, int(raw_h * 0.28))
        draw.rectangle([top_x1, top_y1, top_x2, top_y2], fill=(118, 74, 42, 255), outline=(62, 36, 16, 255), width=2)
        draw.rectangle([top_x1 + 2, top_y1 + 2, top_x2 - 2, top_y1 + 6], fill=(160, 108, 65, 255))
        draw.rectangle([top_x1 + 2, top_y2 - 6, top_x2 - 2, top_y2 - 2], fill=(55, 30, 14, 255))
        apron_h = max(18, int(raw_h * 0.16))
        draw.rectangle([int(raw_w * 0.14), top_y2, int(raw_w * 0.86), top_y2 + apron_h], fill=(98, 58, 30, 255), outline=(55, 30, 14, 255), width=2)
        leg_bottom = max(top_y2 + 20, raw_h - 15)
        draw.rectangle([int(raw_w * 0.14), top_y2, int(raw_w * 0.22), leg_bottom], fill=(85, 48, 25, 255), outline=(50, 26, 12, 255), width=2)
        draw.rectangle([int(raw_w * 0.78), top_y2, int(raw_w * 0.86), leg_bottom], fill=(85, 48, 25, 255), outline=(50, 26, 12, 255), width=2)
        base_y = max(top_y2 + apron_h + 10, raw_h - 40)
        draw.rectangle([int(raw_w * 0.14), base_y, int(raw_w * 0.86), base_y + 16], fill=(78, 42, 20, 255), outline=(48, 22, 10, 255), width=2)

    # Phủ hạt giấy thủ công (Monochromatic paper grain)
    rng = np.random.RandomState(42)
    noise_arr = rng.normal(128, 12, (raw_h, raw_w)).astype(np.uint8)
    noise_img = Image.fromarray(noise_arr, mode="L")
    grain_layer = Image.new("RGBA", (raw_w, raw_h), (255, 255, 255, 0))
    grain_layer.putalpha(noise_img.point(lambda p: int(abs(p - 128) * 0.25)))
    canvas = Image.alpha_composite(canvas, grain_layer)

    # Thêm viền giấy kem 9px (#FFFDF7) & Bóng đổ 3D
    if compositor is None:
        try:
            compositor = MultiLayerCollageCompositor()
        except Exception:
            compositor = None

    try:
        if compositor is not None:
            styled_prop = compositor.apply_paper_cutout_styling(
                canvas,
                outline_width=outline_width,
                shadow_offset=shadow_offset,
                shadow_blur=shadow_blur,
                pad=pad,
                shadow_alpha=120,
                outline_color=(255, 253, 247, 255)
            )
        else:
            styled_prop = apply_paper_cutout_styling(
                canvas,
                outline_width=outline_width,
                shadow_offset=shadow_offset,
                shadow_blur=shadow_blur,
                pad=pad,
                shadow_alpha=120,
                outline_color=(255, 253, 247, 255)
            )
        return styled_prop
    except Exception as e:
        logger.warning(f"Styling prop failed: {e}, returning unstyled canvas")
        return canvas


class GbroAdapter:
    """
    Adapter executing 100% of the gbro-collage-broll pipeline:
    - Prepares 5-layer surreal collage compositions via MultiLayerCollageCompositor.
    - Constructs Gate 3 stop-motion assembly motion prompt.
    - Calls Gemini Omni Flash (gemini-omni-flash-preview) via Interactions API.
    - Provides a true MultiLayerStopMotionAssembler (12 fps multi-layer stop-motion)
      whenever the video API is unavailable or quota is exceeded.
    """

    def __init__(self):
        self.api_key = (
            os.environ.get("GEMINI_API_KEY") or
            os.environ.get("GEMINI_API_KEY_1") or
            os.environ.get("GEMINI_API_KEY_2")
        )
        self.compositor = MultiLayerCollageCompositor()
        self.torn_generator = TornPaperBackdropGenerator()
        self.paper_fx_engine = PaperFXEngine(fps=12)
        self.validator = AssetContentValidator() if AssetContentValidator is not None else None

    def split_image_into_halves(
        self,
        target_image: Image.Image,
        split_axis: str = "vertical",
        apply_styling: bool = True
    ) -> Tuple[Image.Image, Image.Image]:
        """Phương thức adapter gọi toán tử cắt đôi ảnh tổng quát."""
        return split_image_into_halves(target_image, split_axis=split_axis, apply_styling=apply_styling, compositor=self.compositor)

    def build_gate3_motion_prompt(
        self,
        color_field: str,
        color_hex: str,
        assembly_order: str
    ) -> str:
        """
        Builds the standard Gate 3 stop-motion motion prompt from gbro specification.
        """
        clean_hex = color_hex.strip().lstrip("#")
        clean_order = assembly_order.strip() if assembly_order else "central background cardstock -> subject cutout -> physical accents"

        prompt = (
            f"Paper-collage stop-motion assembly, using Image 1 as the exact empty first frame and "
            f"Image 2 as the exact completed last frame. In one continuous locked-off vertical shot, "
            f"open on the empty flat {color_field} paper field. "
            f"Assemble the scene piece by piece with crisp physical stop-motion timing: {clean_order}. "
            f"End by holding the supplied completed composition. "
            f"Preserve the exact 9:16 framing, #{clean_hex} color field, colored cardstock accents, "
            f"uncoated paper grain, halftone dots, cream keylines, crisp cut edges and soft shadows. "
            f"Restrained tactile 2D paper craft only. "
            f"No scene cuts, no camera movement, no zoom, no morphing, no text, no sound."
        )
        return prompt

    def render_gbro_clip(
        self,
        still_image_path: str,
        color_field: str,
        color_hex: str,
        assembly_order: str,
        output_path: str,
        focal_sticker_path: Optional[str] = None,
        secondary_sticker_path: Optional[str] = None,
        layout_type: str = "hero_center",
        topic_domain: str = "general",
        has_hand: bool = False,
        has_camera: bool = False,
        duration: float = 5.0,
        work_dir: Optional[Path] = None,
        width: int = 1080,
        height: int = 1920
    ) -> str:
        """
        Renders a 5-second collage B-roll clip according to gbro protocol:
        1. Generates 5 discrete physical layers and final composite last-frame.png.
        2. Tries Gemini Omni Flash (gemini-omni-flash-preview).
        3. If unavailable, executes Multi-Layer Stop-Motion Assembler (12 fps).
        """
        if work_dir is None:
            work_dir = Path(output_path).parent / "gbro_frames"
        work_dir.mkdir(parents=True, exist_ok=True)

        # Step 2.1: Compose 5 discrete layers and the last-frame composite
        layer_dict = self.compositor.compose_scene(
            color_hex=color_hex,
            color_field=color_field,
            focal_sticker_path=focal_sticker_path,
            secondary_sticker_path=secondary_sticker_path,
            layout_type=layout_type,
            topic_domain=topic_domain,
            has_hand=has_hand,
            has_camera=has_camera,
            output_dir=work_dir,
            width=width,
            height=height
        )

        first_frame = layer_dict["layer_0_bg"]
        last_frame = layer_dict["last_frame"]

        # Step 2.2: Generate Gate 3 motion prompt
        motion_prompt = self.build_gate3_motion_prompt(
            color_field=color_field,
            color_hex=color_hex,
            assembly_order=assembly_order
        )

        # Step 2.3: Call Gemini Omni Flash if API key is present
        api_success = False
        if self.api_key and generate_video:
            try:
                logger.info("✨ [Gate 3 - Omni Flash] Gọi model gemini-omni-flash-preview sinh video stop-motion...")
                omni_out = str(work_dir / "omni_raw.mp4")
                generate_video(
                    prompt=motion_prompt,
                    api_key=self.api_key,
                    model="gemini-omni-flash-preview",
                    aspect_ratio="9:16",
                    duration=int(min(max(duration, 3.0), 10.0)),
                    image_path=[first_frame, last_frame],
                    output_path=omni_out,
                    strip_audio=True
                )
                if os.path.exists(omni_out) and os.path.getsize(omni_out) > 1000:
                    logger.success("🎉 Omni Flash đã xuất video stop-motion thành công!")
                    strip_cmd = [
                        "ffmpeg", "-y",
                        "-i", omni_out,
                        "-c:v", "copy",
                        "-an",
                        output_path
                    ]
                    subprocess.run(strip_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
                    api_success = True
            except Exception as e:
                logger.warning(f"⚠️ Omni Flash API không khả dụng hoặc bị giới hạn ({e}). Chuyển sang Multi-Layer Stop-Motion Assembler.")
                api_success = False

        # Step 3: Multi-Layer Stop-Motion Assembler
        if not api_success:
            logger.info("🛠️ [Multi-Layer Stop-Motion Assembler] Lắp ráp 5 tầng thị giác theo nhịp giật stop-motion 12fps...")
            self.assemble_multilayer_stopmotion(
                layers=layer_dict,
                output_path=output_path,
                duration=duration,
                width=width,
                height=height,
                temp_dir=work_dir / "stop_motion_frames"
            )

        return output_path

    def assemble_multilayer_stopmotion(
        self,
        layers: Dict[str, str],
        output_path: str,
        duration: float = 5.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 12,
        temp_dir: Optional[Path] = None
    ):
        """
        Executes genuine physical multi-layer stop-motion paper craft assembly:
        - 12 fps stepped timing.
        - 0.0s - 0.4s: Layer 0 (empty flat paper field).
        - 0.4s - 1.2s: Layer 1 (Perspective chessboard) drops into place with physical bounce.
        - 1.2s - 2.2s: Layer 3 (B&W Halftone characters) drop down onto chess squares.
        - 2.2s - 3.2s: Layer 4 (Giant manipulator hand) reaches down from top edge.
        - 3.2s - End: Layer 2 (Yellow lighting cone & Vintage camera) turns on / snaps in!
        - Hold completed composition to end with tactile paper grain micro-jitter.
        """
        if temp_dir is None:
            temp_dir = Path(output_path).parent / "sm_frames"
        temp_dir.mkdir(parents=True, exist_ok=True)

        l0_bg = Image.open(layers["layer_0_bg"]).convert("RGBA")
        l1_prop = Image.open(layers["layer_1_prop"]).convert("RGBA")
        l2_light = Image.open(layers["layer_2_lighting"]).convert("RGBA")
        l3_chars = Image.open(layers["layer_3_chars"]).convert("RGBA")
        l4_hand = Image.open(layers["layer_4_hand"]).convert("RGBA")
        last_composite = Image.open(layers["last_frame"]).convert("RGBA")

        total_frames = int(duration * fps)
        frame_paths = []

        # Discrete stop-motion step tables for snappy physical landings
        # Board drop steps from top:
        prop_steps = [-height, int(-height * 0.5), int(-height * 0.18), 16, -4, 0]
        # Chars drop steps from top:
        chars_steps = [-350, -120, 14, -3, 0]
        # Hand reach steps from top:
        hand_steps = [-450, -180, 20, -5, 0]

        for frame_idx in range(total_frames):
            t = frame_idx / fps
            frame_img = l0_bg.copy()

            # Phase 1: 0.0s - 0.4s -> Empty paper field
            if t < 0.4:
                pass

            # Phase 2: 0.4s - 1.2s -> Layer 1 (Chessboard) enters
            elif t < 1.2:
                step_i = min(len(prop_steps) - 1, int((t - 0.4) * 6))
                oy = prop_steps[step_i]
                p_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                p_canvas.paste(l1_prop, (0, oy), mask=l1_prop)
                frame_img.paste(p_canvas, (0, 0), mask=p_canvas)

            # Phase 3: 1.2s - 2.2s -> Board in place, Layer 3 (Characters) enter
            elif t < 2.2:
                frame_img.paste(l1_prop, (0, 0), mask=l1_prop)

                step_i = min(len(chars_steps) - 1, int((t - 1.2) * 5))
                oy = chars_steps[step_i]
                c_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                c_canvas.paste(l3_chars, (0, oy), mask=l3_chars)
                frame_img.paste(c_canvas, (0, 0), mask=c_canvas)

            # Phase 4: 2.2s - 3.2s -> Board and Chars in place, Layer 4 (Giant Hand) enters
            elif t < 3.2:
                frame_img.paste(l1_prop, (0, 0), mask=l1_prop)
                frame_img.paste(l3_chars, (0, 0), mask=l3_chars)

                step_i = min(len(hand_steps) - 1, int((t - 2.2) * 5))
                oy = hand_steps[step_i]
                h_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                h_canvas.paste(l4_hand, (0, oy), mask=l4_hand)
                frame_img.paste(h_canvas, (0, 0), mask=h_canvas)

            # Phase 5: 3.2s - End -> All 5 layers complete! Light cone on, holding composition
            else:
                # Add subtle paper stop-motion breathing (micro tactile jitter ±1px)
                shift_x = random.choice([-1, 0, 1]) if (frame_idx % 2 == 0) else 0
                shift_y = random.choice([-1, 0, 1]) if (frame_idx % 3 == 0) else 0
                frame_img.paste(last_composite, (shift_x, shift_y), mask=last_composite)

            frame_file = temp_dir / f"frame_{frame_idx:04d}.png"
            frame_img.convert("RGB").save(str(frame_file))
            frame_paths.append(str(frame_file))

        # Encode frames into MP4 with FFmpeg at 12 fps stop-motion
        input_pattern = str(temp_dir / "frame_%04d.png")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-r", str(fps),
            "-i", input_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            output_path
        ]
        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            logger.success(f"✅ Multi-Layer Stop-Motion Assembler đã tạo video 12fps thành công: {output_path}")
        except Exception as e:
            logger.error(f"Lỗi FFmpeg assemble frames: {e}")
            raise

        for p in frame_paths:
            try:
                os.remove(p)
            except OSError:
                pass

    def render_universal_artwork_clip(
        self,
        artwork_path: str,
        color_hex: str,
        color_field: str,
        topic_domain: str,
        output_path: str,
        has_hand: bool = False,
        has_camera: bool = False,
        duration: float = 5.0,
        work_dir: Optional[Path] = None,
        width: int = 1080,
        height: int = 1920,
        fps: int = 12
    ) -> str:
        """
        Lắp ráp Stop-Motion 12 FPS từ rỗng (Assemble-from-empty) cho toàn bộ bức tranh 9:16 FLUX:
        - Layer 0: Flat cardstock paper field với uncoated paper grain.
        - Layer 1: Grounding / environment lines thích ứng theo Domain.
        - Layer 2: Mảng cắt dán siêu thực (AI rembg phân rã từ tác phẩm FLUX 9:16).
        - Layer 3: Bàn tay chỉ dẫn Victorian hoặc phụ kiện cổ điển.
        - Nhịp giật 12 FPS stop-motion chuẩn gbro-collage-broll.
        """
        from rembg import remove

        if work_dir is None:
            work_dir = Path(output_path).parent / "universal_frames"
        work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Chuẩn bị ảnh 9:16 và phân rã qua rembg
        raw_art = Image.open(artwork_path).convert("RGB")
        scaled_art = raw_art.resize((width, height), Image.Resampling.LANCZOS)

        cutout_cache = Path(artwork_path).with_suffix(".cutout.png")
        if cutout_cache.exists():
            fg_cutout = Image.open(str(cutout_cache)).convert("RGBA")
        else:
            logger.info(f"✂️ Phân rã mảng cắt dán bằng rembg AI cho {Path(artwork_path).name}...")
            fg_cutout = remove(scaled_art)
            fg_cutout.save(str(cutout_cache), format="PNG")

        if fg_cutout.size != (width, height):
            fg_cutout = fg_cutout.resize((width, height), Image.Resampling.LANCZOS)

        # 2. Tạo Layer 0: Cardstock trơn
        clean_hex = color_hex.strip().lstrip("#")
        if len(clean_hex) != 6:
            clean_hex = "1D3557"
        bg_rgb = (int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16))

        l0_bg = Image.new("RGBA", (width, height), (*bg_rgb, 255))
        noise = Image.effect_noise((width, height), 12).convert("L")
        noise = ImageEnhance.Contrast(noise).enhance(0.5)
        l0_bg.paste(Image.new("RGBA", (width, height), (255, 255, 255, 14)), mask=noise)

        # 3. Tạo Layer 1: Grounding / Environment theo domain
        l1_grounding = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        self.compositor._draw_domain_environment(l1_grounding, topic_domain, "hero_center", width, height)

        # 4. Tạo Layer 3: Contextual Accents (Victorian Hand / Camera)
        l3_accents = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pointing_hand_file = self.compositor.assets_dir / "hands" / "vintage_pointing_hand.png"
        cam_file = self.compositor.assets_dir / "props" / "vintage_camera.png"

        if has_hand and pointing_hand_file.exists():
            h_img = Image.open(pointing_hand_file).convert("RGBA")
            hw = int(width * 0.42)
            hh = int(h_img.height * (hw / h_img.width))
            h_r = h_img.resize((hw, hh), Image.Resampling.LANCZOS)
            l3_accents.paste(h_r, (int(width * 0.58), int(height * 0.16)), mask=h_r)

        if has_camera and cam_file.exists():
            cm_img = Image.open(cam_file).convert("RGBA")
            cam_w = int(width * 0.25)
            cam_h = int(cm_img.height * (cam_w / cm_img.width))
            cam_r = cm_img.resize((cam_w, cam_h), Image.Resampling.LANCZOS)
            l3_accents.paste(cam_r, ((width - cam_w) // 2, int(height * 0.78)), mask=cam_r)

        # 5. Tạo Completed Frame
        completed_comp = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        completed_comp.paste(l0_bg, (0, 0))
        completed_comp.paste(l1_grounding, (0, 0), mask=l1_grounding)
        completed_comp.paste(fg_cutout, (0, 0), mask=fg_cutout)
        completed_comp.paste(l3_accents, (0, 0), mask=l3_accents)

        # 6. Render Stop-Motion Frames
        total_frames = int(duration * fps)
        frame_paths = []

        # Discrete physical step tables
        grounding_steps = [-height, int(-height * 0.4), int(-height * 0.12), 12, -3, 0]
        fg_steps = [-height, int(-height * 0.45), int(-height * 0.15), 18, -4, 0]
        hand_steps = [-450, -180, 20, -5, 0]

        for frame_idx in range(total_frames):
            t = frame_idx / fps
            frame_img = l0_bg.copy()

            if t < 0.4:
                # Phase 1: 0.0s - 0.4s -> Empty cardstock
                pass
            elif t < 1.2:
                # Phase 2: 0.4s - 1.2s -> Grounding layer drops in
                step_i = min(len(grounding_steps) - 1, int((t - 0.4) * 6))
                oy = grounding_steps[step_i]
                g_canv = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                g_canv.paste(l1_grounding, (0, oy), mask=l1_grounding)
                frame_img.paste(g_canv, (0, 0), mask=g_canv)
            elif t < 2.2:
                # Phase 3: 1.2s - 2.2s -> Foreground Collage drops in
                frame_img.paste(l1_grounding, (0, 0), mask=l1_grounding)
                step_i = min(len(fg_steps) - 1, int((t - 1.2) * 5))
                oy = fg_steps[step_i]
                fg_canv = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                fg_canv.paste(fg_cutout, (0, oy), mask=fg_cutout)
                frame_img.paste(fg_canv, (0, 0), mask=fg_canv)
            elif t < 3.0:
                # Phase 4: 2.2s - 3.0s -> Victorian Hand / Accent enters
                frame_img.paste(l1_grounding, (0, 0), mask=l1_grounding)
                frame_img.paste(fg_cutout, (0, 0), mask=fg_cutout)
                step_i = min(len(hand_steps) - 1, int((t - 2.2) * 6))
                oy = hand_steps[step_i]
                h_canv = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                h_canv.paste(l3_accents, (0, oy), mask=l3_accents)
                frame_img.paste(h_canv, (0, 0), mask=h_canv)
            else:
                # Phase 5: 3.0s - End -> Hold complete composition with micro tactile jitter
                shift_x = random.choice([-1, 0, 1]) if (frame_idx % 2 == 0) else 0
                shift_y = random.choice([-1, 0, 1]) if (frame_idx % 3 == 0) else 0
                frame_img.paste(completed_comp, (shift_x, shift_y), mask=completed_comp)

            frame_file = work_dir / f"frame_{frame_idx:04d}.png"
            frame_img.convert("RGB").save(str(frame_file))
            frame_paths.append(str(frame_file))

        # Encode frames into MP4 with FFmpeg at 12 fps stop-motion
        input_pattern = str(work_dir / "frame_%04d.png")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-r", str(fps),
            "-i", input_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            output_path
        ]
        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            logger.success(f"✅ Universal Stop-Motion Assembler đã tạo clip 12fps thành công: {output_path}")
        except Exception as e:
            logger.error(f"Lỗi FFmpeg assemble frames: {e}")
            raise

        for p in frame_paths:
            try:
                os.remove(p)
            except OSError:
                pass

        return output_path

    def generate_procedural_workbench(
        self,
        target_width: int = 702,
        target_height: int = 310,
        outline_width: int = 9,
        shadow_offset: Tuple[int, int] = (12, 14),
        shadow_blur: int = 10,
        pad: int = 55
    ) -> Image.Image:
        """
        Bệ đỡ sân khấu tối giản cổ điển (R2 fallback qua generate_scene_appropriate_prop).
        Hoàn toàn loại bỏ ê-tô thợ mộc hardcoded.
        """
        return generate_scene_appropriate_prop(
            archetype_or_style="classic_plinth",
            target_width=target_width,
            target_height=target_height,
            outline_width=outline_width,
            shadow_offset=shadow_offset,
            shadow_blur=shadow_blur,
            pad=pad,
            compositor=self.compositor
        )

    def generate_scene_appropriate_prop(
        self,
        archetype: str = "default",
        target_width: int = 702,
        outline_width: int = 9,
        shadow_offset: Tuple[int, int] = (12, 14),
        shadow_blur: int = 10,
        pad: int = 55
    ) -> Image.Image:
        """Sinh stage prop phù hợp với archetype của cảnh."""
        return generate_scene_appropriate_prop(
            archetype_or_style=archetype,
            target_width=target_width,
            outline_width=outline_width,
            shadow_offset=shadow_offset,
            shadow_blur=shadow_blur,
            pad=pad,
            compositor=self.compositor
        )



    def render_multi_element_scene(
        self,
        scene_layout: Dict[str, Any],
        hero_asset_path: str,
        secondary_asset_path: str,
        output_video_path: str,
        output_frame_path: Optional[str] = None,
        duration: float = 5.0,
        work_dir: Optional[Path] = None,
        width: int = 1080,
        height: int = 1920,
        fps: int = 12,
        timeline: Optional[List[Dict[str, Any]]] = None,
        action_assets: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Lắp ráp hoạt cảnh Stop-Motion 12 FPS chuẩn Kiến trúc 7 Tầng Không Gian (Cinematic Collage Theatre):
        - Layer 0: Flat Cardstock Paper Field with grain (1080x1920).
        - Layer 1: Torn Paper Backdrop (TornPaperBackdropGenerator, 860x950, #F5EFEB fiber margin, soft shadow, centered at x=110, y=180).
        - Layer 2: Stage Prop (Bàn thợ mộc / carpenter workbench plinth, styled with 9px cream border and 3D shadow).
          Nhận rung chấn cơ học môi trường (+/- 8px) từ paper_fx_engine.get_environmental_shock(t, impact_time).
          Được dán dưới secondary target để khúc gỗ tựa vững chắc lên mặt bàn!
        - Layer 3: Secondary Target (Wood Log), viền kem 9px #FFFDF7 và bóng đổ 3D.
          Trước t_impact: nguyên vẹn trên bàn. Sau t_impact: hai nửa văng dạt tách đôi (260px, 30°).
        - Layer 4: Hero Actor (Axe), viền kem 9px #FFFDF7 và bóng đổ 3D. Vung cao -35° (y=0.16), bổ +6° (y=sec_y-0.02), recoil 8px.
        - Layer 5: Paper Debris FX (PaperFXEngine.get_particles_state), 3-5 mảnh dăm gỗ đa giác sắc nhọn viền kem 1.5px bung tỏa hình nón.
        - Layer 6: Director Accents (Victorian pointing hand / thước đo / thẻ bài).
        """
        out_vid = Path(output_video_path).resolve()
        out_vid.parent.mkdir(parents=True, exist_ok=True)

        if work_dir is None:
            work_dir = out_vid.parent / f"frames_{out_vid.stem}"
        work_dir.mkdir(parents=True, exist_ok=True)

        hero_cfg = scene_layout.get("hero_element", {})
        sec_cfg = scene_layout.get("secondary_element", {})

        hero_asset_path = hero_asset_path or hero_cfg.get("asset_path") or ""
        secondary_asset_path = secondary_asset_path or sec_cfg.get("asset_path") or ""

        # R4: Validate cutout asset paths before rendering
        if getattr(self, "validator", None) is not None:
            hero_asset_path = self.validator.validate_and_reject_if_invalid(hero_asset_path)
            secondary_asset_path = self.validator.validate_and_reject_if_invalid(secondary_asset_path)
            if "asset_path" in hero_cfg:
                hero_cfg["asset_path"] = hero_asset_path
            if "asset_path" in sec_cfg:
                sec_cfg["asset_path"] = secondary_asset_path

        # =========================================================================
        # TẦNG 0: NỀN GIẤY CARDSTOCK PHẲNG CÓ HẠT (FLAT CARDSTOCK WITH GRAIN)
        # =========================================================================
        color_field = scene_layout.get("color_field")
        raw_hex = scene_layout.get("color_hex")
        if not raw_hex and isinstance(color_field, dict):
            raw_hex = color_field.get("hex")
        elif not raw_hex and isinstance(color_field, str) and color_field.startswith("#"):
            raw_hex = color_field
        clean_hex = str(raw_hex or "1D3557").strip().lstrip("#")
        if len(clean_hex) != 6:
            clean_hex = "1D3557"
        bg_rgb = (int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16))

        l0_bg = Image.new("RGBA", (width, height), (*bg_rgb, 255))
        noise = Image.effect_noise((width, height), 12).convert("L")
        grain = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        grain.putalpha(noise.point(lambda p: int(p * 0.08)))
        l0_bg = Image.alpha_composite(l0_bg, grain)

        # =========================================================================
        # TẦNG 1: TRANH TƯ LIỆU PHÔNG NỀN GIẤY RÁCH THỦ CÔNG (TORN PAPER BACKDROP)
        # =========================================================================
        archival_cfg = (
            scene_layout.get("archival_backdrop")
            or scene_layout.get("blueprint", {}).get("archival_backdrop")
            or {}
        )
        backdrop_path = archival_cfg.get("asset_path")
        target_w = archival_cfg.get("target_width", 860)
        target_h = archival_cfg.get("target_height", 950)
        pos_top = archival_cfg.get("position_top", 180)
        roughness = archival_cfg.get("roughness", 12.0)
        fiber_color = archival_cfg.get("cellulose_fiber_color") or (245, 239, 235, 255)
        if isinstance(fiber_color, str) and fiber_color.startswith("#"):
            c_hex = fiber_color.lstrip("#")
            fiber_color = (int(c_hex[0:2], 16), int(c_hex[2:4], 16), int(c_hex[4:6], 16), 255)

        l1_torn_backdrop = self.torn_generator.generate_torn_paper_backdrop(
            image_path=backdrop_path,
            target_width=target_w,
            target_height=target_h,
            full_canvas_size=None,
            position_top=pos_top,
            fiber_color=fiber_color,
            roughness=roughness
        )
        l1_zoom_rate = float(archival_cfg.get("zoom_rate", 1.05))
        # Anchor for Ken Burns zoom centered horizontally (width // 2 = 540)
        # and at vertical center of nominal backdrop (pos_top + target_h // 2 = 180 + 475 = 655)
        l1_anchor_x = width // 2
        l1_anchor_y = pos_top + target_h // 2

        # =========================================================================
        # TẦNG 2: BỆ ĐỠ SÂN KHẤU / BÀN THỢ MỘC (STAGE PROP / CARPENTER WORKBENCH)
        # =========================================================================
        raw_stage_prop = scene_layout.get("stage_prop")
        if raw_stage_prop is None and "blueprint" in scene_layout:
            raw_stage_prop = scene_layout["blueprint"].get("stage_prop")

        is_floating = False
        if raw_stage_prop is None:
            is_floating = True
        elif isinstance(raw_stage_prop, bool):
            is_floating = not raw_stage_prop
        elif isinstance(raw_stage_prop, str):
            if raw_stage_prop.strip().lower() in ["none", "floating", "null", "false", ""]:
                is_floating = True
        elif isinstance(raw_stage_prop, dict):
            if raw_stage_prop.get("is_floating", False):
                is_floating = True
            elif str(raw_stage_prop.get("type", "")).strip().lower() in ["none", "floating", "null"]:
                is_floating = True
            elif not raw_stage_prop.get("enabled", True):
                is_floating = True

        stage_prop_cfg = raw_stage_prop if isinstance(raw_stage_prop, dict) else {}
        prop_asset_path = stage_prop_cfg.get("asset_path")
        if prop_asset_path and getattr(self, "validator", None) is not None:
            prop_asset_path = self.validator.validate_and_reject_if_invalid(prop_asset_path)
            stage_prop_cfg["asset_path"] = prop_asset_path
        prop_scale = stage_prop_cfg.get("scale", 0.65)
        prop_pos = stage_prop_cfg.get("position", [0.50, 0.78])
        prop_cx = int(width * prop_pos[0])
        prop_cy = int(height * prop_pos[1])

        l2_stage_prop = None
        if not is_floating:
            if prop_asset_path and os.path.exists(prop_asset_path):
                p_raw = Image.open(prop_asset_path).convert("RGBA")
                pw = int(width * prop_scale)
                ph = int(p_raw.height * (pw / p_raw.width))
                p_resized = p_raw.resize((pw, ph), Image.Resampling.LANCZOS)
                l2_stage_prop = self.compositor.apply_paper_cutout_styling(
                    p_resized,
                    outline_width=9,
                    shadow_offset=(12, 14),
                    shadow_blur=10,
                    pad=55,
                    shadow_alpha=120,
                    outline_color=(255, 253, 247, 255)
                )
            else:
                # R2: Sinh bệ đỡ thích ứng theo ngữ cảnh archetype khi scene không floating nhưng chưa có asset
                archetype_val = (
                    scene_layout.get("archetype")
                    or stage_prop_cfg.get("style")
                    or stage_prop_cfg.get("type")
                    or stage_prop_cfg.get("name")
                    or "default"
                )
                l2_stage_prop = generate_scene_appropriate_prop(
                    archetype_or_style=archetype_val,
                    target_width=int(width * prop_scale),
                    outline_width=9,
                    shadow_offset=(12, 14),
                    shadow_blur=10,
                    pad=55,
                    compositor=self.compositor
                )


        prop_shock_cfg = stage_prop_cfg.get("environmental_shock") or {}
        prop_shock_enabled = prop_shock_cfg.get("enabled", True) if not is_floating else False
        prop_shock_mag = float(prop_shock_cfg.get("magnitude_px", 8.0))

        # =========================================================================
        # TẦNG 3 & 4: VẬT THỂ HERO (RÌU) & SECONDARY (KHÚC GỖ)
        # =========================================================================
        active_timeline = timeline or scene_layout.get("timeline") or scene_layout.get("motion_timeline")
        active_action_assets = action_assets or scene_layout.get("action_assets") or []

        # 1. Chuẩn bị ảnh styled cho hero (viền kem 9px, bóng đổ 3D)
        hero_styled = None
        hero_sever_parts = None
        if hero_asset_path and os.path.exists(hero_asset_path):
            h_raw = Image.open(hero_asset_path).convert("RGBA")
            if hero_cfg.get("flip_vertical", False):
                h_raw = ImageOps.flip(h_raw)
            if hero_cfg.get("flip_horizontal", False):
                h_raw = ImageOps.mirror(h_raw)
            h_scale = hero_cfg.get("scale", hero_cfg.get("scale_factor", 0.48))
            hw = int(width * h_scale)
            hh = int(h_raw.height * (hw / h_raw.width))
            hero_resized = h_raw.resize((hw, hh), Image.Resampling.LANCZOS)
            rot = hero_cfg.get("rotation_deg", 0)
            if rot != 0:
                hero_resized = hero_resized.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
            hero_styled = self.compositor.apply_paper_cutout_styling(
                hero_resized,
                outline_width=9,
                shadow_offset=(12, 14),
                shadow_blur=10,
                pad=55,
                shadow_alpha=120,
                outline_color=(255, 253, 247, 255)
            )

            is_hero_sever = False
            hero_sever_axis = "vertical"
            hero_sever_angle = None
            if active_timeline:
                for act in active_timeline:
                    if act.get("target") == "hero" and act.get("action", "").upper() in ["ENGINE_SEVER_SHATTER", "SEVER_SHATTER"]:
                        is_hero_sever = True
                        hero_sever_axis = act.get("split_axis", "vertical")
                        hero_sever_angle = act.get("angle_deg")
                        break
            if is_hero_sever:
                hero_sever_parts = split_image_into_halves(
                    hero_resized, split_axis=hero_sever_axis, angle_deg=hero_sever_angle,
                    apply_styling=True, compositor=self.compositor
                )

        # 2. Chuẩn bị ảnh styled cho secondary (viền kem 9px, bóng đổ 3D)
        sec_styled = None
        sec_sever_parts = None
        sec_resized = None
        if secondary_asset_path and os.path.exists(secondary_asset_path):
            s_raw = Image.open(secondary_asset_path).convert("RGBA")
            if sec_cfg.get("flip_vertical", False):
                s_raw = ImageOps.flip(s_raw)
            if sec_cfg.get("flip_horizontal", False):
                s_raw = ImageOps.mirror(s_raw)
            s_scale = sec_cfg.get("scale", sec_cfg.get("scale_factor", 0.38))
            sw = int(width * s_scale)
            sh = int(s_raw.height * (sw / s_raw.width))
            sec_resized = s_raw.resize((sw, sh), Image.Resampling.LANCZOS)
            rot = sec_cfg.get("rotation_deg", 0)
            if rot != 0:
                sec_resized = sec_resized.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
            sec_styled = self.compositor.apply_paper_cutout_styling(
                sec_resized,
                outline_width=9,
                shadow_offset=(12, 14),
                shadow_blur=10,
                pad=55,
                shadow_alpha=120,
                outline_color=(255, 253, 247, 255)
            )

            is_sec_sever = False
            sec_sever_axis = "vertical"
            sec_sever_angle = None
            if active_timeline:
                for act in active_timeline:
                    if act.get("target") == "secondary" and act.get("action", "").upper() in ["ENGINE_SEVER_SHATTER", "SEVER_SHATTER"]:
                        is_sec_sever = True
                        sec_sever_axis = act.get("split_axis", "vertical")
                        sec_sever_angle = act.get("angle_deg")
                        break
            else:
                is_sec_sever = True

            if is_sec_sever:
                sec_sever_parts = split_image_into_halves(
                    sec_resized, split_axis=sec_sever_axis, angle_deg=sec_sever_angle,
                    apply_styling=True, compositor=self.compositor
                )

        # 3. Chuẩn bị ảnh styled cho action assets
        styled_action_assets = {}
        for act in active_action_assets:
            act_id = act.get("id")
            act_p = act.get("path")
            if act_id and act_p and os.path.exists(act_p):
                a_raw = Image.open(act_p).convert("RGBA")
                a_scale = act.get("scale", 0.28)
                aw = int(width * a_scale)
                ah = int(a_raw.height * (aw / a_raw.width))
                a_resized = a_raw.resize((aw, ah), Image.Resampling.LANCZOS)
                styled_action_assets[act_id] = {
                    "image": self.compositor.apply_paper_cutout_styling(
                        a_resized,
                        outline_width=9,
                        shadow_offset=(12, 14),
                        shadow_blur=10,
                        pad=55,
                        shadow_alpha=120,
                        outline_color=(255, 253, 247, 255)
                    ),
                    "layer_order": act.get("layer_order", "below_hero")
                }

        # =========================================================================
        # TẦNG 5: ĐỘNG CƠ MẢNH VỤN GIẤY DĂM GỖ (PAPER DEBRIS FX)
        # =========================================================================
        impact_t = 1.8
        if active_timeline:
            for act in active_timeline:
                if act.get("action", "").upper() in ["ENGINE_SEVER_SHATTER", "SEVER_SHATTER"]:
                    impact_t = float(act.get("impact_time", 1.8))
                    break
        elif "impact_time" in scene_layout:
            impact_t = float(scene_layout["impact_time"])

        sec_norm_pos = sec_cfg.get("position", [0.50, 0.68])
        impact_cx = int(width * 0.50)
        impact_cy = int(height * (sec_norm_pos[1] - 0.02))

        self.paper_fx_engine = PaperFXEngine(fps=fps)
        debris_cfg = scene_layout.get("paper_debris_fx") or {}
        debris_enabled = debris_cfg.get("enabled", True)
        if debris_enabled and sec_resized is not None:
            debris_count = int(debris_cfg.get("count", 4))
            debris_outline_w = float(debris_cfg.get("outline_width", 1.5))
            debris_outline_col = debris_cfg.get("outline_color", "#FFFDF7")
            if isinstance(debris_outline_col, str) and debris_outline_col.startswith("#"):
                d_hex = debris_outline_col.lstrip("#")
                debris_rgba = (int(d_hex[0:2], 16), int(d_hex[2:4], 16), int(d_hex[4:6], 16), 255)
            else:
                debris_rgba = (255, 253, 247, 255)

            self.paper_fx_engine.generate_debris_particles(
                source_image=sec_resized,
                num_particles=debris_count,
                impact_center_px=(impact_cx, impact_cy),
                outline_width=debris_outline_w,
                outline_color=debris_rgba
            )

        # Cache cho các mảnh dăm gỗ sau khi bung tỏa đã đáp xuống mặt bàn
        settled_debris_states = []
        if debris_enabled and self.paper_fx_engine.particles:
            for p in self.paper_fx_engine.particles:
                cx, cy = p.origin_pos
                dx = p.burst_speed_px * math.cos(p.cone_angle_rad) * 1.45
                dy = p.burst_speed_px * math.sin(p.cone_angle_rad) * 0.95 + p.gravity_drop_px
                settled_debris_states.append({
                    "image": p.image,
                    "position": (cx + dx, cy + dy),
                    "rotation_deg": p.spin_step3,
                    "opacity": 0.85
                })

        # =========================================================================
        # TẦNG 6: ĐIỂM NHẤN ĐẠO DIỄN (DIRECTOR ACCENTS - BÀN TAY VICTORIAN)
        # =========================================================================
        accents_cfg = scene_layout.get("director_accents") or {}
        if "has_hand" in accents_cfg:
            has_hand = bool(accents_cfg.get("has_hand"))
        elif "has_pointing_hand" in scene_layout:
            has_hand = bool(scene_layout.get("has_pointing_hand"))
        else:
            has_hand = False

        hand_img = None
        if has_hand:
            proj_root = Path(__file__).resolve().parents[2]
            gesture = str(accents_cfg.get("gesture") or accents_cfg.get("hand_gesture") or "pointing").lower().strip()
            rotation_offset = 0.0
            preferred_file = None

            if gesture == "presenting":
                cand_clean = proj_root / "assets" / "collage_assets" / "hands" / "vintage_hand_clean.png"
                if cand_clean.exists():
                    preferred_file = cand_clean
                rotation_offset = 15.0
            elif gesture == "helpless":
                cand_clean = proj_root / "assets" / "collage_assets" / "hands" / "vintage_hand_clean.png"
                if cand_clean.exists():
                    preferred_file = cand_clean
                rotation_offset = -35.0
            else:  # "pointing" or default
                cand_point = proj_root / "assets" / "collage_assets" / "hands" / "vintage_pointing_hand.png"
                if cand_point.exists():
                    preferred_file = cand_point
                rotation_offset = 0.0

            if not preferred_file:
                hand_candidates = [
                    proj_root / "assets" / "collage_assets" / "hands" / "vintage_pointing_hand.png",
                    Path("assets/collage_assets/hands/vintage_pointing_hand.png"),
                    proj_root / "assets" / "collage_assets" / "hands" / "vintage_hand_clean.png",
                    Path("assets/collage_assets/hands/vintage_hand_clean.png"),
                ]
                preferred_file = next((p for p in hand_candidates if p.exists()), None)

            if preferred_file:
                h_raw = Image.open(preferred_file).convert("RGBA")
                hw = int(width * 0.38)
                hh = int(h_raw.height * (hw / h_raw.width))
                h_resized = h_raw.resize((hw, hh), Image.Resampling.LANCZOS)
                if rotation_offset != 0.0:
                    h_resized = h_resized.rotate(rotation_offset, expand=True, resample=Image.Resampling.BICUBIC)
                hand_img = self.compositor.apply_paper_cutout_styling(
                    h_resized,
                    outline_width=9,
                    shadow_offset=(10, 12),
                    shadow_blur=8,
                    pad=45,
                    shadow_alpha=110,
                    outline_color=(255, 253, 247, 255)
                )

        hand_steps = [-380, -180, 20, -5, 0]
        total_frames = int(duration * fps)
        frame_paths = []

        # =========================================================================
        # CHẾ ĐỘ 1: SỬ DỤNG MOTION TIMELINE ENGINE (DIỄN HOẠT CƠ HỌC TỪNG NẤC GIẬT)
        # =========================================================================
        if active_timeline:
            logger.info(f"🎬 [GbroAdapter] Kích hoạt MotionTimelineEngine 7 Tầng ({len(active_timeline)} actions, {len(active_action_assets)} action assets)...")

            base_configs = {}
            if hero_styled:
                base_configs["hero"] = {
                    "position": hero_cfg.get("position", [0.5, 0.16]),
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                    "rotation_deg": float(hero_cfg.get("rotation_deg", 0.0)),
                    "visible": hero_cfg.get("visible", True)
                }
            if sec_styled:
                base_configs["secondary"] = {
                    "position": sec_cfg.get("position", [0.5, 0.68]),
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                    "rotation_deg": float(sec_cfg.get("rotation_deg", 0.0)),
                    "visible": sec_cfg.get("visible", True)
                }
            for act_id in styled_action_assets:
                base_configs[act_id] = {
                    "position": [0.5, 0.5],
                    "scale_x": 1.0,
                    "scale_y": 1.0,
                    "rotation_deg": 0.0,
                    "visible": False
                }

            motion_engine = MotionTimelineEngine(timeline=active_timeline, base_configs=base_configs)

            for frame_idx in range(total_frames):
                t = frame_idx / fps
                states = motion_engine.get_frame_state(t, frame_idx=frame_idx, width=width, height=height)

                # Rung chấn camera (Camera Screen Shake ±8px)
                shake_x, shake_y = 0, 0
                if states.get("__screen_shake__", False):
                    shake_patterns_x = [-8, 8, -6, 6, 0]
                    shake_patterns_y = [5, -7, 6, -5, 0]
                    shake_x = shake_patterns_x[frame_idx % len(shake_patterns_x)]
                    shake_y = shake_patterns_y[frame_idx % len(shake_patterns_y)]

                frame_img = Image.new("RGBA", (width, height), (0, 0, 0, 255))

                # -----------------------------------------------------------------
                # LAYER 0: Flat Cardstock Paper Field with grain
                # -----------------------------------------------------------------
                frame_img.paste(l0_bg, (shake_x, shake_y))

                # -----------------------------------------------------------------
                # LAYER 1: Torn Paper Backdrop (Archival Backdrop with Ken Burns Zoom)
                # -----------------------------------------------------------------
                zoom_progress = min(1.0, max(0.0, t / max(duration, 0.01)))
                scale_factor = 1.0 + (l1_zoom_rate - 1.0) * zoom_progress
                if abs(scale_factor - 1.0) > 0.001:
                    cur_w = max(1, int(round(l1_torn_backdrop.width * scale_factor)))
                    cur_h = max(1, int(round(l1_torn_backdrop.height * scale_factor)))
                    cur_l1 = l1_torn_backdrop.resize((cur_w, cur_h), Image.Resampling.BILINEAR)
                else:
                    cur_l1 = l1_torn_backdrop

                l1_x = int(round(l1_anchor_x - cur_l1.width / 2.0)) + shake_x
                l1_y = int(round(l1_anchor_y - cur_l1.height / 2.0)) + shake_y
                frame_img.paste(cur_l1, (l1_x, l1_y), mask=cur_l1)

                # -----------------------------------------------------------------
                # LAYER 2: Stage Prop (Stage Prop Plinth) with Environmental Shock
                # -----------------------------------------------------------------
                if l2_stage_prop is not None:
                    if prop_shock_enabled:
                        shock_dx, shock_dy = self.paper_fx_engine.get_environmental_shock(
                            t, impact_t, shock_amplitude=prop_shock_mag
                        )
                    else:
                        shock_dx, shock_dy = 0.0, 0.0

                    prop_x = prop_cx + int(shock_dx) - l2_stage_prop.width // 2 + shake_x
                    prop_y = prop_cy + int(shock_dy) - l2_stage_prop.height // 2 + shake_y
                    frame_img.paste(l2_stage_prop, (prop_x, prop_y), mask=l2_stage_prop)

                sec_layer = states.get("secondary", {}).get("layer_order", "below_hero")

                def render_secondary_element():
                    if not (sec_styled and states.get("secondary", {}).get("visible", True)):
                        return
                    st = states["secondary"]
                    opac = st.get("opacity", 1.0)
                    pos = st.get("position", [width * 0.5, height * 0.68])

                    if st.get("is_severed", False) and sec_sever_parts:
                        part_1, part_2 = sec_sever_parts
                        sp1 = st.get("sever_part_1", {})
                        sp2 = st.get("sever_part_2", {})

                        # Mảnh 1 (bên trái): giật nảy sang trái và xoay ngược chiều kim đồng hồ
                        p1_img = part_1
                        rot1 = sp1.get("rotation_deg", -30.0)
                        if rot1 != 0:
                            p1_img = p1_img.rotate(rot1, expand=True, resample=Image.Resampling.BICUBIC)
                        if opac < 0.99:
                            p1_img = p1_img.copy()
                            alpha = p1_img.split()[3].point(lambda p: int(p * opac))
                            p1_img.putalpha(alpha)
                        nat_off_1 = getattr(part_1, "natural_offset", (-part_1.width // 4, 0))
                        px1 = int(pos[0] + nat_off_1[0] + sp1.get("offset_x", 0.0) - p1_img.width // 2) + shake_x
                        py1 = int(pos[1] + nat_off_1[1] + sp1.get("offset_y", 0.0) - p1_img.height // 2) + shake_y
                        frame_img.paste(p1_img, (px1, py1), mask=p1_img)

                        # Mảnh 2 (bên phải): giật nảy sang phải và xoay thuận chiều kim đồng hồ
                        p2_img = part_2
                        rot2 = sp2.get("rotation_deg", 30.0)
                        if rot2 != 0:
                            p2_img = p2_img.rotate(rot2, expand=True, resample=Image.Resampling.BICUBIC)
                        if opac < 0.99:
                            p2_img = p2_img.copy()
                            alpha = p2_img.split()[3].point(lambda p: int(p * opac))
                            p2_img.putalpha(alpha)
                        nat_off_2 = getattr(part_2, "natural_offset", (part_2.width // 4, 0))
                        px2 = int(pos[0] + nat_off_2[0] + sp2.get("offset_x", 0.0) - p2_img.width // 2) + shake_x
                        py2 = int(pos[1] + nat_off_2[1] + sp2.get("offset_y", 0.0) - p2_img.height // 2) + shake_y
                        frame_img.paste(p2_img, (px2, py2), mask=p2_img)

                    else:
                        # Trạng thái nguyên vẹn bình thường tựa trên bàn thợ mộc
                        sx = st.get("scale_x", 1.0)
                        sy = st.get("scale_y", 1.0)
                        rot = st.get("rotation_deg", 0.0)

                        if sx > 0.02 and sy > 0.02 and opac > 0.02:
                            curr_sec = sec_styled
                            if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
                                nw = max(5, int(sec_styled.width * sx))
                                nh = max(5, int(sec_styled.height * sy))
                                curr_sec = sec_styled.resize((nw, nh), Image.Resampling.BILINEAR)
                            if rot != 0:
                                curr_sec = curr_sec.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
                            if opac < 0.99:
                                curr_sec = curr_sec.copy()
                                alpha = curr_sec.split()[3].point(lambda p: int(p * opac))
                                curr_sec.putalpha(alpha)

                            bottom_anchor = sec_cfg.get("bottom_anchor", False) or any(
                                act.get("target") == "secondary" and act.get("action", "").upper() in ["ENGINE_COMPRESS_SQUASH", "COMPRESS_SQUASH", "SQUASH_AND_STRETCH"]
                                for act in active_timeline
                            )
                            if bottom_anchor and sy < 0.99:
                                delta_y = int(sec_styled.height * (1.0 - sy) / 2.0)
                                py = int(pos[1] + delta_y - curr_sec.height // 2) + shake_y
                            else:
                                py = int(pos[1] - curr_sec.height // 2) + shake_y

                            px = int(pos[0] - curr_sec.width // 2) + shake_x
                            frame_img.paste(curr_sec, (px, py), mask=curr_sec)

                # -----------------------------------------------------------------
                # LAYER 3: Secondary Element (vẽ ở đây nếu là below_hero)
                # -----------------------------------------------------------------
                if sec_layer != "above_hero":
                    render_secondary_element()

                # Action Assets (nằm dưới Hero)
                for act_id, act_dict in styled_action_assets.items():
                    if act_dict.get("layer_order") == "below_hero":
                        st = states.get(act_id)
                        if st and st.get("visible", False):
                            sx = st.get("scale_x", 1.0)
                            sy = st.get("scale_y", 1.0)
                            rot = st.get("rotation_deg", 0.0)
                            opac = st.get("opacity", 1.0)
                            if sx > 0.02 and sy > 0.02 and opac > 0.02:
                                act_img = act_dict["image"]
                                if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
                                    nw = max(5, int(act_img.width * sx))
                                    nh = max(5, int(act_img.height * sy))
                                    act_img = act_img.resize((nw, nh), Image.Resampling.BILINEAR)
                                if rot != 0:
                                    act_img = act_img.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
                                pos = st.get("position", [width * 0.5, height * 0.5])
                                px = int(pos[0] - act_img.width // 2) + shake_x
                                py = int(pos[1] - act_img.height // 2) + shake_y
                                frame_img.paste(act_img, (px, py), mask=act_img)

                # -----------------------------------------------------------------
                # LAYER 4: Hero Element (Lưỡi rìu bổ cắm ngập tâm, recoil 8px)
                # -----------------------------------------------------------------
                if hero_styled and states.get("hero", {}).get("visible", True):
                    st = states["hero"]
                    opac = st.get("opacity", 1.0)
                    pos = st.get("position", [width * 0.5, height * 0.16])

                    if st.get("is_severed", False) and hero_sever_parts:
                        part_1, part_2 = hero_sever_parts
                        sp1 = st.get("sever_part_1", {})
                        sp2 = st.get("sever_part_2", {})

                        p1_img = part_1
                        rot1 = sp1.get("rotation_deg", -15.0)
                        if rot1 != 0:
                            p1_img = p1_img.rotate(rot1, expand=True, resample=Image.Resampling.BICUBIC)
                        if opac < 0.99:
                            p1_img = p1_img.copy()
                            alpha = p1_img.split()[3].point(lambda p: int(p * opac))
                            p1_img.putalpha(alpha)
                        nat_off_1 = getattr(part_1, "natural_offset", (-part_1.width // 4, 0))
                        px1 = int(pos[0] + nat_off_1[0] + sp1.get("offset_x", 0.0) - p1_img.width // 2) + shake_x
                        py1 = int(pos[1] + nat_off_1[1] + sp1.get("offset_y", 0.0) - p1_img.height // 2) + shake_y
                        frame_img.paste(p1_img, (px1, py1), mask=p1_img)

                        p2_img = part_2
                        rot2 = sp2.get("rotation_deg", 15.0)
                        if rot2 != 0:
                            p2_img = p2_img.rotate(rot2, expand=True, resample=Image.Resampling.BICUBIC)
                        if opac < 0.99:
                            p2_img = p2_img.copy()
                            alpha = p2_img.split()[3].point(lambda p: int(p * opac))
                            p2_img.putalpha(alpha)
                        nat_off_2 = getattr(part_2, "natural_offset", (part_2.width // 4, 0))
                        px2 = int(pos[0] + nat_off_2[0] + sp2.get("offset_x", 0.0) - p2_img.width // 2) + shake_x
                        py2 = int(pos[1] + nat_off_2[1] + sp2.get("offset_y", 0.0) - p2_img.height // 2) + shake_y
                        frame_img.paste(p2_img, (px2, py2), mask=p2_img)

                    else:
                        sx = st.get("scale_x", 1.0)
                        sy = st.get("scale_y", 1.0)
                        rot = st.get("rotation_deg", 0.0)

                        if sx > 0.02 and sy > 0.02 and opac > 0.02:
                            curr_hero = hero_styled
                            if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
                                nw = max(5, int(hero_styled.width * sx))
                                nh = max(5, int(hero_styled.height * sy))
                                curr_hero = hero_styled.resize((nw, nh), Image.Resampling.BILINEAR)
                            if opac < 0.99:
                                curr_hero = curr_hero.copy()
                                alpha = curr_hero.split()[3].point(lambda p: int(p * opac))
                                curr_hero.putalpha(alpha)

                            pivot = hero_cfg.get("pivot_point", st.get("pivot_point"))
                            if pivot and rot != 0:
                                curr_hero_rot, piv_x, piv_y = rotate_with_fixed_pivot(curr_hero, rot, pivot)
                                px = int(pos[0] - piv_x) + shake_x
                                py = int(pos[1] - piv_y) + shake_y
                                frame_img.paste(curr_hero_rot, (px, py), mask=curr_hero_rot)
                            else:
                                if rot != 0:
                                    curr_hero = curr_hero.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
                                px = int(pos[0] - curr_hero.width // 2) + shake_x
                                py = int(pos[1] - curr_hero.height // 2) + shake_y
                                frame_img.paste(curr_hero, (px, py), mask=curr_hero)

                # Action Assets (nằm trên Hero)
                for act_id, act_dict in styled_action_assets.items():
                    if act_dict.get("layer_order") == "above_hero":
                        st = states.get(act_id)
                        if st and st.get("visible", False):
                            sx = st.get("scale_x", 1.0)
                            sy = st.get("scale_y", 1.0)
                            rot = st.get("rotation_deg", 0.0)
                            opac = st.get("opacity", 1.0)
                            if sx > 0.02 and sy > 0.02 and opac > 0.02:
                                act_img = act_dict["image"]
                                if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
                                    nw = max(5, int(act_img.width * sx))
                                    nh = max(5, int(act_img.height * sy))
                                    act_img = act_img.resize((nw, nh), Image.Resampling.BILINEAR)
                                if rot != 0:
                                    act_img = act_img.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
                                pos = st.get("position", [width * 0.5, height * 0.5])
                                px = int(pos[0] - act_img.width // 2) + shake_x
                                py = int(pos[1] - act_img.height // 2) + shake_y
                                frame_img.paste(act_img, (px, py), mask=act_img)

                # Secondary Element khi layer_order == "above_hero"
                if sec_layer == "above_hero":
                    render_secondary_element()

                # -----------------------------------------------------------------
                # LAYER 5: Paper Debris FX (Mảnh vụn dăm gỗ 12fps bung tỏa hình nón)
                # -----------------------------------------------------------------
                if debris_enabled and self.paper_fx_engine.particles:
                    debris_states = self.paper_fx_engine.get_particles_state(t, impact_t)
                    if debris_states:
                        for p_state in debris_states:
                            p_img = p_state["image"]
                            p_rot = p_state.get("rotation_deg", 0.0)
                            p_opac = p_state.get("opacity", 1.0)
                            p_pos = p_state["position"]
                            if p_rot != 0:
                                p_img = p_img.rotate(p_rot, expand=True, resample=Image.Resampling.BICUBIC)
                            if p_opac < 0.99:
                                p_img = p_img.copy()
                                p_alpha = p_img.split()[3].point(lambda a: int(a * p_opac))
                                p_img.putalpha(p_alpha)
                            p_x = int(p_pos[0] - p_img.width // 2) + shake_x
                            p_y = int(p_pos[1] - p_img.height // 2) + shake_y
                            frame_img.paste(p_img, (p_x, p_y), mask=p_img)
                    elif t >= impact_t and settled_debris_states:
                        # Sau giai đoạn động lực học, các mảnh dăm gỗ đã đáp xuống mặt bàn quanh khúc gỗ
                        for p_state in settled_debris_states:
                            p_img = p_state["image"]
                            p_rot = p_state.get("rotation_deg", 0.0)
                            p_opac = p_state.get("opacity", 0.85)
                            p_pos = p_state["position"]
                            if p_rot != 0:
                                p_img = p_img.rotate(p_rot, expand=True, resample=Image.Resampling.BICUBIC)
                            if p_opac < 0.99:
                                p_img = p_img.copy()
                                p_alpha = p_img.split()[3].point(lambda a: int(a * p_opac))
                                p_img.putalpha(p_alpha)
                            p_x = int(p_pos[0] - p_img.width // 2) + shake_x
                            p_y = int(p_pos[1] - p_img.height // 2) + shake_y
                            frame_img.paste(p_img, (p_x, p_y), mask=p_img)

                # -----------------------------------------------------------------
                # LAYER 6: Director Accents (Bàn tay Victorian chỉ điểm góc trên)
                # -----------------------------------------------------------------
                if hand_img:
                    if t >= 0.5:
                        step_idx = min(len(hand_steps) - 1, int((t - 0.5) * 6))
                        offset_y = hand_steps[step_idx]
                    else:
                        offset_y = -500

                    if offset_y > -450:
                        hand_px = int(width * 0.58) + shake_x
                        hand_py = int(height * 0.10) + offset_y + shake_y
                        frame_img.paste(hand_img, (hand_px, hand_py), mask=hand_img)

                frame_file = work_dir / f"frame_{frame_idx:04d}.png"
                frame_img.convert("RGB").save(str(frame_file))
                frame_paths.append(str(frame_file))

                if frame_idx == total_frames - 1 and output_frame_path:
                    frame_img.convert("RGB").save(str(Path(output_frame_path).resolve()), format="PNG")

        # =========================================================================
        # CHẾ ĐỘ 2: FALLBACK STATIC DISCRETE DROP TABLE (TƯƠNG THÍCH NGƯỢC)
        # =========================================================================
        else:
            # Tạo composite hoàn chỉnh cho chế độ tĩnh
            last_composite = Image.new("RGBA", (width, height), (0, 0, 0, 255))
            last_composite.paste(l0_bg, (0, 0))
            l1_init_x = int(round(l1_anchor_x - l1_torn_backdrop.width / 2.0))
            l1_init_y = int(round(l1_anchor_y - l1_torn_backdrop.height / 2.0))
            last_composite.paste(l1_torn_backdrop, (l1_init_x, l1_init_y), mask=l1_torn_backdrop)
            if l2_stage_prop is not None:
                last_composite.paste(l2_stage_prop, (prop_cx - l2_stage_prop.width // 2, prop_cy - l2_stage_prop.height // 2), mask=l2_stage_prop)
            if sec_styled:
                last_composite.paste(sec_styled, (int(width * 0.5) - sec_styled.width // 2, int(height * 0.68) - sec_styled.height // 2), mask=sec_styled)
            if hero_styled:
                last_composite.paste(hero_styled, (int(width * 0.5) - hero_styled.width // 2, int(height * 0.66) - hero_styled.height // 2), mask=hero_styled)
            if hand_img:
                last_composite.paste(hand_img, (int(width * 0.58), int(height * 0.10)), mask=hand_img)

            if output_frame_path:
                frame_out = Path(output_frame_path).resolve()
                frame_out.parent.mkdir(parents=True, exist_ok=True)
                last_composite.convert("RGB").save(str(frame_out), format="PNG")

            prop_steps = [-height, int(-height * 0.30), 10, -2, 0]
            sec_steps = [-height, int(-height * 0.35), int(-height * 0.12), 15, -4, 0]
            hero_steps = [-height, int(-height * 0.50), int(-height * 0.18), 24, -8, 3, 0]

            for frame_idx in range(total_frames):
                t = frame_idx / fps
                frame_img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
                frame_img.paste(l0_bg, (0, 0))

                zoom_progress = min(1.0, max(0.0, t / max(duration, 0.01)))
                scale_factor = 1.0 + (l1_zoom_rate - 1.0) * zoom_progress
                if abs(scale_factor - 1.0) > 0.001:
                    cur_w = max(1, int(round(l1_torn_backdrop.width * scale_factor)))
                    cur_h = max(1, int(round(l1_torn_backdrop.height * scale_factor)))
                    cur_l1 = l1_torn_backdrop.resize((cur_w, cur_h), Image.Resampling.BILINEAR)
                else:
                    cur_l1 = l1_torn_backdrop
                l1_x = int(round(l1_anchor_x - cur_l1.width / 2.0))
                l1_y = int(round(l1_anchor_y - cur_l1.height / 2.0))

                if t < 0.3:
                    pass
                elif t < 1.0:
                    frame_img.paste(cur_l1, (l1_x, l1_y), mask=cur_l1)
                elif t < 1.8:
                    frame_img.paste(cur_l1, (l1_x, l1_y), mask=cur_l1)
                    if l2_stage_prop is not None:
                        step_i = min(len(prop_steps) - 1, int((t - 1.0) * 6))
                        oy = prop_steps[step_i]
                        frame_img.paste(l2_stage_prop, (prop_cx - l2_stage_prop.width // 2, prop_cy + oy - l2_stage_prop.height // 2), mask=l2_stage_prop)
                elif t < 2.6:
                    frame_img.paste(cur_l1, (l1_x, l1_y), mask=cur_l1)
                    if l2_stage_prop is not None:
                        frame_img.paste(l2_stage_prop, (prop_cx - l2_stage_prop.width // 2, prop_cy - l2_stage_prop.height // 2), mask=l2_stage_prop)
                    step_i = min(len(sec_steps) - 1, int((t - 1.8) * 6))
                    oy = sec_steps[step_i]
                    if sec_styled:
                        frame_img.paste(sec_styled, (int(width * 0.5) - sec_styled.width // 2, int(height * 0.68) + oy - sec_styled.height // 2), mask=sec_styled)
                elif t < 3.4:
                    frame_img.paste(cur_l1, (l1_x, l1_y), mask=cur_l1)
                    if l2_stage_prop is not None:
                        frame_img.paste(l2_stage_prop, (prop_cx - l2_stage_prop.width // 2, prop_cy - l2_stage_prop.height // 2), mask=l2_stage_prop)
                    if sec_styled:
                        frame_img.paste(sec_styled, (int(width * 0.5) - sec_styled.width // 2, int(height * 0.68) - sec_styled.height // 2), mask=sec_styled)
                    step_i = min(len(hero_steps) - 1, int((t - 2.6) * 7))
                    oy = hero_steps[step_i]
                    if hero_styled:
                        frame_img.paste(hero_styled, (int(width * 0.5) - hero_styled.width // 2, int(height * 0.66) + oy - hero_styled.height // 2), mask=hero_styled)
                else:
                    shift_x = random.choice([-1, 0, 1]) if (frame_idx % 2 == 0) else 0
                    shift_y = random.choice([-1, 0, 1]) if (frame_idx % 3 == 0) else 0
                    frame_img.paste(last_composite, (shift_x, shift_y), mask=last_composite)

                frame_file = work_dir / f"frame_{frame_idx:04d}.png"
                frame_img.convert("RGB").save(str(frame_file))
                frame_paths.append(str(frame_file))

        # Mã hóa FFmpeg xuất video 12 FPS stop-motion
        input_pattern = str(work_dir / "frame_%04d.png")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-r", str(fps),
            "-i", input_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            str(out_vid)
        ]
        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            logger.success(f"🎬 [Stop-Motion 12fps PASS] Đã tạo video chuyển động cơ học 7 tầng: {out_vid.name}")
        except Exception as e:
            logger.error(f"Lỗi FFmpeg assemble frames: {e}")
            raise

        for p in frame_paths:
            try:
                os.remove(p)
            except OSError:
                pass

        return str(out_vid)

    # -------------------------------------------------------------------------
    # Alias cho chuẩn 7 Tầng Không Gian Cinematic Collage Theatre (Milestone M3)
    # -------------------------------------------------------------------------
    render_multi_layer_scene = render_multi_element_scene



