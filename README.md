# 客户经营 Bot 模板（customer-ops-bot）

一套**模板 + 字段定义 + 初始化说明**的完整交付件：把「一个客户从进来到复购」的经营动作写成可参数化的模板，
换一家客户只改参数，不改代码。零第三方依赖，Python 3.9+ 标准库即可运行。

## 这单交的三样东西（对着验收条）

| 验收要求 | 文件 | 怎么验 |
|---|---|---|
| 模板 | `templates/customer_ops_bot.json`（开场语/跟进语/升级语/四步 playbook/护栏） | `python3 run.py render instances/example_params.json out.json` |
| 字段定义 | `botkit/schema.py`（16 个字段，唯一真相源）+ `FIELDS.md`（自动生成） | `python3 run.py fields` |
| 初始化说明 | `SETUP.md`（5 分钟从零到实例）+ `USER_GUIDE.md`（日常操作与排错） | 照 SETUP 走一遍，或 `python3 run.py simulate instances/example_params.json 30` |

## 一条命令验完

```bash
python3 test_all.py        # 105 项测试，约 1 秒
```

## 目录

```
run.py                        入口
botkit/schema.py              16 个字段的定义（类型/必填/取值/默认/说明）
botkit/validate.py            校验：结构化错误码，一次列全不短路
botkit/render.py              实例化：模板 + 参数 -> 实例配置（幂等 id + 内容哈希）
botkit/simulate.py            干跑：假时钟跑 30 天，验证静默/上限/升级/退订
botkit/cli.py                 子命令：validate render simulate fields selftest
templates/customer_ops_bot.json  模板本体
instances/example_params.json    一份可直接用的示例参数
FIELDS.md                     字段定义表（由 tools/gen_fields.py 生成，勿手改）
tools/gen_fields.py           生成 FIELDS.md
tests/                        105 项测试 + 一份故意写错的参数样例
```

## 16 个字段速查（完整表见 FIELDS.md）

必填 7 个：`business_name`、`owner_name`、`owner_email`、`timezone`、`stages`、`entry_stage`、`cadence_hours`。
可选 9 个（都有默认值）：`brand_tone`、`quiet_hours`、`daily_cap`、`weekly_cap`、`escalation_days`、
`opt_out_keyword`、`language`、`retention_days`、`data_scope`。

## 三条设计取舍（不是随手写的）

1. **未知字段直接报错，不静默忽略**。`dailly_cap` 这种手滑若被忽略，客户会以为日上限生效了，实际是默认值 3 —— 这是最危险的静默失败，所以判定为 `E_UNKNOWN` 而不是 warning。
2. **实例 id = sha256(模板版本 + 规范化参数)**。同一份参数重复渲染得到同一个 id，便于审计与去重；参数变了 id 必变。
3. **干跑用真时区**。`Asia/Shanghai` 与 `America/New_York` 的静默时段落点不同，用固定 +8 偏移会在有夏令时的时区算错。

## 已知边界

- 模板只做「什么时候说什么」，不含真实发送通道（短信/企微/WhatsApp 需你侧提供接口）；交付物是配置与规则，不是营销外呼系统。
- 不存储客户个人数据；`data_scope` 只声明允许读取的范围，实际存储由你侧系统负责。
- 干跑的时间线基于规则推演，不是线上流量回放。
