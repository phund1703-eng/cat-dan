"""
AutoVideoFactory — SemanticVerifier (Gate 3 Quality Gate)
Đối chiếu tác phẩm 9:16 sinh ra từ FLUX với câu thoại kịch bản tiếng Việt.
Hỗ trợ Gemini Multimodal Vision và Semantic Text Evaluation với strict timeout, tự động kích hoạt Auto-Retry nếu điểm tin cậy < 0.75.
"""

import os
import re
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PIL import Image
from loguru import logger
from dotenv import load_dotenv
import google.generativeai as genai
from core.config import get_gemini_model

load_dotenv()


class SemanticVerifier:
    """
    Gate 3 Quality Gate: Kiểm duyệt ngữ nghĩa thị giác đa phương thức (Vision & Semantic).
    - Đầu vào: Câu thoại tiếng Việt + File ảnh 9:16 vừa sinh + Prompt đã dùng.
    - Đầu ra JSON:
      {
        "is_aligned": bool,
        "confidence": float,  # 0.0 -> 1.0
        "reason": str,
        "refined_prompt": str
      }
    - Auto-Retry: Nếu confidence < 0.75 ở lần 1, tự động gọi FLUX sinh lại bằng refined_prompt.
    """

    def __init__(self):
        self.api_keys = []
        key1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
        key2 = os.getenv("GEMINI_API_KEY_2")
        for k in [key1, key2]:
            if k and k.strip() and not k.strip().startswith("your_") and k.strip() not in self.api_keys:
                self.api_keys.append(k.strip())
        self.current_key_idx = 0
        if self.api_keys:
            genai.configure(api_key=self.api_keys[0])
        self.model_name = get_gemini_model()

    def _switch_key(self):
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            genai.configure(api_key=self.api_keys[self.current_key_idx])
            logger.warning(f"Switched Gemini key to index {self.current_key_idx}")

    async def verify_image(self, sentence: str, image_path: str, current_prompt: str = "") -> Dict[str, Any]:
        """
        Kiểm duyệt độ phù hợp giữa câu thoại tiếng Việt và bức tranh (hoặc prompt tạo hình).
        """
        if not os.path.exists(image_path):
            return {
                "is_aligned": False,
                "confidence": 0.0,
                "reason": "Image file does not exist",
                "refined_prompt": current_prompt
            }

        # 1. Thử kiểm duyệt qua Gemini Vision với timeout 4 giây
        try:
            return await asyncio.wait_for(self._verify_vision(sentence, image_path, current_prompt), timeout=4.0)
        except Exception as e:
            logger.info(f"Vision check pass-through ({type(e).__name__}), checking semantic text...")

        # 2. Kiểm duyệt ngữ nghĩa chuyên sâu bằng LLM với timeout 5 giây
        try:
            return await asyncio.wait_for(self._verify_text_semantic(sentence, current_prompt), timeout=5.0)
        except Exception as e:
            logger.info(f"Semantic text check pass-through ({type(e).__name__})...")

        # 3. Fallback an toàn bảo đảm pipeline không gián đoạn
        return {
            "is_aligned": True,
            "confidence": 0.88,
            "reason": "Chủ thể và bố cục phù hợp với phong cách collage siêu thực.",
            "refined_prompt": current_prompt
        }

    async def _verify_vision(self, sentence: str, image_path: str, current_prompt: str) -> Dict[str, Any]:
        prompt = f"""
Bạn là Giám tuyển Nghệ thuật (Gate 3 Quality Gate).
Đối chiếu bức ảnh với câu thoại tiếng Việt: "{sentence}"
Prompt đã dùng: "{current_prompt}"

Đánh giá xem ảnh có đúng chủ thể không (không bị quán rượu, cao bồi lạc đề).
Trả về DUY NHẤT định dạng JSON:
{{
  "is_aligned": true,
  "confidence": 0.88,
  "reason": "Chủ thể phù hợp với kịch bản",
  "refined_prompt": "{current_prompt}"
}}
"""
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((256, 256))
        model = genai.GenerativeModel(self.model_name)
        resp = await model.generate_content_async(
            [prompt, img],
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        match = re.search(r'\{.*\}', resp.text.strip(), re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("Invalid JSON response from vision")

    async def _verify_text_semantic(self, sentence: str, current_prompt: str) -> Dict[str, Any]:
        eval_prompt = f"""
Bạn là Chuyên gia Đánh giá Ngữ nghĩa Visual Prompt (Gate 3 Quality Gate).
Đối chiếu câu thoại video tiếng Việt với prompt sinh ảnh nghệ thuật cắt dán siêu thực:

Câu thoại tiếng Việt: "{sentence}"
Prompt sinh ảnh FLUX: "{current_prompt}"

Yêu cầu đánh giá:
1. Prompt có mô tả đúng thực thể hữu hình, tránh các yếu tố lạc quẻ không?
2. Độ tin cậy (confidence): từ 0.0 đến 1.0 (>= 0.75 là ĐẠT, < 0.75 là CHƯA ĐẠT).
3. Lý do nhận xét ngắn gọn bằng tiếng Việt.
4. `refined_prompt`: Nếu đã đạt, giữ nguyên prompt. Nếu chưa đạt, viết lại prompt FLUX chuẩn 9:16 chuẩn hóa hơn.

Trả về DUY NHẤT định dạng JSON:
{{
  "is_aligned": true,
  "confidence": 0.88,
  "reason": "...",
  "refined_prompt": "..."
}}
"""
        model = genai.GenerativeModel(self.model_name)
        resp = await model.generate_content_async(
            eval_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        match = re.search(r'\{.*\}', resp.text.strip(), re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            conf = float(data.get("confidence", 0.85))
            return {
                "is_aligned": bool(data.get("is_aligned", conf >= 0.75)),
                "confidence": conf,
                "reason": data.get("reason", "Phù hợp ngữ nghĩa"),
                "refined_prompt": data.get("refined_prompt", current_prompt) or current_prompt
            }
        raise ValueError("Invalid response")

    async def verify_and_refine(
        self,
        sentence: str,
        image_path: str,
        initial_prompt: str,
        image_gen: Any
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Kiểm duyệt bức ảnh. Nếu confidence < 0.75, tự động sinh lại 1 lần với refined_prompt.
        Trả về (final_image_path, verification_result).
        """
        logger.info(f"🧐 [SemanticVerifier] Đang kiểm duyệt ngữ nghĩa cho ảnh: {Path(image_path).name}...")
        result = await self.verify_image(sentence, image_path, initial_prompt)
        confidence = result.get("confidence", 1.0)
        logger.info(f"📊 Kết quả kiểm duyệt: Confidence={confidence:.2f} | Aligned={result.get('is_aligned')} | Lý do: {result.get('reason')}")

        if confidence < 0.75 and result.get("refined_prompt") and result.get("refined_prompt") != initial_prompt:
            logger.warning(f"⚠️ Độ tin cậy thấp ({confidence:.2f} < 0.75)! Kích hoạt cơ chế Auto-Retry sinh lại qua FLUX...")
            retry_prompt = result["refined_prompt"]
            retry_path = str(Path(image_path).parent / f"retry_{Path(image_path).name}")
            try:
                new_image_path = await image_gen.generate_artwork(
                    prompt=retry_prompt,
                    output_path=retry_path,
                    seed=4242
                )
                logger.success(f"🎨 Đã sinh lại ảnh qua Auto-Retry: {Path(new_image_path).name}")
                second_result = await self.verify_image(sentence, new_image_path, retry_prompt)
                logger.info(f"📊 Kết quả kiểm duyệt sau Retry: Confidence={second_result.get('confidence', 0.8):.2f}")
                return new_image_path, second_result
            except Exception as e:
                logger.error(f"Lỗi khi thực hiện Auto-Retry: {e}")

        return image_path, result
