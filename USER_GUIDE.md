# 使用与排错指南

## 五条命令

| 命令 | 用途 | 退出码 |
|---|---|---|
| `python3 run.py fields` | 打印 16 个字段定义 | 0 |
| `python3 run.py validate <params.json>` | 只校验，不改任何东西 | 0 通过 / 4 有问题 / 2 文件或 JSON 问题 |
| `python3 run.py render <params.json> [out.json]` | 生成实例配置 | 同上 |
| `python3 run.py simulate <params.json> [天数]` | 干跑时间线 | 同上 |
| `python3 test_all.py` | 跑 105 项测试 | 0 全过 / 1 有失败 |

退出码口径：**0 = 通过，2 = 你给的文件有问题（找不到/不是合法 JSON），4 = 参数内容不合规**。
脚本化调用时据此判断，不要靠抓标准输出的中文。

## 错误码对照

| 码 | 含义 | 典型触发 |
|---|---|---|
| `E_REQUIRED` | 必填字段缺失（空字符串也算缺） | 忘填 `timezone` |
| `E_TYPE` | 类型不对 | `"daily_cap": "3"`（字符串）、`true`（布尔冒充整数） |
| `E_RANGE` | 数值或长度越界 | `daily_cap: 0`、`business_name` 超过 60 字 |
| `E_ENUM` | 不在枚举内 | `brand_tone: "casual"` |
| `E_EMAIL` | 邮箱不合法 | `limin@example` |
| `E_TZ` | 未知时区 | `Asia/Shanghia`（拼错） |
| `E_LEN` | 列表长度不对 | `quiet_hours` 只给一个数 |
| `E_EMPTY` / `E_DUP` | 阶段为空 / 重名 | `["新客","新客"]` |
| `E_QUIET` | 静默起止相同 | `[8, 8]` |
| `E_CAP` | 周上限小于日上限 | `daily_cap: 5, weekly_cap: 3` |
| `E_STAGE` | 入口阶段不在阶段表内 | `entry_stage: "流失"` 但 `stages` 里没有 |
| `E_CADENCE` | 节奏长度不等于 `len(stages)-1` | 4 个阶段却给 2 个节奏 |
| `E_UNKNOWN` | 未知字段（多为拼写错误） | `dailly_cap` |
| `E_DEPRECATED` | 用了旧字段名 | `daily_limit` → 请改用 `daily_cap` |

`E_UNKNOWN` 与 `E_DEPRECATED` 都是**错误**，不是警告：静默忽略拼错的字段，会让客户以为规则生效了。

## 干跑结果怎么读

```
2026-01-05T09:00:00+08:00  新客   touch     第 1 次触达
2026-01-06T09:00:00+08:00  新客   touch     第 1 次触达
2026-01-06T10:00:00+08:00  体验   advance   客户有回应
```

- `touch` = 一次触达，时间戳是实例时区的本地时间（带 +08:00 偏移，不会看错时区）
- `advance` = 客户有回应，阶段前移一格；**阶段只进不退**
- `escalate` = 连续 `escalation_days` 天客户无回应，转 `owner_name`
- `stop` = 客户回复了 `opt_out_keyword`，此后不再有任何触达

## 三个常见误解

1. **「我把 daily_cap 调大就能多触达」** —— 不会。`cadence_hours` 决定最小间隔，上限只是天花板，两者取更严的那个。
2. **「静默时段内排的计划会丢」** —— 不会丢，会顺延到静默结束的第一个整点。
3. **「同一份参数渲染两次会不会生成两个实例」** —— 不会，`instance_id` 由参数哈希决定，相同参数得到相同 id。

## 想改模板本身

`templates/customer_ops_bot.json` 里的 `{{...}}` 只能引用 `botkit/schema.py` 里已定义的字段。
写了不存在的占位符会报 `E_PLACEHOLDER`，不会渲染出一个带着 `{{xxx}}` 的残件。
新增字段请改 `schema.py` 的 `FIELD_SPECS`，然后 `python3 tools/gen_fields.py` 重新生成 `FIELDS.md`（测试会校验两者一致）。
