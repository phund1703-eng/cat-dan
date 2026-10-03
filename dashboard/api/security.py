"""
dashboard/api/security.py — An toàn API tối thiểu (Task 5.4).

Cơ chế X-API-Key cho các endpoint GHI (POST/PUT/PATCH/DELETE):

- Key lấy từ biến môi trường `SECRET_KEY` trong .env.
- Chưa đặt SECRET_KEY (hoặc vẫn để nguyên giá trị mẫu trong .env.example):
  API chạy KHÔNG khoá như môi trường dev localhost, nhưng log cảnh báo rõ
  một lần khi khởi động/khi có request ghi đầu tiên — tránh việc người dùng
  tự khoá mình ngoài ý muốn trên máy dev.
- Đã đặt SECRET_KEY thật: request ghi thiếu header `X-API-Key` hoặc sai
  key → 401. Request đọc (GET/HEAD/OPTIONS) luôn mở để Dashboard xem
  dữ liệu bình thường.
"""

from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

API_KEY_HEADER = "X-API-Key"

#: Giá trị mẫu trong .env.example — coi như CHƯA đặt key (không khoá API).
_PLACEHOLDER_KEYS = {
    "",
    "change_this_to_random_secret_key_for_production",
}

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_warned_no_key = False


def configured_api_key() -> str | None:
    """SECRET_KEY hiệu lực; None nếu chưa đặt/đang là giá trị mẫu."""
    value = os.getenv("SECRET_KEY", "").strip()
    if value in _PLACEHOLDER_KEYS:
        return None
    return value


def is_auth_enabled() -> bool:
    return configured_api_key() is not None


def _warn_once_not_locked() -> None:
    global _warned_no_key
    if not _warned_no_key:
        _warned_no_key = True
        logger.warning(
            "⚠️ [API Security] SECRET_KEY chưa được đặt trong .env — các endpoint "
            "GHI (tạo/xoá job, publish, upload...) đang KHÔNG khoá. Chỉ phù hợp "
            "khi chạy localhost lúc dev; hãy đặt SECRET_KEY ngẫu nhiên mạnh "
            "trong .env trước khi mở API ra mạng."
        )


def check_write_request(request: Request) -> None:
    """
    Kiểm tra quyền cho 1 request ghi. Ném HTTPException 401 khi đã đặt
    SECRET_KEY mà header X-API-Key thiếu/sai.
    """
    api_key = configured_api_key()
    if api_key is None:
        _warn_once_not_locked()
        return
    provided = request.headers.get(API_KEY_HEADER, "")
    if not provided or not hmac.compare_digest(provided, api_key):
        raise HTTPException(
            status_code=401,
            detail=f"Thiếu hoặc sai header {API_KEY_HEADER}",
        )


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Khoá mọi request ghi (POST/PUT/PATCH/DELETE) bằng X-API-Key."""

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() in _WRITE_METHODS:
            try:
                check_write_request(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code, content={"detail": exc.detail}
                )
        return await call_next(request)


__all__ = [
    "API_KEY_HEADER",
    "ApiKeyMiddleware",
    "configured_api_key",
    "is_auth_enabled",
    "check_write_request",
]
