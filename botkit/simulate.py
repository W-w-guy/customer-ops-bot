"""干跑：用假时钟把一份实例配置跑一遍，验证节奏/静默/上限/升级/退订真的按定义生效。

不连任何真实通道，不发消息；产出的是时间线（可粘贴进验证记录）。
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timedelta
from .render import fill, canon
from .validate import validate
from .schema import defaults

from .tzutil import resolve as _resolve_tz

MAX_STEPS = 20000


def _tz(name):
    return _resolve_tz(name)


def _in_quiet(dt, q):
    start, end = q
    h = dt.hour
    if start < end:
        return start <= h < end
    return h >= start or h < end          # 跨零点


def _next_allowed(dt, q):
    """把时刻推到静默结束；若不在静默内原样返回。"""
    if not _in_quiet(dt, q):
        return dt
    out = dt
    for _ in range(24):
        out = out.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        if not _in_quiet(out, q):
            break
    return out


def simulate(params, events=None, start="2026-01-05T09:00", days=30):
    """events: [{"at": ISO 或 天数int, "type": "reply"|"opt_out"}]，返回时间线字典。"""
    errs = validate(params)
    if errs:
        return {"ok": False, "errors": errs, "timeline": []}
    p = dict(defaults())
    p.update({k: v for k, v in params.items() if v is not None})
    tz = _tz(p["timezone"])
    t = datetime.fromisoformat(start).replace(tzinfo=tz)
    if t.minute or t.second or t.microsecond:      # 对齐整点网格，避免每步取整丢分钟
        t = t + timedelta(hours=1)
    end = t + timedelta(days=days)

    evs = []
    for e in (events or []):
        at = e["at"]
        when = (t + timedelta(days=at)) if isinstance(at, int) else \
            datetime.fromisoformat(at).replace(tzinfo=tz)
        evs.append((when, e["type"]))
    evs.sort(key=lambda x: x[0])

    stages, cad = p["stages"], p["cadence_hours"]
    si = stages.index(p["entry_stage"])
    nxt = t
    last_reply = t
    day_c, week_c = {}, {}
    tl, escalated, stopped = [], None, None
    steps = 0
    while t < end and steps < MAX_STEPS:
        steps += 1
        while evs and evs[0][0] <= t:
            when, kind = evs.pop(0)
            if kind == "opt_out":
                tl.append({"at": when.isoformat(), "stage": stages[si],
                           "action": "stop", "reason": "客户回复 %s" % p["opt_out_keyword"]})
                stopped = "opt_out"
                evs.clear()
                break
            if kind == "reply":
                si = min(si + 1, len(stages) - 1)
                last_reply = when
                nxt = when + timedelta(hours=cad[min(si, len(cad) - 1)])
                tl.append({"at": when.isoformat(), "stage": stages[si],
                           "action": "advance", "reason": "客户有回应"})
        if stopped:
            break
        if (t - last_reply) >= timedelta(days=p["escalation_days"]) and escalated is None:
            escalated = t
            tl.append({"at": t.isoformat(), "stage": stages[si], "action": "escalate",
                       "reason": "%d 天无响应，转 %s" % (p["escalation_days"], p["owner_name"])})
            break
        if t >= nxt:
            if _in_quiet(t, p["quiet_hours"]):
                t = _next_allowed(t, p["quiet_hours"])
                nxt = t
                continue
            dk, wk = t.date().isoformat(), t.isocalendar()[:2]
            if day_c.get(dk, 0) >= p["daily_cap"] or week_c.get(wk, 0) >= p["weekly_cap"]:
                t = (t + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                continue
            day_c[dk] = day_c.get(dk, 0) + 1
            week_c[wk] = week_c.get(wk, 0) + 1
            tl.append({"at": t.isoformat(), "stage": stages[si], "action": "touch",
                       "reason": "第 %d 次触达" % day_c[dk]})
            nxt = t + timedelta(hours=cad[si])
        t = t + timedelta(hours=1)
    return {"ok": True, "errors": [], "timeline": tl, "escalated_at":
            escalated.isoformat() if escalated else None,
            "stopped": stopped, "touches": sum(1 for x in tl if x["action"] == "touch"),
            "params_hash": hashlib.sha256(canon(p).encode("utf-8")).hexdigest()[:12]}
