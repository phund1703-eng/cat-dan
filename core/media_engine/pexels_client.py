"""Pexels API client for stock video/image."""
import os
import urllib.parse
from pathlib import Path

import requests
from loguru import logger
from tqdm import tqdm
from dotenv import load_dotenv

from core.media_engine.asset_provenance import write_asset_meta

load_dotenv()

PEXELS_LICENSE = "Pexels License (free to use, attribution appreciated): https://www.pexels.com/license/"


class PexelsClient:
    """Client for Pexels API."""
    
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY")
        self.base_url = "https://api.pexels.com/v1"
        self.video_url = "https://api.pexels.com/videos"
        self.cache_dir = Path("data/cache/pexels")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.api_key:
            logger.warning("PEXELS_API_KEY is not set in environment variables.")

    @property
    def headers(self) -> dict:
        return {"Authorization": self.api_key} if self.api_key else {}

    def search_videos(self, query: str, per_page: int = 10, orientation: str = 'landscape') -> list[dict]:
        """Search for videos on Pexels."""
        logger.info(f"Searching Pexels for videos: {query}")
        url = f"{self.video_url}/search?query={urllib.parse.quote(query)}&per_page={per_page}&orientation={orientation}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            videos = []
            for item in data.get('videos', []):
                best_file = max(item.get('video_files', []), key=lambda x: x.get('width', 0) * x.get('height', 0), default={})
                videos.append({
                    "id": item.get("id"),
                    "url": item.get("url"),
                    "author": item.get("user", {}).get("name"),
                    "duration": item.get("duration"),
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "thumbnail_url": item.get("image"),
                    "download_url": best_file.get("link")
                })
            return videos
        except Exception as e:
            logger.error(f"Error searching Pexels videos: {e}")
            return []

    def download_video(self, video_info: dict, output_path: str) -> str:
        """Download video file from Pexels."""
        url = video_info.get("download_url")
        if not url:
            raise ValueError("No download URL provided in video_info")
        saved = self._download_file(url, output_path)
        write_asset_meta(
            saved,
            source="pexels",
            source_url=video_info.get("url"),
            author=video_info.get("author"),
            license=PEXELS_LICENSE,
        )
        return saved

    def search_images(self, query: str, per_page: int = 10, orientation: str = 'landscape') -> list[dict]:
        """Search for images on Pexels."""
        logger.info(f"Searching Pexels for images: {query}")
        url = f"{self.base_url}/search?query={urllib.parse.quote(query)}&per_page={per_page}&orientation={orientation}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            images = []
            for item in data.get('photos', []):
                images.append({
                    "id": item.get("id"),
                    "url": item.get("url"),
                    "author": item.get("photographer"),
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "thumbnail_url": item.get("src", {}).get("medium"),
                    "download_url": item.get("src", {}).get("original")
                })
            return images
        except Exception as e:
            logger.error(f"Error searching Pexels images: {e}")
            return []

    def download_image(self, image_info: dict, output_path: str) -> str:
        """Download image file from Pexels."""
        url = image_info.get("download_url")
        if not url:
            raise ValueError("No download URL provided in image_info")
        saved = self._download_file(url, output_path)
        write_asset_meta(
            saved,
            source="pexels",
            source_url=image_info.get("url"),
            author=image_info.get("author"),
            license=PEXELS_LICENSE,
        )
        return saved

    def _download_file(self, url: str, output_path: str) -> str:
        try:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            
            with open(out_path, 'wb') as f, tqdm(
                desc=out_path.name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for data in response.iter_content(block_size):
                    f.write(data)
                    bar.update(len(data))
            
            # Cache logic would go here
            return str(out_path.absolute())
        except Exception as e:
            logger.error(f"Error downloading file {url}: {e}")
            raise
