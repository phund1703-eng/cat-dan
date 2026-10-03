"""
Source Gate (Task 2.2) — lớp kiểm chứng nguồn trích dẫn bắt buộc.

Nguyên tắc (kế hoạch Giai đoạn 2):
- Mọi cảnh chứa con số / năm / tỉ lệ / đơn vị đo (khẳng định định lượng) phải có
  ít nhất một nguồn `sources` mở được. Thiếu nguồn -> status `needs_source` và
  job Auto bị chặn ở stage `source_review` trước khi sinh giọng đọc.
- URL có sẵn sẽ được tải thử (timeout 10s, cache `data/cache/sources/`) và trích
  đoạn text liên quan lưu kèm để đối chiếu. HTTP 200/301/302/403 (bot-block)
  được coi là mở được -> `verified`; còn lại -> `unreachable`.

Module này thuần logic + một lớp fetch có thể thay thế (fetcher) để test không
phụ thuộc mạng thật.
"""

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from loguru import logger

CACHE_DIR = Path("data/cache/sources")
FETCH_TIMEOUT_SECONDS = 10
CACHE_TTL_SECONDS = 7 * 24 * 3600

STATUS_VERIFIED = "verified"
STATUS_NEEDS_SOURCE = "needs_source"
STATUS_UNREACHABLE = "unreachable"

# ---------------------------------------------------------------------------
# Phát hiện khẳng định định lượng (con số / năm / tỉ lệ / đơn vị đo)
# ---------------------------------------------------------------------------
_DIGIT_RE = re.compile(r"\d")
_MEASURE_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(km/h|m/s|km|cm|mm|kg|mg|ml|°c|°f|nm|µm|hz|khz|mhz|kw|mph)\b",
    re.IGNORECASE,
)
_NUMBER_WORDS_RE = re.compile(
    r"(phần trăm|phần nghìn|triệu|tỷ|tỉ|nghìn|ngàn|percent|million|billion|trillion|thousand)",
    re.IGNORECASE,
)


def contains_numeric_claim(text: str) -> bool:
    """True khi text chứa con số, năm, tỉ lệ hoặc đơn vị đo định lượng."""
    if not text:
        return False
    return bool(
        _DIGIT_RE.search(text)
        or _MEASURE_RE.search(text)
        or _NUMBER_WORDS_RE.search(text)
    )


# ---------------------------------------------------------------------------
# Kiểm tra định dạng URL nguồn
# ---------------------------------------------------------------------------
def validate_source_url(url: Any) -> Tuple[bool, str]:
    """(ok, reason). Chỉ chấp nhận http/https với domain thật, không phải địa chỉ nội bộ."""
    if not isinstance(url, str) or not url.strip():
        return False, "URL trống"
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return False, "URL phải bắt đầu bằng http:// hoặc https://"
    host = (parsed.hostname or "").lower()
    if not host or "." not in host:
        return False, "URL không có domain hợp lệ"
    if host == "localhost" or host.startswith(("127.", "10.", "192.168.", "172.16.", "::1")):
        return False, "Địa chỉ nội bộ không phải nguồn trích dẫn công khai"
    return True, ""


