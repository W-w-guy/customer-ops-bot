# 验证记录

本文件里的每一行都来自**真实运行**，不是手写。复跑方式见文末。

## 一、两个平台、同一份代码

| | 平台 A | 平台 B |
|---|---|---|
| 系统 | Windows 11 (10.0.22631) | Ubuntu 24.04 (kernel 7.0.0-38) |
| Python | 3.11.7 | 3.12.3 |
| IANA 时区库 | **无**（tzdata 未安装，ZoneInfo 直接抛 ZoneInfoNotFoundError） | 有 |
| 全部测试 | **105 项通过** | **105 项通过** |

第二行那个「无」不是笔误：Windows 版 Python 默认不带 tzdata。第一版实现只用了
`zoneinfo.ZoneInfo("Asia/Shanghai")`，在 Ubuntu 上 100 项全绿，拿到 Windows 上一跑
**18 个失败 + 23 个错误**，报的全是 `E_TZ 未知时区 'Asia/Shanghai'`。
这正是「只在一边验证过」的典型事故。修法见 `botkit/tzutil.py`：优先 zoneinfo，
缺失时退到内置固定偏移表，并在 CLI 的 stderr 上明确提示用户（不静默降级）。

## 二、平台 A（Windows 11 / Python 3.11.7，无 tzdata，走降级路径）

| 步骤 | 命令 | 退出码 | 期望 | 耗时 | 首行输出 |
|---|---|---|---|---|---|
| 看字段定义 | `python3 run.py fields` | 0 ✅ | 0 | 0.06s | business_name    str       必填                 经营主体名称，出现在开场语与签名 |
| 校验示例参数 | `python3 run.py validate instances/example_params.json` | 0 ✅ | 0 | 0.09s | 校验通过：16 个字段全部合规 |
| 校验错参（应报错） | `python3 run.py validate tests/fixtures/bad_params.json` | 4 ✅ | 4 | 0.08s | 校验未通过： |
| 生成实例 | `python3 run.py render instances/example_params.json instances/_v.json` | 0 ✅ | 0 | 0.09s | 已写出 instances/_v.json（instance_id=inst_f2d67ee4bf0fbb09） |
| 干跑 30 天 | `python3 run.py simulate instances/example_params.json 30` | 0 ✅ | 0 | 0.08s | 预演 30 天：触达 7 次，升级 2026-01-12T09:00:00+08:00，终止 无 |
| 全部测试 | `python3 test_all.py` | 0 ✅ | 0 | 1.02s | 通过：105 项，失败 0，错误 0 |

## 三、平台 B（Ubuntu 24.04 / Python 3.12.3，有 tzdata，走原生路径）

| 步骤 | 命令 | 退出码 | 期望 | 耗时 | 首行输出 |
|---|---|---|---|---|---|
| 看字段定义 | `python3 run.py fields` | 0 ✅ | 0 | 0.02s | business_name    str       必填                 经营主体名称，出现在开场语与签名 |
| 校验示例参数 | `python3 run.py validate instances/example_params.json` | 0 ✅ | 0 | 0.02s | 校验通过：16 个字段全部合规 |
| 校验错参（应报错） | `python3 run.py validate tests/fixtures/bad_params.json` | 4 ✅ | 4 | 0.02s | 校验未通过： |
| 生成实例 | `python3 run.py render instances/example_params.json instances/_v.json` | 0 ✅ | 0 | 0.02s | 已写出 instances/_v.json（instance_id=inst_f2d67ee4bf0fbb09） |
| 干跑 30 天 | `python3 run.py simulate instances/example_params.json 30` | 0 ✅ | 0 | 0.02s | 预演 30 天：触达 7 次，升级 2026-01-12T09:00:00+08:00，终止 无 |
| 全部测试 | `python3 test_all.py` | 0 ✅ | 0 | 0.31s | 通过：105 项，失败 0，错误 0 |

**两平台的 `instance_id` 完全相同（`inst_f2d67ee4bf0fbb09`）**，说明模板渲染与参数规范化
在有无 tzdata、不同 Python 版本、不同时区库实现下都给出同一结果——这是可以拿去核对的指纹。

## 四、验证了什么（不是「能跑起来」而已）

| 主题 | 具体断言 |
|---|---|
| 字段校验 | 16 个字段逐个必填/类型/范围/枚举/邮箱/时区；缺一个就报 `E_REQUIRED`，一次列全不短路 |
| 跨字段约束 | 静默起止相同（`E_QUIET`）、周上限小于日上限（`E_CAP`）、入口阶段不在阶段表内（`E_STAGE`）、节奏长度≠阶段数-1（`E_CADENCE`）、升级窗口不晚于首次节奏（`E_ESCALATION`） |
| 拼写与旧名 | `dailly_cap` → `E_UNKNOWN`（不静默忽略）；`daily_limit` → `E_DEPRECATED` 且提示新名 |
| 实例化 | 同参数同 id 幂等；改参数换 id；**改模板或版本号也换 id**（否则审计对不上） |
| 隔离 | 甲客户的参数不出现在乙客户的实例里；渲染不改入参、不改模板 |
| 干跑 | 静默时段内零触达（含跨零点）、日/周上限不被突破、阶段只进不退、退订立即停止、无响应按期升级、不同时区落点不同、DST 跨日不崩 |
| 文案 | 模板里的 `{{quiet_hours|window}}` 渲染成 `21:00-次日 08:00`，不把原始 JSON 列表塞进句子 |
| 健壮性 | 参数文件是 `null`/`[]`/字符串时不吐 Python 栈回溯，退出码 2 并给中文提示；输出到目录不崩 |
| 文档一致性 | `FIELDS.md` 必须等于 `schema.py` 现算结果；README/SETUP/GUIDE 里写的测试条数必须等于真实条数（写错测试直接失败） |

## 五、怎么复跑

```bash
python3 tools/verify.py     # 重跑上面 6 条命令，打印新的记录，任何一条不符预期即非 0 退出
python3 test_all.py         # 105 项
```
