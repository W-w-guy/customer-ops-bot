# 字段定义（自动生成，勿手改）

由 `python3 tools/gen_fields.py` 从 `botkit/schema.py` 生成。
测试 `FieldDocSync` 会比对两者，不一致即失败。

| 字段 | 类型 | 必填 | 取值 | 默认 | 说明 |
|---|---|---|---|---|---|
| `business_name` | str | 是 | 1..60 | - | 经营主体名称，出现在开场语与签名 |
| `owner_name` | str | 是 | 1..40 | - | 对客署名的负责人 |
| `owner_email` | email | 是 | - | - | 异常与升级通知的收件地址 |
| `timezone` | tz | 是 | - | - | 实例时区（IANA 名），决定静默时段与节奏的落点 |
| `brand_tone` | enum | 否 | `formal` / `friendly` / `expert` | `friendly` | 对客语气档位 |
| `quiet_hours` | int_list | 否 | 0..23 | `[21, 8]` | 静默时段 [起, 止) 整点，可跨零点 |
| `daily_cap` | int | 否 | 1..50 | `3` | 单客单日触达上限 |
| `weekly_cap` | int | 否 | 1..200 | `10` | 单客单周触达上限 |
| `stages` | str_list | 是 | 长度 2..12 | - | 客户经营阶段，顺序即推进方向 |
| `entry_stage` | str | 是 | - | - | 新客进入的阶段，必须是 stages 之一 |
| `cadence_hours` | int_list | 是 | 1..720 | - | 每个阶段停留多少小时后尝试下一次触达，长度=len(stages)-1 |
| `escalation_days` | int | 否 | 1..90 | `7` | 连续无响应多少天升级给负责人 |
| `opt_out_keyword` | str | 否 | 1..12 | `STOP` | 客户回复该词即永久停止触达 |
| `language` | enum | 否 | `zh` / `en` | `zh` | 对客文案语言 |
| `retention_days` | int | 否 | 30..3650 | `365` | 互动记录保留天数 |
| `data_scope` | enum | 否 | `contact_only` / `contact_and_history` | `contact_only` | 允许模板读取的客户数据范围 |

已废弃别名（写了会报 E_DEPRECATED，不会静默忽略）：

- `daily_limit` → `daily_cap`
- `stages_list` → `stages`
- `tz` → `timezone`
