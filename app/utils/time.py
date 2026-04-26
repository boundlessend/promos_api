from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings

MOSCOW_TZ = ZoneInfo(get_settings().moscow_timezone)


def now_msk() -> datetime:
    """возвращает текущее время в москве"""

    return datetime.now(MOSCOW_TZ)


def ensure_moscow_tz(value: datetime | None) -> datetime | None:
    """приводит дату ко времени москвы"""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=MOSCOW_TZ)
    return value.astimezone(MOSCOW_TZ)


def is_started(
    starts_at: datetime | None, current_time: datetime | None = None
) -> bool:
    """проверяет что окно уже началось"""

    current_time = current_time or now_msk()
    if starts_at is None:
        return True
    return ensure_moscow_tz(starts_at) <= current_time


def is_not_expired(
    expires_at: datetime | None, current_time: datetime | None = None
) -> bool:
    """проверяет что окно еще не истекло"""

    current_time = current_time or now_msk()
    if expires_at is None:
        return True
    return ensure_moscow_tz(expires_at) >= current_time
