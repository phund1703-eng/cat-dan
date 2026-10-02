"""FFmpeg utility functions."""
from pathlib import Path
from loguru import logger
import ffmpeg

def get_video_info(video_path: str) -> dict:
    """Returns duration, width, height, fps, audio info."""
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
        
        info = {
            "duration": float(probe.get('format', {}).get('duration', 0)),
            "width": int(video_stream.get('width', 0)) if video_stream else 0,
            "height": int(video_stream.get('height', 0)) if video_stream else 0,
            "fps": eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0,
            "has_audio": audio_stream is not None
        }
        return info
    except ffmpeg.Error as e:
        logger.error(f"Error probing video {video_path}: {e}")
        return {}

def concat_videos(video_paths: list[str], output_path: str, transition: str = 'none') -> str:
    """Concatenate video files."""
    logger.info(f"Concatenating {len(video_paths)} videos to {output_path}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    list_file_path = out_path.parent / "concat_list.txt"
    with open(list_file_path, "w", encoding="utf-8") as f:
        for p in video_paths:
            posix_p = Path(p).resolve().as_posix()
            f.write(f"file '{posix_p}'\n")
            
    try:
        (
            ffmpeg
            .input(str(list_file_path), format='concat', safe=0)
            .output(str(out_path), c='copy')
            .run(overwrite_output=True, quiet=True)
        )
        return str(out_path.absolute())
    except ffmpeg.Error as e:
        logger.error(f"Error concatenating videos: {e}")
        raise
    finally:
        if list_file_path.exists():
            list_file_path.unlink()

def add_audio_to_video(video_path: str, audio_path: str, output_path: str, audio_volume: float = 1.0) -> str:
    """Mix audio with video."""
    logger.info(f"Adding audio {audio_path} to video {video_path}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        video = ffmpeg.input(video_path)
        audio = ffmpeg.input(audio_path).filter('volume', audio_volume)
        
        out = ffmpeg.output(video.video, audio, str(out_path), vcodec='copy', acodec='aac', shortest=None)
        out.run(overwrite_output=True, quiet=True)
        return str(out_path.absolute())
    except ffmpeg.Error as e:
        logger.error(f"Error adding audio: {e}")
        raise

def add_background_music(video_path: str, music_path: str, output_path: str, music_volume: float = 0.08) -> str:
    """Add background music at low volume."""
    logger.info(f"Adding BGM {music_path} to {video_path}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        video = ffmpeg.input(video_path)
        music = ffmpeg.input(music_path).filter('volume', music_volume)
        
        info = get_video_info(video_path)
        if info.get('has_audio'):
            vid_audio = video.audio
            mixed_audio = ffmpeg.filter([vid_audio, music], 'amix', inputs=2, duration='first')
            out = ffmpeg.output(video.video, mixed_audio, str(out_path), vcodec='copy', acodec='aac')
        else:
            out = ffmpeg.output(video.video, music, str(out_path), vcodec='copy', acodec='aac', shortest=None)
            
        out.run(overwrite_output=True, quiet=True)
        return str(out_path.absolute())
    except ffmpeg.Error as e:
        logger.error(f"Error adding BGM: {e}")
        raise

def resize_video(input_path: str, output_path: str, width: int, height: int) -> str:
    """Resize/crop video to target dimensions."""
    logger.info(f"Resizing {input_path} to {width}x{height}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.filter(stream, 'scale', width, height, force_original_aspect_ratio='increase')
        stream = ffmpeg.filter(stream, 'crop', width, height)
        stream = ffmpeg.output(stream, str(out_path), vcodec='libx264', acodec='copy')
        stream.run(overwrite_output=True, quiet=True)
        return str(out_path.absolute())
    except ffmpeg.Error as e:
        logger.error(f"Error resizing video: {e}")
        raise

def add_text_overlay(video_path: str, text: str, output_path: str, position: str = 'bottom', style: dict = None) -> str:
    """Add animated text overlay."""
    logger.info(f"Adding text overlay to {video_path}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        stream = ffmpeg.input(video_path)
        y_pos = "h-th-10" if position == 'bottom' else "10"
        stream = ffmpeg.drawtext(stream, text=text, x="(w-tw)/2", y=y_pos, fontsize=24, fontcolor='white')
        stream = ffmpeg.output(stream, str(out_path), vcodec='libx264', acodec='copy')
        stream.run(overwrite_output=True, quiet=True)
        return str(out_path.absolute())
    except ffmpeg.Error as e:
        logger.error(f"Error adding text overlay: {e}")
        raise

def create_slideshow(image_paths: list[str], audio_path: str, output_path: str, duration_per_image: float = 3.0) -> str:
    """Create video slideshow from images + audio."""
    logger.info(f"Creating slideshow from {len(image_paths)} images")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        list_file_path = out_path.parent / "img_list.txt"
        with open(list_file_path, "w", encoding="utf-8") as f:
            for p in image_paths:
                f.write(f"file '{Path(p).absolute()}'\n")
                f.write(f"duration {duration_per_image}\n")
        
        video = ffmpeg.input(str(list_file_path), format='concat', safe=0)
        audio = ffmpeg.input(audio_path)
        
        out = ffmpeg.output(video, audio, str(out_path), vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
        out.run(overwrite_output=True, quiet=True)
        return str(out_path.absolute())
    except ffmpeg.Error as e:
        logger.error(f"Error creating slideshow: {e}")
        raise
    finally:
        if 'list_file_path' in locals() and list_file_path.exists():
            list_file_path.unlink()

def trim_video(input_path: str, output_path: str, start: float, end: float) -> str:
    """Trim video."""
    logger.info(f"Trimming {input_path} from {start} to {end}")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        stream = ffmpeg.input(input_path, ss=start, to=end)
        stream = ffmpeg.output(stream, str(out_path), c='copy')
        stream.run(overwrite_output=True, quiet=True)
        return str(out_path.absolute())
    except ffmpeg.Error as e:
        logger.error(f"Error trimming video: {e}")
        raise
