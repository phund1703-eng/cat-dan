"""
AutoVideoFactory — Dynamic Cutout Manager
Quản lý thu nạp, AI tách nền và lưu cache vĩnh viễn các sticker cắt dán:
1. Cơ chế 2 nấc:
   - Ưu tiên 1 (AI Image Gen): Sinh ảnh đơn lập trên phông trắng tinh khiết theo prompt chuẩn.
   - Ưu tiên 2 (Web Search Fallback): Tìm kiếm Wikimedia/Unsplash với truy vấn isolated cutout,
     bắt buộc có bộ lọc tiêu cực (loại bỏ pub, bar, building, facade, people, crowd...).
2. Quality Gate (Alpha Channel Check):
   - Đảm bảo tỷ lệ pixel trong suốt nằm trong khoảng 20% - 85% (không bị rỗng hoàn toàn và không bị đen đặc 100%).
3. Lưu cache vĩnh viễn: data/cache/cutouts/{domain}_{keyword}.png.
"""

import os
import re
import io
import httpx
import asyncio
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from loguru import logger

from core.media_engine.cutout_engine import CutoutEngine


class DynamicCutoutManager:
    """Quản lý và sinh các sticker cắt dán động cho từng cảnh."""

    NEGATIVE_WORDS = [
        "pub", "bar", "building", "facade", "hotel", "house", "street",
        "people", "crowd", "restaurant", "store", "shop", "town", "village",
        "architecture", "group", "cowboy", "portrait", "inn", "party"
    ]

    CURATED_MAP = {
        # Biology
        "white_blood_cell": "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=800&auto=format&fit=crop",
        "macrophage": "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=800&auto=format&fit=crop",
        "leukocyte": "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=800&auto=format&fit=crop",
        "bacterium": "https://images.unsplash.com/photo-1584036561566-baf8f5f1b144?w=800&auto=format&fit=crop",
        "bacteria": "https://images.unsplash.com/photo-1584036561566-baf8f5f1b144?w=800&auto=format&fit=crop",
        "microbe": "https://images.unsplash.com/photo-1584036561566-baf8f5f1b144?w=800&auto=format&fit=crop",
        "microscope": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&auto=format&fit=crop",
        "virus": "https://images.unsplash.com/photo-1584036561566-baf8f5f1b144?w=800&auto=format&fit=crop",
        "dna": "https://images.unsplash.com/photo-1530497610245-94d3c16cda28?w=800&auto=format&fit=crop",
        "cell": "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=800&auto=format&fit=crop",

        # Geography & Oceanography
        "mariana_trench": "https://images.unsplash.com/photo-1682687220063-4742bd7fd538?w=800&auto=format&fit=crop",
        "deep_sea": "https://images.unsplash.com/photo-1682687220063-4742bd7fd538?w=800&auto=format&fit=crop",
        "submarine": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&auto=format&fit=crop",
        "bathyscaphe": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&auto=format&fit=crop",
        "submersible": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&auto=format&fit=crop",
        "anglerfish": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&auto=format&fit=crop",
        "anchor": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop",
        "pressure_gauge": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop",
        "compass": "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?w=800&auto=format&fit=crop",

        # History & Archaeology
        "pharaoh": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800&auto=format&fit=crop",
        "sarcophagus": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800&auto=format&fit=crop",
        "mummy": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800&auto=format&fit=crop",
        "canopic_jar": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=800&auto=format&fit=crop",
        "pyramid": "https://images.unsplash.com/photo-1503177119275-0aa32b3a9368?w=800&auto=format&fit=crop",
        "papyrus": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop",
        "scarab": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=800&auto=format&fit=crop",
        "ankh": "https://images.unsplash.com/photo-1582139329536-e7284fece509?w=800&auto=format&fit=crop",

        # Space & Cosmos
        "black_hole": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop",
        "galaxy": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=800&auto=format&fit=crop",
        "planet": "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=800&auto=format&fit=crop",
        "astronaut": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=800&auto=format&fit=crop",
        "telescope": "https://images.unsplash.com/photo-1528722828814-77b9b83aafb2?w=800&auto=format&fit=crop",
        "hourglass": "https://images.unsplash.com/photo-1518241353330-0f7941c2d9b5?w=800&auto=format&fit=crop",
        "clock": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&auto=format&fit=crop",

        # Psychology & Technology
        "brain": "https://images.unsplash.com/photo-1559757175-5700dde675bc?w=800&auto=format&fit=crop",
        "scale": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&auto=format&fit=crop",
        "golden_scale": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&auto=format&fit=crop",
        "light_bulb": "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=800&auto=format&fit=crop",
        "incandescent_bulb": "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=800&auto=format&fit=crop",
        "golden_key": "https://images.unsplash.com/photo-1582139329536-e7284fece509?w=800&auto=format&fit=crop",
        "key": "https://images.unsplash.com/photo-1582139329536-e7284fece509?w=800&auto=format&fit=crop",
        "chains": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop",
        "mask": "https://images.unsplash.com/photo-1549488344-cbb6c34cf08b?w=800&auto=format&fit=crop",
        "vintage_camera": "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=800&auto=format&fit=crop"
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            self.cache_dir = Path("data/cache/cutouts")
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cutout_engine = CutoutEngine()
        self.assets_dir = Path("assets/collage_assets")
        self.api_keys = [
            k.strip() for k in [
                os.getenv("GEMINI_API_KEY_1"),
                os.getenv("GEMINI_API_KEY_2"),
                os.getenv("GEMINI_API_KEY")
            ] if k and k.strip() and not k.strip().startswith("your_")
        ]
        self.current_key_idx = 0

    def _sanitize_keyword(self, keyword: str) -> str:
        """Chuẩn hóa từ khóa thành tên file an toàn."""
        clean = re.sub(r"[^\w\s-]", "", keyword.lower().strip())
        clean = re.sub(r"[-\s]+", "_", clean)
        return clean or "element"

    def check_alpha_quality_gate(self, img: Image.Image) -> Tuple[bool, float]:
        """
        Quality Gate: Kiểm tra tỷ lệ pixel trong suốt trong kênh Alpha.
        Yêu cầu: tỷ lệ pixel trong suốt (alpha == 0) nằm trong khoảng 20% - 85%
        (không bị rỗng hoàn toàn và không bị đen đặc / giữ nguyên khối chữ nhật).
        """
        if "A" not in img.getbands():
            return False, 0.0

        alpha = np.array(img.getchannel("A"))
        total_pixels = alpha.size
        transparent_pixels = np.sum(alpha == 0)
        trans_ratio = transparent_pixels / total_pixels

        is_valid = 0.20 <= trans_ratio <= 0.85
        return is_valid, trans_ratio

    async def get_cutout_sticker(
        self,
        keyword: str,
        domain: str = "general",
        is_character: bool = False,
        fallback_scene_index: int = 0
    ) -> str:
        """
        Lấy hoặc sinh sticker cắt dán PNG trong suốt theo cơ chế 2 nấc:
        Ưu tiên 1: AI Image Gen (nền trắng tinh khiết) + rembg.
        Ưu tiên 2: Web Search Fallback (Wikimedia Commons / Unsplash + Negative Filter).
        Quality Gate: Kiểm tra tỷ lệ Alpha [20% - 85%].
        Cache: data/cache/cutouts/{domain}_{keyword}.png.
        """
        if not keyword or keyword.strip().lower() == "none":
            return ""

        safe_domain = self._sanitize_keyword(domain or "general")
        safe_key = self._sanitize_keyword(keyword)
        cached_file = self.cache_dir / f"{safe_domain}_{safe_key}.png"

        # 1. Kiểm tra cache
        if cached_file.exists() and cached_file.stat().st_size > 4000:
            try:
                test_img = Image.open(cached_file)
                valid, ratio = self.check_alpha_quality_gate(test_img)
                if valid:
                    logger.info(f"⚡ [Sticker Cache HIT] ({safe_domain}) {cached_file.name} (trans={ratio:.2f})")
                    return str(cached_file.resolve())
                else:
                    logger.warning(f"⚠️ [Sticker Cache INVALID] {cached_file.name} không đạt Quality Gate ({ratio:.2f}), tái tạo...")
            except Exception:
                pass

        logger.info(f"🔍 [Sticker Harvester] Thu nạp sticker cho '{keyword}' (domain: {safe_domain})...")

        # 2. ƯU TIÊN 1: Thử nghiệm AI Image Generation trên phông trắng
        raw_image_bytes = await self._generate_isolated_ai_image(keyword, safe_domain)

        # 3. ƯU TIÊN 2: Web Search Fallback (Wikimedia / Unsplash + Negative Filter)
        if not raw_image_bytes:
            logger.info(f"🌐 [Tier 2 Fallback] Tìm kiếm qua Web Search & Curated Library cho '{keyword}'...")
            raw_image_bytes = await self._fetch_stock_image(keyword, safe_domain)

        if raw_image_bytes:
            try:
                raw_img = Image.open(io.BytesIO(raw_image_bytes)).convert("RGBA")
                if max(raw_img.size) > 1200:
                    raw_img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

                # Chạy AI rembg tách nền
                logger.info(f"✂️ [AI rembg] Đang bóc tách nền alpha cho '{keyword}'...")
                cutout = self.cutout_engine.remove_background(raw_img)

                # Quality Gate Check
                is_valid, trans_ratio = self.check_alpha_quality_gate(cutout)
                logger.info(f"🛡️ [Quality Gate] Tỷ lệ trong suốt: {trans_ratio:.2%} (Hợp lệ: {is_valid})")

                if is_valid:
                    # Halftone Noir 1950s
                    halftone = self.cutout_engine.apply_vintage_halftone(cutout, contrast_boost=1.5)
                    # Viền kem + bóng đổ vật lý
                    final_sticker = self.cutout_engine.add_paper_keyline_and_shadow(
                        halftone,
                        border_px=10,
                        border_color=(253, 251, 245, 255),
                        shadow_blur=16,
                        shadow_offset=(8, 14)
                    )
                    final_sticker.save(cached_file, format="PNG")
                    logger.success(f"🎉 [Sticker Created] Đạt Quality Gate: {cached_file.name}")
                    return str(cached_file.resolve())
                else:
                    logger.warning(f"⚠️ Cutout không đạt tỷ lệ alpha mong đợi ({trans_ratio:.2%}), kích hoạt procedural fallback.")

            except Exception as e:
                logger.warning(f"Lỗi bóc tách sticker cho '{keyword}': {e}")

        # 4. Tầng 3: Domain-Specific Procedural Fallback
        fallback_path = self._get_domain_fallback_sticker(safe_key, safe_domain, fallback_scene_index)
        return fallback_path

    async def _generate_isolated_ai_image(self, keyword: str, domain: str) -> Optional[bytes]:
        """Ưu tiên 1: Dùng AI sinh ảnh vật thể đơn lập trên phông trắng tinh khiết."""
        if not self.api_keys:
            return None

        prompt_text = (
            f"Isolated single {keyword} on solid pure white background, studio product shot, "
            f"clean sharp silhouette edges, high contrast vintage scientific engraving or archival photo style, "
            f"no background elements, no text, no shadow, centered."
        )

        try:
            from google import genai
            api_key = self.api_keys[self.current_key_idx]
            client = genai.Client(api_key=api_key)

            logger.info(f"🤖 [Tier 1 - AI Gen] Thử sinh ảnh AI cho '{keyword}'...")
            result = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt_text,
                config=dict(
                    number_of_images=1,
                    output_mime_type="image/png",
                    aspect_ratio="1:1"
                )
            )
            for generated in result.generated_images:
                if generated.image and generated.image.image_bytes:
                    logger.success(f"✨ AI Imagen 3 đã sinh thành công ảnh cho '{keyword}'")
                    return generated.image.image_bytes
        except Exception as e:
            logger.debug(f"AI Image Gen không khả dụng ({e}). Chuyển sang Tier 2 Web Search.")

        return None

    async def _fetch_stock_image(self, keyword: str, domain: str) -> Optional[bytes]:
        """Ưu tiên 2: Tìm kiếm Wikimedia Commons hoặc Curated Map với bộ lọc tiêu cực nghiêm ngặt."""
        safe_k = self._sanitize_keyword(keyword)

        # 1. Tra cứu Curated Map
        if safe_k in self.CURATED_MAP:
            curated_url = self.CURATED_MAP[safe_k]
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    res = await client.get(curated_url, headers={"User-Agent": "AutoVideoFactoryBot/2.0"})
                    if res.status_code == 200 and len(res.content) > 10000:
                        logger.info(f"💎 [Curated Sticker] Nạp ảnh chuẩn khớp nghĩa cho '{safe_k}'")
                        return res.content
            except Exception as e:
                logger.warning(f"Lỗi tải curated asset cho {safe_k}: {e}")

        # 2. Tìm kiếm trên Wikimedia Commons với từ khóa isolated object
        search_query = f"{keyword} isolated cutout object on white background"
        api_url = (
            f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
            f"&gsrnamespace=6&gsrsearch={search_query}&gsrlimit=8&prop=imageinfo&iiprop=url|mime|size&format=json"
        )
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                res = await client.get(api_url, headers={"User-Agent": "AutoVideoFactoryBot/2.0"})
                if res.status_code == 200:
                    data = res.json()
                    pages = data.get("query", {}).get("pages", {})
                    for _, page in pages.items():
                        title = page.get("title", "").lower()
                        # Bộ lọc tiêu cực: loại bỏ pub, bar, building, house, street, people...
                        if any(bad in title for bad in self.NEGATIVE_WORDS):
                            logger.info(f"🛡️ [Filter Discard] Loại bỏ ảnh lệch nghĩa: {title}")
                            continue

                        info_list = page.get("imageinfo", [])
                        if not info_list:
                            continue
                        info = info_list[0]
                        img_url = info.get("url", "")
                        if any(bad in img_url.lower() for bad in self.NEGATIVE_WORDS):
                            continue

                        mime = info.get("mime", "")
                        if img_url and ("image/jpeg" in mime or "image/png" in mime):
                            img_resp = await client.get(img_url, headers={"User-Agent": "AutoVideoFactoryBot/2.0"})
                            if img_resp.status_code == 200 and len(img_resp.content) > 10000:
                                logger.info(f"🎯 [Wikimedia HIT] Chọn ảnh: {title}")
                                return img_resp.content
        except Exception as e:
            logger.warning(f"Lỗi tìm kiếm Wikimedia cho '{keyword}': {e}")

        return None

    def _get_domain_fallback_sticker(self, safe_key: str, domain: str, scene_idx: int) -> str:
        """Tạo sticker hình học/khoa học cổ điển tương thích theo từng Domain nếu không tải được từ web."""
        cached_file = self.cache_dir / f"{domain}_{safe_key}.png"
        if cached_file.exists():
            return str(cached_file.resolve())

        w, h = 600, 600
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        if domain == "biology":
            # Tế bào / vi khuẩn hình elip với màng phân nhánh và hạt nhân
            cx, cy = w // 2, h // 2
            draw.ellipse([cx - 200, cy - 160, cx + 200, cy + 160], fill=(235, 235, 230, 255), outline=(30, 30, 30, 255), width=6)
            draw.ellipse([cx - 80, cy - 60, cx + 80, cy + 60], fill=(80, 80, 80, 255), outline=(20, 20, 20, 255), width=4)
            # Các gai bề mặt kháng thể
            for angle in range(0, 360, 30):
                rad = np.radians(angle)
                x1 = cx + int(190 * np.cos(rad))
                y1 = cy + int(150 * np.sin(rad))
                x2 = cx + int(240 * np.cos(rad))
                y2 = cy + int(190 * np.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=(30, 30, 30, 255), width=5)
                draw.ellipse([x2 - 8, y2 - 8, x2 + 8, y2 + 8], fill=(20, 20, 20, 255))

        elif domain == "geography":
            # La bàn hải trình hoặc thiết bị đo áp suất biển sâu
            cx, cy = w // 2, h // 2
            draw.ellipse([cx - 210, cy - 210, cx + 210, cy + 210], fill=(240, 235, 220, 255), outline=(30, 30, 30, 255), width=6)
            draw.ellipse([cx - 180, cy - 180, cx + 180, cy + 180], outline=(80, 80, 80, 255), width=2)
            # 8 cánh sao hoa tiêu
            draw.polygon([(cx, cy - 170), (cx + 25, cy - 25), (cx, cy)], fill=(30, 30, 30, 255))
            draw.polygon([(cx, cy + 170), (cx - 25, cy + 25), (cx, cy)], fill=(30, 30, 30, 255))
            draw.polygon([(cx + 170, cy), (cx + 25, cy + 25), (cx, cy)], fill=(60, 60, 60, 255))
            draw.polygon([(cx - 170, cy), (cx - 25, cy - 25), (cx, cy)], fill=(60, 60, 60, 255))

        elif domain == "history":
            # Con dấu hoàng gia Ai Cập / cartouche cổ đại
            cx, cy = w // 2, h // 2
            draw.rounded_rectangle([cx - 160, cy - 220, cx + 160, cy + 220], radius=80, fill=(245, 238, 215, 255), outline=(30, 30, 30, 255), width=6)
            draw.line([(cx - 120, cy + 210), (cx + 120, cy + 210)], fill=(30, 30, 30, 255), width=8)
            # Biểu tượng mắt Horus / Ankh cách điệu
            draw.ellipse([cx - 45, cy - 120, cx + 45, cy - 30], outline=(30, 30, 30, 255), width=6)
            draw.line([(cx - 70, cy), (cx + 70, cy)], fill=(30, 30, 30, 255), width=6)
            draw.line([(cx, cy - 30), (cx, cy + 130)], fill=(30, 30, 30, 255), width=8)

        elif domain == "space":
            # Hành tinh có vành đai và thiên thể
            cx, cy = w // 2, h // 2
            draw.ellipse([cx - 150, cy - 150, cx + 150, cy + 150], fill=(220, 220, 225, 255), outline=(30, 30, 30, 255), width=5)
            # Vành đai nghiêng
            draw.arc([cx - 260, cy - 60, cx + 260, cy + 60], start=0, end=360, fill=(40, 40, 40, 255), width=6)

        else:
            # Tem thư khoa học cổ điển
            cx, cy = w // 2, h // 2
            draw.rectangle([cx - 180, cy - 180, cx + 180, cy + 180], fill=(245, 240, 230, 255), outline=(30, 30, 30, 255), width=6)
            draw.rectangle([cx - 150, cy - 150, cx + 150, cy + 150], outline=(80, 80, 80, 255), width=2)
            draw.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], outline=(30, 30, 30, 255), width=4)

        final_sticker = self.cutout_engine.add_paper_keyline_and_shadow(canvas, border_px=10, shadow_blur=14)
        final_sticker.save(cached_file, format="PNG")
        logger.info(f"🎨 [Procedural Fallback] Đã tạo sticker dự phòng ({domain}): {cached_file.name}")
        return str(cached_file.resolve())
