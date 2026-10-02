import os
import math
import random
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from loguru import logger

BASE_ASSET_DIR = Path(__file__).parent.parent.parent / "assets" / "collage_assets"


def apply_paper_cutout_styling(
    img: Image.Image,
    outline_width: int = 9,
    shadow_offset: Tuple[int, int] = (12, 14),
    shadow_blur: int = 10,
    pad: int = 55,
    shadow_alpha: int = 120,
    outline_color: Tuple[int, int, int, int] = (255, 253, 247, 255)
) -> Image.Image:
    """
    Thêm hiệu ứng giấy cắt dán thủ công chuẩn gbro-collage-broll cao cấp:
    1. Viền giấy trắng kem (cream outline #FFFDF7) dày 9px xung quanh viền cắt.
    2. Bóng đổ vật lý 3D (drop shadow): Gaussian blur 10px, chếch (12, 14), độ mờ ~47% (alpha 120).
    3. Padded canvas 55px tránh xén cụt viền.
    CRITICAL VISUAL FIX: shadow_mask PHẢI được tạo từ dilated_mask.filter(GaussianBlur)
    thay vì từ alpha gốc. Điều này đảm bảo bóng đổ 3D xuất phát từ mép viền giấy cắt 9px
    thay vì bị viền giấy cắt che khuất hoặc cắt cụt.
    """
    if img is None:
        raise ValueError("Input image cannot be None")

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    w = img.width + pad * 2
    h = img.height + pad * 2

    # 1. Padded canvas (bảo toàn transparent margins của ảnh RGBA)
    padded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    padded.paste(img, (pad, pad), mask=img)
    alpha = padded.split()[-1]

    # 2. Cream keyline (dilate mask by outline_width)
    if outline_width > 0:
        filter_size = outline_width * 2 + 1
        dilated_mask = alpha.filter(ImageFilter.MaxFilter(filter_size))
    else:
        dilated_mask = alpha.copy()

    # 3. Drop shadow 3D: tạo shadow_mask từ dilated_mask để bóng đổ vươn ra từ viền ngoài giấy cắt
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow_blur > 0:
        shadow_mask = dilated_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
    else:
        shadow_mask = dilated_mask.copy()
    shadow.paste(Image.new("RGBA", (w, h), (0, 0, 0, shadow_alpha)), mask=shadow_mask)

    # 4. Cream outline (#FFFDF7 = (255, 253, 247, 255))
    outline = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    outline.paste(Image.new("RGBA", (w, h), outline_color), mask=dilated_mask)

    # 5. Composite order: shadow (at shadow_offset) -> outline (at (0, 0)) -> original image (at (0, 0))
    styled = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    styled.paste(shadow, shadow_offset, mask=shadow)
    styled.paste(outline, (0, 0), mask=outline)
    styled.paste(padded, (0, 0), mask=padded)
    return styled


