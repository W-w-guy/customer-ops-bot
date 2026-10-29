# 初始化说明（5 分钟）

## 0. 前置

- Python 3.9 及以上（`python3 --version` 确认）
- 不需要 pip install、不需要 venv、不需要数据库

## 1. 拿到代码

```bash
git clone <你的仓库地址> customer-ops-bot
cd customer-ops-bot
```

## 2. 一条命令确认环境可用

```bash
python3 test_all.py
```

预期最后一行：`通过：105 项，失败 0，错误 0`。若失败，先解决环境，不要往下走。

## 3. 看字段定义

```bash
python3 run.py fields
```

16 行，每行「字段 类型 必填/默认 说明」。完整表格在 `FIELDS.md`。

## 4. 写你自己的参数

复制 `instances/example_params.json`，改成你自己的：

| 字段 | 怎么填 | 填错会怎样 |
|---|---|---|
| `business_name` | 1-60 字，出现在开场语 | 报 `E_RANGE` |
| `owner_name` / `owner_email` | 对客署名与升级收件人 | 邮箱格式错报 `E_EMAIL` |
| `timezone` | IANA 名，如 `Asia/Shanghai` | 写错报 `E_TZ`，会明确告诉你是时区问题 |
| `stages` | 2-12 个阶段，不能重名 | 重名报 `E_DUP` |
| `entry_stage` | 必须是 `stages` 之一 | 不在里面报 `E_STAGE` |
| `cadence_hours` | 长度必须 = `len(stages)-1` | 长度不符报 `E_CADENCE` |
| `quiet_hours` | `[起, 止)` 整点，可跨零点 | 起止相同报 `E_QUIET`（拒绝全天静默） |
| `daily_cap` / `weekly_cap` | 单客频次上限，周不得小于日 | 报 `E_CAP` |

## 5. 校验

```bash
python3 run.py validate instances/my_params.json
```

- 通过：`校验通过：16 个字段全部合规`，退出码 0
- 不通过：逐条列出 `[错误码] 字段 原因`，退出码 4。**一次列全**，不需要改了再跑、跑了再改。

## 6. 生成实例配置

```bash
python3 run.py render instances/my_params.json instances/my_bot.json
```

输出里 `instance_id` 是这份参数的指纹；参数不变，重复渲染 id 不变。

## 7. 干跑 30 天

```bash
python3 run.py simulate instances/my_params.json 30
```

看三件事：触达是否都落在静默时段之外、每天是否没超过 `daily_cap`、无响应是否在 `escalation_days` 天后升级。

## 8. 上线前自查（3 条）

1. `quiet_hours` 覆盖了当地夜间（中国常见 `[21, 8]`）
2. `opt_out_keyword` 你的通道能识别（若用短信，确认该词被路由到本系统）
3. `owner_email` 是真人会看的邮箱，不是 noreply

## 常见错误

| 现象 | 原因 | 处理 |
|---|---|---|
| `JSON 解析失败：... 第 N 行第 M 列` | 逗号/引号/尾逗号 | 按行列出错位置改 |
| `字段已更名，请改用 daily_cap` | 用了旧字段名 | 按提示改名，不会自动兼容 |
| `未知字段（常见于拼写错误）` | 字段名拼错 | 跑 `python3 run.py fields` 对照 |
