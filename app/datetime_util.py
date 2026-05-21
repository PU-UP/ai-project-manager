"""北京时间（UTC+8）存储与展示。"""

from datetime import datetime, timedelta, timezone

# 中国不使用夏令时，固定 UTC+8
BEIJING = timezone(timedelta(hours=8))
STORAGE_FMT = "%Y-%m-%d %H:%M:%S"
DISPLAY_FMT = "%Y-%m-%d %H:%M"
DISPLAY_FMT_SEC = "%Y-%m-%d %H:%M:%S"


def now_beijing() -> str:
    """写入数据库：北京时间，如 2026-05-18 17:25:54"""
    return datetime.now(BEIJING).strftime(STORAGE_FMT)


def _parse_timestamp(ts: str) -> datetime | None:
    if not ts or not str(ts).strip():
        return None
    s = str(ts).strip()
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(BEIJING)
        if "+" in s or s.endswith("00:00") and "T" in s:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is not None:
                return dt.astimezone(BEIJING)
        if "T" in s:
            dt = datetime.fromisoformat(s)
            return dt.replace(tzinfo=BEIJING) if dt.tzinfo is None else dt.astimezone(BEIJING)
        if len(s) >= 19:
            return datetime.strptime(s[:19], STORAGE_FMT).replace(tzinfo=BEIJING)
        if len(s) >= 16:
            return datetime.strptime(s[:16], DISPLAY_FMT).replace(tzinfo=BEIJING)
        if len(s) >= 10:
            return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=BEIJING)
    except ValueError:
        return None
    return None


def format_display(ts: str | None, *, with_seconds: bool = False) -> str:
    """展示用：转为北京时间字符串。"""
    dt = _parse_timestamp(ts) if ts else None
    if dt is None:
        return ts or ""
    fmt = DISPLAY_FMT_SEC if with_seconds else DISPLAY_FMT
    return dt.strftime(fmt)
