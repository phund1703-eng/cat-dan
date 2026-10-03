"""
dashboard/api/upload_validation.py — Validate file upload dùng chung (Task 5.4).

Cả hai đường upload (`/jobs/{id}/upload-scene-image` và `/voices/upload`)
đều validate qua helper ở đây thay vì mỗi nơi tự chế:

- Giới hạn dung lượng (đọc theo chunk, vượt giới hạn → 413).
- Kiểm tra định dạng THẬT bằng magic bytes đầu file — không tin đuôi
  file hay Content-Type do client khai. File .exe đổi đuôi .png/.mp3
  sẽ bị chặn (400).
"""

from __future__ import annotations

from fastapi import HTTPException, UploadFile
from loguru import logger

# Giới hạn dung lượng upload
MAX_IMAGE_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB cho 1 ảnh scene
MAX_VOICE_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB cho 1 mẫu giọng

_CHUNK = 1024 * 1024

# Magic bytes của các định dạng được chấp nhận
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def detect_image_format(content: bytes) -> str | None:
    """Nhận diện ảnh từ magic bytes: 'png' | 'jpg' | 'webp' | None."""
    if content.startswith(_PNG_MAGIC):
        return "png"
    if content.startswith(_JPEG_MAGIC):
        return "jpg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


def detect_audio_format(content: bytes) -> str | None:
    """Nhận diện audio từ magic bytes: 'wav' | 'mp3' | None."""
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WAVE":
        return "wav"
    if content.startswith(b"ID3"):
        return "mp3"
    # MPEG audio frame sync: 11 bit đầu đều là 1 (0xFFEx)
    if len(content) >= 2 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0:
        return "mp3"
    return None


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Đọc toàn bộ file upload theo chunk; vượt giới hạn → HTTP 413."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            logger.warning(
                f"Upload '{upload.filename}' vượt giới hạn {max_bytes} bytes"
            )
            raise HTTPException(
                status_code=413,
                detail=f"File quá lớn (tối đa {max_bytes // (1024 * 1024)} MB)",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def validate_image_upload(
    upload: UploadFile, max_bytes: int = MAX_IMAGE_UPLOAD_BYTES
) -> tuple[bytes, str]:
    """
    Đọc + kiểm chứng 1 ảnh upload. Trả `(nội dung, định dạng thật)`.
    Nội dung rỗng hoặc không phải PNG/JPEG/WebP thật → HTTP 400.
    """
    content = await read_upload_limited(upload, max_bytes)
    if not content:
        raise HTTPException(status_code=400, detail="File tải lên rỗng")
    fmt = detect_image_format(content)
    if fmt is None:
        raise HTTPException(
            status_code=400,
            detail="Nội dung file không phải ảnh PNG/JPEG/WebP hợp lệ",
        )
    return content, fmt


async def validate_audio_upload(
    upload: UploadFile, max_bytes: int = MAX_VOICE_UPLOAD_BYTES
) -> tuple[bytes, str]:
    """
    Đọc + kiểm chứng 1 file giọng upload. Trả `(nội dung, định dạng thật)`.
    Nội dung rỗng hoặc không phải WAV/MP3 thật → HTTP 400.
    """
    content = await read_upload_limited(upload, max_bytes)
    if not content:
        raise HTTPException(status_code=400, detail="File tải lên rỗng")
    fmt = detect_audio_format(content)
    if fmt is None:
        raise HTTPException(
            status_code=400,
            detail="Nội dung file không phải audio WAV/MP3 hợp lệ",
        )
    return content, fmt


__all__ = [
    "MAX_IMAGE_UPLOAD_BYTES",
    "MAX_VOICE_UPLOAD_BYTES",
    "detect_image_format",
    "detect_audio_format",
    "read_upload_limited",
    "validate_image_upload",
    "validate_audio_upload",
]
