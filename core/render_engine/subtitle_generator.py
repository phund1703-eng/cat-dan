"""Auto subtitle generation using faster-whisper."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Union, List, Optional, Dict, Any

from loguru import logger
from PIL import Image, ImageDraw, ImageFont
import ffmpeg

from core.render_engine.ffmpeg_utils import get_video_info

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    logger.warning("faster-whisper is not installed. Subtitle generation will fail.")

class SubtitleGenerator:
    """Generates subtitles from audio."""
    
    def __init__(self, model_size: str = "base", compute_type: str = "int8"):
        """Initialize the Whisper model."""
        self.model_size = model_size
        if WhisperModel:
            try:
                # Ưu tiên CPU int8 trên Windows để tránh phụ thuộc cublas64_12.dll
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            except Exception as e:
                logger.warning(f"Error initializing WhisperModel: {e}")
                self.model = None
        else:
            self.model = None

    def format_timestamp(self, seconds: float, separator: str = ',') -> str:
        """Format timestamp for SRT."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}{separator}{millis:03d}"

    def generate_srt(self, audio_path: str, output_path: str, language: str = 'vi') -> str:
        """Transcribe audio and save as SRT."""
        logger.info(f"Generating SRT for {audio_path} in language {language}")
        if not self.model:
            try:
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except Exception as e:
                raise RuntimeError(f"Whisper model not loaded: {e}")
            
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            segments, info = self.model.transcribe(audio_path, language=language)
            segments_list = list(segments)
        except Exception as e:
            logger.warning(f"Transcribe retry with CPU int8 due to: {e}")
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            segments, info = self.model.transcribe(audio_path, language=language)
            segments_list = list(segments)
        
        with open(out_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments_list, start=1):
                start = self.format_timestamp(segment.start)
                end = self.format_timestamp(segment.end)
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{segment.text.strip()}\n\n")
                
        return str(out_path.absolute())

    def generate_ass(self, audio_path: str, output_path: str, language: str = 'vi', style: dict = None) -> str:
        """Generate ASS subtitle."""
        logger.info(f"Generating ASS for {audio_path}")
        if not self.model:
            raise RuntimeError("Whisper model not loaded.")
            
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        ass_content = """[Script Info]
ScriptType: v4.00+
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        segments, info = self.model.transcribe(audio_path, language=language)
        
        for segment in segments:
            start = self.format_timestamp(segment.start, '.')[:10]
            end = self.format_timestamp(segment.end, '.')[:10]
            if len(start) == 12: start = start[1:]
            if len(end) == 12: end = end[1:]
            
            text = segment.text.strip()
            ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"
            
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
            
    @staticmethod
    def _format_ass_timestamp_static(seconds: float) -> str:
        """Format timestamp for ASS (H:MM:SS.cs) with robust centisecond rounding."""
        seconds = max(0.0, float(seconds))
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        if centis >= 100:
            centis = 0
            secs += 1
            if secs >= 60:
                secs = 0
                mins += 1
                if mins >= 60:
                    mins = 0
                    hrs += 1
        return f"{hrs:d}:{mins:02d}:{secs:02d}.{centis:02d}"

    def format_ass_timestamp(self, seconds: float) -> str:
        """Format timestamp for ASS (H:MM:SS.cs)."""
        return self._format_ass_timestamp_static(seconds)

    @staticmethod
    def generate_dynamic_chunked_ass(
        sentence: str,
        duration: float,
        output_path: Union[str, Path],
        chunk_words: int = 3,
        font_size: int = 44,
        margin_v: int = 180
    ) -> str:
        """
        Generates dynamic chunked ASS subtitles (TikTok style) with 2-4 words per chunk.

        - 2-4 words grouping logic: slices by chunk_words (default 3); if the final
          chunk has only 1 word, it merges into the previous chunk (resulting in 4 words).
        - Uniform duration distribution: chunk_dur = duration / total_chunks.
        - Alternating colors: TikTokYellow (&H0000FFFF) and TikTokWhite (&H00FFFFFF).
        - Safe Zone: 9:16 vertical resolution (1080x1920), MarginV=180, Fontsize=44.
        """
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        res_x = 1080
        res_y = 1920

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokYellow,Arial,{font_size},&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,2,30,30,{margin_v},1
Style: TikTokWhite,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,2,30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        words = sentence.strip().split()
        if not words:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(ass_header)
            return str(out_path)

        # 1. 2-4 words grouping logic
        if len(words) <= chunk_words:
            chunks = [words]
        else:
            raw_chunks = []
            for i in range(0, len(words), chunk_words):
                raw_chunks.append(words[i:i + chunk_words])

            # Merge leftover 1 word into previous chunk
            if len(raw_chunks) > 1 and len(raw_chunks[-1]) == 1:
                leftover = raw_chunks.pop()
                raw_chunks[-1].extend(leftover)

            chunks = raw_chunks

        total_chunks = len(chunks)
        effective_dur = max(0.1, float(duration))
        chunk_dur = effective_dur / total_chunks

        dialogues = []
        for k, chunk_list in enumerate(chunks):
            t_start = k * chunk_dur
            t_end = (k + 1) * chunk_dur
            if k == total_chunks - 1:
                t_end = effective_dur

            start_str = SubtitleGenerator._format_ass_timestamp_static(t_start)
            end_str = SubtitleGenerator._format_ass_timestamp_static(t_end)

            clean_text = " ".join(chunk_list).upper()
            style_name = "TikTokYellow" if (k % 2 == 0) else "TikTokWhite"

            dialogues.append(f"Dialogue: 0,{start_str},{end_str},{style_name},,0,0,0,,{clean_text}")

        full_content = ass_header + "\n".join(dialogues) + "\n"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        logger.success(f"Dynamic chunked ASS created ({total_chunks} chunks): {out_path}")
        return str(out_path)


    def generate_tiktok_ass(
        self,
        script: dict,
        scene_durations: list,
        output_path: str,
        format: str = 'shorts'
    ) -> str:
        """
        Sinh phụ đề kiểu TikTok / Shorts chuẩn 100% chính tả tiếng Việt từ kịch bản gốc.
        Chia nhịp hiển thị từng cụm từ (3-5 từ) đồng bộ theo thời lượng audio thực tế của từng cảnh.
        """
        logger.info(f"Tạo phụ đề TikTok ASS từ kịch bản gốc tiếng Việt -> {output_path}")
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        is_shorts = (format == 'shorts')
        res_x = 1080 if is_shorts else 1920
        res_y = 1920 if is_shorts else 1080
        font_size = 46 if is_shorts else 38
        margin_v = 280 if is_shorts else 110  # Đặt tại 1/3 dưới màn hình, không che hình giữa

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokYellow,Arial,{font_size},&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,2,30,30,{margin_v},1
Style: TikTokWhite,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,2,30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogues = []
        scenes = script.get("scenes", [])
        current_time = 0.0

        for i, scene in enumerate(scenes):
            duration = scene_durations[i] if i < len(scene_durations) else float(scene.get("duration", 5.0))
            narration = scene.get("narration", "").strip()
            if not narration:
                current_time += duration
                continue

            # Chia câu văn thành các cụm từ súc tích (3-4 từ mỗi cụm)
            words = narration.split()
            if not words:
                current_time += duration
                continue

            chunk_size = 4
            chunks = []
            for c_i in range(0, len(words), chunk_size):
                chunk_words = words[c_i:c_i + chunk_size]
                chunks.append(" ".join(chunk_words))

            # Phân bổ thời lượng đều theo số cụm từ trong cảnh
            total_chunks = len(chunks)
            chunk_duration = duration / total_chunks

            for k, chunk_text in enumerate(chunks):
                t_start = current_time + (k * chunk_duration)
                t_end = current_time + ((k + 1) * chunk_duration)
                
                # Tránh dính sát mốc cuối
                if k == total_chunks - 1:
                    t_end = min(t_end, current_time + duration - 0.05)

                start_str = self.format_ass_timestamp(t_start)
                end_str = self.format_ass_timestamp(t_end)
                
                # Định dạng chữ nổi bật phong cách TikTok (chữ hoa đậm, viền đen dày)
                clean_text = chunk_text.upper()
                # Xen kẽ màu vàng và màu trắng để tạo nhịp điệu sinh động
                style_name = "TikTokYellow" if (k % 2 == 0) else "TikTokWhite"

                dialogues.append(f"Dialogue: 0,{start_str},{end_str},{style_name},,0,0,0,,{clean_text}")

            current_time += duration

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(dialogues) + "\n")

        logger.success(f"✅ Đã tạo file phụ đề TikTok ASS chuẩn 100% tiếng Việt: {out_path}")
        return str(out_path)

    # ------------------------------------------------------------------
    # Stage 6 Step 5 — word-level karaoke theo nhịp giọng đọc thật
    # ------------------------------------------------------------------
    def transcribe_words(
        self,
        audio_path: str,
        language: str = "vi",
    ) -> List[Dict[str, Any]]:
        """
        Transcribe 1 file audio, trả về list [{word, start, end}] (giây).
        Trả [] khi model lỗi/thiếu hoặc không có từ nào — caller fallback.
        """
        if not self.model or not audio_path or not os.path.exists(audio_path):
            return []
        try:
            segments, _info = self.model.transcribe(
                audio_path, language=language, word_timestamps=True
            )
            words: List[Dict[str, Any]] = []
            for seg in segments or []:
                for w in getattr(seg, "words", None) or []:
                    txt = str(getattr(w, "word", "") or "").strip()
                    if not txt:
                        continue
                    words.append({
                        "word": txt,
                        "start": float(getattr(w, "start", 0.0) or 0.0),
                        "end": float(getattr(w, "end", 0.0) or 0.0),
                    })
            return [w for w in words if w["end"] > w["start"]]
        except Exception as e:
            logger.warning(f"transcribe_words lỗi ({e}), fallback chia đều.")
            return []

    @staticmethod
    def _map_script_words_to_timings(
        script_words: List[str],
        heard: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Gán timing của Whisper cho từng từ kịch bản (giữ chính tả kịch bản).
        Khớp 1:1 khi số từ bằng nhau; ngược lại nội suy theo tỉ lệ.
        """
        n, m = len(script_words), len(heard)
        if n == 0:
            return []
        if m == 0:
            return [{"word": w, "start": -1.0, "end": -1.0} for w in script_words]
        out = []
        for i, w in enumerate(script_words):
            j = i if n == m else round(i * (m - 1) / max(1, n - 1))
            h = heard[min(j, m - 1)]
            out.append({"word": w, "start": h["start"], "end": h["end"]})
        return out

    def generate_wordkaraoke_ass(
        self,
        script: dict,
        scene_audios: list,
        scene_durations: list,
        output_path: str,
        format: str = "shorts",
        language: str = "vi",
        scene_start_times: Optional[list] = None,
    ) -> str:
        """
        Phụ đề karaoke từng từ theo nhịp giọng đọc thật (Whisper word_timestamps).

        - Timing lấy từ audio TTS thật của từng scene; chữ hiển thị lấy từ
          narration trong kịch bản (giữ chính tả 100%).
        - scene_start_times: mốc bắt đầu mỗi scene trên timeline cuối (đã gồm
          wipe chuyển cảnh). Không truyền thì dùng cộng dồn scene_durations.
        - Scene nào không transcribe được -> fallback chia đều như generate_tiktok_ass.
        """
        logger.info(f"Tạo phụ đề karaoke word-level -> {output_path}")
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        is_shorts = (format == "shorts")
        res_x = 1080 if is_shorts else 1920
        res_y = 1920 if is_shorts else 1080
        font_size = 46 if is_shorts else 38
        margin_v = 280 if is_shorts else 110

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokKaraoke,Arial,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,2,30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogues = []
        scenes = script.get("scenes", [])
        current_time = 0.0

        for i, scene in enumerate(scenes):
            duration = scene_durations[i] if i < len(scene_durations) else float(scene.get("duration", 5.0))
            base = float(scene_start_times[i]) if scene_start_times and i < len(scene_start_times) else current_time
            narration = scene.get("narration", "").strip()
            if not narration:
                current_time = base + duration
                continue
            script_words = narration.split()

            audio = scene_audios[i] if i < len(scene_audios) else ""
            heard = self.transcribe_words(audio, language=language) if audio else []
            timed = self._map_script_words_to_timings(script_words, heard)
            has_timing = any(w["start"] >= 0 for w in timed)

            # Gom 4 từ/chunk như generate_tiktok_ass để nhịp hiển thị quen thuộc.
            chunk_size = 4
            for c_i in range(0, len(timed), chunk_size):
                chunk = timed[c_i:c_i + chunk_size]
                if has_timing:
                    t_start = base + max(0.0, chunk[0]["start"])
                    # Từ cuối chunk: cộng thêm 60% khoảng nghỉ tới từ tiếp theo (tối đa +0.6s)
                    if c_i + chunk_size < len(timed):
                        gap = max(0.0, timed[c_i + chunk_size]["start"] - chunk[-1]["end"])
                        t_end = base + chunk[-1]["end"] + min(0.6, gap * 0.6)
                    else:
                        t_end = base + chunk[-1]["end"] + 0.25
                    t_end = min(t_end, base + duration - 0.02)
                    parts = []
                    for w in chunk:
                        cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                        parts.append(f"{{\\k{cs}}}{w['word']}")
                    text = " ".join(parts)
                else:
                    # Fallback: chia đều thời lượng scene.
                    total_chunks = (len(timed) + chunk_size - 1) // chunk_size
                    k = c_i // chunk_size
                    chunk_dur = duration / max(1, total_chunks)
                    t_start = base + k * chunk_dur
                    t_end = base + (k + 1) * chunk_dur
                    if k == total_chunks - 1:
                        t_end = min(t_end, base + duration - 0.05)
                    text = " ".join(w["word"] for w in chunk).upper()
                dialogues.append(
                    f"Dialogue: 0,{self.format_ass_timestamp(t_start)},"
                    f"{self.format_ass_timestamp(t_end)},TikTokKaraoke,,0,0,0,,{text}"
                )
            current_time = base + duration

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(dialogues) + "\n")
        logger.success(f"✅ Đã tạo phụ đề karaoke word-level: {out_path}")
        return str(out_path)

    # Style configuration map for Pillow fallback overlay
    STYLE_CONFIG = {
        "TikTokYellow": {
            "fill": (255, 255, 0, 255),
            "stroke_fill": (0, 0, 0, 255),
            "font_size": 44,
            "stroke_width": 4,
            "margin_v": 180
        },
        "TikTokWhite": {
            "fill": (255, 255, 255, 255),
            "stroke_fill": (0, 0, 0, 255),
            "font_size": 44,
            "stroke_width": 4,
            "margin_v": 180
        },
        "Default": {
            "fill": (255, 255, 255, 255),
            "stroke_fill": (0, 0, 0, 255),
            "font_size": 40,
            "stroke_width": 3,
            "margin_v": 180
        }
    }

    @staticmethod
    def _parse_ass_timestamp(ts: str) -> float:
        """Parse ASS timestamp (H:MM:SS.cs) into seconds float."""
        try:
            parts = ts.strip().split(":")
            if len(parts) == 3:
                h = float(parts[0])
                m = float(parts[1])
                s = float(parts[2])
                return h * 3600.0 + m * 60.0 + s
        except Exception:
            pass
        return 0.0

    @staticmethod
    def parse_ass_dialogues(ass_path: Union[str, Path]) -> List[dict]:
        """Parse dialogue events from an ASS file into structured dicts."""
        dialogues = []
        path = Path(ass_path)
        if not path.exists():
            return dialogues

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Dialogue:"):
                    # Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                    payload = line[len("Dialogue:"):].strip()
                    parts = payload.split(",", 9)
                    if len(parts) >= 10:
                        start_sec = SubtitleGenerator._parse_ass_timestamp(parts[1])
                        end_sec = SubtitleGenerator._parse_ass_timestamp(parts[2])
                        style = parts[3].strip()
                        try:
                            margin_v = int(parts[7].strip())
                        except ValueError:
                            margin_v = 180
                        text = parts[9].strip()
                        dialogues.append({
                            "start": start_sec,
                            "end": end_sec,
                            "style": style,
                            "margin_v": margin_v,
                            "text": text
                        })
        return dialogues

    def burn_subtitles_pillow_fallback(
        self,
        video_path: Union[str, Path],
        sub_path: Union[str, Path],
        output_path: Union[str, Path],
        audio_path: Optional[Union[str, Path]] = None,
        fps: Optional[float] = None
    ) -> str:
        """
        Frame-by-frame Pillow subtitle burning fallback when FFmpeg libass is unavailable.
        Extracts frames, renders ASS text with exact safe-zone typography, and re-encodes.
        """
        logger.info(f"Executing Pillow subtitle overlay fallback: {sub_path} -> {video_path}")
        vid_p = Path(video_path).resolve()
        sub_p = Path(sub_path).resolve()
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        dialogues = self.parse_ass_dialogues(sub_p)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            frames_pattern = str(temp_dir_path / "frame_%05d.png")

            # 1. Extract frames from input video
            extract_cmd = ["ffmpeg", "-y", "-i", str(vid_p), frames_pattern]
            subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)

            frame_files = sorted(temp_dir_path.glob("frame_*.png"))
            if not frame_files:
                raise RuntimeError(f"No frames extracted from {vid_p} for subtitle burning.")

            if not fps or fps <= 0:
                info = get_video_info(str(vid_p))
                fps = float(info.get("fps", 12.0))
                if fps <= 0:
                    fps = 12.0

            # 2. Overlay subtitles onto frames
            for i, f_file in enumerate(frame_files):
                t = i / fps
                active = [d for d in dialogues if d["start"] <= t < d["end"]]
                if not active:
                    continue

                diag = active[0]
                with Image.open(f_file) as base_img:
                    img = base_img.convert("RGBA")
                    draw = ImageDraw.Draw(img)
                    cfg = self.STYLE_CONFIG.get(diag["style"], self.STYLE_CONFIG["Default"])
                    margin_v = diag.get("margin_v") or cfg["margin_v"]
                    font_size = cfg["font_size"]

                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()

                    text = diag["text"]
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    x_pos = (img.width - text_w) // 2
                    y_pos = img.height - margin_v - text_h

                    draw.text(
                        (x_pos, y_pos),
                        text,
                        font=font,
                        fill=cfg["fill"],
                        stroke_width=cfg["stroke_width"],
                        stroke_fill=cfg["stroke_fill"]
                    )
                    img.convert("RGB").save(f_file)

            # 3. Assemble video with FFmpeg and mux audio
            input_pattern = str(temp_dir_path / "frame_%05d.png")
            encode_cmd = [
                "ffmpeg", "-y",
                "-r", str(fps),
                "-i", input_pattern
            ]

            if audio_path and Path(audio_path).exists():
                encode_cmd.extend(["-i", str(Path(audio_path).resolve())])
                encode_cmd.extend(["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"])
            else:
                info = get_video_info(str(vid_p))
                if info.get("has_audio"):
                    encode_cmd.extend(["-i", str(vid_p)])
                    encode_cmd.extend(["-map", "0:v", "-map", "1:a", "-c:a", "copy", "-shortest"])

            encode_cmd.extend([
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-preset", "fast",
                str(out_p)
            ])

            subprocess.run(encode_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            logger.success(f"Pillow fallback burned subtitles successfully: {out_p}")
            return str(out_p)

    def burn_subtitles(
        self,
        video_path: Union[str, Path],
        sub_path: Union[str, Path],
        output_path: Union[str, Path],
        audio_path: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Burns subtitles (SRT or ASS) into video using FFmpeg.
        Automatically falls back to engine-level Pillow frame burning if
        FFmpeg lacks libass or fails to process filter.
        """
        logger.info(f"Burning subtitles {sub_path} into {video_path}")
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        vid_p = Path(video_path).resolve()
        sub_p = Path(sub_path).resolve()

        # Step 1: Attempt native FFmpeg burning with sanitized ASCII temp path
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy ASS/SRT to a safe ASCII path in temp directory to prevent Windows UTF-8 fopen failure
                safe_sub = Path(temp_dir) / f"sub_{sub_p.name}"
                shutil.copy2(sub_p, safe_sub)
                
                sub_posix = safe_sub.as_posix().replace(':', r'\:')
                if str(sub_p).endswith('.ass'):
                    vf_filter = f"ass='{sub_posix}'"
                else:
                    vf_filter = f"subtitles='{sub_posix}':force_style='FontSize=16,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=30'"

                cmd = ["ffmpeg", "-y", "-i", str(vid_p)]
                if audio_path and Path(audio_path).exists():
                    cmd.extend(["-i", str(Path(audio_path).resolve())])
                    cmd.extend(["-filter_complex", f"[0:v]{vf_filter}[v]", "-map", "[v]", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"])
                else:
                    cmd.extend(["-vf", vf_filter, "-c:a", "copy"])

                cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out_path)])
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                
                if res.returncode == 0 and out_path.exists():
                    logger.success(f"FFmpeg native subtitle burning succeeded: {out_path}")
                    return str(out_path)
                else:
                    err_msg = res.stderr.decode('utf-8', errors='replace') if res.stderr else "Unknown error"
                    logger.warning(f"Native FFmpeg subtitle burning failed (code {res.returncode}): {err_msg.strip()[:200]}")
        except Exception as e:
            logger.warning(f"Native FFmpeg subtitle burning exception: {e}")

        # Step 2: Fallback to engine-level Pillow frame burning
        logger.info("Engaging SubtitleGenerator Pillow frame-by-frame burning fallback...")
        return self.burn_subtitles_pillow_fallback(
            video_path=vid_p,
            sub_path=sub_p,
            output_path=out_path,
            audio_path=audio_path
        )
