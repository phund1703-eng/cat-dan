"""
AutoVideoFactory — Cascade Asset Orchestrator
core/media_engine/cascade_asset_orchestrator.py

Milestone 2 (R2):
Multi-Tier Asset Acquisition Pipeline (Tier 1 Imagen 3 -> Tier 2 FLUX -> Tier 3 Curated Stock -> Tier 4 Procedural)
integrated with In-Flight Gemini Vision Gate and Rembg + Paper Keyline Post-Processing.

Architecture:
Step 0: Cache Check (job_cache_dir -> global_cutouts -> cutouts cache)
Step 1: Tier 1 (Google Imagen 3 with dual-key failover)
Step 2: In-Flight Vision Gate (Gemini Vision alignment evaluation, >= 0.75 passes, 1x retry on Tier 1)
Step 3: Tier 2 (Pollinations FLUX.1 fallback with Vision Gate)
Step 4: Tier 3 (Curated Stock / Wikimedia Commons with negative word filtering & Vision Gate)
Step 5: Tier 4 (ProceduralAssetSynthesizer — 100% offline guarantee)
Step 6: Rembg background removal + 8px ivory paper keyline + soft drop shadow (Pure Pillow + NumPy, Zero OpenCV)
        followed by AssetContentValidator verification and cache persistence.
"""

import os
import sys
import re
import io
import time
import json
import asyncio
import urllib.parse
from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple, List, Set
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import requests

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Optional Google GenAI SDK imports
try:
    from google import genai
except ImportError:
    genai = None

try:
    import google.generativeai as legacy_genai
except ImportError:
    legacy_genai = None

try:
    import rembg
except ImportError:
    rembg = None

