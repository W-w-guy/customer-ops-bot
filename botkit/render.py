"""实例化：模板 + 参数 -> 客户可运行的实例配置。

设计口径：
- 同一 (模板版本, 规范化参数) 必须得到同一 instance_id —— 幂等，便于复跑与审计。
- 渲染前先校验；有错就不产出半成品（避免交付一份"看起来能用"的残件）。
- 模板里任何 {{占位符}} 必须在字段定义里存在，否则报 E_PLACEHOLDER。
"""
from __future__ import annotations
import hashlib
import json
import re
from .schema import defaults, spec_index
from .validate import validate

PH_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)(?:\|([a-z_]+))?\s*\}\}")
FORMATS = ("window", "hours", "label", "csv")


def canon(obj):
    """规范化序列化：键排序、无多余空格、ensure_ascii=False，用于哈希与 diff。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def template_hash(template):
    return hashlib.sha256(canon(template).encode("utf-8")).hexdigest()[:8]


def instance_id(template_id, version, params, tpl_hash=""):
    """实例指纹必须同时覆盖模板内容：只改文案不改参数时 id 也得变，否则审计对不上。"""
    key = "%s@%s#%s|%s" % (template_id, version, tpl_hash, canon(params))
    return "inst_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def placeholders(text):
    return sorted({m[0] for m in PH_RE.findall(text)})


def formats_used(obj):
    out = set()
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            out.update(f for _, f in PH_RE.findall(cur) if f)
        elif isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return sorted(out)


def check_placeholders(obj, allowed=None):
    """递归收集模板里的占位符，返回 (全部, 未知)。"""
    allowed = set(allowed or spec_index().keys())
    found = set()
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            found.update(m[0] for m in PH_RE.findall(cur))
        elif isinstance(cur, dict):
            stack.extend(cur.values())
            stack.extend(cur.keys())
        elif isinstance(cur, list):
            stack.extend(cur)
    return sorted(found), sorted(found - allowed)


def _fmt(v, fmt=None, spec=None):
    """把人看得懂的格式交给模板指定，而不是把原始列表直接塞进句子。"""
    labels = (spec or {}).get("labels") or {}
    if fmt == "window" and isinstance(v, list) and len(v) == 2:
        a, b = v
        if a < b:
            return "%02d:00-%02d:00" % (a, b)
        return "%02d:00-次日 %02d:00" % (a, b)
    if fmt == "hours" and isinstance(v, list):
        return "/".join("%d 小时" % x for x in v)
    if fmt == "label":
        return labels.get(v, str(v))
    if fmt == "csv" and isinstance(v, list):
        return "、".join(str(x) for x in v)
    if isinstance(v, list):
        return " / ".join(str(x) for x in v)
    return str(v)


def _subst(text, ctx, specs=None):
    specs = specs or {}

    def one(m):
        name, fmt = m.group(1), m.group(2)
        return _fmt(ctx[name], fmt, specs.get(name))
    return PH_RE.sub(one, text)


def fill(template, params, strict=True):
    """把模板里的占位符换成参数值；strict=True 时遇未知占位符直接抛错。"""
    merged = dict(defaults())
    merged.update({k: v for k, v in params.items() if v is not None})
    found, unknown = check_placeholders(template)
    if strict and unknown:
        raise ValueError("模板占位符不在字段定义内：%s" % ", ".join(unknown))
    missing = [k for k in found if k not in merged]
    if missing:
        raise ValueError("占位符缺参数：%s" % ", ".join(missing))
    ctx = {k: merged[k] for k in found}
    if isinstance(template, str):
        return _subst(template, ctx, spec_index())
    if isinstance(template, list):
        return [fill(x, merged, strict) for x in template]
    if isinstance(template, dict):
        return {fill(k, merged, strict): fill(v, merged, strict) for k, v in template.items()}
    return template


def render(template, params, strict_unknown=True):
    """返回 (实例配置, 错误列表)。有错误时实例为 None。"""
    errs = validate(params, strict_unknown=strict_unknown)
    if errs:
        return None, errs
    merged = dict(defaults())
    merged.update({k: v for k, v in params.items() if v is not None})
    _, unknown_ph = check_placeholders(template, merged.keys())
    if unknown_ph:
        errs.append({"field": "__template__", "code": "E_PLACEHOLDER",
                     "msg": "模板占位符无对应字段：%s" % ", ".join(unknown_ph)})
    if errs:
        return None, errs
    bad_fmt = [f for f in formats_used(template) if f not in FORMATS]
    if bad_fmt:
        return None, [{"field": "__template__", "code": "E_FORMAT",
                       "msg": "未知格式修饰符：%s（可用 %s）" % (bad_fmt, list(FORMATS))}]
    body = fill(template, merged)
    th = template_hash(template)
    out = {
        "instance_id": instance_id(template["template_id"], template["version"], merged, th),
        "template_hash": th,
        "template_id": template["template_id"],
        "template_version": template["version"],
        "params": {k: merged[k] for k in sorted(merged)},
        "spec": body,
        "content_hash": hashlib.sha256(canon(merged).encode("utf-8")).hexdigest()[:32],
    }
    return out, []
