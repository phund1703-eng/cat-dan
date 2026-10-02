"""
AutoVideoFactory — Metadata Generator
Tự động sinh title, description, hashtags từ script dùng Gemini
"""

import json
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class MetadataGenerator:
    """
    Sinh metadata SEO-optimized cho video:
    - Title hấp dẫn
    - Description chi tiết
    - Hashtags trending
    - Tags YouTube
    """
    
    def __init__(self):
        from core.script_engine.gemini_client import GeminiClient
        self.gemini = GeminiClient()
    
    async def generate(
        self,
        script: dict,
        language: str = "vi",
        style: str = "collage_broll",
        platform: str = "youtube",
    ) -> dict:
        """
        Sinh metadata cho video.
        
        Args:
            script: Script dict với title, description, scenes
            language: 'vi' hoặc 'en'
            style: Phong cách video
            platform: 'youtube', 'tiktok', 'facebook'
            
        Returns:
            dict: {title, description, hashtags, tags, thumbnail_text}
        """
        
        if not self.gemini.api_keys:
            logger.info("Chưa có Gemini API key, sử dụng fallback metadata từ kịch bản.")
            return self._fallback_metadata(script, language)
            
        # Tạo prompt theo platform
        prompt = self._build_prompt(script, language, style, platform)
        
        try:
            response = await self.gemini.generate(prompt)
            
            # Parse JSON từ response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            metadata = json.loads(json_str)
            logger.success(f"✅ Đã sinh metadata: {metadata.get('title', '')[:50]}...")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Lỗi sinh metadata: {e}")
            # Fallback: dùng thông tin từ script
            return self._fallback_metadata(script, language)
    
    def _build_prompt(self, script: dict, language: str, style: str, platform: str) -> str:
        """Tạo prompt sinh metadata"""
        
        # Tóm tắt nội dung
        narrations = [s.get("narration", "") for s in script.get("scenes", [])]
        content_summary = " ".join(narrations)[:500]
        
        if language == "vi":
            platform_tips = {
                "youtube": "YouTube: Title 60-70 ký tự, Description 150-200 từ với từ khóa SEO, Tags 5-10",
                "tiktok": "TikTok: Caption ngắn gọn (<150 ký tự), Hashtags trending 5-8 cái",
                "facebook": "Facebook: Description 100-150 từ, ít hashtag hơn (3-5)",
            }
            tip = platform_tips.get(platform, platform_tips["youtube"])
            
            return f"""Bạn là chuyên gia SEO và mạng xã hội. Hãy tạo metadata hấp dẫn cho video sau:

NỘI DUNG VIDEO:
{content_summary}

PHONG CÁCH: {style}
NỀN TẢNG: {platform.upper()}
QUY TẮC: {tip}

Hãy tạo metadata theo định dạng JSON sau:
```json
{{
  "title": "Tiêu đề hấp dẫn, có từ khóa, tạo curiosity gap",
  "description": "Mô tả chi tiết với từ khóa SEO, CTA, links...",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "tags": ["tag1", "tag2", "tag3"],
  "thumbnail_text": "Chữ ngắn gọn cho thumbnail (5-8 từ)"
}}
```

Lưu ý:
- Title phải tạo curiosity, có số liệu hoặc từ mạnh
- Description bắt đầu bằng hook (câu đầu quan trọng nhất)
- Hashtags phải trending và liên quan
- Thumbnail text phải nổi bật, dễ đọc"""
        else:
            return f"""You are an expert in SEO and social media marketing. Create compelling metadata for this video:

VIDEO CONTENT:
{content_summary}

STYLE: {style}
PLATFORM: {platform.upper()}

Create metadata in this JSON format:
```json
{{
  "title": "Engaging title with keywords and curiosity gap",
  "description": "Detailed description with SEO keywords, CTA, and value proposition",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "tags": ["tag1", "tag2", "tag3"],
  "thumbnail_text": "Short punchy text for thumbnail (3-6 words)"
}}
```

Requirements:
- Title must create curiosity, include numbers or power words
- Description starts with a hook
- Hashtags must be trending and relevant"""
    
    def _fallback_metadata(self, script: dict, language: str) -> dict:
        """Fallback metadata nếu Gemini thất bại"""
        title = script.get("title", "Video mới")
        return {
            "title": title,
            "description": script.get("description", title),
            "hashtags": script.get("hashtags", []),
            "tags": [],
            "thumbnail_text": title[:30],
        }
