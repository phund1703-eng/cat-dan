"""Pixabay API client for stock video/image."""
import os
import urllib.parse
from pathlib import Path

import requests
from loguru import logger
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

class PixabayClient:
    """Client for Pixabay API."""
    
    def __init__(self):
        self.api_key = os.getenv("PIXABAY_API_KEY")
        self.base_url = "https://pixabay.com/api/"
        self.video_url = "https://pixabay.com/api/videos/"
        self.cache_dir = Path("data/cache/pixabay")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.api_key:
            logger.warning("PIXABAY_API_KEY is not set in environment variables.")

    def search_videos(self, query: str, per_page: int = 10) -> list[dict]:
        """Search for videos on Pixabay."""
        logger.info(f"Searching Pixabay for videos: {query}")
        url = f"{self.video_url}?key={self.api_key}&q={urllib.parse.quote(query)}&per_page={per_page}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            videos = []
            for item in data.get('hits', []):
                videos_data = item.get('videos', {})
                best_file = videos_data.get('large', videos_data.get('medium', {}))
                videos.append({
                    "id": item.get("id"),
                    "url": item.get("pageURL"),
                    "duration": item.get("duration"),
                    "width": best_file.get("width"),
                    "height": best_file.get("height"),
                    "thumbnail_url": item.get("picture_id"),
                    "download_url": best_file.get("url")
                })
            return videos
        except Exception as e:
            logger.error(f"Error searching Pixabay videos: {e}")
            return []

    def download_video(self, video_info: dict, output_path: str) -> str:
        """Download video file from Pixabay."""
        url = video_info.get("download_url")
        if not url:
            raise ValueError("No download URL provided in video_info")
        return self._download_file(url, output_path)

    def search_images(self, query: str, per_page: int = 10) -> list[dict]:
        """Search for images on Pixabay."""
        logger.info(f"Searching Pixabay for images: {query}")
        url = f"{self.base_url}?key={self.api_key}&q={urllib.parse.quote(query)}&per_page={per_page}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            images = []
            for item in data.get('hits', []):
                images.append({
                    "id": item.get("id"),
                    "url": item.get("pageURL"),
                    "width": item.get("imageWidth"),
                    "height": item.get("imageHeight"),
                    "thumbnail_url": item.get("previewURL"),
                    "download_url": item.get("largeImageURL")
                })
            return images
        except Exception as e:
            logger.error(f"Error searching Pixabay images: {e}")
            return []

    def download_image(self, image_info: dict, output_path: str) -> str:
        """Download image file from Pixabay."""
        url = image_info.get("download_url")
        if not url:
            raise ValueError("No download URL provided in image_info")
        return self._download_file(url, output_path)

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
            
            return str(out_path.absolute())
        except Exception as e:
            logger.error(f"Error downloading file {url}: {e}")
            raise
