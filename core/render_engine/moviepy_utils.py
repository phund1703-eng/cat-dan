"""MoviePy utility functions."""
from pathlib import Path
from loguru import logger

try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ImageClip, concatenate_videoclips
except ImportError:
    logger.warning("moviepy not installed. MoviePy utilities will not work.")

def create_video_with_text(clips_info: list[dict], output_path: str) -> str:
    """Creates video with text overlaid on each clip.
    clips_info: [{"path": str, "text": str, "duration": float}]
    """
    logger.info("Creating video with text using MoviePy")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    final_clips = []
    try:
        for info in clips_info:
            path = info.get("path")
            text = info.get("text")
            dur = info.get("duration", 3.0)
            
            if not path: continue
            
            if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                clip = ImageClip(path).set_duration(dur)
            else:
                clip = VideoFileClip(path).subclip(0, dur)
                
            if text:
                txt_clip = TextClip(text, fontsize=70, color='white')
                txt_clip = txt_clip.set_position('bottom').set_duration(dur)
                clip = CompositeVideoClip([clip, txt_clip])
                
            final_clips.append(clip)
            
        if final_clips:
            final_video = concatenate_videoclips(final_clips)
            final_video.write_videofile(str(out_path), fps=24)
        return str(out_path.absolute())
    except Exception as e:
        logger.error(f"Error creating video with text: {e}")
        raise

def add_intro_outro(video_path: str, output_path: str, intro_path: str = None, outro_path: str = None) -> str:
    """Add intro and/or outro to a video."""
    logger.info(f"Adding intro/outro to {video_path}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        clips = []
        if intro_path:
            clips.append(VideoFileClip(intro_path))
            
        clips.append(VideoFileClip(video_path))
        
        if outro_path:
            clips.append(VideoFileClip(outro_path))
            
        final_video = concatenate_videoclips(clips)
        final_video.write_videofile(str(out_path), fps=24)
        return str(out_path.absolute())
    except Exception as e:
        logger.error(f"Error adding intro/outro: {e}")
        raise

def apply_ken_burns(image_path: str, output_path: str, duration: float = 5.0, zoom_direction: str = 'in') -> str:
    """Ken Burns effect (pan + zoom) on still image."""
    logger.info(f"Applying Ken Burns to {image_path}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        clip = ImageClip(image_path).set_duration(duration)
        
        def resize_func(t):
            if zoom_direction == 'in':
                return 1 + 0.05 * t
            else:
                return 1.2 - 0.05 * t
                
        clip = clip.resize(resize_func)
        clip = clip.set_position('center')
        
        clip.write_videofile(str(out_path), fps=24)
        return str(out_path.absolute())
    except Exception as e:
        logger.error(f"Error applying Ken Burns: {e}")
        raise

def create_text_animation(text: str, output_path: str, duration: float = 3.0, style: str = 'fade_in') -> str:
    """Creates a short animated text clip."""
    logger.info(f"Creating text animation for '{text}'")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        txt_clip = TextClip(text, fontsize=70, color='white', bg_color='black', size=(1920, 1080))
        txt_clip = txt_clip.set_position('center').set_duration(duration)
        
        if style == 'fade_in':
            txt_clip = txt_clip.crossfadein(1.0)
            
        txt_clip.write_videofile(str(out_path), fps=24)
        return str(out_path.absolute())
    except Exception as e:
        logger.error(f"Error creating text animation: {e}")
        raise
