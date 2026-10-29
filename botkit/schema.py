"""字段定义（FIELD_SPECS）——本模板唯一的字段真相源。

FIELDS.md 由 tools/gen_fields.py 从本模块生成，测试会比对二者，
文档漂移即测试失败。
"""
from __future__ import annotations

KINDS = ("str", "int", "int_list", "str_list", "enum", "email", "tz", "bool")

FIELD_SPECS = [
    {"name": "business_name", "kind": "str", "required": True, "min": 1, "max": 60,
     "desc": "经营主体名称，出现在开场语与签名", "example": "青柠健身"},
    {"name": "owner_name", "kind": "str", "required": True, "min": 1, "max": 40,
     "desc": "对客署名的负责人", "example": "李敏"},
    {"name": "owner_email", "kind": "email", "required": True,
     "desc": "异常与升级通知的收件地址", "example": "ops@example.com"},
    {"name": "timezone", "kind": "tz", "required": True,
     "desc": "实例时区（IANA 名），决定静默时段与节奏的落点", "example": "Asia/Shanghai"},
    {"name": "brand_tone", "kind": "enum", "required": False, "default": "friendly",
     "enum": ["formal", "friendly", "expert"],
     "labels": {"formal": "正式", "friendly": "亲切", "expert": "专业"}, "desc": "对客语气档位", "example": "friendly"},
    {"name": "quiet_hours", "kind": "int_list", "required": False, "default": [21, 8],
     "len": 2, "min": 0, "max": 23,
     "desc": "静默时段 [起, 止) 整点，可跨零点", "example": [21, 8]},
    {"name": "daily_cap", "kind": "int", "required": False, "default": 3, "min": 1, "max": 50,
     "desc": "单客单日触达上限", "example": 3},
    {"name": "weekly_cap", "kind": "int", "required": False, "default": 10, "min": 1, "max": 200,
     "desc": "单客单周触达上限", "example": 10},
    {"name": "stages", "kind": "str_list", "required": True, "min_len": 2, "max_len": 12,
     "desc": "客户经营阶段，顺序即推进方向", "example": ["新客", "体验", "成交", "复购"]},
    {"name": "entry_stage", "kind": "str", "required": True,
     "desc": "新客进入的阶段，必须是 stages 之一", "example": "新客"},
    {"name": "cadence_hours", "kind": "int_list", "required": True, "min": 1, "max": 720,
     "desc": "每个阶段停留多少小时后尝试下一次触达，长度=len(stages)-1", "example": [24, 72, 168]},
    {"name": "escalation_days", "kind": "int", "required": False, "default": 7, "min": 1, "max": 90,
     "desc": "连续无响应多少天升级给负责人", "example": 7},
    {"name": "opt_out_keyword", "kind": "str", "required": False, "default": "STOP",
     "min": 1, "max": 12, "desc": "客户回复该词即永久停止触达", "example": "STOP"},
    {"name": "language", "kind": "enum", "required": False, "default": "zh",
     "enum": ["zh", "en"],
     "labels": {"zh": "中文", "en": "英文"}, "desc": "对客文案语言", "example": "zh"},
    {"name": "retention_days", "kind": "int", "required": False, "default": 365,
     "min": 30, "max": 3650, "desc": "互动记录保留天数", "example": 365},
    {"name": "data_scope", "kind": "enum", "required": False, "default": "contact_only",
     "enum": ["contact_only", "contact_and_history"],
     "labels": {"contact_only": "仅联系方式", "contact_and_history": "联系方式与互动历史"},
     "desc": "允许模板读取的客户数据范围", "example": "contact_only"},
]

DEPRECATED = {"daily_limit": "daily_cap", "stages_list": "stages", "tz": "timezone"}


def spec_index():
    return {s["name"]: s for s in FIELD_SPECS}


def defaults():
    return {s["name"]: s["default"] for s in FIELD_SPECS if "default" in s}
