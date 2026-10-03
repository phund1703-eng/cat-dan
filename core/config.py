"""
core/config.py — Nguồn cấu hình hành vi DUY NHẤT của AutoVideoFactory.

Quy ước (Giai đoạn 5.2):
- `config/settings.yaml` chứa mọi cấu hình *hành vi*: model Gemini, TTS ưu
  tiên, chất lượng video, nhạc nền, `queue.max_concurrent_jobs`...
- `.env` chỉ chứa *bí mật* (API key, SECRET_KEY) — cộng 2 biến override tuỳ
  chọn `GEMINI_MODEL` / `GEMINI_PRO_MODEL` (ghi rõ là override, xem .env.example).

Mọi module cần cấu hình hành vi hãy đọc qua `get_settings()` /
`get_setting()` / `get_gemini_model()` ở đây, không tự mở settings.yaml
hay tự đặt default model rải rác nữa.

Đường dẫn file settings có thể đổi bằng biến môi trường
`CATDAN_SETTINGS_FILE` (dùng cho test). Cache được giữ trong tiến trình;
gọi `clear_settings_cache()` sau khi sửa file settings lúc runtime.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
SETTINGS_PATH_ENV = "CATDAN_SETTINGS_FILE"

#: Fallback cuối cùng khi settings.yaml thiếu llm.model — phải khớp
#: llm.model trong config/settings.yaml (test_gemini_client_empirical kiểm).
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


def settings_path() -> Path:
    """Đường dẫn file settings đang hiệu lực (CATDAN_SETTINGS_FILE ghi đè)."""
    override = os.getenv(SETTINGS_PATH_ENV, "").strip()
    return Path(override) if override else DEFAULT_SETTINGS_PATH


@lru_cache(maxsize=1)
def _load_settings() -> dict:
    path = settings_path()
    try:
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                return data
            logger.warning(f"{path} không phải YAML mapping — dùng cấu hình rỗng")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Không đọc được {path}: {exc} — dùng cấu hình rỗng")
    return {}


def get_settings(reload: bool = False) -> dict:
    """
    Trả toàn bộ cấu hình hành vi từ config/settings.yaml (có cache).

    Dict trả về là bản cache dùng chung — module gọi chỉ nên ĐỌC,
    không sửa trực tiếp. `reload=True` ép đọc lại file.
    """
    if reload:
        clear_settings_cache()
    return _load_settings()


def clear_settings_cache() -> None:
    """Xoá cache settings (dùng sau khi sửa file hoặc trong test)."""
    _load_settings.cache_clear()


def get_setting(dotted_path: str, default: Any = None) -> Any:
    """Đọc 1 giá trị theo đường dẫn chấm, vd get_setting("llm.model")."""
    node: Any = get_settings()
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def get_gemini_model(pro: bool = False) -> str:
    """
    Tên model Gemini thống nhất một chỗ cho toàn hệ thống.

    Thứ tự ưu tiên: biến môi trường `GEMINI_MODEL` / `GEMINI_PRO_MODEL`
    (override trong .env, chỉ khi thật sự cần) → `llm.model` /
    `llm.pro_model` trong config/settings.yaml → DEFAULT_GEMINI_MODEL.
    """
    env_name = "GEMINI_PRO_MODEL" if pro else "GEMINI_MODEL"
    env_value = os.getenv(env_name, "").strip()
    if env_value:
        return env_value
    yaml_key = "llm.pro_model" if pro else "llm.model"
    value = get_setting(yaml_key, DEFAULT_GEMINI_MODEL)
    return str(value).strip() if value else DEFAULT_GEMINI_MODEL


def get_queue_max_concurrent_jobs() -> int:
    """Số job chạy đồng thời tối đa (queue.max_concurrent_jobs, mặc định 2)."""
    try:
        return max(1, int(get_setting("queue.max_concurrent_jobs", 2)))
    except (TypeError, ValueError):
        logger.warning("queue.max_concurrent_jobs không hợp lệ — dùng mặc định 2")
        return 2


__all__ = [
    "PROJECT_ROOT",
    "DEFAULT_SETTINGS_PATH",
    "SETTINGS_PATH_ENV",
    "DEFAULT_GEMINI_MODEL",
    "settings_path",
    "get_settings",
    "clear_settings_cache",
    "get_setting",
    "get_gemini_model",
    "get_queue_max_concurrent_jobs",
]
