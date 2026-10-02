"""Unified media management."""
import re
from pathlib import Path

from loguru import logger
from .pexels_client import PexelsClient
from .pixabay_client import PixabayClient

class MediaManager:
    """Manager for media search and download across different sources."""
    
    def __init__(self):
        self.pexels = PexelsClient()
        self.pixabay = PixabayClient()
        self.cache_dir = Path("data/cache")

    def find_media_for_scene(self, visual_description: str, media_type: str = 'video') -> list[dict]:
        """Searches both Pexels and Pixabay and returns combined and deduplicated results."""
        keywords = self.extract_keywords(visual_description)
        query = " ".join(keywords) if keywords else visual_description
        
        logger.info(f"Searching media for scene with query: {query}, type: {media_type}")
        
        results = []
        if media_type == 'video':
            pex_results = self.pexels.search_videos(query)
            pix_results = self.pixabay.search_videos(query)
        else:
            pex_results = self.pexels.search_images(query)
            pix_results = self.pixabay.search_images(query)
            
        # Combine and simple deduplication based on download_url
        seen_urls = set()
        for item in pex_results + pix_results:
            url = item.get("download_url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(item)
                
        return results

    def download_scene_media(self, scenes: list, output_dir: str, media_type: str = 'video') -> list[str]:
        """For each scene, download 1-2 media files matching visual_description."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        downloaded_paths = []
        
        for i, scene in enumerate(scenes):
            desc = scene.get("visual_description", "")
            media_list = self.find_media_for_scene(desc, media_type)
            
            if not media_list:
                logger.warning(f"No media found for scene {i}: {desc}")
                continue
                
            to_download = media_list[:2]
            for j, media_info in enumerate(to_download):
                ext = ".mp4" if media_type == 'video' else ".jpg"
                out_name = f"scene_{i}_{j}{ext}"
                out_path = out_dir / out_name
                
                try:
                    if "pexels" in media_info.get("url", ""):
                        path = self.pexels.download_video(media_info, str(out_path)) if media_type == 'video' else self.pexels.download_image(media_info, str(out_path))
                    else:
                        path = self.pixabay.download_video(media_info, str(out_path)) if media_type == 'video' else self.pixabay.download_image(media_info, str(out_path))
                    downloaded_paths.append(path)
                except Exception as e:
                    logger.error(f"Failed to download media for scene {i}: {e}")
                    
        return downloaded_paths

    def extract_keywords(self, text: str) -> list[str]:
        """Extract search keywords from text."""
        stop_words = {"a", "an", "the", "and", "or", "but", "is", "are", "was", "were", "in", "on", "at", "to", "for", "with"}
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords[:5]

    def get_cached_media(self, query: str) -> list[str] | None:
        """Check if we already have downloaded media for this query."""
        logger.info(f"Checking cache for query: {query}")
        return None
