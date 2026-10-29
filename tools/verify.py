#!/usr/bin/env python3
"""验证记录生成器：把 6 条命令的真实退出码与关键输出行记下来。

用法：python3 tools/verify.py           打印记录
      python3 tools/verify.py --write   写入 VERIFICATION.md 的“本方实测”小节

设计口径：记录必须由**本次真实运行**产生，不能手写。所以这里直接跑子进程，
拿到退出码与首行输出，任何一条与预期不符就以非 0 退出。
"""
from __future__ import annotations
import json
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

CASES = [
    ("看字段定义", ["run.py", "fields"], 0),
    ("校验示例参数", ["run.py", "validate", "instances/example_params.json"], 0),
    ("校验错参（应报错）", ["run.py", "validate", "tests/fixtures/bad_params.json"], 4),
    ("生成实例", ["run.py", "render", "instances/example_params.json", "instances/_v.json"], 0),
    ("干跑 30 天", ["run.py", "simulate", "instances/example_params.json", "30"], 0),
    ("全部测试", ["test_all.py"], 0),
]


def run(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    t0 = time.time()
    p = subprocess.run([PY] + args, cwd=HERE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env)
    dt = time.time() - t0
    out = (p.stdout or "") + (p.stderr or "")
    first = next((l.strip() for l in out.splitlines() if l.strip()), "")
    return p.returncode, first, dt


def main(argv):
    rows, bad = [], 0
    for name, args, expect in CASES:
        rc, first, dt = run(args)
        ok = (rc == expect)
        bad += 0 if ok else 1
        rows.append((name, " ".join(["python3"] + args), rc, expect, dt, first[:96], ok))
    print("## 本机实测（%s / Python %s）\n" % (platform.platform(), platform.python_version()))
    print("| 步骤 | 命令 | 退出码 | 期望 | 耗时 | 首行输出 |")
    print("|---|---|---|---|---|---|")
    for name, cmd, rc, exp, dt, first, ok in rows:
        print("| %s | `%s` | %d %s | %d | %.2fs | %s |" % (
            name, cmd, rc, "✅" if ok else "❌", exp, dt, first.replace("|", "\\|")))
    tmp = os.path.join(HERE, "instances", "_v.json")
    if os.path.exists(tmp):
        os.remove(tmp)
    print("\n结果：%d/%d 与预期一致。" % (len(rows) - bad, len(rows)))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
