"""字段校验：结构化错误（field/code/msg），一次列全，不短路。"""
from __future__ import annotations
import re
from .schema import FIELD_SPECS, DEPRECATED, spec_index

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _err(field, code, msg):
    return {"field": field, "code": code, "msg": msg}


def _check_tz(v):
    from .tzutil import known
    return known(v)


def _check(spec, v):
    out = []
    n, k = spec["name"], spec["kind"]
    if k == "str":
        if not isinstance(v, str):
            out.append(_err(n, "E_TYPE", "需要字符串，收到 %s" % type(v).__name__))
        else:
            lo, hi = spec.get("min"), spec.get("max")
            if lo is not None and len(v) < lo:
                out.append(_err(n, "E_RANGE", "长度不得小于 %d，实际 %d" % (lo, len(v))))
            if hi is not None and len(v) > hi:
                out.append(_err(n, "E_RANGE", "长度不得超过 %d，实际 %d" % (hi, len(v))))
    elif k == "int":
        if isinstance(v, bool) or not isinstance(v, int):
            out.append(_err(n, "E_TYPE", "需要整数，收到 %s" % type(v).__name__))
        else:
            lo, hi = spec.get("min"), spec.get("max")
            if lo is not None and v < lo:
                out.append(_err(n, "E_RANGE", "不得小于 %d，实际 %d" % (lo, v)))
            if hi is not None and v > hi:
                out.append(_err(n, "E_RANGE", "不得大于 %d，实际 %d" % (hi, v)))
    elif k == "bool":
        if not isinstance(v, bool):
            out.append(_err(n, "E_TYPE", "需要 true/false"))
    elif k == "enum":
        if v not in spec["enum"]:
            out.append(_err(n, "E_ENUM", "只能是 %s，收到 %r" % ("/".join(spec["enum"]), v)))
    elif k == "email":
        if not isinstance(v, str) or not EMAIL_RE.match(v):
            out.append(_err(n, "E_EMAIL", "不是合法邮箱：%r" % (v,)))
    elif k == "tz":
        if not isinstance(v, str) or not _check_tz(v):
            out.append(_err(n, "E_TZ", "未知时区 %r，需 IANA 名如 Asia/Shanghai" % (v,)))
    elif k in ("int_list", "str_list"):
        if not isinstance(v, list):
            out.append(_err(n, "E_TYPE", "需要列表，收到 %s" % type(v).__name__))
            return out
        want = int if k == "int_list" else str
        bad = [i for i, x in enumerate(v) if not isinstance(x, want) or isinstance(x, bool)]
        if bad:
            out.append(_err(n, "E_TYPE", "第 %s 项类型不是 %s" % (bad, want.__name__)))
            return out
        ln = spec.get("len")
        if ln is not None and len(v) != ln:
            out.append(_err(n, "E_LEN", "长度必须为 %d，实际 %d" % (ln, len(v))))
        lo, hi = spec.get("min_len"), spec.get("max_len")
        if lo is not None and len(v) < lo:
            out.append(_err(n, "E_LEN", "至少 %d 项，实际 %d" % (lo, len(v))))
        if hi is not None and len(v) > hi:
            out.append(_err(n, "E_LEN", "至多 %d 项，实际 %d" % (hi, len(v))))
        nlo, nhi = spec.get("min"), spec.get("max")
        if k == "int_list" and nlo is not None:
            out += [_err(n, "E_RANGE", "第 %d 项 %d 超出 %d..%d" % (i, x, nlo, nhi))
                    for i, x in enumerate(v) if x < nlo or x > nhi]
        if k == "str_list":
            empty = [i for i, x in enumerate(v) if not x.strip()]
            if empty:
                out.append(_err(n, "E_EMPTY", "第 %s 项为空" % empty))
            dup = sorted({x for x in v if v.count(x) > 1})
            if dup:
                out.append(_err(n, "E_DUP", "阶段重复：%s" % dup))
    return out


def validate(params, strict_unknown=True):
    """返回错误列表；空列表=通过。一次列全所有问题。"""
    if not isinstance(params, dict):
        return [_err("(root)", "E_ROOT", "参数必须是 JSON 对象，收到 %s" % type(params).__name__)]
    errs, idx = [], spec_index()
    for spec in FIELD_SPECS:
        n = spec["name"]
        if params.get(n) in (None, ""):
            if spec["required"]:
                errs.append(_err(n, "E_REQUIRED", "必填字段缺失"))
            continue
        errs += _check(spec, params[n])
    for k in params:
        if k in idx:
            continue
        if k in DEPRECATED:
            errs.append(_err(k, "E_DEPRECATED", "字段已更名，请改用 %s" % DEPRECATED[k]))
        elif strict_unknown:
            errs.append(_err(k, "E_UNKNOWN", "未知字段（常见于拼写错误）"))
    return errs + cross_check(params)


def cross_check(p):
    """字段之间的约束——单字段校验看不见的那一类错误。"""
    out = []
    q, st, cd = p.get("quiet_hours"), p.get("stages"), p.get("cadence_hours")
    dc, wc = p.get("daily_cap"), p.get("weekly_cap")
    if isinstance(q, list) and len(q) == 2 and q[0] == q[1]:
        out.append(_err("quiet_hours", "E_QUIET", "起止相同等于全天静默，拒绝静默 24 小时"))
    if isinstance(dc, int) and isinstance(wc, int) and wc < dc:
        out.append(_err("weekly_cap", "E_CAP", "周上限(%d)不得小于日上限(%d)" % (wc, dc)))
    esc = p.get("escalation_days")
    if isinstance(cd, list) and cd and isinstance(esc, int) and esc * 24 <= cd[0]:
        out.append(_err("escalation_days", "E_ESCALATION",
                        "升级窗口(%d 天)不晚于首次触达节奏(%d 小时)，客户只会被打扰一次就升级"
                        % (esc, cd[0])))
    ent = p.get("entry_stage")
    if isinstance(st, list) and ent and ent not in st:
        out.append(_err("entry_stage", "E_STAGE", "入口阶段 %r 不在 stages 内" % ent))
    if isinstance(st, list) and isinstance(cd, list) and len(cd) != len(st) - 1:
        out.append(_err("cadence_hours", "E_CADENCE",
                        "节奏长度应为 len(stages)-1=%d，实际 %d" % (len(st) - 1, len(cd))))
    return out
