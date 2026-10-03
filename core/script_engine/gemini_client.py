import os
import json
import asyncio
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from loguru import logger
from dotenv import load_dotenv

from core.config import get_gemini_model

load_dotenv()

DEFAULT_FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"]

class GeminiClient:
    """Client for interacting with Google's Gemini API with Dual-Key Failover and Dynamic Model Fallback support."""

    DEFAULT_FALLBACK_MODELS = DEFAULT_FALLBACK_MODELS

    def __init__(self):
        """Initializes the GeminiClient with API keys from environment."""
        self.api_keys = []
        key1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
        key2 = os.getenv("GEMINI_API_KEY_2")
        
        for k in [key1, key2]:
            if k and k.strip() and not k.strip().startswith("your_") and k.strip() not in self.api_keys:
                self.api_keys.append(k.strip())
                
        self.current_key_index = 0
        if not self.api_keys:
            logger.warning("No valid Gemini API key found (GEMINI_API_KEY_1, GEMINI_API_KEY_2, or GEMINI_API_KEY).")
        else:
            self._apply_current_key()
            logger.info(f"GeminiClient initialized with {len(self.api_keys)} API key(s). Active key: Key #{self.current_key_index + 1}")
            
        # Model Gemini đọc từ nguồn cấu hình duy nhất (core/config.py):
        # env GEMINI_MODEL/GEMINI_PRO_MODEL (override) → settings.yaml llm.*.
        self.default_model = get_gemini_model()
        self.pro_model = get_gemini_model(pro=True)
        # Chuỗi fallback: model mặc định hiện tại đứng đầu, sau đó tới
        # danh sách fallback chuẩn (dedup, giữ nguyên thứ tự cũ khi
        # settings.yaml để model mặc định).
        self.fallback_models = list(
            dict.fromkeys([self.default_model, *DEFAULT_FALLBACK_MODELS])
        )

    def _apply_current_key(self):
        """Applies the current active API key to genai."""
        if self.api_keys:
            active_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=active_key)
            masked = active_key[:4] + "..." + active_key[-4:] if len(active_key) > 8 else "***"
            logger.info(f"Configured Gemini with key #{self.current_key_index + 1} ({masked})")

    def switch_key_on_quota(self) -> bool:
        """
        Switches to the alternate key when encountering quota limits (HTTP 429).
        Returns True if a switch was performed, False if no other keys available.
        """
        if len(self.api_keys) > 1:
            prev_index = self.current_key_index
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            logger.warning(
                f"⚠️ Quota exceeded (HTTP 429) on Key #{prev_index + 1}! "
                f"Failover triggered: Switching to Key #{self.current_key_index + 1}."
            )
            self._apply_current_key()
            return True
        logger.error("⚠️ Quota exceeded (HTTP 429), but no backup Gemini API key (GEMINI_API_KEY_2) is configured!")
        return False

    def _is_quota_error(self, exc: Exception) -> bool:
        """Checks if exception is a 429 or quota exhaustion error."""
        msg = str(exc).lower()
        return "429" in msg or "resourceexhausted" in msg or "quota" in msg or "rate limit" in msg

    def _get_candidate_models(self, preferred_model: Optional[str] = None) -> List[str]:
        """Builds deduplicated list of candidate models starting with preferred model."""
        candidates = []
        primary = preferred_model or self.default_model
        if primary:
            candidates.append(primary)
        for m in self.fallback_models:
            if m and m not in candidates:
                candidates.append(m)
        return candidates

    async def generate(self, prompt: str, model: str = None, temperature: float = 0.7) -> str:
        """
        Generates text using the Gemini API with automatic key failover and dynamic model fallback.
        Calls gen_model.generate_content via asyncio.to_thread to prevent gRPC loop conflicts on Windows.
        """
        candidate_models = self._get_candidate_models(model)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
        )
        
        last_error = None
        for m_idx, candidate_model in enumerate(candidate_models):
            logger.info(
                f"Attempting text generation with model '{candidate_model}' "
                f"(candidate {m_idx + 1}/{len(candidate_models)})"
            )
            max_attempts = max(2, len(self.api_keys) * 2) if self.api_keys else 1
            for attempt in range(max_attempts):
                try:
                    gen_model = genai.GenerativeModel(model_name=candidate_model)
                    response = await asyncio.to_thread(
                        gen_model.generate_content,
                        prompt,
                        generation_config=generation_config
                    )
                    return response.text
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Error generating text with model '{candidate_model}' "
                        f"(Attempt {attempt + 1}/{max_attempts}): {e}"
                    )
                    if self._is_quota_error(e) and self.switch_key_on_quota():
                        continue
                    # Non-quota error or out of keys to switch: fall back to next model
                    break
        
        logger.error(f"All candidate models {candidate_models} failed for generate. Last error: {last_error}")
        raise last_error or RuntimeError("Failed to generate text after testing all candidate models")

    async def generate_script(self, topic: str, style: str, language: str, duration: int = 60, model: str = None) -> Dict[str, Any]:
        """
        Generates a video script structured as JSON with automatic key failover and dynamic model fallback.
        Calls gen_model.generate_content via asyncio.to_thread to prevent gRPC loop conflicts on Windows.
        """
        from .prompt_templates import PromptTemplates
        from .scene_schema import normalize_script_scenes

        prompt = PromptTemplates.get_script_prompt(topic, style, language, duration)
        candidate_models = self._get_candidate_models(model)
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            response_mime_type="application/json"
        )
        
        last_error = None
        for m_idx, candidate_model in enumerate(candidate_models):
            logger.info(
                f"Attempting script generation with model '{candidate_model}' "
                f"(candidate {m_idx + 1}/{len(candidate_models)})"
            )
            max_attempts = len(self.api_keys) if self.api_keys else 1
            for attempt in range(max_attempts):
                try:
                    gen_model = genai.GenerativeModel(model_name=candidate_model)
                    response = await asyncio.to_thread(
                        gen_model.generate_content,
                        prompt,
                        generation_config=generation_config
                    )
                    
                    try:
                        result = json.loads(response.text)
                        logger.success(f"Successfully generated script for topic '{topic}' using model '{candidate_model}'")
                        return normalize_script_scenes(result)
                    except (json.JSONDecodeError, AttributeError) as e:
                        logger.warning(
                            f"Failed to parse JSON from Gemini response using model '{candidate_model}': {e}. "
                            f"Attempting markdown extraction..."
                        )
                        import re
                        raw_text = getattr(response, "text", "")
                        match = re.search(r'```(?:json)?(.*?)```', raw_text, re.DOTALL)
                        if match:
                            try:
                                result = json.loads(match.group(1).strip())
                                logger.success(f"Successfully extracted JSON from markdown block using model '{candidate_model}'")
                                return normalize_script_scenes(result)
                            except Exception:
                                pass
                        raise ValueError(f"Could not parse valid JSON from response: {raw_text[:200]}")
                        
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Error generating script with model '{candidate_model}' "
                        f"(Attempt {attempt + 1}/{max_attempts}): {e}"
                    )
                    if self._is_quota_error(e):
                        if attempt < len(self.api_keys) - 1:
                            self.switch_key_on_quota()
                            continue
                    # Break out to try next candidate model
                    break
        
        logger.error(f"All candidate models {candidate_models} failed to generate script. Last error: {last_error}")
        raise last_error or RuntimeError("Failed to generate script after testing all candidate models")
