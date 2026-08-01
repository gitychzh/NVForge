# R-legacy-remote: HM2 全配置对齐 HM1 + 三层 4101→40001 根治

**日期**: 2026-08-01
**主机**: HM2
**铁律**: HM1 零改动

## 问题

cc2 和 cloudcli 走 4101 (cc4101), 但 cc4101 breaker OPEN + FALLBACK=none = 100% "upstream failed".
之前改 settings.json 无效, 因为 4101 在三个地方硬编码, 互相覆盖:

1. **cc2-resume.service** (systemd unit) — Environment=ANTHROPIC_BASE_URL=4101
2. **cc2_resume.sh** (脚本) — export ANTHROPIC_BASE_URL=4101
3. **project settings.json** (.claude/settings.json) — env.ANTHROPIC_BASE_URL=4101

systemd Environment > script export > project settings env > user settings env (优先级链)

## 变更 (6 个文件)

| 文件 | 改了什么 |
|---|---|
| cc2-resume.service | BASE_URL 4101→40001, API_KEY cc4101-token→sk-litellm-local |
| cc2_resume.sh | BASE_URL 4101→40001, API_KEY, COMPACT 50000→155000, STREAM_IDLE 500000→900000, prompt 参数描述 |
| .claude/settings.json (user) | contextWindow 80000→170000, autoCompactWindow 50000→155000, autoUpdates=false |
| .claude/settings.json (project) | BASE_URL 4101→40001, API_KEY, COMPACT, STREAM_IDLE, API_TIMEOUT, model, contextWindow, autoCompactWindow 全对齐 |
| cloudcli-webui.service | COMPACT 90000→155000 (上一轮已改 BASE_URL+API_KEY) |
| ~/.cloudcli/.env | 40000→40001 (上一轮) |

## 对齐后参数 (HM2 = HM1)

| 参数 | 值 |
|---|---|
| ANTHROPIC_BASE_URL | http://127.0.0.1:40001 |
| ANTHROPIC_API_KEY | sk-litellm-local |
| model | glm5.2_cc |
| contextWindow | 170000 |
| autoCompactWindow | 155000 |
| CLAUDE_CODE_AUTO_COMPACT_WINDOW | 155000 |
| API_TIMEOUT_MS | 600000 |
| CLAUDE_STREAM_IDLE_TIMEOUT_MS | 900000 |

## 验证

- claude pid=3333022 env: ANTHROPIC_BASE_URL=40001, API_KEY=sk-litellm-local, COMPACT=155000, STREAM_IDLE=900000
- 网络连接: claude→127.0.0.1:40001 (ESTAB), 4101 零活跃连接
- cloudcli env 同上
- cc4101 (4101) 原链路保留未动

## 回滚

各文件 .bak.R-legacy-remote 备份