class MultiLayerCollageCompositor:
    """
    Composites 5-layer surreal editorial paper collage works (1080x1920)
    matching the iconic style of gbro-collage-broll, dynamically adapted to domains:
    - Layer 0: Flat Kraft/Cardstock Paper Field with uncoated paper grain.
    - Layer 1: Domain-Adaptive Environment Graphics (Biology, Geography, History, Space...).
    - Layer 2: Atmospheric Lighting (translucent warm light cone/spotlight).
    - Layer 3: Subject Cutout Stickers (Focal & Secondary) with cream keylines and drop shadows.
    - Layer 4: Contextual Accents (Clean vintage pointing hand or camera ONLY when requested).
    """

    def __init__(self):
        self.assets_dir = BASE_ASSET_DIR

    def compose_scene(
        self,
        color_hex: str,
        color_field: str = "Crimson Red",
        visual_metaphor: str = "",
        assembly_order: str = "",
        focal_sticker_path: Optional[str] = None,
        secondary_sticker_path: Optional[str] = None,
        layout_type: str = "hero_center",
        topic_domain: str = "general",
        has_hand: bool = False,
        has_camera: bool = False,
        output_dir: Optional[Path] = None,
        width: int = 1080,
        height: int = 1920
    ) -> Dict[str, str]:
        """
        Creates all 5 independent layers and the completed composite last-frame.png
        adapting dynamically to domain, layout type, and contextual flags:
        - Layout types: hero_center, split_contrast, surreal_interaction, stage_prop
        - Topic domains: biology, geography, history, space, psychology, technology, general
        - Contextual flags: has_hand (bool), has_camera (bool)
        """
        if output_dir is None:
            output_dir = Path("data/temp_collage")
        output_dir.mkdir(parents=True, exist_ok=True)

        clean_hex = color_hex.strip().lstrip("#")
        if len(clean_hex) != 6:
            clean_hex = "1D3557"

        bg_rgb = (int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16))

        # ----------------------------------------------------
        # Layer 0: Flat Kraft/Cardstock Paper Field (1080x1920)
        # ----------------------------------------------------
        layer0_img = Image.new("RGBA", (width, height), (*bg_rgb, 255))
        noise = Image.effect_noise((width, height), 12).convert("L")
        grain = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        grain.putalpha(noise.point(lambda p: int(p * 0.08)))
        layer0_img = Image.alpha_composite(layer0_img, grain)
        layer0_path = str(output_dir / "layer_0_bg.png")
        layer0_img.save(layer0_path, format="PNG")

        # ----------------------------------------------------
        # Layers 1, 2, 3, 4: Assembled by layout type & domain
        # ----------------------------------------------------
        normalized_layout = (layout_type or "hero_center").lower().strip()
        if normalized_layout not in ["hero_center", "split_contrast", "surreal_interaction", "stage_prop"]:
            normalized_layout = "hero_center"

        normalized_domain = (topic_domain or "general").lower().strip()

        logger.info(
            f"📐 Bố cục: [{normalized_layout}] | Domain: [{normalized_domain}] | "
            f"Hand: {has_hand} | Camera: {has_camera} | "
            f"Focal: {Path(focal_sticker_path).name if focal_sticker_path else 'None'}"
        )

        layer1_canvas, layer2_canvas, layer3_canvas, layer4_canvas = self._build_layout_layers(
            layout_type=normalized_layout,
            topic_domain=normalized_domain,
            focal_sticker_path=focal_sticker_path,
            secondary_sticker_path=secondary_sticker_path,
            has_hand=has_hand,
            has_camera=has_camera,
            width=width,
            height=height
        )

        layer1_path = str(output_dir / "layer_1_prop.png")
        layer1_canvas.save(layer1_path, format="PNG")

        layer2_path = str(output_dir / "layer_2_lighting.png")
        layer2_canvas.save(layer2_path, format="PNG")

        layer3_path = str(output_dir / "layer_3_chars.png")
        layer3_canvas.save(layer3_path, format="PNG")

        layer4_path = str(output_dir / "layer_4_hand.png")
        layer4_canvas.save(layer4_path, format="PNG")

        # ----------------------------------------------------
        # Composite Final Frame (last-frame.png)
        # ----------------------------------------------------
        composite = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        composite.paste(layer0_img, (0, 0))
        composite.paste(layer1_canvas, (0, 0), mask=layer1_canvas)
        composite.paste(layer2_canvas, (0, 0), mask=layer2_canvas)
        composite.paste(layer3_canvas, (0, 0), mask=layer3_canvas)
        composite.paste(layer4_canvas, (0, 0), mask=layer4_canvas)

        last_frame_path = str(output_dir / "last-frame.png")
        composite.convert("RGB").save(last_frame_path, format="PNG")
        logger.success(f"🎨 Đã ghép tác phẩm [{normalized_domain} | {normalized_layout}]: {last_frame_path}")

        return {
            "layer_0_bg": layer0_path,
            "layer_1_prop": layer1_path,
            "layer_2_lighting": layer2_path,
            "layer_3_chars": layer3_path,
            "layer_4_hand": layer4_path,
            "last_frame": last_frame_path
        }

    def _load_and_scale_sticker(self, sticker_path: Optional[str], target_max_w: int, target_max_h: int) -> Optional[Image.Image]:
        """Tải và scale ảnh sticker giữ tỷ lệ khung hình."""
        if not sticker_path or not os.path.exists(sticker_path):
            return None
        try:
            img = Image.open(sticker_path).convert("RGBA")
            scale = min(target_max_w / img.width, target_max_h / img.height)
            if scale > 1.2:
                scale = 1.2
            new_w = max(10, int(img.width * scale))
            new_h = max(10, int(img.height * scale))
            return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        except Exception as e:
            logger.warning(f"Không thể đọc sticker {sticker_path}: {e}")
            return None

    def _draw_domain_environment(self, canvas: Image.Image, domain: str, layout: str, width: int, height: int):
        """Vẽ đồ họa môi trường Layer 1 thích ứng theo từng Domain chủ đề."""
        draw = ImageDraw.Draw(canvas)
        cx, cy = width // 2, int(height * 0.48)

        if domain == "biology":
            # Thị trường kính hiển vi sinh học: vòng tròn quang học, dấu thập crosshair và thang đo micromet
            draw.ellipse([cx - 360, cy - 360, cx + 360, cy + 360], outline=(255, 255, 255, 35), width=3)
            draw.ellipse([cx - 380, cy - 380, cx + 380, cy + 380], outline=(255, 255, 255, 15), width=1)
            # Thước đo crosshair
            draw.line([(cx - 370, cy), (cx + 370, cy)], fill=(255, 255, 255, 25), width=1)
            draw.line([(cx, cy - 370), (cx, cy + 370)], fill=(255, 255, 255, 25), width=1)
            # Thang đo vạch chia micromet (micrometer ticks)
            for tick in range(-300, 301, 50):
                draw.line([(cx + tick, cy - 10), (cx + tick, cy + 10)], fill=(255, 255, 255, 30), width=1)
                draw.line([(cx - 10, cy + tick), (cx + 10, cy + tick)], fill=(255, 255, 255, 30), width=1)

        elif domain == "geography":
            # Hải đồ hàng hải: lưới tọa độ kinh vĩ độ, hoa tiêu la bàn và đường đẳng sâu bathymetric
            for x in range(100, width, 180):
                draw.line([(x, int(height * 0.15)), (x, int(height * 0.85))], fill=(255, 255, 255, 18), width=1)
            for y in range(int(height * 0.15), int(height * 0.85), 180):
                draw.line([(100, y), (width - 100, y)], fill=(255, 255, 255, 18), width=1)
            # Các đường đồng mức đẳng sâu (depth contour rings)
            draw.ellipse([cx - 320, cy - 280, cx + 320, cy + 280], outline=(255, 255, 255, 28), width=2)
            draw.ellipse([cx - 240, cy - 200, cx + 240, cy + 200], outline=(255, 255, 255, 22), width=1)
            draw.ellipse([cx - 150, cy - 120, cx + 150, cy + 120], outline=(255, 255, 255, 18), width=1)

        elif domain == "history":
            # Khung viền văn thư cổ / con dấu hoàng gia / góc tem bưu chính cổ điển
            pad = 90
            draw.rectangle([pad, int(height * 0.14), width - pad, int(height * 0.82)], outline=(255, 255, 255, 30), width=3)
            draw.rectangle([pad + 12, int(height * 0.14) + 12, width - pad - 12, int(height * 0.82) - 12], outline=(255, 255, 255, 15), width=1)
            # Dấu sáp tròn hoàng gia
            draw.ellipse([cx - 220, cy - 220, cx + 220, cy + 220], outline=(255, 255, 255, 25), width=2)
            draw.ellipse([cx - 190, cy - 190, cx + 190, cy + 190], outline=(255, 255, 255, 15), width=1)

        elif domain == "space":
            # Quỹ đạo elip hành tinh và mạng lưới chòm sao thiên văn
            draw.arc([cx - 420, cy - 160, cx + 420, cy + 160], start=0, end=360, fill=(255, 255, 255, 30), width=2)
            draw.arc([cx - 280, cy - 280, cx + 280, cy + 280], start=0, end=360, fill=(255, 255, 255, 22), width=1)
            draw.arc([cx - 160, cy - 380, cx + 160, cy + 380], start=0, end=360, fill=(255, 255, 255, 18), width=1)
            # Các điểm nút sao (star nodes)
            star_points = [(cx - 250, cy - 120), (cx + 210, cy - 180), (cx + 180, cy + 220), (cx - 190, cy + 160)]
            for sx, sy in star_points:
                draw.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=(255, 255, 255, 60))

        elif domain == "psychology":
            # Trục đối lập và cán cân phân định tâm lý
            draw.line([(width // 2, int(height * 0.18)), (width // 2, int(height * 0.78))], fill=(255, 255, 255, 35), width=3)
            draw.line([(int(width * 0.15), cy), (int(width * 0.85), cy)], fill=(255, 255, 255, 25), width=2)
            draw.ellipse([cx - 260, cy - 260, cx + 260, cy + 260], outline=(255, 255, 255, 20), width=2)

        else:
            # General / Technology: Lưới schematic tối giản
            draw.rectangle([cx - 290, cy - 290, cx + 290, cy + 290], outline=(255, 255, 255, 25), width=2)
            draw.rectangle([cx - 270, cy - 270, cx + 270, cy + 270], outline=(255, 255, 255, 12), width=1)

    def _draw_domain_stage(self, canvas: Image.Image, domain: str, width: int, height: int):
        """Vẽ bục sân khấu phối cảnh sạch sẽ theo từng Domain cho layout stage_prop."""
        draw = ImageDraw.Draw(canvas)
        base_y = int(height * 0.58)

        if domain == "biology":
            # Đĩa petri / phiến kính hiển vi elip cách điệu
            draw.ellipse([int(width * 0.12), base_y - 80, int(width * 0.88), base_y + 120], fill=(245, 245, 240, 190), outline=(255, 255, 255, 240), width=6)
            draw.ellipse([int(width * 0.15), base_y - 65, int(width * 0.85), base_y + 105], outline=(180, 180, 180, 160), width=3)

        elif domain == "geography":
            # Bục trầm tích đáy biển / thềm đá phối cảnh
            pts = [
                (int(width * 0.16), base_y),
                (int(width * 0.84), base_y),
                (int(width * 0.94), base_y + 110),
                (int(width * 0.06), base_y + 110)
            ]
            draw.polygon(pts, fill=(230, 225, 215, 210), outline=(255, 255, 255, 240))
            draw.line([(int(width * 0.06), base_y + 110), (int(width * 0.06), base_y + 140),
                       (int(width * 0.94), base_y + 140), (int(width * 0.94), base_y + 110)], fill=(160, 155, 145, 230), width=4)

        elif domain == "history":
            # Bệ đá cổ Ai Cập / bia đá sa thạch phối cảnh
            pts = [
                (int(width * 0.18), base_y - 20),
                (int(width * 0.82), base_y - 20),
                (int(width * 0.90), base_y + 90),
                (int(width * 0.10), base_y + 90)
            ]
            draw.polygon(pts, fill=(242, 234, 212, 220), outline=(255, 255, 255, 240))
            draw.line([(int(width * 0.10), base_y + 90), (int(width * 0.10), base_y + 125),
                       (int(width * 0.90), base_y + 125), (int(width * 0.90), base_y + 90)], fill=(190, 180, 155, 240), width=4)

        else:
            # Bục trưng bày hình học editorial thanh lịch
            pts = [
                (int(width * 0.18), base_y),
                (int(width * 0.82), base_y),
                (int(width * 0.90), base_y + 100),
                (int(width * 0.10), base_y + 100)
            ]
            draw.polygon(pts, fill=(245, 242, 235, 210), outline=(255, 255, 255, 240))

    def _build_layout_layers(
        self,
        layout_type: str,
        topic_domain: str,
        focal_sticker_path: Optional[str],
        secondary_sticker_path: Optional[str],
        has_hand: bool,
        has_camera: bool,
        width: int,
        height: int
    ) -> Tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
        """Xây dựng 4 layers theo đúng mẫu bố cục, domain và cờ ngữ cảnh chỉ định."""
        l1 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        l2 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        l3 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        l4 = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        # Tải sticker chính và phụ
        focal_img = self._load_and_scale_sticker(focal_sticker_path, int(width * 0.65), int(height * 0.45))
        sec_img = self._load_and_scale_sticker(secondary_sticker_path, int(width * 0.38), int(height * 0.28))

        # Ánh sáng chung
        cone_file = self.assets_dir / "lighting" / "yellow_light_cone.png"
        cam_file = self.assets_dir / "props" / "vintage_camera.png"
        pointing_hand_file = self.assets_dir / "hands" / "vintage_pointing_hand.png"

        # 1. Vẽ Layer 1: Môi trường đồ họa theo Domain
        self._draw_domain_environment(l1, topic_domain, layout_type, width, height)

        if layout_type == "stage_prop":
            # Bục sân khấu sạch sẽ theo domain
            self._draw_domain_stage(l1, topic_domain, width, height)

            # Layer 2: Luồng sáng spotlight rọi xuống bục
            if cone_file.exists():
                c_img = Image.open(cone_file).convert("RGBA")
                cw = int(width * 0.72)
                ch = int(height * 0.48)
                cone_r = c_img.resize((cw, ch), Image.Resampling.LANCZOS)
                l2.paste(cone_r, ((width - cw) // 2, int(height * 0.32)), mask=cone_r)

            # Layer 3: Vật thể đứng trên bục
            if focal_img:
                fx = (width - focal_img.width) // 2
                fy = int(height * 0.54) - focal_img.height
                l3.paste(focal_img, (fx, fy), mask=focal_img)

            if sec_img:
                sx = int(width * 0.68)
                sy = int(height * 0.58)
                l3.paste(sec_img, (sx, sy), mask=sec_img)

        elif layout_type == "split_contrast":
            # Layer 1: Thêm đường phân tách đối xứng nhẹ
            draw1 = ImageDraw.Draw(l1)
            draw1.line([(width // 2, int(height * 0.18)), (width // 2, int(height * 0.78))], fill=(255, 255, 255, 30), width=3)

            # Layer 2: Luồng sáng đôi 2 bên
            if cone_file.exists():
                c_img = Image.open(cone_file).convert("RGBA")
                cw = int(width * 0.48)
                ch = int(height * 0.45)
                cone_r = c_img.resize((cw, ch), Image.Resampling.LANCZOS)
                l2.paste(cone_r, (int(width * 0.04), int(height * 0.30)), mask=cone_r)
                l2.paste(cone_r.transpose(Image.FLIP_LEFT_RIGHT), (int(width * 0.48), int(height * 0.30)), mask=cone_r.transpose(Image.FLIP_LEFT_RIGHT))

            # Layer 3: Vật thể chính bên trái, Vật thể phụ bên phải
            if focal_img:
                fx = int(width * 0.28) - (focal_img.width // 2)
                fy = int(height * 0.48) - (focal_img.height // 2)
                l3.paste(focal_img, (fx, fy), mask=focal_img)

            if sec_img:
                sx = int(width * 0.72) - (sec_img.width // 2)
                sy = int(height * 0.48) - (sec_img.height // 2)
                l3.paste(sec_img, (sx, sy), mask=sec_img)

        elif layout_type == "surreal_interaction":
            # Layer 2: Luồng sáng từ trên tỏa xuống
            if cone_file.exists():
                c_img = Image.open(cone_file).convert("RGBA")
                cw = int(width * 0.80)
                ch = int(height * 0.52)
                cone_r = c_img.resize((cw, ch), Image.Resampling.LANCZOS)
                l2.paste(cone_r, ((width - cw) // 2, int(height * 0.26)), mask=cone_r)

            # Layer 3: Focal sticker ở giữa
            if focal_img:
                fx = (width - focal_img.width) // 2
                fy = int(height * 0.50) - (focal_img.height // 2)
                l3.paste(focal_img, (fx, fy), mask=focal_img)

            if sec_img:
                sx = int(width * 0.68)
                sy = int(height * 0.64)
                l3.paste(sec_img, (sx, sy), mask=sec_img)

        else:
            # hero_center (mặc định)
            # Layer 2: Vầng sáng trung tâm
            if cone_file.exists():
                c_img = Image.open(cone_file).convert("RGBA")
                cw = int(width * 0.70)
                ch = int(height * 0.45)
                cone_r = c_img.resize((cw, ch), Image.Resampling.LANCZOS)
                l2.paste(cone_r, ((width - cw) // 2, int(height * 0.28)), mask=cone_r)

            # Layer 3: Focal sticker ở trung tâm uy nghi
            if focal_img:
                fx = (width - focal_img.width) // 2
                fy = int(height * 0.46) - (focal_img.height // 2)
                l3.paste(focal_img, (fx, fy), mask=focal_img)

            if sec_img:
                sx = int(width * 0.65)
                sy = int(height * 0.62)
                l3.paste(sec_img, (sx, sy), mask=sec_img)

        # ----------------------------------------------------
        # Layer 4: Contextual Accents (Chỉ xuất hiện khi kịch bản yêu cầu)
        # ----------------------------------------------------
        # Bàn tay chỉ dẫn / can thiệp (chỉ hiện khi has_hand = True)
        if has_hand and pointing_hand_file.exists():
            h_img = Image.open(pointing_hand_file).convert("RGBA")
            hw = int(width * 0.42)
            hh = int(h_img.height * (hw / h_img.width))
            h_r = h_img.resize((hw, hh), Image.Resampling.LANCZOS)
            # Đặt ở góc trên phải chỉ xuống hoặc xoay góc phù hợp
            l4.paste(h_r, (int(width * 0.58), int(height * 0.16)), mask=h_r)
            logger.info("👉 [Layer 4 Accent] Đã thêm bàn tay chỉ dẫn cổ điển theo kịch bản.")

        # Máy quay truyền thông (chỉ hiện khi has_camera = True)
        if has_camera and cam_file.exists():
            cm_img = Image.open(cam_file).convert("RGBA")
            cam_w = int(width * 0.25)
            cam_h = int(cm_img.height * (cam_w / cm_img.width))
            cam_r = cm_img.resize((cam_w, cam_h), Image.Resampling.LANCZOS)
            l4.paste(cam_r, ((width - cam_w) // 2, int(height * 0.78)), mask=cam_r)
            logger.info("🎥 [Layer 4 Accent] Đã thêm máy quay cổ điển theo kịch bản.")

        return l1, l2, l3, l4

    def apply_paper_cutout_styling(
        self,
        img: Optional[Image.Image] = None,
        outline_width: int = 9,
        shadow_offset: Tuple[int, int] = (12, 14),
        shadow_blur: int = 10,
        pad: int = 55,
        shadow_alpha: int = 120,
        outline_color: Tuple[int, int, int, int] = (255, 253, 247, 255)
    ) -> Image.Image:
        """
        Thêm hiệu ứng giấy cắt dán thủ công chuẩn gbro-collage-broll cao cấp:
        1. Viền giấy trắng kem (cream outline #FFFDF7) dày 9px xung quanh viền cắt.
        2. Bóng đổ vật lý 3D (drop shadow): Gaussian blur 10px, chếch (12, 14), độ mờ ~47% (alpha 120).
        3. Padded canvas 55px tránh xén cụt viền.
        CRITICAL VISUAL FIX: shadow_mask PHẢI được tạo từ dilated_mask.filter(GaussianBlur)
        thay vì từ alpha gốc. Điều này đảm bảo bóng đổ 3D xuất phát từ mép viền giấy cắt 9px
        thay vì bị viền giấy cắt che khuất hoặc cắt cụt.
        """
        if isinstance(self, Image.Image):
            target_img = self
        else:
            target_img = img

        return apply_paper_cutout_styling(
            img=target_img,
            outline_width=outline_width,
            shadow_offset=shadow_offset,
            shadow_blur=shadow_blur,
            pad=pad,
            shadow_alpha=shadow_alpha,
            outline_color=outline_color
        )

    def draw_environment_graphic(self, canvas: Image.Image, graphic_type: str, width: int = 1080, height: int = 1920):
        """Vẽ đồ họa môi trường Layer 1 theo chỉ định."""
        draw = ImageDraw.Draw(canvas)
        cx, cy = width // 2, int(height * 0.48)
        gt = (graphic_type or "microscope_reticle").lower().strip()

        if "microscope" in gt or "reticle" in gt:
            draw.ellipse([cx - 380, cy - 380, cx + 380, cy + 380], outline=(255, 255, 255, 40), width=3)
            draw.ellipse([cx - 400, cy - 400, cx + 400, cy + 400], outline=(255, 255, 255, 20), width=1)
            draw.line([(cx - 390, cy), (cx + 390, cy)], fill=(255, 255, 255, 30), width=1)
            draw.line([(cx, cy - 390), (cx, cy + 390)], fill=(255, 255, 255, 30), width=1)
            for tick in range(-320, 321, 40):
                draw.line([(cx + tick, cy - 12), (cx + tick, cy + 12)], fill=(255, 255, 255, 35), width=1)
                draw.line([(cx - 12, cy + tick), (cx + 12, cy + tick)], fill=(255, 255, 255, 35), width=1)

        elif "grid" in gt or "coordinate" in gt or "nautical" in gt:
            for x in range(80, width, 160):
                draw.line([(x, int(height * 0.12)), (x, int(height * 0.88))], fill=(255, 255, 255, 20), width=1)
            for y in range(int(height * 0.12), int(height * 0.88), 160):
                draw.line([(80, y), (width - 80, y)], fill=(255, 255, 255, 20), width=1)
            draw.ellipse([cx - 320, cy - 280, cx + 320, cy + 280], outline=(255, 255, 255, 32), width=2)
            draw.ellipse([cx - 200, cy - 160, cx + 200, cy + 160], outline=(255, 255, 255, 22), width=1)

        elif "ruler" in gt or "scale" in gt or "press" in gt or "isometric" in gt or "mechanic" in gt:
            draw.rectangle([cx - 340, cy - 420, cx + 340, cy + 420], outline=(255, 255, 255, 28), width=2)
            draw.rectangle([cx - 320, cy - 400, cx + 320, cy + 400], outline=(255, 255, 255, 14), width=1)
            for ry in range(cy - 400, cy + 401, 35):
                draw.line([(cx - 320, ry), (cx - 300, ry)], fill=(255, 255, 255, 40), width=2)
                draw.line([(cx + 300, ry), (cx + 320, ry)], fill=(255, 255, 255, 40), width=2)
            for rx in range(cx - 320, cx + 321, 45):
                draw.line([(rx, cy + 380), (rx, cy + 400)], fill=(255, 255, 255, 40), width=2)

        elif "papyrus" in gt or "relic" in gt or "history" in gt:
            pad = 85
            draw.rectangle([pad, int(height * 0.12), width - pad, int(height * 0.84)], outline=(255, 255, 255, 32), width=4)
            draw.rectangle([pad + 14, int(height * 0.12) + 14, width - pad - 14, int(height * 0.84) - 14], outline=(255, 255, 255, 18), width=1)
            draw.ellipse([cx - 210, cy - 210, cx + 210, cy + 210], outline=(255, 255, 255, 28), width=2)

        else:  # depth_contours / generic
            draw.ellipse([cx - 360, cy - 320, cx + 360, cy + 320], outline=(255, 255, 255, 30), width=2)
            draw.ellipse([cx - 260, cy - 220, cx + 260, cy + 220], outline=(255, 255, 255, 24), width=2)
            draw.ellipse([cx - 160, cy - 130, cx + 160, cy + 130], outline=(255, 255, 255, 18), width=1)

    def compose_multi_element_layers(
        self,
        scene_layout: Dict[str, Any],
        hero_asset_path: str,
        secondary_asset_path: str,
        width: int = 1080,
        height: int = 1920
    ) -> Dict[str, Image.Image]:
        """
        Lắp ráp 5 tầng độc lập cho cảnh đa vật thể tương tác:
        - Layer 0: Flat cardstock paper field (1080x1920)
        - Layer 1: Environment graphic (PIL drawn)
        - Layer 2: Secondary element (styled with cream outline + drop shadow)
        - Layer 3: Hero element (styled with cream outline + drop shadow)
        - Layer 4: Contextual accents (Victorian pointing hand)
        - last_frame: Completed composite frame
        """
        color_field = scene_layout.get("color_field")
        raw_hex = scene_layout.get("color_hex")
        if not raw_hex and isinstance(color_field, dict):
            raw_hex = color_field.get("hex")
        elif not raw_hex and isinstance(color_field, str) and color_field.startswith("#"):
            raw_hex = color_field

        color_hex = str(raw_hex or "1D3557").strip().lstrip("#")
        if len(color_hex) != 6:
            color_hex = "1D3557"
        bg_rgb = (int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16))

        # Layer 0: Flat Cardstock Paper Field
        l0_bg = Image.new("RGBA", (width, height), (*bg_rgb, 255))
        noise = Image.effect_noise((width, height), 12).convert("L")
        grain = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        grain.putalpha(noise.point(lambda p: int(p * 0.08)))
        l0_bg = Image.alpha_composite(l0_bg, grain)

        # Layer 1: Environment Graphic
        l1_env = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        env_name = scene_layout.get("environment_graphic", "microscope_reticle")
        self.draw_environment_graphic(l1_env, env_name, width, height)

        # Layer 2: Secondary Element (Vật bị tác động) & Layer 3: Hero Element (Vật chủ động)
        l2_sec = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        l3_hero = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        sec_cfg = scene_layout.get("secondary_element", {})
        hero_cfg = scene_layout.get("hero_element", {})
        interaction = str(scene_layout.get("interaction_type", "EXAMINING")).upper()

        sec_styled = None
        if os.path.exists(secondary_asset_path):
            sec_raw = Image.open(secondary_asset_path).convert("RGBA")
            sec_scale = sec_cfg.get("scale", sec_cfg.get("scale_factor", 0.32))
            sec_w = int(width * sec_scale)
            sec_h = int(sec_raw.height * (sec_w / sec_raw.width))
            sec_resized = sec_raw.resize((sec_w, sec_h), Image.Resampling.LANCZOS)
            rot = sec_cfg.get("rotation_deg", 0)
            if rot != 0:
                sec_resized = sec_resized.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
            sec_styled = self.apply_paper_cutout_styling(sec_resized)

        hero_styled = None
        if os.path.exists(hero_asset_path):
            hero_raw = Image.open(hero_asset_path).convert("RGBA")
            hero_scale = hero_cfg.get("scale", hero_cfg.get("scale_factor", 0.52))
            hero_w = int(width * hero_scale)
            hero_h = int(hero_raw.height * (hero_w / hero_raw.width))
            hero_resized = hero_raw.resize((hero_w, hero_h), Image.Resampling.LANCZOS)
            rot = hero_cfg.get("rotation_deg", 0)
            if rot != 0:
                hero_resized = hero_resized.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
            hero_styled = self.apply_paper_cutout_styling(hero_resized)

        # Tính toán cự ly tương tác vật lý (Spatial Proximity)
        if hero_styled and sec_styled:
            is_pressing = any(act in interaction for act in ["PRESS", "CRUSH", "SQUEEZE", "ENGULF", "SWALLOW", "STAMP", "OPPRESS"])
            is_examining = any(act in interaction for act in ["EXAMIN", "INSPECT", "OBSERVE", "MEASUR", "SCAN"])

            if is_pressing:
                # Chạm nhẹ / Đè ép: Overlap 7-9% chiều cao của vật thể secondary
                overlap_px = max(20, int(sec_styled.height * 0.08))
                total_h = hero_styled.height + sec_styled.height - overlap_px
                cluster_cy = int(height * 0.52)
                hero_py = max(int(height * 0.15), cluster_cy - total_h // 2)
                sec_py = hero_py + hero_styled.height - overlap_px
                hero_px = int(width * 0.50) - hero_styled.width // 2
                sec_px = int(width * 0.50) - sec_styled.width // 2
            elif is_examining:
                # Soi/Quan sát: Cự ly gần với khoảng cách 35px
                gap_px = 35
                total_h = hero_styled.height + sec_styled.height + gap_px
                cluster_cy = int(height * 0.50)
                hero_py = max(int(height * 0.15), cluster_cy - total_h // 2)
                sec_py = hero_py + hero_styled.height + gap_px
                hero_px = int(width * 0.50) - hero_styled.width // 2
                sec_px = int(width * 0.50) - sec_styled.width // 2
            else:
                # Các tương tác khác: giữ cự ly hợp lý 50px
                gap_px = 50
                total_h = hero_styled.height + sec_styled.height + gap_px
                cluster_cy = int(height * 0.51)
                hero_py = max(int(height * 0.15), cluster_cy - total_h // 2)
                sec_py = hero_py + hero_styled.height + gap_px
                hero_px = int(width * 0.50) - hero_styled.width // 2
                sec_px = int(width * 0.50) - sec_styled.width // 2

            l2_sec.paste(sec_styled, (sec_px, sec_py), mask=sec_styled)
            l3_hero.paste(hero_styled, (hero_px, hero_py), mask=hero_styled)

        else:
            # Fallback nếu chỉ có 1 vật thể
            if sec_styled:
                raw_pos = sec_cfg.get("position", [0.5, 0.70])
                if isinstance(raw_pos, dict):
                    cx = raw_pos.get("x", 540)
                    cy = raw_pos.get("y", 1300)
                    px = int(cx if cx > 1.0 else cx * width) - sec_styled.width // 2
                    py = int(cy if cy > 1.0 else cy * height) - sec_styled.height // 2
                else:
                    px = int(width * raw_pos[0]) - sec_styled.width // 2
                    py = int(height * raw_pos[1]) - sec_styled.height // 2
                l2_sec.paste(sec_styled, (px, py), mask=sec_styled)

            if hero_styled:
                raw_pos = hero_cfg.get("position", [0.5, 0.45])
                if isinstance(raw_pos, dict):
                    cx = raw_pos.get("x", 540)
                    cy = raw_pos.get("y", 850)
                    px = int(cx if cx > 1.0 else cx * width) - hero_styled.width // 2
                    py = int(cy if cy > 1.0 else cy * height) - hero_styled.height // 2
                else:
                    px = int(width * raw_pos[0]) - hero_styled.width // 2
                    py = int(height * raw_pos[1]) - hero_styled.height // 2
                l3_hero.paste(hero_styled, (px, py), mask=hero_styled)

        # Layer 4: Contextual Accents (Victorian Pointing Hand)
        l4_hand = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        has_hand = scene_layout.get("has_pointing_hand", False)
        pointing_hand_file = self.assets_dir / "hands" / "vintage_pointing_hand.png"
        if has_hand and pointing_hand_file.exists():
            h_raw = Image.open(pointing_hand_file).convert("RGBA")
            hw = int(width * 0.40)
            hh = int(h_raw.height * (hw / h_raw.width))
            h_resized = h_raw.resize((hw, hh), Image.Resampling.LANCZOS)
            l4_hand.paste(h_resized, (int(width * 0.58), int(height * 0.16)), mask=h_resized)

        # Final Composite
        composite = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        composite.paste(l0_bg, (0, 0))
        composite.paste(l1_env, (0, 0), mask=l1_env)
        composite.paste(l2_sec, (0, 0), mask=l2_sec)
        composite.paste(l3_hero, (0, 0), mask=l3_hero)
        composite.paste(l4_hand, (0, 0), mask=l4_hand)

        return {
            "layer_0": l0_bg,
            "layer_1": l1_env,
            "layer_2": l2_sec,
            "layer_3": l3_hero,
            "layer_4": l4_hand,
            "composite": composite
        }

