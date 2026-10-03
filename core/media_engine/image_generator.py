"""
AutoVideoFactory — Image Generator
Sinh và tải ảnh minh họa đa tầng cho các phân cảnh video:
- Tầng 1: Google Imagen 3 (imagen-3.0-generate-002) qua SDK google-genai
- Tầng 2: Fallback tải ảnh chủ đề chất lượng cao (Wikimedia Commons, NASA Public Domain, Pexels/Pixabay)
- Tầng 3: Kiểm tra kho ảnh mẫu assets/templates/
"""

import os
import re
import io
import math
import httpx
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image, ImageDraw, ImageFilter
from loguru import logger
from dotenv import load_dotenv

from core.media_engine.asset_provenance import write_asset_meta

load_dotenv()


class ImageGenerator:
    """Tự động sinh và tải ảnh minh họa chất lượng cao cho từng phân cảnh."""

    def __init__(self):
        self.api_keys = []
        key1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
        key2 = os.getenv("GEMINI_API_KEY_2")
        for k in [key1, key2]:
            if k and k.strip() and not k.strip().startswith("your_") and k.strip() not in self.api_keys:
                self.api_keys.append(k.strip())
                
        self.current_key_idx = 0
        self.templates_dir = Path("assets/templates")
        self.cache_dir = Path("data/cache/images")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def generate_scene_image(
        self,
        scene: Dict[str, Any],
        output_path: str,
        topic: str = "",
        scene_index: int = 0
    ) -> str:
        """
        Sinh hoặc tải ảnh minh họa cho cảnh.
        
        Args:
            scene: Dữ liệu cảnh chứa narration và visual_description
            output_path: Đường dẫn lưu file ảnh (PNG/JPG)
            topic: Chủ đề video
            scene_index: Chỉ số cảnh (0, 1, 2...)
            
        Returns:
            str: Đường dẫn file ảnh hoàn tất
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        visual_desc = scene.get("visual_description", "")
        narration = scene.get("narration", "")

        # 1. Tầng 3: Kiểm tra trong assets/templates/ trước
        template_img = self._check_template_image(scene_index, topic)
        if template_img:
            logger.info(f"✨ [Tầng 3] Dùng ảnh template có sẵn: {template_img}")
            import shutil
            shutil.copyfile(template_img, str(out_file))
            write_asset_meta(
                out_file,
                source="template",
                license="Repo-bundled template asset (assets/templates)",
            )
            return str(out_file)

        # 2. Tầng 1: Google Imagen 3 (nếu có API key hợp lệ)
        if self.api_keys:
            try:
                prompt_for_image = scene.get("still_image_prompt") or visual_desc or narration
                success = await self._generate_with_imagen3(prompt_for_image, str(out_file))
                if success and out_file.exists() and out_file.stat().st_size > 1000:
                    logger.success(f"✅ Sinh ảnh Imagen 3 thành công: {out_file}")
                    return str(out_file)
            except Exception as e:
                logger.warning(f"⚠️ Imagen 3 thất bại ({e}), chuyển sang Tầng 2 Fallback...")

        # 3. Tầng 2: Fallback tải ảnh thực tế chất lượng cao từ kho ảnh mở (Wikimedia/NASA/Curated)
        logger.info(f"🌐 [Tầng 2] Đang tìm và tải ảnh minh họa chất lượng cao cho Scene {scene_index + 1}...")
        stock_path = await self._fetch_curated_or_web_image(scene, topic, scene_index, str(out_file))
        if stock_path and os.path.exists(stock_path):
            return str(stock_path)

        # 4. Fallback tạo đồ họa cắt dán chủ đề nâng cao bằng Pillow
        logger.info(f"🖼️ [Tầng 4] Tạo hình minh họa nghệ thuật collage cho Scene {scene_index + 1}...")
        self._generate_artistic_collage_fallback(scene, scene_index, str(out_file))
        return str(out_file)

    async def _generate_with_imagen3(self, prompt_text: str, output_path: str) -> bool:
        """Gọi Google Imagen 3 qua google-genai SDK."""
        try:
            from google import genai
            api_key = self.api_keys[self.current_key_idx]
            client = genai.Client(api_key=api_key)
            
            # Tối ưu prompt cho phong cách collage cutout
            refined_prompt = (
                f"{prompt_text}, editorial paper collage cutout style, isolated object on white background, "
                f"crisp clean borders, high detail, tactile cardstock, photorealistic textures"
            )
            
            result = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=refined_prompt,
                config=dict(
                    number_of_images=1,
                    output_mime_type="image/png",
                    aspect_ratio="1:1"
                )
            )
            
            for generated in result.generated_images:
                image_bytes = generated.image.image_bytes
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                write_asset_meta(
                    output_path,
                    source="imagen",
                    author="Google Imagen 3 (imagen-3.0-generate-002)",
                    license="AI-generated content",
                    prompt=prompt_text,
                )
                return True
        except Exception as e:
            logger.warning(f"Lỗi Imagen 3 với key #{self.current_key_idx + 1}: {e}")
            if len(self.api_keys) > 1:
                self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            return False

    async def _fetch_curated_or_web_image(
        self,
        scene: Dict[str, Any],
        topic: str,
        scene_index: int,
        output_path: str
    ) -> Optional[str]:
        """Tải ảnh thực tế chất lượng cao từ Wikimedia Commons hoặc NASA Public Domain."""
        # Danh mục ảnh độ phân giải cao công cộng cho chủ đề Vũ Trụ & Khoa Học
        CURATED_SPACE_URLS = [
            # Cảnh 1: Thiên hà rực rỡ / Dải ngân hà sâu thẳm
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop",
            # Cảnh 2: Hành tinh sao Kim / Bề mặt hành tinh phát sáng
            "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=800&auto=format&fit=crop",
            # Cảnh 3: Nhà du hành vũ trụ / Trạm không gian trong vũ trụ tĩnh lặng
            "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=800&auto=format&fit=crop",
        ]
        CURATED_POWER_URLS = [
            # Cảnh 1: Bàn cờ vua / quân vua / bàn tay đen trắng
            "https://images.unsplash.com/photo-1529699211952-734e80c4d42b?w=800&auto=format&fit=crop",
            # Cảnh 2: Mặt nạ kịch nghệ / lăng kính bí ẩn
            "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800&auto=format&fit=crop",
            # Cảnh 3: Chìa khóa vàng cổ điển / mở khóa tâm trí
            "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?w=800&auto=format&fit=crop",
        ]
        
        # Thử tải từ kho ảnh chất lượng cao
        target_url = None
        topic_lower = topic.lower()
        if "vũ trụ" in topic_lower or "universe" in topic_lower or "space" in topic_lower:
            target_url = CURATED_SPACE_URLS[scene_index % len(CURATED_SPACE_URLS)]
        elif "quyền lực" in topic_lower or "thao túng" in topic_lower or "tâm lý" in topic_lower or "power" in topic_lower or "mind" in topic_lower:
            target_url = CURATED_POWER_URLS[scene_index % len(CURATED_POWER_URLS)]
            
        # Tìm kiếm động qua Wikimedia Commons nếu là chủ đề khác
        if not target_url:
            query = self._extract_search_keywords(scene.get("visual_description", "") or topic)
            target_url = await self._search_wikimedia_image(query)

        if target_url:
            try:
                async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                    resp = await client.get(target_url, headers={"User-Agent": "AutoVideoFactory/2.0"})
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                        # Crop vuông và lưu
                        min_dim = min(img.size)
                        left = (img.width - min_dim) // 2
                        top = (img.height - min_dim) // 2
                        cropped = img.crop((left, top, left + min_dim, top + min_dim))
                        cropped.resize((800, 800), Image.Resampling.LANCZOS).save(output_path, format="PNG")
                        _is_unsplash = "unsplash" in target_url
                        write_asset_meta(
                            output_path,
                            source="unsplash" if _is_unsplash else "wikimedia",
                            source_url=target_url,
                            license=(
                                "Unsplash License" if _is_unsplash
                                else "Wikimedia Commons (see source file page for exact license)"
                            ),
                        )
                        logger.success(f"✅ Đã tải ảnh minh họa thực tế thành công: {output_path}")
                        return output_path
            except Exception as e:
                logger.warning(f"Không thể tải ảnh từ {target_url}: {e}")

        return None

    async def _search_wikimedia_image(self, query: str) -> Optional[str]:
        """Tìm URL ảnh chất lượng cao trên Wikimedia Commons."""
        api_url = (
            f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
            f"&gsrnamespace=6&gsrsearch={query}&gsrlimit=3&prop=imageinfo&iiprop=url|mime&format=json"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(api_url, headers={"User-Agent": "AutoVideoFactoryBot/1.0"})
                if res.status_code == 200:
                    data = res.json()
                    pages = data.get("query", {}).get("pages", {})
                    for _, page in pages.items():
                        info = page.get("imageinfo", [{}])[0]
                        mime = info.get("mime", "")
                        if "jpeg" in mime or "png" in mime:
                            return info.get("url")
        except Exception:
            pass
        return None

    def _extract_search_keywords(self, text: str) -> str:
        """Trích xuất từ khóa tìm kiếm tiếng Anh ngắn gọn."""
        clean = re.sub(r'halftone|paper|collage|cutout|style|isolated|background', '', text, flags=re.I)
        words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', clean)]
        return "+".join(words[:3]) if words else "space+universe"

    def _check_template_image(self, scene_index: int, topic: str) -> Optional[str]:
        """Kiểm tra ảnh mẫu có sẵn trong assets/templates/."""
        if not self.templates_dir.exists():
            return None
        candidates = list(self.templates_dir.glob(f"scene_{scene_index}*.*")) + \
                     list(self.templates_dir.glob(f"*{scene_index}*.*")) + \
                     list(self.templates_dir.glob("*.png")) + \
                     list(self.templates_dir.glob("*.jpg"))
        return str(candidates[0]) if candidates else None

    def _generate_artistic_collage_fallback(self, scene: Dict[str, Any], scene_index: int, output_path: str):
        """Tạo hình minh họa nghệ thuật thiên hà/sao/du hành vũ trụ đa lớp (KHÔNG dùng hình tròn trắng)."""
        w, h = 800, 800
        img = Image.new("RGBA", (w, h), (15, 23, 42, 255)) # Dark cosmic background
        draw = ImageDraw.Draw(img)

        # Vẽ sao và bụi thiên hà rực rỡ
        import random
        rnd = random.Random(scene_index * 999 + 42)
        
        # 1. Quầng sáng gradient thiên hà
        for r in range(350, 50, -15):
            alpha = int(120 * (1 - r / 350))
            color = (147, 51, 234, alpha) if scene_index == 0 else (234, 88, 12, alpha) if scene_index == 1 else (6, 182, 212, alpha)
            draw.ellipse([w//2 - r, h//2 - r, w//2 + r, h//2 + r], fill=color)

        # 2. Hàng trăm ngôi sao lấp lánh
        for _ in range(120):
            sx = rnd.randint(40, w - 40)
            sy = rnd.randint(40, h - 40)
            s_rad = rnd.randint(1, 4)
            s_bright = rnd.randint(180, 255)
            draw.ellipse([sx - s_rad, sy - s_rad, sx + s_rad, sy + s_rad], fill=(s_bright, s_bright, 255, 240))

        # 3. Đối tượng trung tâm đặc trưng theo từng cảnh
        if scene_index == 0:
            # Thiên hà xoắn ốc (Spiral Galaxy)
            for angle_deg in range(0, 720, 10):
                rad = math.radians(angle_deg)
                dist = angle_deg * 0.45
                cx = int(w//2 + dist * math.cos(rad))
                cy = int(h//2 + dist * math.sin(rad))
                draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(255, 220, 150, 220))
                # Cánh đối diện
                cx2 = int(w//2 - dist * math.cos(rad))
                cy2 = int(h//2 - dist * math.sin(rad))
                draw.ellipse([cx2 - 8, cy2 - 8, cx2 + 8, cy2 + 8], fill=(236, 72, 153, 220))
        elif scene_index == 1:
            # Hành tinh sao Kim với các dải mây vàng cam (Venus Planet with cloud bands)
            p_radius = 220
            p_box = [w//2 - p_radius, h//2 - p_radius, w//2 + p_radius, h//2 + p_radius]
            draw.ellipse(p_box, fill=(245, 158, 11, 255), outline=(255, 253, 240, 255), width=6)
            for y_offset in range(-180, 180, 25):
                curve_h = int(math.sqrt(max(0, p_radius**2 - y_offset**2)))
                draw.line([(w//2 - curve_h, h//2 + y_offset), (w//2 + curve_h, h//2 + y_offset)], fill=(180, 83, 9, 180), width=8)
        else:
            # Mũ phi hành gia / Biểu tượng không gian (Astronaut Helmet Icon)
            draw.ellipse([w//2 - 190, h//2 - 190, w//2 + 190, h//2 + 190], fill=(241, 245, 249, 255), outline=(20, 20, 20, 255), width=8)
            # Kính che mặt phản chiếu vũ trụ (Golden Visor)
            draw.ellipse([w//2 - 130, h//2 - 100, w//2 + 130, h//2 + 90], fill=(234, 179, 8, 240), outline=(15, 23, 42, 255), width=6)
            # Vệt sáng phản chiếu trên kính
            draw.arc([w//2 - 110, h//2 - 80, w//2 + 110, h//2 + 70], start=200, end=340, fill=(255, 255, 255, 255), width=10)

        img.save(output_path, format="PNG")
        write_asset_meta(
            output_path,
            source="procedural",
            author="AutoVideoFactory ImageGenerator (Pillow artistic collage)",
            license="Generated in-repo (project LICENSE)",
            prompt=(scene or {}).get("narration"),
        )
