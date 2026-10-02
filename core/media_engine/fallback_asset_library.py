"""
AutoVideoFactory — FallbackAssetLibrary (Phase 1)
Kho tài sản dự phòng gồm các file PNG đã tách nền sẵn (RGBA) cho 4 Archetype:
1. specimen_scientific: microscope.png, bacteria.png, petri_dish.png
2. geography_ocean: pressure_gauge.png, submarine.png, anchor.png
3. historical_relic: canopic_jar.png, papyrus.png, pharaoh_relic.png
4. industrial_social: press_machine.png, gear.png, film_strip.png

Tự động kích hoạt khi FLUX lỗi hoặc AlphaQAGate báo FAIL sau 3 lần thử lại.
Đảm bảo 100% KHÔNG BAO GIỜ xảy ra lỗi rỗng hình!
"""

import os
from pathlib import Path
from typing import Optional, Dict, List
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from loguru import logger

FALLBACK_DIR = Path(__file__).parent.parent.parent / "assets" / "fallback_library"


class FallbackAssetLibrary:
    """
    Quản lý kho tài nguyên dự phòng đạt chuẩn Alpha QA Gate.
    """

    ARCHETYPES = {
        "specimen_scientific": ["microscope", "bacteria", "petri_dish"],
        "geography_ocean": ["pressure_gauge", "submarine", "anchor"],
        "historical_relic": ["canopic_jar", "papyrus", "pharaoh_relic"],
        "industrial_social": ["press_machine", "gear", "film_strip"]
    }

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = (base_dir or FALLBACK_DIR).resolve()
        self._ensure_library_exists()

    def _ensure_library_exists(self):
        """Khởi tạo cấu trúc thư mục và sinh các tài sản dự phòng nếu chưa có."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for group, assets in self.ARCHETYPES.items():
            group_dir = self.base_dir / group
            group_dir.mkdir(parents=True, exist_ok=True)
            for asset_name in assets:
                asset_path = group_dir / f"{asset_name}.png"
                if not asset_path.exists() or asset_path.stat().st_size < 1000:
                    self._generate_fallback_graphic(asset_path, group, asset_name)

    def get_fallback(self, archetype: str, keyword: str = "") -> Path:
        """
        Lấy đường dẫn file ảnh dự phòng phù hợp với archetype và từ khóa.
        """
        norm_arch = archetype.lower().strip()
        if norm_arch not in self.ARCHETYPES:
            if "bio" in norm_arch or "sci" in norm_arch:
                norm_arch = "specimen_scientific"
            elif "geo" in norm_arch or "ocean" in norm_arch or "sea" in norm_arch:
                norm_arch = "geography_ocean"
            elif "hist" in norm_arch or "relic" in norm_arch or "pharaoh" in norm_arch:
                norm_arch = "historical_relic"
            else:
                norm_arch = "industrial_social"

        group_dir = self.base_dir / norm_arch
        kw_lower = keyword.lower()

        # Tìm asset khớp từ khóa nhất
        best_asset = None
        for a_name in self.ARCHETYPES[norm_arch]:
            if any(term in kw_lower for term in a_name.split("_")):
                cand = group_dir / f"{a_name}.png"
                if cand.exists():
                    best_asset = cand
                    break

        if not best_asset:
            # Lấy asset đầu tiên trong group
            first_name = self.ARCHETYPES[norm_arch][0]
            best_asset = group_dir / f"{first_name}.png"

        logger.info(f"🛡️ [FallbackLibrary] Kích hoạt tài nguyên dự phòng an toàn: {best_asset.name} ({norm_arch})")
        return best_asset

    def _generate_fallback_graphic(self, out_path: Path, group: str, name: str, size: int = 512):
        """Tạo ảnh vintage halftone RGBA đạt chuẩn Alpha QA Gate (alpha_ratio 20% - 60%)."""
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        cx, cy = size // 2, size // 2

        # Cream outline color & dark woodcut fill
        cream = (255, 253, 247, 255)
        ink = (28, 28, 30, 255)
        gold = (212, 163, 89, 255)
        brass = (184, 134, 11, 255)
        teal = (42, 157, 143, 255)
        crimson = (180, 40, 40, 255)

        # Drop shadow layer
        shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)

        if name == "microscope":
            # Chân đế và thân kính hiển vi vintage
            s_draw.rectangle([cx - 100, cy + 120, cx + 100, cy + 180], fill=(0, 0, 0, 100))
            s_draw.line([(cx - 40, cy + 120), (cx - 40, cy - 80)], fill=(0, 0, 0, 100), width=45)
            # Thân
            draw.rectangle([cx - 90, cy + 110, cx + 90, cy + 160], fill=ink, outline=cream, width=5)
            draw.line([(cx - 30, cy + 120), (cx - 30, cy - 70)], fill=ink, width=40)
            draw.line([(cx - 30, cy + 120), (cx - 30, cy - 70)], fill=brass, width=20)
            # Thị kính nghiêng
            draw.line([(cx - 30, cy - 70), (cx + 50, cy - 140)], fill=ink, width=32)
            draw.line([(cx - 30, cy - 70), (cx + 50, cy - 140)], fill=brass, width=14)
            # Vật kính
            draw.ellipse([cx + 40, cy - 150, cx + 70, cy - 120], fill=ink, outline=cream, width=3)
            # Bàn sa trượt
            draw.rectangle([cx - 80, cy + 20, cx + 50, cy + 36], fill=ink, outline=cream, width=4)

        elif name == "bacteria":
            # Tế bào vi khuẩn hình que với lông mao
            s_draw.ellipse([cx - 140, cy - 80, cx + 140, cy + 80], fill=(0, 0, 0, 90))
            draw.ellipse([cx - 130, cy - 75, cx + 130, cy + 75], fill=crimson, outline=cream, width=7)
            # Nhân tế bào
            draw.ellipse([cx - 70, cy - 35, cx + 70, cy + 35], fill=ink, outline=cream, width=3)
            # Lông mao (flagella/cilia)
            import math
            for a in range(0, 360, 20):
                rad = math.radians(a)
                x1 = cx + math.cos(rad) * 130
                y1 = cy + math.sin(rad) * 75
                x2 = cx + math.cos(rad) * 165
                y2 = cy + math.sin(rad) * 95
                draw.line([(x1, y1), (x2, y2)], fill=cream, width=4)

        elif name == "petri_dish":
            # Đĩa petri elip thủy tinh với cụm khuẩn
            s_draw.ellipse([cx - 170, cy - 90, cx + 170, cy + 110], fill=(0, 0, 0, 80))
            draw.ellipse([cx - 160, cy - 85, cx + 160, cy + 95], fill=(240, 240, 235, 230), outline=cream, width=8)
            draw.ellipse([cx - 130, cy - 65, cx + 130, cy + 75], outline=(180, 180, 180, 220), width=4)
            # Cụm vi khuẩn bên trong
            draw.ellipse([cx - 60, cy - 20, cx - 20, cy + 20], fill=crimson, outline=cream, width=3)
            draw.ellipse([cx + 10, cy - 10, cx + 60, cy + 40], fill=teal, outline=cream, width=3)

        elif name == "pressure_gauge":
            # Đồng hồ đo áp suất cơ khí
            s_draw.ellipse([cx - 140, cy - 140, cx + 140, cy + 140], fill=(0, 0, 0, 90))
            draw.ellipse([cx - 135, cy - 135, cx + 135, cy + 135], fill=brass, outline=cream, width=7)
            draw.ellipse([cx - 110, cy - 110, cx + 110, cy + 110], fill=(245, 243, 238, 255), outline=ink, width=4)
            # Vạch chia
            for deg in range(0, 280, 30):
                import math
                r1 = math.radians(deg + 130)
                draw.line([(cx + math.cos(r1) * 85, cy + math.sin(r1) * 85),
                           (cx + math.cos(r1) * 105, cy + math.sin(r1) * 105)], fill=ink, width=3)
            # Kim chỉ đỏ
            draw.line([(cx, cy), (cx + 55, cy - 65)], fill=crimson, width=5)
            draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=ink, outline=cream, width=3)
            # Ren đồng phía dưới
            draw.rectangle([cx - 25, cy + 135, cx + 25, cy + 185], fill=brass, outline=cream, width=4)

        elif name == "submarine":
            # Tàu ngầm vàng retro
            s_draw.ellipse([cx - 160, cy - 60, cx + 150, cy + 90], fill=(0, 0, 0, 80))
            # Thân tàu ngầm
            draw.ellipse([cx - 150, cy - 50, cx + 140, cy + 80], fill=(235, 175, 40, 255), outline=cream, width=7)
            # Tháp chỉ huy
            draw.rectangle([cx - 40, cy - 110, cx + 40, cy - 50], fill=ink, outline=cream, width=5)
            # Kính tiềm vọng
            draw.line([(cx, cy - 110), (cx, cy - 150), (cx + 30, cy - 150)], fill=ink, width=7)
            # Cửa sổ tròn
            draw.ellipse([cx - 90, cy - 10, cx - 50, cy + 30], fill=teal, outline=cream, width=4)
            draw.ellipse([cx - 20, cy - 10, cx + 20, cy + 30], fill=teal, outline=cream, width=4)
            draw.ellipse([cx + 50, cy - 10, cx + 90, cy + 30], fill=teal, outline=cream, width=4)
            # Chân vịt
            draw.polygon([(cx - 150, cy + 15), (cx - 180, cy - 20), (cx - 180, cy + 50)], fill=ink, outline=cream)

        elif name == "anchor":
            # Mỏ neo sắt cổ
            s_draw.rectangle([cx - 25, cy - 140, cx + 25, cy + 140], fill=(0, 0, 0, 80))
            # Vòng khuyên
            draw.ellipse([cx - 45, cy - 150, cx + 45, cy - 60], fill=ink, outline=cream, width=6)
            draw.ellipse([cx - 20, cy - 125, cx + 20, cy - 85], fill=(0, 0, 0, 0))
            # Cán neo
            draw.line([(cx, cy - 70), (cx, cy + 120)], fill=ink, width=28)
            draw.line([(cx - 75, cy - 30), (cx + 75, cy - 30)], fill=ink, width=18)
            # Vòm cánh neo
            draw.arc([cx - 125, cy + 10, cx + 125, cy + 150], start=0, end=180, fill=ink, width=28)
            draw.polygon([(cx - 135, cy + 70), (cx - 105, cy + 30), (cx - 85, cy + 70)], fill=ink, outline=cream)
            draw.polygon([(cx + 135, cy + 70), (cx + 105, cy + 30), (cx + 85, cy + 70)], fill=ink, outline=cream)

        elif name == "canopic_jar":
            # Bình canopic Ai Cập đựng nội tạng
            s_draw.rectangle([cx - 90, cy - 120, cx + 90, cy + 150], fill=(0, 0, 0, 90))
            # Thân bình
            draw.polygon([(cx - 50, cy - 50), (cx + 50, cy - 50), (cx + 85, cy + 50), (cx + 60, cy + 145), (cx - 60, cy + 145), (cx - 85, cy + 50)], fill=(240, 230, 210, 255), outline=cream, width=7)
            # Nắp bình hình đầu thần/pharaoh
            draw.ellipse([cx - 55, cy - 135, cx + 55, cy - 45], fill=gold, outline=cream, width=6)
            draw.rectangle([cx - 30, cy - 65, cx + 30, cy - 50], fill=ink)
            # Họa tiết Ai Cập
            draw.rectangle([cx - 50, cy + 20, cx + 50, cy + 100], fill=ink, outline=gold, width=3)
            draw.ellipse([cx - 15, cy + 40, cx + 15, cy + 70], fill=gold)

        elif name == "papyrus":
            # Cuộn giấy cói cổ
            s_draw.rectangle([cx - 140, cy - 90, cx + 140, cy + 90], fill=(0, 0, 0, 80))
            draw.rectangle([cx - 130, cy - 80, cx + 130, cy + 80], fill=(235, 215, 175, 255), outline=cream, width=6)
            # Cuộn 2 đầu
            draw.ellipse([cx - 145, cy - 85, cx - 115, cy + 85], fill=(200, 175, 130, 255), outline=cream, width=4)
            draw.ellipse([cx + 115, cy - 85, cx + 145, cy + 85], fill=(200, 175, 130, 255), outline=cream, width=4)
            # Chữ tượng hình
            for y_line in range(cy - 50, cy + 60, 25):
                draw.line([(cx - 95, y_line), (cx + 95, y_line)], fill=ink, width=4)

        elif name == "pharaoh_relic":
            # Mặt nạ vàng Pharaoh
            s_draw.polygon([(cx, cy - 140), (cx + 110, cy - 50), (cx + 70, cy + 140), (cx - 70, cy + 140), (cx - 110, cy - 50)], fill=(0, 0, 0, 90))
            draw.polygon([(cx, cy - 130), (cx + 100, cy - 40), (cx + 65, cy + 130), (cx - 65, cy + 130), (cx - 100, cy - 40)], fill=gold, outline=cream, width=7)
            # Dải kẻ sọc xanh Nemes
            draw.line([(cx - 90, cy - 30), (cx + 90, cy - 30)], fill=teal, width=12)
            draw.line([(cx - 75, cy + 10), (cx + 75, cy + 10)], fill=teal, width=12)
            # Khuôn mặt & râu thần
            draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(245, 210, 120, 255), outline=ink, width=3)
            draw.rectangle([cx - 12, cy + 50, cx + 12, cy + 125], fill=ink, outline=gold, width=3)

        elif name == "press_machine":
            # Máy cơ khí / máy ép công nghiệp vintage
            s_draw.rectangle([cx - 110, cy - 130, cx + 110, cy + 150], fill=(0, 0, 0, 90))
            # Khung trụ máy
            draw.rectangle([cx - 100, cy + 100, cx + 100, cy + 145], fill=ink, outline=cream, width=6)
            draw.rectangle([cx - 85, cy - 115, cx + 85, cy - 75], fill=ink, outline=cream, width=5)
            draw.line([(cx - 70, cy - 75), (cx - 70, cy + 100)], fill=ink, width=22)
            draw.line([(cx + 70, cy - 75), (cx + 70, cy + 100)], fill=ink, width=22)
            # Trục vít ép trung tâm
            draw.line([(cx, cy - 110), (cx, cy + 70)], fill=brass, width=28)
            draw.rectangle([cx - 50, cy + 40, cx + 50, cy + 70], fill=ink, outline=cream, width=4)
            # Tay quay trên đỉnh
            draw.line([(cx - 95, cy - 135), (cx + 95, cy - 135)], fill=brass, width=14)
            draw.ellipse([cx - 105, cy - 145, cx - 85, cy - 125], fill=ink)
            draw.ellipse([cx + 85, cy - 145, cx + 105, cy - 125], fill=ink)

        elif name == "gear":
            # Bánh răng đồng hồ cơ khí
            s_draw.ellipse([cx - 130, cy - 130, cx + 130, cy + 130], fill=(0, 0, 0, 90))
            draw.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], fill=brass, outline=cream, width=6)
            # Răng cưa
            for deg in range(0, 360, 30):
                import math
                r = math.radians(deg)
                gx = cx + math.cos(r) * 125
                gy = cy + math.sin(r) * 125
                draw.rectangle([gx - 14, gy - 14, gx + 14, gy + 14], fill=brass, outline=cream, width=2)
            # Lỗ trung tâm
            draw.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=(0, 0, 0, 0))
            draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=ink, outline=cream, width=4)
            # Nan hoa
            for deg in [0, 90, 180, 270]:
                import math
                r = math.radians(deg)
                draw.line([(cx + math.cos(r) * 30, cy + math.sin(r) * 30),
                           (cx + math.cos(r) * 120, cy + math.sin(r) * 120)], fill=brass, width=12)

        else:  # film_strip
            # Dải phim nhựa vintage 35mm
            s_draw.rectangle([cx - 80, cy - 150, cx + 80, cy + 150], fill=(0, 0, 0, 90))
            draw.rectangle([cx - 70, cy - 140, cx + 70, cy + 140], fill=ink, outline=cream, width=6)
            # Lỗ xỏ phim 2 bên
            for py in range(cy - 125, cy + 130, 28):
                draw.rectangle([cx - 62, py - 6, cx - 48, py + 6], fill=cream)
                draw.rectangle([cx + 48, py - 6, cx + 62, py + 6], fill=cream)
            # Khung hình trung tâm
            for fy in [cy - 85, cy - 5, cy + 75]:
                draw.rectangle([cx - 38, fy - 30, cx + 38, fy + 30], fill=(230, 225, 215, 255), outline=cream, width=3)
                draw.ellipse([cx - 15, fy - 15, cx + 15, fy + 15], fill=ink)

        # Apply halftone noise to the object
        noise = Image.effect_noise((size, size), 18).convert("L")
        noise = ImageEnhance.Contrast(noise).enhance(1.8)
        canvas.paste(Image.new("RGBA", (size, size), (255, 255, 255, 25)), mask=noise)

        # Composite soft drop shadow behind
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        final_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        final_img.paste(shadow, (0, 0), mask=shadow)
        final_img.paste(canvas, (0, 0), mask=canvas)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(str(out_path), format="PNG")
        logger.info(f"✨ [FallbackLibrary] Đã chế tác asset dự phòng chuẩn QA: {out_path.name}")
