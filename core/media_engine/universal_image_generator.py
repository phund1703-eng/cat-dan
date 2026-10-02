"""
AutoVideoFactory — UniversalImageGenerator (Gate 2 / Phase 1)
Tạo vật thể đơn lẻ (Single Isolated Asset) 512x512 trên nền trắng tinh khiết (#FFFFFF),
tách nền qua rembg và kiểm duyệt nghiêm ngặt qua AlphaQAGate.
Tích hợp FallbackAssetLibrary bảo đảm 100% không bao giờ rỗng hình.
"""

import os
import time
import hashlib
import requests
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from loguru import logger
from rembg import remove

from .alpha_qa_gate import AlphaQAGate
from .fallback_asset_library import FallbackAssetLibrary


class UniversalImageGenerator:
    """
    Gate 2: Tạo vật thể đơn lẻ (Single Isolated Asset) 512x512 qua FLUX.1 (Pollinations AI).
    - Prompt ép buộc: nền trắng tinh khiết (#FFFFFF), phong cách bách khoa toàn thư 1950s.
    - Bóc tách nền rembg sắc nét.
    - Kiểm soát kênh Alpha qua AlphaQAGate.
    - Tự động thay thế bằng FallbackAssetLibrary nếu lỗi sau 3 lần thử.
    """

    ISOLATED_ASSET_TEMPLATE = (
        "A single detailed vintage cut-out illustration of {concrete_object}, "
        "1950s archival encyclopedia print style, crisp clean edges, subtle halftone dot texture, "
        "isolated on pure solid white background (#FFFFFF), no shadow, no background elements, no text."
    )

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("data/cache/universal_images").resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })
        self.fallback_library = FallbackAssetLibrary()

    def _get_cache_path(self, prompt: str, seed: int, prefix_tag: str = "flux") -> Path:
        key = f"{prompt}_{seed}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:16]
        prefix = "".join(c for c in prompt[:25] if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
        return self.cache_dir / f"{prefix_tag}_{prefix}_{digest}.png"

    def _clean_prompt(self, prompt: str) -> str:
        """Làm sạch prompt để tránh URL quá dài hoặc ký tự đặc biệt gây lỗi HTTP 500."""
        clean = " ".join(prompt.split())
        if len(clean) > 350:
            clean = clean[:340] + "..."
        return clean

    async def generate_isolated_asset(
        self,
        concrete_object: str,
        output_path: Optional[str] = None,
        seed: Optional[int] = None,
        archetype: str = "specimen_scientific",
        width: int = 512,
        height: int = 512,
        timeout: int = 30
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Sinh vật thể đơn lẻ (Single Isolated Asset) 512x512 trên nền trắng tinh khiết (#FFFFFF),
        tách nền qua rembg và kiểm soát qua AlphaQAGate.
        """
        prompt = self.ISOLATED_ASSET_TEMPLATE.format(concrete_object=concrete_object)
        clean_p = self._clean_prompt(prompt)

        target_out = Path(output_path) if output_path else (self.cache_dir / f"isolated_{concrete_object[:15].replace(' ', '_')}.png")
        target_out.parent.mkdir(parents=True, exist_ok=True)
        cutout_target = target_out.parent / f"{target_out.stem}_cutout.png"

        # Kiểm tra nếu cutout đã có trong cache và đạt chuẩn QA
        if cutout_target.exists():
            qa_res = AlphaQAGate.verify(cutout_target)
            if qa_res["passed"]:
                logger.info(f"⚡ [UniversalImageGen] Tái sử dụng isolated cutout từ cache: {cutout_target.name}")
                return str(cutout_target), qa_res

        base_seed = seed if seed is not None else int(time.time()) % 100000

        # Thử tối đa 3 lần với FLUX
        for attempt in range(1, 4):
            cur_seed = base_seed + (attempt - 1) * 17
            raw_target = target_out.parent / f"{target_out.stem}_raw_try{attempt}.png"

            logger.info(f"🎨 [UniversalImageGen] Tạo vật thể '{concrete_object}' qua FLUX 512x512 (Thử lần {attempt}/3, seed={cur_seed})...")
            encoded_prompt = urllib.parse.quote(clean_p)
            url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width={width}&height={height}&nologo=true&seed={cur_seed}&model=flux"
            )

            raw_downloaded = False
            try:
                resp = self.session.get(url, timeout=timeout)
                if resp.status_code == 200 and len(resp.content) > 3000:
                    with open(str(raw_target), "wb") as f:
                        f.write(resp.content)
                    with Image.open(str(raw_target)) as img:
                        img.convert("RGB").save(str(raw_target), format="PNG")
                    raw_downloaded = True
                    logger.info(f"📥 Đã tải ảnh thô 512x512: {raw_target.name} ({len(resp.content)} bytes)")
            except Exception as e:
                logger.warning(f"⚠️ Lỗi gọi FLUX cho '{concrete_object}' (Lần {attempt}): {e}")

            # Nếu không tải được qua mạng, sinh fallback trên nền trắng
            if not raw_downloaded:
                self._generate_white_bg_fallback(concrete_object, str(raw_target), width, height)

            # Tách nền bằng rembg
            try:
                logger.info(f"✂️ Đang bóc tách nền rembg trên nền trắng: {raw_target.name}...")
                with Image.open(str(raw_target)) as raw_img:
                    cutout_img = remove(raw_img)
                    # Resize lại đúng chuẩn 512x512
                    cutout_img = cutout_img.resize((width, height), Image.Resampling.LANCZOS)
                    cutout_img.save(str(cutout_target), format="PNG")
            except Exception as e:
                logger.error(f"Lỗi khi chạy rembg: {e}")
                continue

            # Kiểm duyệt qua AlphaQAGate
            qa_res = AlphaQAGate.verify(cutout_target)
            if qa_res["passed"]:
                logger.success(f"🎯 [Phase 1 QA PASS] Vật thể '{concrete_object}' đã bóc tách hoàn hảo! Tỷ lệ alpha: {qa_res['ratio']*100:.1f}%")
                return str(cutout_target), qa_res
            else:
                logger.warning(f"❌ [Phase 1 QA FAIL] Lần {attempt} không đạt chuẩn: {qa_res['message']}")
                if attempt < 3:
                    import asyncio
                    await asyncio.sleep(1)

        # Nếu sau 3 lần thử vẫn không PASS, kích hoạt FallbackAssetLibrary
        logger.warning(f"🛡️ Kích hoạt FallbackAssetLibrary an toàn cho '{concrete_object}' (Archetype: {archetype})...")
        fallback_path = self.fallback_library.get_fallback(archetype, concrete_object)
        import shutil
        shutil.copyfile(str(fallback_path), str(cutout_target))
        qa_res = AlphaQAGate.verify(cutout_target)
        logger.success(f"✅ Đã sử dụng asset dự phòng được chứng nhận: {cutout_target.name} (Tỷ lệ: {qa_res['ratio']*100:.1f}%)")
        return str(cutout_target), qa_res

    def _generate_white_bg_fallback(self, concrete_object: str, out_path: str, width: int = 512, height: int = 512):
        """Tạo minh họa vintage halftone trên nền trắng tinh khiết (#FFFFFF) làm fallback cục bộ."""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2

        obj_lower = concrete_object.lower()
        ink = (24, 24, 26)
        brass = (180, 130, 20)
        crimson = (180, 35, 35)
        teal = (35, 145, 135)
        gold = (215, 160, 40)

        if "microscope" in obj_lower:
            draw.rectangle([cx - 70, cy + 80, cx + 70, cy + 130], fill=ink)
            draw.line([(cx - 25, cy + 90), (cx - 25, cy - 60)], fill=ink, width=32)
            draw.line([(cx - 25, cy - 60), (cx + 40, cy - 120)], fill=brass, width=24)
            draw.ellipse([cx + 35, cy - 130, cx + 60, cy - 105], fill=ink)
            draw.rectangle([cx - 60, cy + 10, cx + 40, cy + 24], fill=brass)
        elif "bacteria" in obj_lower:
            draw.ellipse([cx - 110, cy - 60, cx + 110, cy + 60], fill=crimson, outline=ink, width=5)
            draw.ellipse([cx - 50, cy - 25, cx + 50, cy + 25], fill=ink)
            import math
            for a in range(0, 360, 24):
                rad = math.radians(a)
                x1 = cx + math.cos(rad) * 110
                y1 = cy + math.sin(rad) * 60
                x2 = cx + math.cos(rad) * 140
                y2 = cy + math.sin(rad) * 80
                draw.line([(x1, y1), (x2, y2)], fill=ink, width=3)
        elif "pressure" in obj_lower or "gauge" in obj_lower or "manometer" in obj_lower:
            draw.ellipse([cx - 115, cy - 115, cx + 115, cy + 115], fill=brass, outline=ink, width=6)
            draw.ellipse([cx - 95, cy - 95, cx + 95, cy + 95], fill=(245, 243, 235), outline=ink, width=3)
            draw.line([(cx, cy), (cx + 45, cy - 50)], fill=crimson, width=4)
            draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=ink)
            draw.rectangle([cx - 20, cy + 115, cx + 20, cy + 155], fill=brass, outline=ink, width=3)
        elif "submarine" in obj_lower:
            draw.ellipse([cx - 135, cy - 45, cx + 125, cy + 70], fill=gold, outline=ink, width=6)
            draw.rectangle([cx - 30, cy - 95, cx + 30, cy - 45], fill=ink)
            draw.line([(cx, cy - 95), (cx, cy - 130), (cx + 25, cy - 130)], fill=ink, width=6)
            draw.ellipse([cx - 80, cy - 10, cx - 45, cy + 25], fill=teal, outline=ink, width=3)
            draw.ellipse([cx - 15, cy - 10, cx + 20, cy + 25], fill=teal, outline=ink, width=3)
            draw.ellipse([cx + 50, cy - 10, cx + 85, cy + 25], fill=teal, outline=ink, width=3)
        elif "canopic" in obj_lower or "jar" in obj_lower or "egyptian" in obj_lower:
            draw.polygon([(cx - 45, cy - 40), (cx + 45, cy - 40), (cx + 75, cy + 50), (cx + 50, cy + 130), (cx - 50, cy + 130), (cx - 75, cy + 50)], fill=(235, 220, 195), outline=ink, width=6)
            draw.ellipse([cx - 50, cy - 120, cx + 50, cy - 35], fill=gold, outline=ink, width=5)
            draw.rectangle([cx - 40, cy + 15, cx + 40, cy + 85], fill=ink, outline=gold, width=2)
        else:  # squeezer / press machine
            draw.rectangle([cx - 85, cy + 80, cx + 85, cy + 120], fill=ink)
            draw.line([(cx - 60, cy - 60), (cx - 60, cy + 80)], fill=ink, width=18)
            draw.line([(cx + 60, cy - 60), (cx + 60, cy + 80)], fill=ink, width=18)
            draw.rectangle([cx - 50, cy - 75, cx + 50, cy - 45], fill=brass, outline=ink, width=3)
            draw.polygon([(cx, cy + 40), (cx - 45, cy - 30), (cx + 45, cy - 30)], fill=gold, outline=ink, width=4)
            draw.line([(cx, cy - 75), (cx, cy - 130)], fill=brass, width=20)
            draw.line([(cx - 75, cy - 130), (cx + 75, cy - 130)], fill=ink, width=12)

        # Subtle Halftone Dot Effect
        noise = Image.effect_noise((width, height), 22).convert("L")
        noise = ImageEnhance.Contrast(noise).enhance(2.2)
        img.paste(Image.new("RGB", (width, height), (0, 0, 0)), mask=noise)

        out_path_obj = Path(out_path)
        out_path_obj.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out_path_obj), format="PNG")
        logger.info(f"🎨 Đã tạo White-Background Graphic Fallback: {out_path_obj.name}")

    async def generate_artwork(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        seed: Optional[int] = None,
        width: int = 720,
        height: int = 1280,
        timeout: int = 35
    ) -> str:
        """Sinh ảnh 9:16 tương thích ngược cho pipeline cũ."""
        if seed is None:
            seed = int(time.time()) % 100000

        clean_p = self._clean_prompt(prompt)
        cache_file = self._get_cache_path(clean_p, seed)
        if cache_file.exists() and cache_file.stat().st_size > 10000:
            logger.info(f"⚡ [UniversalImageGen] Tái sử dụng ảnh từ cache: {cache_file.name}")
            if output_path and output_path != str(cache_file):
                import shutil
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(cache_file), output_path)
                return str(output_path)
            return str(cache_file)

        target_path = Path(output_path) if output_path else cache_file
        target_path.parent.mkdir(parents=True, exist_ok=True)

        encoded_prompt = urllib.parse.quote(clean_p)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&nologo=true&seed={seed}&model=flux"
        )

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                resp = self.session.get(url, timeout=timeout)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    with open(str(target_path), "wb") as f:
                        f.write(resp.content)
                    with Image.open(str(target_path)) as img:
                        img.convert("RGB").save(str(target_path), format="PNG")
                    return str(target_path)
            except Exception as e:
                logger.warning(f"FLUX attempt {attempt} failed: {e}")

        # Fallback cardstock
        self._generate_cardstock_fallback(clean_p, str(target_path), width, height)
        return str(target_path)

    def _generate_cardstock_fallback(self, prompt: str, out_path: str, width: int, height: int):
        img = Image.new("RGBA", (width, height), (29, 53, 87, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, int(height * 0.48)
        draw.ellipse([cx - 200, cy - 200, cx + 200, cy + 200], fill=(245, 242, 235, 255), outline=(255, 253, 247, 255), width=8)
        img.convert("RGB").save(out_path, format="PNG")
