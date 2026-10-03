"""
AutoVideoFactory — Metadata Generator
Tự động sinh title, description, hashtags từ script dùng Gemini
"""

import json
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def collect_sources(script: dict) -> list:
    """Danh sách nguồn trích dẫn từ mọi scene, deduplicate theo URL (Task 2.4)."""
    seen = set()
    collected = []
    for scene in (script or {}).get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        for src in scene.get("sources") or []:
            if not isinstance(src, dict):
                continue
            url = str(src.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            collected.append({
                "title": str(src.get("title") or ""),
                "url": url,
                "publisher": str(src.get("publisher") or ""),
                "accessed_date": str(src.get("accessed_date") or ""),
            })
    return collected


def format_sources_section(script: dict, language: str = "vi") -> str:
    """Khối 'Nguồn tham khảo:' để chèn vào mô tả video. Rỗng khi chưa có nguồn."""
    sources = collect_sources(script)
    if not sources:
        return ""
    heading = "Nguồn tham khảo:" if language == "vi" else "Sources:"
    lines = [heading]
    for s in sources:
        label = s["title"] or s["url"]
        lines.append(f"- {label}: {s['url']}" if label != s["url"] else f"- {s['url']}")
    return "\n".join(lines)


def append_sources_to_description(description: str, script: dict, language: str = "vi") -> str:
    """Chèn mục nguồn tham khảo vào cuối mô tả (idempotent)."""
    section = format_sources_section(script, language)
    if not section:
        return description or ""
    desc = (description or "").rstrip()
    if section.splitlines()[0] in desc:
        return description or ""
    return f"{desc}\n\n{section}" if desc else section


def build_sources_payload(scenes: list) -> dict:
    """Payload cho sources.json khi export ZIP: nguồn dedupe + nguồn theo từng cảnh."""
    per_scene = []
    for i, sc in enumerate(scenes or []):
        if not isinstance(sc, dict):
            continue
        srcs = [
            s for s in (sc.get("sources") or [])
            if isinstance(s, dict) and str(s.get("url") or "").strip()
        ]
        per_scene.append({
            "scene_index": sc.get("scene_index", sc.get("index", i)),
            "fact": sc.get("fact", ""),
            "sources": srcs,
        })
    return {"sources": collect_sources({"scenes": scenes or []}), "scenes": per_scene}


def build_sources_markdown(scenes: list) -> str:
    """Nội dung sources.md khi export ZIP."""
    payload = build_sources_payload(scenes)
    lines = ["# Nguồn tham khảo", ""]
    if payload["sources"]:
        for s in payload["sources"]:
            title = s["title"] or s["url"]
            extras = [x for x in [s["publisher"], (f"truy cập {s['accessed_date']}" if s["accessed_date"] else "")] if x]
            lines.append(f"- [{title}]({s['url']})" + (f" — {' · '.join(extras)}" if extras else ""))
    else:
        lines.append("_Chưa có nguồn trích dẫn nào được ghi nhận._")

    lines += ["", "## Nguồn theo từng cảnh", ""]
    for item in payload["scenes"]:
        fact = item["fact"] or "(không có fact)"
        lines.append(f"### Cảnh #{int(item['scene_index']) + 1}: {fact}")
        if item["sources"]:
            for s in item["sources"]:
                lines.append(f"- [{s.get('title') or s['url']}]({s['url']})")
        else:
            lines.append("- (chưa có nguồn)")
        lines.append("")
    return "\n".join(lines)


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
            return self._with_sources_section(self._fallback_metadata(script, language), script, language)
            
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
            return self._with_sources_section(metadata, script, language)

        except Exception as e:
            logger.error(f"❌ Lỗi sinh metadata: {e}")
            # Fallback: dùng thông tin từ script
            return self._with_sources_section(self._fallback_metadata(script, language), script, language)
    
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
    
    @staticmethod
    def _with_sources_section(metadata: dict, script: dict, language: str) -> dict:
        """Chèn mục 'Nguồn tham khảo:' vào mô tả + đính kèm danh sách nguồn (Task 2.4)."""
        if isinstance(metadata, dict):
            metadata["description"] = append_sources_to_description(
                metadata.get("description", ""), script, language
            )
            metadata["sources"] = collect_sources(script)
        return metadata

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
