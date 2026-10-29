"""CLI：validate / render / simulate / fields / selftest

退出码：0 通过、2 参数或文件问题、3 校验失败、4 预检未通过（缺字段/未知字段）
"""
from __future__ import annotations
import json
import os
import sys
from . import schema, render as render_mod, simulate as sim_mod

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(HERE, "templates", "customer_ops_bot.json")


def _load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TypeError("参数文件必须是 JSON 对象，收到 %s" % type(data).__name__)
    return data


def _report(errs):
    for e in errs:
        print("  [%s] %-14s %s" % (e["code"], e["field"], e["msg"]))
    print("共 %d 个问题" % len(errs))


def cmd_validate(args):
    params = _load(args[0])
    errs = schema and __import__("botkit.validate", fromlist=["validate"]).validate(params)
    if errs:
        print("校验未通过：")
        _report(errs)
        return 4
    print("校验通过：%d 个字段全部合规" % len(params))
    return 0


def cmd_render(args):
    params = _load(args[0])
    out, errs = render_mod.render(_load(TPL), params)
    if errs:
        print("无法实例化：")
        _report(errs)
        return 4
    dst = args[1] if len(args) > 1 else "-"
    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    if dst == "-":
        print(text)
    else:
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("已写出 %s（instance_id=%s）" % (dst, out["instance_id"]))
    return 0


def cmd_simulate(args):
    params = _load(args[0])
    days = int(args[1]) if len(args) > 1 else 30
    r = sim_mod.simulate(params, days=days)
    if not r["ok"]:
        print("无法预演：")
        _report(r["errors"])
        return 4
    print("预演 %d 天：触达 %d 次，升级 %s，终止 %s" %
          (days, r["touches"], r["escalated_at"] or "无", r["stopped"] or "无"))
    for x in r["timeline"]:
        print("  %s  %-4s  %-8s %s" % (x["at"], x["stage"], x["action"], x["reason"]))
    return 0


def cmd_fields(args):
    for s in schema.FIELD_SPECS:
        req = "必填" if s["required"] else "可选,默认=%r" % (s.get("default"),)
        print("%-16s %-9s %-18s %s" % (s["name"], s["kind"], req, s["desc"]))
    print("共 %d 个字段；已废弃别名：%s" %
          (len(schema.FIELD_SPECS), ", ".join(sorted(schema.DEPRECATED))))
    return 0


def cmd_selftest(args):
    import subprocess
    p = subprocess.run([sys.executable, os.path.join(HERE, "test_all.py")])
    return p.returncode


CMDS = {"validate": cmd_validate, "render": cmd_render, "simulate": cmd_simulate,
        "fields": cmd_fields, "selftest": cmd_selftest}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print("用法: run.py <%s> [参数]" % "|".join(CMDS))
        print("  validate <params.json>            只校验字段")
        print("  render <params.json> [out.json]   生成实例配置")
        print("  simulate <params.json> [天数]      干跑时间线")
        print("  fields                            打印字段定义")
        print("  selftest                          跑全部测试")
        return 0
    cmd = argv.pop(0)
    if cmd not in CMDS:
        print("未知子命令 %r" % cmd)
        return 2
    try:
        rc = CMDS[cmd](argv)
        from .tzutil import STATE
        if STATE["degraded"]:
            print("[提示] %s" % STATE["reason"], file=sys.stderr)
        return rc
    except FileNotFoundError as e:
        print("找不到文件：%s" % e.filename)
        return 2
    except IsADirectoryError:
        print("输出路径是目录，请给出文件名")
        return 2
    except TypeError as e:
        print("参数文件格式不对：%s" % e)
        return 2
    except OSError as e:
        print("读写失败：%s" % e)
        return 2
    except json.JSONDecodeError as e:
        print("JSON 解析失败：%s（第 %d 行第 %d 列）" % (e.msg, e.lineno, e.colno))
        return 2
