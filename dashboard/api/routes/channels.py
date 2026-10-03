from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter()

# dashboard/api/routes/channels.py -> repository root is three parents up.
CHANNELS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "channels.yaml"

_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def load_channels_config() -> Dict[str, Dict[str, Any]]:
    """Load the style-keyed channel mapping from config/channels.yaml."""
    if not CHANNELS_CONFIG_PATH.exists():
        logger.warning(f"Channels config not found: {CHANNELS_CONFIG_PATH}")
        return {}
    with open(CHANNELS_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    channels = data.get("channels", {}) if isinstance(data, dict) else {}
    return channels if isinstance(channels, dict) else {}


def load_channels():
    """Backward-compatible payload used by the channels API."""
    return {"channels": load_channels_config()}


def get_channel_config(channel_id: str) -> Optional[Dict[str, Any]]:
    """Return one channel by config key or by its declared style."""
    channels = load_channels_config()
    if channel_id in channels:
        return {"id": channel_id, **channels[channel_id]}
    for key, channel in channels.items():
        if isinstance(channel, dict) and channel.get("style") == channel_id:
            return {"id": key, **channel}
    return None


def get_schedule_for_style(style: str) -> Dict[str, Any]:
    """Return the posting schedule configured for a video style/channel."""
    channel = get_channel_config(style or "")
    if not channel:
        return {}
    schedule = channel.get("schedule", {})
    return schedule if isinstance(schedule, dict) else {}


def get_schedule_timezone(schedule: Dict[str, Any]):
    """Resolve a schedule timezone, with a stable Vietnam fallback."""
    tz_name = str((schedule or {}).get("timezone") or "Asia/Ho_Chi_Minh")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        if tz_name == "Asia/Ho_Chi_Minh":
            return timezone(timedelta(hours=7), name=tz_name)
        return timezone.utc


def _parse_posting_time(value: Any) -> Optional[time]:
    if isinstance(value, time):
        return value
    text = str(value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _coerce_datetime(value: Any, tz) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def compute_next_publish_slot(
    schedule: Dict[str, Any],
    reserved_slots: Optional[Iterable[Any]] = None,
    now: Optional[datetime] = None,
) -> datetime:
    """
    Compute the next available posting slot.

    A day can receive at most ``max_per_day`` reservations. Candidate times
    come from ``posting_times`` in the channel timezone; days not listed in
    ``days`` are skipped. This pure helper is deliberately clock-injectable
    for tests.
    """
    schedule = schedule or {}
    tz = get_schedule_timezone(schedule)
    local_now = _coerce_datetime(now or datetime.now(tz), tz) or datetime.now(tz)

    if not schedule.get("enabled", True):
        return local_now

    posting_times = sorted(
        filter(None, (_parse_posting_time(v) for v in schedule.get("posting_times", [])))
    )
    if not posting_times:
        return local_now

    try:
        max_per_day = int(schedule.get("max_per_day", len(posting_times)))
    except (TypeError, ValueError):
        max_per_day = len(posting_times)
    if max_per_day <= 0:
        return local_now

    reservations: Dict[Any, int] = {}
    occupied_slots = set()
    for value in reserved_slots or []:
        reserved_at = _coerce_datetime(value, tz)
        if reserved_at:
            day = reserved_at.date()
            reservations[day] = reservations.get(day, 0) + 1
            occupied_slots.add(reserved_at)

    allowed_days = schedule.get("days")
    allowed_weekdays = None
    if allowed_days:
        allowed_weekdays = {
            _WEEKDAY_NAMES.index(str(day)[:3].title())
            for day in allowed_days
            if str(day)[:3].title() in _WEEKDAY_NAMES
        }

    for offset in range(0, 370):
        candidate_date = local_now.date() + timedelta(days=offset)
        if allowed_weekdays is not None and candidate_date.weekday() not in allowed_weekdays:
            continue
        if reservations.get(candidate_date, 0) >= max_per_day:
            continue
        for posting_time in posting_times:
            candidate = datetime.combine(candidate_date, posting_time, tzinfo=tz)
            if candidate >= local_now and candidate not in occupied_slots:
                return candidate

    # Defensive fallback; practically unreachable with at least one time.
    return local_now


@router.get("")
def list_channels():
    channels = load_channels_config()
    return {
        "channels": [
            {"id": channel_id, **channel}
            for channel_id, channel in channels.items()
            if isinstance(channel, dict)
        ]
    }


@router.get("/{channel_id}")
def get_channel(channel_id: str):
    channel = get_channel_config(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.get("/{channel_id}/schedule")
def get_channel_schedule(channel_id: str):
    channel = get_channel(channel_id)
    return {"schedule": channel.get("schedule", {})}