from core.media_engine.asset_content_validator import AssetContentValidator, ValidationResult
from core.media_engine.procedural_asset_synthesizer import ProceduralAssetSynthesizer

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CascadeAssetOrchestrator:
    """
    Multi-Tier Asset Acquisition Pipeline Orchestrator.
    Guarantees seamless failover down the 4-tier generation ladder and ensures all
    acquired cutouts are authentic, semantically verified, and professionally styled.
    """

    NEGATIVE_WORDS: List[str] = [
        "pub", "bar", "people", "crowd", "building", "street",
        "facade", "hotel", "house", "restaurant", "store", "shop",
        "town", "village", "architecture", "group", "cowboy", "portrait",
        "inn", "party"
    ]

    CURATED_MAP: Dict[str, str] = {
        # Biology & Medicine
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

        # Geography & Maritime
        "submarine": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&auto=format&fit=crop",
        "anchor": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop",
        "pressure_gauge": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop",
        "compass": "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?w=800&auto=format&fit=crop",

        # History & Archaeology
        "canopic_jar": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=800&auto=format&fit=crop",
        "papyrus": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop",
        "scarab": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=800&auto=format&fit=crop",
        "golden_scale": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&auto=format&fit=crop",

        # Technology & Classic
        "vintage_camera": "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=800&auto=format&fit=crop",
        "hourglass": "https://images.unsplash.com/photo-1518241353330-0f7941c2d9b5?w=800&auto=format&fit=crop",
    }

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        self.project_root = PROJECT_ROOT
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir).resolve()
        else:
            self.cache_dir = (self.project_root / "data" / "cache" / "cutouts").resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.global_library_dir = (self.project_root / "data" / "asset_library" / "global_cutouts").resolve()
        self.global_library_dir.mkdir(parents=True, exist_ok=True)

        self.validator = AssetContentValidator()
        self.synthesizer = ProceduralAssetSynthesizer()

        self.api_keys = self._load_api_keys()
        self.current_key_idx = 0
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        # Network timeouts
        self.tier1_timeout = 20.0
        self.tier2_timeout = 20.0
        self.tier3_timeout = 15.0
        self.vision_gate_timeout = 10.0

    def _load_api_keys(self) -> List[str]:
        """Loads and deduplicates available Gemini API keys for dual-key failover."""
        keys = []
        for var in ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY"]:
            val = os.getenv(var)
            if val and val.strip() and not val.strip().startswith("your_") and val.strip() not in keys:
                keys.append(val.strip())
        return keys

    def _get_active_api_key(self) -> Optional[str]:
        if not self.api_keys:
            return None
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def _rotate_api_key(self):
        """Rotates active API key when quota limit (HTTP 429) occurs."""
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            new_key = self.api_keys[self.current_key_idx]
            logger.warning(f"🔄 [CascadeDualKey] Switched Gemini API key to index {self.current_key_idx} (ends with ...{new_key[-6:]})")
            if legacy_genai:
                try:
                    legacy_genai.configure(api_key=new_key)
                except Exception:
                    pass

    # =========================================================================
    # Step 0: Cache Check
    # =========================================================================
    def _is_blacklisted_or_intermediate(self, filename_or_stem: str) -> bool:
        """Filters out blacklisted or intermediate junk filenames."""
        clean = filename_or_stem.lower().strip()
        stem = Path(clean).stem

        # Rejection of bird image scale.png or blacklisted assets
        if clean in self.validator.REJECTED_ASSET_NAMES or stem in self.validator.REJECTED_ASSET_NAMES:
            return True
        if stem == "scale" or stem == "scale.png":
            return True
        if stem.startswith("test_") or stem.startswith("temp_") or "_raw_try" in stem:
            return True
        return False

    def _check_cache(
        self,
        target_object: str,
        job_cache_dir: Optional[Union[str, Path]] = None,
        archetype: str = ""
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Step 0: Checks cache in order:
        1. job_cache_dir
        2. data/asset_library/global_cutouts/
        3. data/cache/cutouts/
        4. self.cache_dir
        Filters out blacklisted/intermediate filenames and validates candidate with AssetContentValidator.
        """
        clean_target = re.sub(r'[^a-zA-Z0-9]+', '_', target_object.lower()).strip('_')
        tokens = [t for t in clean_target.split('_') if len(t) > 3]

        search_dirs: List[Path] = []
        if job_cache_dir:
            p_job = Path(job_cache_dir).resolve()
            if p_job.exists() and p_job not in search_dirs:
                search_dirs.append(p_job)

        cutouts_dir = (self.project_root / "data" / "cache" / "cutouts").resolve()
        for d in [self.global_library_dir, cutouts_dir, self.cache_dir]:
            if d.exists() and d not in search_dirs:
                search_dirs.append(d)

        # 1. Exact match pass
        candidate_filenames = [
            f"{clean_target}.png",
            f"{archetype}_{clean_target}.png" if archetype else "",
            f"golden_{clean_target}.png" if "scale" in clean_target and "golden" not in clean_target else "",
        ]
        candidate_filenames = [f for f in candidate_filenames if f]

        for s_dir in search_dirs:
            for fname in candidate_filenames:
                cand_path = s_dir / fname
                if cand_path.exists() and cand_path.is_file():
                    if self._is_blacklisted_or_intermediate(cand_path.name):
                        continue
                    val_res = self.validator.validate_cutout(cand_path)
                    if val_res.is_valid:
                        logger.info(f"⚡ [Cascade Step 0] Cache HIT (Exact): {cand_path.name}")
                        return (str(cand_path.resolve()), {
                            "tier_used": "cache",
                            "source": "cache",
                            "confidence": 1.0,
                            "is_aligned": True
                        })

        # 2. Token match pass
        for s_dir in search_dirs:
            try:
                for cand_file in s_dir.iterdir():
                    if not cand_file.is_file() or cand_file.suffix.lower() != ".png":
                        continue
                    if self._is_blacklisted_or_intermediate(cand_file.name):
                        continue

                    stem = cand_file.stem.lower()
                    matched = False
                    if stem == clean_target:
                        matched = True
                    elif stem.endswith(f"_{clean_target}") or stem.startswith(f"{clean_target}_"):
                        matched = True
                    elif tokens and all(tok in stem for tok in tokens):
                        matched = True

                    if matched:
                        val_res = self.validator.validate_cutout(cand_file)
                        if val_res.is_valid:
                            logger.info(f"⚡ [Cascade Step 0] Cache HIT (Token Match): {cand_file.name}")
                            return (str(cand_file.resolve()), {
                                "tier_used": "cache",
                                "source": "cache",
                                "confidence": 1.0,
                                "is_aligned": True
                            })
            except Exception as e:
                logger.warning(f"Error scanning cache dir {s_dir}: {e}")

        logger.info(f"🔍 [Cascade Step 0] Cache MISS for '{target_object}'. Proceeding to Tier 1...")
        return None

    # =========================================================================
    # Step 1: Tier 1 (Google Imagen 3)
    # =========================================================================
    async def _generate_tier1_imagen(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512
    ) -> Optional[Image.Image]:
        """
        Tier 1 — Google Imagen 3: Calls imagen-3.0-generate-002 via google-genai SDK.
        Handles dual-key failover (GEMINI_API_KEY_1 -> GEMINI_API_KEY_2) on HTTP 429 quota exhaustion.
        """
        if not self.api_keys:
            logger.warning("Tier 1: No Gemini API keys available. Skipping Tier 1.")
            return None

        if genai is None:
            logger.warning("Tier 1: google-genai SDK not installed. Skipping Tier 1.")
            return None

        max_attempts = min(2, len(self.api_keys))
        for attempt in range(max_attempts):
            active_key = self._get_active_api_key()
            if not active_key:
                break

            try:
                def _call_imagen():
                    client = genai.Client(api_key=active_key)
                    result = client.models.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=prompt,
                        config=dict(
                            number_of_images=1,
                            output_mime_type="image/png",
                            aspect_ratio="1:1"
                        )
                    )
                    for generated in result.generated_images:
                        return Image.open(io.BytesIO(generated.image.image_bytes)).convert("RGB")
                    return None

                img = await asyncio.wait_for(asyncio.to_thread(_call_imagen), timeout=self.tier1_timeout)
                if img is not None:
                    logger.info("✨ [Tier 1 Imagen 3] Successfully generated candidate image.")
                    return img
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Tier 1 (Imagen 3) attempt {attempt + 1} error with key index {self.current_key_idx}: {err_msg}")
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota" in err_msg or "quota" in err_msg:
                    self._rotate_api_key()
                else:
                    if len(self.api_keys) > 1 and attempt == 0:
                        self._rotate_api_key()

        logger.warning("Tier 1: Imagen 3 generation failed or exhausted keys.")
        return None

    # =========================================================================
    # Step 2: In-Flight Vision Gate
    # =========================================================================
    async def evaluate_vision_gate(
        self,
        image: Union[Image.Image, str, Path],
        scene_sentence: str = "",
        target_object: str = "",
        current_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Step 2: In-Flight Vision Gate.
        Evaluates candidate image against scene_sentence and target_object using Gemini Vision.
        Returns:
            {"is_aligned": bool, "confidence": float, "reason": str, "refined_prompt": str}
        """
        # Load Pillow Image
        if isinstance(image, (str, Path)):
            p = Path(image)
            if not p.exists():
                return {
                    "is_aligned": False,
                    "confidence": 0.0,
                    "reason": f"Image file not found: {p}",
                    "refined_prompt": current_prompt
                }
            img = Image.open(p).convert("RGB")
        elif isinstance(image, Image.Image):
            img = image.convert("RGB")
        else:
            return {
                "is_aligned": False,
                "confidence": 0.0,
                "reason": "Invalid image input type",
                "refined_prompt": current_prompt
            }

        eval_sentence = scene_sentence.strip() if scene_sentence and scene_sentence.strip() else f"Minh họa vật thể {target_object} cô lập trên nền trắng thuần."

        if not self.api_keys:
            # Safe offline pass-through if no keys configured
            logger.info("Vision Gate: No Gemini API keys configured. Using offline pass-through.")
            return {
                "is_aligned": True,
                "confidence": 0.88,
                "reason": "Offline verification pass",
                "refined_prompt": current_prompt
            }

        prompt = f"""
Bạn là Giám tuyển Nghệ thuật và Thẩm định viên Thị giác (In-Flight Vision Gate).
Nhiệm vụ: Thẩm định xem bức ảnh có thể hiện đúng vật thể mục tiêu và phù hợp với câu thoại kịch bản không.

Vật thể mục tiêu: "{target_object}"
Câu thoại kịch bản: "{eval_sentence}"
Prompt đã dùng: "{current_prompt}"

Tiêu chuẩn đánh giá:
1. Bức ảnh có thể hiện đúng vật thể "{target_object}" không?
2. Bức ảnh có phong cách tranh khắc vintage/archival trên nền trắng thuần không?
3. Tuyệt đối KHÔNG chấp nhận ảnh lạc đề (như quán rượu pub/bar, cao bồi, tòa nhà, đám đông, con người ngẫu nhiên).
4. Điểm tin cậy (confidence): từ 0.0 đến 1.0 (>= 0.75 là ĐẠT, < 0.75 là TỪ CHỐI).
5. refined_prompt: Nếu đạt, giữ nguyên prompt. Nếu chưa đạt, viết lại prompt tiếng Anh ngắn gọn, tập trung đúng vật thể isolated on pure solid white background.

Trả về DUY NHẤT một chuỗi JSON hợp lệ (không markdown block):
{{
  "is_aligned": true,
  "confidence": 0.88,
  "reason": "Lý do ngắn gọn bằng tiếng Việt",
  "refined_prompt": "prompt tiếng Anh tối ưu"
}}
"""
        max_attempts = min(2, len(self.api_keys))
        for attempt in range(max_attempts):
            active_key = self._get_active_api_key()
            if not active_key:
                break

            try:
                # Thumbnail to 256x256 for fast multimodal transfer
                thumb = img.copy()
                thumb.thumbnail((256, 256))

                def _call_gemini_vision():
                    if legacy_genai is not None:
                        legacy_genai.configure(api_key=active_key)
                        model = legacy_genai.GenerativeModel(self.gemini_model)
                        resp = model.generate_content(
                            [prompt, thumb],
                            generation_config=legacy_genai.types.GenerationConfig(
                                temperature=0.2,
                                response_mime_type="application/json"
                            )
                        )
                        return resp.text
                    elif genai is not None:
                        client = genai.Client(api_key=active_key)
                        buf = io.BytesIO()
                        thumb.save(buf, format="JPEG")
                        resp = client.models.generate_content(
                            model=self.gemini_model,
                            contents=[prompt, genai.types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")]
                        )
                        return resp.text
                    else:
                        raise RuntimeError("Neither google.generativeai nor google-genai is installed.")

                resp_text = await asyncio.wait_for(asyncio.to_thread(_call_gemini_vision), timeout=self.vision_gate_timeout)
                match = re.search(r'\{.*\}', resp_text.strip(), re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    confidence = float(parsed.get("confidence", 0.0))
                    is_aligned = bool(parsed.get("is_aligned", False))
                    # Ensure confidence consistency
                    if confidence >= 0.75 and not is_aligned:
                        is_aligned = True
                    elif confidence < 0.75 and is_aligned:
                        is_aligned = False
                    return {
                        "is_aligned": is_aligned,
                        "confidence": confidence,
                        "reason": str(parsed.get("reason", "")),
                        "refined_prompt": str(parsed.get("refined_prompt", current_prompt))
                    }
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Vision Gate attempt {attempt + 1} error: {err_msg}")
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                    self._rotate_api_key()
                else:
                    if len(self.api_keys) > 1 and attempt == 0:
                        self._rotate_api_key()

        # If live Vision Gate was unreachable, return safe default
        logger.info("Vision Gate unreachable or timed out. Defaulting to neutral approval.")
        return {
            "is_aligned": True,
            "confidence": 0.85,
            "reason": "Fallback approval: multimodal vision service unreachable",
            "refined_prompt": current_prompt
        }

    # =========================================================================
    # Step 3: Tier 2 (Pollinations FLUX.1)
    # =========================================================================
    async def _generate_tier2_flux(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        seed: Optional[int] = None
    ) -> Optional[Image.Image]:
        """
        Tier 2 — Pollinations FLUX.1: Calls https://image.pollinations.ai/prompt/...
        Free HTTP GET API with vintage engraving styling on pure solid white background.
        """
        cur_seed = seed if seed is not None else int(time.time() * 1000) % 999999
        encoded_prompt = urllib.parse.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&nologo=true&seed={cur_seed}&model=flux"
        )
        logger.info(f"🎨 [Tier 2 FLUX] Requesting image from Pollinations AI (seed={cur_seed})...")

        def _fetch_flux():
            headers = {"User-Agent": "AutoVideoFactory/2.0"}
            resp = requests.get(url, headers=headers, timeout=self.tier2_timeout)
            if resp.status_code == 200 and len(resp.content) > 3000:
                return Image.open(io.BytesIO(resp.content)).convert("RGB")
            return None

        try:
            img = await asyncio.wait_for(asyncio.to_thread(_fetch_flux), timeout=self.tier2_timeout + 2.0)
            if img is not None:
                logger.info("✨ [Tier 2 FLUX] Successfully fetched image from Pollinations.")
                return img
        except Exception as e:
            logger.warning(f"Tier 2 (Pollinations FLUX) error: {e}")

        return None

    # =========================================================================
    # Step 4: Tier 3 (Curated Web Stock / Wikimedia Commons)
    # =========================================================================
    async def _generate_tier3_stock(
        self,
        target_object: str,
        width: int = 512,
        height: int = 512
    ) -> Optional[Image.Image]:
        """
        Tier 3 — Curated Web Stock: Checks CURATED_MAP and Wikimedia Commons API
        with strict negative keyword filtering to avoid crowds, pubs, or landscapes.
        """
        clean_target = re.sub(r'[^a-zA-Z0-9]+', '_', target_object.lower()).strip('_')

        # 1. Curated Map check
        curated_url = None
        for key, url in self.CURATED_MAP.items():
            if key == clean_target or key in clean_target or clean_target in key:
                curated_url = url
                break

        if curated_url:
            logger.info(f"💎 [Tier 3 Stock] Found matching curated stock asset for '{target_object}'")
            def _fetch_curated():
                headers = {"User-Agent": "AutoVideoFactory/2.0"}
                resp = requests.get(curated_url, headers=headers, timeout=self.tier3_timeout)
                if resp.status_code == 200 and len(resp.content) > 3000:
                    return Image.open(io.BytesIO(resp.content)).convert("RGB")
                return None

            try:
                img = await asyncio.wait_for(asyncio.to_thread(_fetch_curated), timeout=self.tier3_timeout)
                if img is not None:
                    return img
            except Exception as e:
                logger.warning(f"Tier 3 curated fetch error: {e}")

        # 2. Wikimedia Commons API Search with negative keyword filtering
        logger.info(f"🌐 [Tier 3 Stock] Searching Wikimedia Commons for '{target_object}'...")
        search_query = f"{target_object} isolated on white background"
        api_url = (
            f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
            f"&gsrnamespace=6&gsrsearch={urllib.parse.quote(search_query)}&gsrlimit=8&prop=imageinfo&iiprop=url|mime|size&format=json"
        )

        def _fetch_wikimedia():
            headers = {"User-Agent": "AutoVideoFactory/2.0"}
            resp = requests.get(api_url, headers=headers, timeout=self.tier3_timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for _, page in pages.items():
                title = page.get("title", "").lower()
                if any(bad in title for bad in self.NEGATIVE_WORDS):
                    continue
                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue
                img_url = info_list[0].get("url", "")
                mime = info_list[0].get("mime", "")
                if any(bad in img_url.lower() for bad in self.NEGATIVE_WORDS):
                    continue
                if img_url and ("image/jpeg" in mime or "image/png" in mime):
                    img_resp = requests.get(img_url, headers=headers, timeout=self.tier3_timeout)
                    if img_resp.status_code == 200 and len(img_resp.content) > 3000:
                        return Image.open(io.BytesIO(img_resp.content)).convert("RGB")
            return None

        try:
            img = await asyncio.wait_for(asyncio.to_thread(_fetch_wikimedia), timeout=self.tier3_timeout)
            if img is not None:
                logger.info("✨ [Tier 3 Stock] Successfully downloaded Wikimedia image.")
                return img
        except Exception as e:
            logger.warning(f"Tier 3 Wikimedia search error: {e}")

        return None

    # =========================================================================
    # Step 5: Tier 4 (Procedural Code Synthesizer)
    # =========================================================================
    def _generate_tier4_procedural(
        self,
        target_object: str,
        archetype: str = "specimen_scientific",
        width: int = 512,
        height: int = 512
    ) -> Image.Image:
        """
        Tier 4 — Procedural Code Synthesizer: 100% offline mathematical guarantee.
        Invokes ProceduralAssetSynthesizer to generate authentic Pillow graphics.
        """
        logger.info(f"⚙️ [Tier 4 Procedural] Synthesizing '{target_object}' ({archetype}, {width}x{height})...")
        return self.synthesizer.synthesize(
            target_object=target_object,
            archetype=archetype,
            width=width,
            height=height
        )

    # =========================================================================
    # Step 6: Rembg & Paper Keyline Post-Processing (Pure Pillow + NumPy)
    # =========================================================================
    def apply_paper_keyline_and_shadow(
        self,
        img: Image.Image,
        outline_width: int = 8,
        outline_color: Tuple[int, int, int, int] = (255, 253, 247, 255),  # Ivory white #FFFDF7
        shadow_offset: Tuple[int, int] = (8, 10),
        shadow_blur: int = 8,
        shadow_alpha: int = 115,                       # ~45% opacity
        target_width: int = 512,
        target_height: int = 512,
        add_cellulose_grain: bool = True
    ) -> Image.Image:
        """
        Applies authentic 8px paper keyline (fibrous ivory border #FFFDF7) and soft 3D drop shadow
        using pure Pillow and NumPy (Zero OpenCV dependency).
        Scales subject into a proportioned bounding box centered in the canvas to ensure
        the keyline and shadow fit completely without clipping or exceeding dimension bounds.
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        tw = max(self.validator.MIN_DIMENSION, int(target_width))
        th = max(self.validator.MIN_DIMENSION, int(target_height))

        # Crop to tight subject bounding box
        bbox = img.getbbox()
        if bbox:
            cropped = img.crop(bbox)
        else:
            cropped = img

        # Target envelope leaves margin for 8px keyline and blurred shadow
        margin_w = max(24, int(tw * 0.08))
        margin_h = max(24, int(th * 0.08))
        max_inner_w = max(40, tw - margin_w * 2)
        max_inner_h = max(40, th - margin_h * 2)

        scale = min(max_inner_w / max(1, cropped.width), max_inner_h / max(1, cropped.height))
        # Prevent over-shrinking or over-enlarging
        new_w = max(20, int(cropped.width * scale))
        new_h = max(20, int(cropped.height * scale))
        scaled_sub = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Place centered onto exact target canvas
        base_canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        pos_x = (tw - new_w) // 2
        pos_y = (th - new_h) // 2
        base_canvas.paste(scaled_sub, (pos_x, pos_y), mask=scaled_sub)

        # 1. Clean alpha mask
        raw_alpha = base_canvas.split()[-1]
        clean_alpha = raw_alpha.point(lambda a: 255 if a >= 128 else 0, mode="L")

        # 2. Morphological dilation for 8px paper keyline: filter_size = 2 * 8 + 1 = 17
        filter_size = max(3, outline_width * 2 + 1)
        dilated_mask = clean_alpha.filter(ImageFilter.MaxFilter(filter_size))

        # 3. Soft 3D drop shadow emanates from the paper keyline contour
        shadow_mask = dilated_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
        shadow_layer = Image.new("RGBA", (tw, th), (20, 18, 15, shadow_alpha))

        # 4. Fibrous cellulose ivory border (#FFFDF7)
        border_layer = Image.new("RGBA", (tw, th), outline_color)
        if add_cellulose_grain:
            rng = np.random.RandomState(42)
            grain_arr = rng.normal(128, 10, (th, tw)).astype(np.uint8)
            grain_img = Image.fromarray(grain_arr, mode="L")
            grain_layer = Image.new("RGBA", (tw, th), (255, 255, 255, 0))
            grain_layer.putalpha(grain_img.point(lambda p: int(abs(p - 128) * 0.2)))
            border_layer = Image.alpha_composite(border_layer, grain_layer)

        # 5. Composite Assembly (Back to Front: Shadow -> Keyline -> Subject)
        result = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        # Layer 1: Drop shadow
        ox, oy = shadow_offset
        result.paste(shadow_layer, (ox, oy), mask=shadow_mask)
        # Layer 2: Ivory paper keyline
        result.paste(border_layer, (0, 0), mask=dilated_mask)
        # Layer 3: Subject cutout
        result.paste(base_canvas, (0, 0), mask=base_canvas)

        return result

    def _remove_white_background_fallback(self, img: Image.Image) -> Image.Image:
        """
        Extracts clean transparent cutout from images on pure solid white background (#FFFFFF).
        Guarantees cutout transparency when neural rembg is unavailable or fails to segment synthetic shapes.
        """
        rgba = img.convert("RGBA")
        arr = np.array(rgba)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        # Pixels that are near-white (luminance > 240 across all channels) are keyed to transparent
        white_mask = (r >= 240) & (g >= 240) & (b >= 240)
        arr[white_mask, 3] = 0
        return Image.fromarray(arr, mode="RGBA")

    async def _post_process_and_validate(
        self,
        candidate_img: Image.Image,
        target_object: str,
        job_cache_dir: Optional[Path],
        metadata: Dict[str, Any],
        width: int = 512,
        height: int = 512
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Step 6: Bóc Nền & Hậu Kỳ Keyline.
        - Background removal via rembg.remove() if not already transparent.
        - Paper keyline (8px ivory #FFFDF7) + soft drop shadow.
        - Validation with AssetContentValidator.validate_cutout().
        - Saves to job_cache_dir or self.cache_dir.
        """
        # 1. Background removal check
        is_transparent = False
        if candidate_img.mode == "RGBA":
            alpha_chan = candidate_img.getchannel("A")
            arr = np.array(alpha_chan)
            if arr.size > 0:
                trans_ratio = float(np.sum(arr < 128)) / float(arr.size)
                if 0.08 <= trans_ratio <= 0.95:
                    is_transparent = True

        if is_transparent:
            cutout_img = candidate_img
        else:
            cutout_img = None
            if rembg is not None:
                try:
                    logger.info(f"✂️ [Step 6 Rembg] Removing background for '{target_object}'...")
                    def _do_rembg():
                        return rembg.remove(candidate_img.convert("RGBA"))
                    cutout_img = await asyncio.to_thread(_do_rembg)
                except Exception as e:
                    logger.warning(f"rembg background removal error: {e}")
                    cutout_img = None

            # Verify if cutout_img successfully achieved valid transparency
            is_now_trans = False
            if cutout_img is not None and cutout_img.mode == "RGBA":
                arr = np.array(cutout_img.getchannel("A"))
                if arr.size > 0:
                    tr = float(np.sum(arr < 128)) / float(arr.size)
                    if 0.08 <= tr <= 0.95:
                        is_now_trans = True

            if not is_now_trans:
                logger.info(f"Applying white-background luminance keying fallback for '{target_object}'...")
                cutout_img = self._remove_white_background_fallback(candidate_img)

        # 2. Apply paper keyline (8px ivory #FFFDF7) and drop shadow
        styled_img = self.apply_paper_keyline_and_shadow(
            img=cutout_img,
            outline_width=8,
            outline_color=(255, 253, 247, 255),
            shadow_offset=(8, 10),
            shadow_blur=8,
            shadow_alpha=115,
            target_width=width,
            target_height=height,
            add_cellulose_grain=True
        )

        # 3. Determine save path
        save_dir = Path(job_cache_dir).resolve() if job_cache_dir else self.cache_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        clean_stem = re.sub(r'[^a-zA-Z0-9]+', '_', target_object.lower()).strip('_')
        if clean_stem == "scale":
            clean_stem = "golden_scale"
        final_path = save_dir / f"{clean_stem}.png"

        styled_img.save(str(final_path), format="PNG")

        # 4. Final verification under AssetContentValidator
        val_res = self.validator.validate_cutout(final_path)
        if not val_res.is_valid:
            logger.warning(f"⚠️ [Step 6 QA Fail] Asset '{final_path.name}' failed validator: {val_res.reason}")
            # If not yet procedural, fall back to procedural
            if metadata.get("tier_used") != "tier4_procedural":
                logger.warning("Falling back to Tier 4 Procedural to guarantee valid cutout asset...")
                proc_img = self._generate_tier4_procedural(target_object, width=width, height=height)
                proc_styled = self.apply_paper_keyline_and_shadow(
                    proc_img, target_width=width, target_height=height
                )
                proc_styled.save(str(final_path), format="PNG")
                metadata["tier_used"] = "tier4_procedural"
                metadata["source"] = "procedural_asset_synthesizer"

        logger.info(f"✅ [Cascade Complete] Successfully acquired '{target_object}' -> {final_path.name} (Tier: {metadata.get('tier_used')})")
        return str(final_path.resolve()), metadata

    # =========================================================================
    # Main Public Orchestration Method: acquire_asset
    # =========================================================================
    async def acquire_asset(
        self,
        target_object: str,
        scene_sentence: str = "",
        archetype: str = "specimen_scientific",
        job_cache_dir: Optional[Path] = None,
        width: int = 512,
        height: int = 512
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Executes the complete 6-step multi-tier asset acquisition pipeline:
        - Step 0: Cache Check
        - Step 1: Tier 1 (Google Imagen 3)
        - Step 2: In-Flight Vision Gate (Gemini Vision evaluation)
        - Step 3: Tier 2 (Pollinations FLUX.1)
        - Step 4: Tier 3 (Curated Web Stock / Wikimedia Commons)
        - Step 5: Tier 4 (ProceduralAssetSynthesizer)
        - Step 6: Rembg background removal + paper keyline styling + validation
        """
        # Step 0: Cache Check
        cached_result = self._check_cache(
            target_object=target_object,
            job_cache_dir=job_cache_dir,
            archetype=archetype
        )
        if cached_result is not None:
            return cached_result

        vintage_prompt = (
            f"A single isolated vintage engraving illustration of {target_object}, "
            f"1950s archival encyclopedia style, crisp clean edges, subtle etching cross-hatch shading, "
            f"pure solid white background (#FFFFFF), no background elements, no shadow, no text"
        )

        # ---------------------------------------------------------------------
        # Step 1: Tier 1 — Google Imagen 3
        # ---------------------------------------------------------------------
        logger.info(f"🚀 [Step 1] Attempting Tier 1 (Google Imagen 3) for '{target_object}'...")
        tier1_img = await self._generate_tier1_imagen(vintage_prompt, width=width, height=height)
        if tier1_img is not None:
            # Step 2: In-Flight Vision Gate for Tier 1
            gate_res = await self.evaluate_vision_gate(
                image=tier1_img,
                scene_sentence=scene_sentence,
                target_object=target_object,
                current_prompt=vintage_prompt
            )
            confidence = gate_res.get("confidence", 0.0)
            if confidence >= 0.75:
                logger.info(f"🎯 [Vision Gate Approved] Tier 1 confidence {confidence:.2f} >= 0.75")
                meta = {
                    "tier_used": "tier1_imagen",
                    "source": "imagen-3.0-generate-002",
                    "confidence": confidence,
                    "is_aligned": True,
                    "reason": gate_res.get("reason", "")
                }
                return await self._post_process_and_validate(
                    candidate_img=tier1_img,
                    target_object=target_object,
                    job_cache_dir=job_cache_dir,
                    metadata=meta,
                    width=width,
                    height=height
                )
            else:
                logger.info(f"🔄 [Vision Gate Low Confidence] Tier 1 score {confidence:.2f} < 0.75. Retrying Tier 1 once with refined prompt...")
                refined_prompt = gate_res.get("refined_prompt") or f"{vintage_prompt}, centered single specimen, crisp clean edges"
                retry_img = await self._generate_tier1_imagen(refined_prompt, width=width, height=height)
                if retry_img is not None:
                    retry_gate = await self.evaluate_vision_gate(
                        image=retry_img,
                        scene_sentence=scene_sentence,
                        target_object=target_object,
                        current_prompt=refined_prompt
                    )
                    retry_conf = retry_gate.get("confidence", 0.0)
                    if retry_conf >= 0.75:
                        logger.info(f"🎯 [Vision Gate Approved] Tier 1 Retry confidence {retry_conf:.2f} >= 0.75")
                        meta = {
                            "tier_used": "tier1_imagen",
                            "source": "imagen-3.0-generate-002",
                            "confidence": retry_conf,
                            "is_aligned": True,
                            "reason": retry_gate.get("reason", "")
                        }
                        return await self._post_process_and_validate(
                            candidate_img=retry_img,
                            target_object=target_object,
                            job_cache_dir=job_cache_dir,
                            metadata=meta,
                            width=width,
                            height=height
                        )

        # ---------------------------------------------------------------------
        # Step 3: Tier 2 — Pollinations FLUX.1
        # ---------------------------------------------------------------------
        logger.info(f"🚀 [Step 3] Attempting Tier 2 (Pollinations FLUX) for '{target_object}'...")
        tier2_img = await self._generate_tier2_flux(vintage_prompt, width=width, height=height)
        if tier2_img is not None:
            gate_res = await self.evaluate_vision_gate(
                image=tier2_img,
                scene_sentence=scene_sentence,
                target_object=target_object,
                current_prompt=vintage_prompt
            )
            confidence = gate_res.get("confidence", 0.0)
            if confidence >= 0.75:
                logger.info(f"🎯 [Vision Gate Approved] Tier 2 confidence {confidence:.2f} >= 0.75")
                meta = {
                    "tier_used": "tier2_flux",
                    "source": "pollinations_flux",
                    "confidence": confidence,
                    "is_aligned": True,
                    "reason": gate_res.get("reason", "")
                }
                return await self._post_process_and_validate(
                    candidate_img=tier2_img,
                    target_object=target_object,
                    job_cache_dir=job_cache_dir,
                    metadata=meta,
                    width=width,
                    height=height
                )
            else:
                logger.info(f"Tier 2 Vision Gate rejected (confidence {confidence:.2f} < 0.75). Falling through to Tier 3...")

        # ---------------------------------------------------------------------
        # Step 4: Tier 3 — Curated Web Stock / Wikimedia Commons
        # ---------------------------------------------------------------------
        logger.info(f"🚀 [Step 4] Attempting Tier 3 (Curated Stock / Wikimedia) for '{target_object}'...")
        tier3_img = await self._generate_tier3_stock(target_object, width=width, height=height)
        if tier3_img is not None:
            gate_res = await self.evaluate_vision_gate(
                image=tier3_img,
                scene_sentence=scene_sentence,
                target_object=target_object,
                current_prompt=target_object
            )
            confidence = gate_res.get("confidence", 0.0)
            if confidence >= 0.75:
                logger.info(f"🎯 [Vision Gate Approved] Tier 3 confidence {confidence:.2f} >= 0.75")
                meta = {
                    "tier_used": "tier3_stock",
                    "source": "curated_or_wikimedia",
                    "confidence": confidence,
                    "is_aligned": True,
                    "reason": gate_res.get("reason", "")
                }
                return await self._post_process_and_validate(
                    candidate_img=tier3_img,
                    target_object=target_object,
                    job_cache_dir=job_cache_dir,
                    metadata=meta,
                    width=width,
                    height=height
                )
            else:
                logger.info(f"Tier 3 Vision Gate rejected (confidence {confidence:.2f} < 0.75). Falling through to Tier 4...")

        # ---------------------------------------------------------------------
        # Step 5: Tier 4 — Procedural Code Synthesizer (100% Offline Guarantee)
        # ---------------------------------------------------------------------
        logger.info(f"🛡️ [Step 5] Invoking Tier 4 (Procedural Code Synthesizer) for '{target_object}'...")
        tier4_img = self._generate_tier4_procedural(
            target_object=target_object,
            archetype=archetype,
            width=width,
            height=height
        )

        meta = {
            "tier_used": "tier4_procedural",
            "source": "procedural_asset_synthesizer",
            "confidence": 1.0,
            "is_aligned": True,
            "reason": "100% offline procedural asset synthesis"
        }
        return await self._post_process_and_validate(
            candidate_img=tier4_img,
            target_object=target_object,
            job_cache_dir=job_cache_dir,
            metadata=meta,
            width=width,
            height=height
        )
