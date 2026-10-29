"""时区解析：优先 zoneinfo（IANA 全表），退化到内置固定偏移表。

为什么需要这个：Windows 版 Python 不带 tzdata，ZoneInfo("Asia/Shanghai")
在干净 Windows 上必然抛 ZoneInfoNotFoundError。Ubuntu 上全绿、客户 Windows 上一跑
就全红，是最典型的“只在一边验证过”事故，所以这里显式降级并告知用户。
"""
from __future__ import annotations
from datetime import timedelta, timezone

try:
    from zoneinfo import ZoneInfo as _ZI
except Exception:
    _ZI = None

FALLBACK_OFFSETS = {
    "UTC": 0, "Asia/Shanghai": 8, "Asia/Hong_Kong": 8, "Asia/Singapore": 8,
    "Asia/Taipei": 8, "Asia/Tokyo": 9, "Asia/Seoul": 9, "Asia/Kolkata": 5.5,
    "Asia/Dubai": 4, "Europe/London": 0, "Europe/Berlin": 1, "Europe/Paris": 1,
    "Europe/Moscow": 3, "America/New_York": -5, "America/Chicago": -6,
    "America/Denver": -7, "America/Los_Angeles": -8, "America/Sao_Paulo": -3,
    "Australia/Sydney": 10, "Pacific/Auckland": 12,
}

STATE = {"degraded": False, "reason": ""}


def resolve(name):
    """返回 tzinfo；未知则抛 KeyError。降级时把 STATE 标 dirty，供 CLI 提示用户。"""
    if isinstance(name, str) and _ZI is not None:
        try:
            return _ZI(name)
        except Exception:
            pass
    if name in FALLBACK_OFFSETS:
        if not STATE["degraded"]:
            STATE["degraded"] = True
            STATE["reason"] = ("本机缺少 IANA 时区库(tzdata)，已用固定偏移；"
                               "含夏令时的时区会偏 1 小时，建议 pip install tzdata")
        return timezone(timedelta(hours=FALLBACK_OFFSETS[name]), str(name))
    raise KeyError(name)


def known(name):
    if not isinstance(name, str) or not name:
        return False
    try:
        resolve(name)
        return True
    except KeyError:
        return False
