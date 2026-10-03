"""
AutoVideoFactory — Publishing Module
Tích hợp với Postiz (self-hosted) để đăng video lên các nền tảng
"""

import os
import mimetypes
import httpx
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class PostizClient:
    """
    Client tích hợp với Postiz self-hosted instance.
    Postiz: https://github.com/gitroomhq/postiz-app
    
    Cài Postiz: docker run -d -p 3000:3000 ghcr.io/gitroomhq/postiz-app:latest
    """
    
    def __init__(self):
        self.base_url = os.getenv("POSTIZ_URL", "http://localhost:3000")
        self.api_key = os.getenv("POSTIZ_API_KEY", "")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def check_health(self) -> bool:
        """Kiểm tra Postiz có đang chạy không"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/health", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
    
    async def schedule_post(
        self,
        video_path: str,
        title: str,
        description: str,
        hashtags: list[str],
        platforms: list[str],
        schedule_time: Optional[datetime] = None,
        thumbnail_path: Optional[str] = None,
    ) -> dict:
        """
        Đặt lịch đăng video lên các nền tảng qua Postiz.
        
        Args:
            video_path: Đường dẫn file video
            title: Tiêu đề video
            description: Mô tả video
            hashtags: Danh sách hashtag
            platforms: ['youtube', 'tiktok', 'facebook', 'instagram']
            schedule_time: Thời gian đăng (None = đăng ngay)
            thumbnail_path: Ảnh thumbnail (optional)
            
        Returns:
            dict với thông tin job đăng bài
        """
        
        # Upload video file trước
        logger.info(f"📤 Đang upload video lên Postiz: {Path(video_path).name}")
        upload_result = await self._upload_media(video_path)
        
        thumbnail_id = None
        if thumbnail_path:
            thumbnail_result = await self._upload_media(thumbnail_path)
            thumbnail_id = thumbnail_result.get("id")
        
        # Tạo post payload
        content = f"{title}\n\n{description}\n\n{' '.join(hashtags)}"
        
        payload = {
            "content": content,
            "mediaIds": [upload_result["id"]],
            "platforms": platforms,
        }
        
        if schedule_time:
            payload["scheduledAt"] = schedule_time.isoformat()
        
        if thumbnail_id:
            payload["thumbnailId"] = thumbnail_id
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/posts",
                headers=self.headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            
        logger.success(f"✅ Đã lên lịch đăng bài thành công: {result.get('id')}")
        return result
    
    async def _upload_media(self, file_path: str) -> dict:
        """Upload media file lên Postiz"""
        file_path = Path(file_path)
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, mime_type)}
                response = await client.post(
                    f"{self.base_url}/api/media",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    timeout=120.0,  # Upload có thể mất thời gian
                )
                response.raise_for_status()
                return response.json()
    
    async def get_post_status(self, post_id: str) -> dict:
        """Kiểm tra trạng thái bài đăng"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/posts/{post_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