# ---------------------------------------------------------------------------
# Tải URL + trích đoạn liên quan (có cache)
# ---------------------------------------------------------------------------
def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&(nbsp|amp|lt|gt|quot|#39);", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _make_excerpt(text: str, fact: str, max_chars: int = 400) -> str:
    """Cắt đoạn text quanh từ khóa của fact để đối chiếu nội dung nguồn."""
    if not text:
        return ""
    keywords = [w.strip(".,;:!?()\"'").lower() for w in re.split(r"\s+", fact or "") if len(w) > 3]
    lowered = text.lower()
    for kw in keywords:
        pos = lowered.find(kw)
        if pos >= 0:
            start = max(0, pos - 120)
            end = min(len(text), pos + max_chars - 120)
            return ("..." if start > 0 else "") + text[start:end].strip()
    return text[:max_chars].strip()


def _default_fetcher(url: str) -> Dict[str, Any]:
    """Fetcher mặc định bằng urllib. Trả {reachable, http_status, text, error}."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CatDanSourceGate/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_SECONDS) as resp:
            status = int(resp.getcode() or 0)
            body = resp.read(300_000)
    except urllib.error.HTTPError as e:
        status = int(e.code or 0)
        try:
            body = e.read(100_000)
        except Exception:
            body = b""
    except Exception as e:  # DNS, timeout, SSL...
        return {"reachable": False, "http_status": None, "text": "", "error": str(e)}

    reachable = status in (200, 301, 302, 403)
    return {
        "reachable": reachable,
        "http_status": status,
        "text": _strip_html(body.decode("utf-8", errors="replace"))[:8000],
        "error": "" if reachable else f"HTTP {status}",
    }


def _cache_path(cache_dir: Path, url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    return cache_dir / f"{digest}.json"


def fetch_source(
    url: str,
    fact: str = "",
    fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
    use_cache: bool = True,
    cache_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Tải (hoặc đọc cache) một URL nguồn.
    Trả {url, reachable, http_status, excerpt, error, from_cache}.
    """
    cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
    cache_file = _cache_path(cache_dir, url)

    if use_cache and cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - float(cached.get("fetched_at", 0)) < CACHE_TTL_SECONDS:
                return {
                    "url": url,
                    "reachable": bool(cached.get("reachable")),
                    "http_status": cached.get("http_status"),
                    "excerpt": _make_excerpt(cached.get("text", ""), fact),
                    "error": cached.get("error", ""),
                    "from_cache": True,
                }
        except Exception as e_cache:
            logger.debug(f"Source cache unreadable ({e_cache}), refetching {url}")

    result = (fetcher or _default_fetcher)(url)
    out = {
        "url": url,
        "reachable": bool(result.get("reachable")),
        "http_status": result.get("http_status"),
        "excerpt": _make_excerpt(result.get("text", ""), fact),
        "error": result.get("error", ""),
        "from_cache": False,
    }

    if use_cache:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps(
                    {
                        "url": url,
                        "fetched_at": time.time(),
                        "reachable": out["reachable"],
                        "http_status": out["http_status"],
                        "error": out["error"],
                        "text": result.get("text", "")[:8000],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as e_cache:
            logger.debug(f"Could not write source cache ({e_cache})")

    return out


# ---------------------------------------------------------------------------
# Audit toàn bộ scene
# ---------------------------------------------------------------------------
def audit_scene(
    scene: Dict[str, Any],
    scene_index: int,
    fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
    use_cache: bool = True,
    cache_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Kiểm chứng một scene, trả entry audit {scene_index, status, url, ...}."""
    claim_text = " ".join(
        str(scene.get(k) or "") for k in ("narration", "fact")
    ).strip()
    sources = [
        s for s in (scene.get("sources") or [])
        if isinstance(s, dict) and str(s.get("url") or "").strip()
    ]

    entry: Dict[str, Any] = {
        "scene_index": scene_index,
        "status": STATUS_VERIFIED,
        "url": "",
        "title": "",
        "fact": str(scene.get("fact") or ""),
        "detail": "",
        "excerpt": "",
    }

    if not sources:
        if contains_numeric_claim(claim_text):
            entry["status"] = STATUS_NEEDS_SOURCE
            entry["detail"] = "Cảnh có số liệu/năm/đơn vị đo nhưng chưa có nguồn trích dẫn."
        else:
            entry["detail"] = "Cảnh định tính, không chứa số liệu nên không bắt buộc nguồn."
        return entry

    errors: List[str] = []
    for src in sources:
        url = str(src.get("url") or "").strip()
        ok, reason = validate_source_url(url)
        if not ok:
            errors.append(f"{url}: {reason}")
            continue
        fetched = fetch_source(
            url,
            fact=str(scene.get("fact") or ""),
            fetcher=fetcher,
            use_cache=use_cache,
            cache_dir=cache_dir,
        )
        if fetched["reachable"]:
            entry["status"] = STATUS_VERIFIED
            entry["url"] = url
            entry["title"] = str(src.get("title") or "")
            entry["excerpt"] = fetched.get("excerpt", "")
            entry["detail"] = f"Nguồn mở được (HTTP {fetched.get('http_status')})."
            return entry
        errors.append(f"{url}: {fetched.get('error') or 'không mở được'}")

    entry["status"] = STATUS_UNREACHABLE
    entry["url"] = str(sources[0].get("url") or "").strip()
    entry["title"] = str(sources[0].get("title") or "")
    entry["detail"] = "Không nguồn nào mở được: " + "; ".join(errors)
    return entry


def audit_scenes(
    scenes: List[Dict[str, Any]],
    fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
    use_cache: bool = True,
    cache_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Audit toàn bộ danh sách scene theo thứ tự."""
    audit: List[Dict[str, Any]] = []
    for i, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        idx = scene.get("scene_index", scene.get("index", i))
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = i
        audit.append(
            audit_scene(scene, idx, fetcher=fetcher, use_cache=use_cache, cache_dir=cache_dir)
        )
    return audit


def evaluate_gate(
    scenes: List[Dict[str, Any]],
    fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
    use_cache: bool = True,
    cache_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Chạy Source Gate cho job.
    Trả {audit, blocking, has_blocking}; blocking = scene_index các cảnh needs_source.
    """
    audit = audit_scenes(scenes, fetcher=fetcher, use_cache=use_cache, cache_dir=cache_dir)
    blocking = [a["scene_index"] for a in audit if a["status"] == STATUS_NEEDS_SOURCE]
    if blocking:
        logger.warning(f"Source Gate: {len(blocking)} scene(s) missing sources: {blocking}")
    return {"audit": audit, "blocking": blocking, "has_blocking": bool(blocking)}
