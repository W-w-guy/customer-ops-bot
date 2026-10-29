"""从 botkit/schema.py 生成 FIELDS.md —— 文档不得手写，否则必然漂移。"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from botkit import schema  # noqa: E402


def build():
    rows = ["| 字段 | 类型 | 必填 | 取值 | 默认 | 说明 |", "|---|---|---|---|---|---|"]
    for s in schema.FIELD_SPECS:
        if s.get("enum"):
            rng = " / ".join("`%s`" % x for x in s["enum"])
        elif s.get("min") is not None or s.get("max") is not None:
            rng = "%s..%s" % (s.get("min", "-"), s.get("max", "-"))
        elif s.get("len"):
            rng = "长度 %d" % s["len"]
        elif s.get("min_len") or s.get("max_len"):
            rng = "长度 %s..%s" % (s.get("min_len", "-"), s.get("max_len", "-"))
        else:
            rng = "-"
        rows.append("| `%s` | %s | %s | %s | %s | %s |" % (
            s["name"], s["kind"], "是" if s["required"] else "否", rng,
            "`%s`" % (s["default"],) if "default" in s else "-", s["desc"]))
    dep = ["已废弃别名（写了会报 E_DEPRECATED，不会静默忽略）：", ""]
    dep += ["- `%s` → `%s`" % (a, b) for a, b in sorted(schema.DEPRECATED.items())]
    return "\n".join(["# 字段定义（自动生成，勿手改）", "",
                      "由 `python3 tools/gen_fields.py` 从 `botkit/schema.py` 生成。",
                      "测试 `FieldDocSync` 会比对两者，不一致即失败。", ""] + rows + [""] + dep + [""])


if __name__ == "__main__":
    p = os.path.join(HERE, "FIELDS.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(build())
    print("已生成 %s（%d 个字段）" % (p, len(schema.FIELD_SPECS)))
