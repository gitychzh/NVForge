# R-cc2-31dd48a5-stuck: cc2 session 卡死根因与修复 (HM2)

> **时间**: 2026-08-03 20:50 CST
> **影响**: cc2 自优化 agent 自 2026-08-01 起 ~48h 全部流量走错链路 (legacy_cc_1:40001 而非 cc4101:4101)
> **现象**: session 31dd48a5 (webui 内部 ID) → provider_session_id 55f1500a 在 plan mode 下卡死

## 一、定位过程

### 症状
- 用户报告 cloudcli webui session 31dd48a5 毫无征兆卡住
- `ps` 显示 PID 2891257 (claude --resume=55f1500a, plan mode) 从 20:04 运行至今, ep_poll sleeping
- PID 2908180/2908182 (bash+claude --resume) 也卡在同一 session

### 根因链
1. **R-legacy-remote (2026-08-01)** 部署 legacy_cc_1 (40001) + legacy_ms_litellm (41001)
2. 部署时修改了 `~/cc_ps/cc2_repair_self/.claude/settings.json`:
   - `ANTHROPIC_BASE_URL`: `http://127.0.0.1:4101` → `http://127.0.0.1:40001` ❌
   - `ANTHROPIC_API_KEY`: `cc4101-token` → `sk-litellm-local` ❌
3. 项目级 settings.json 优先级 > 进程环境变量 > 全局 settings.json
4. 所有从 cloudcli webui 在 cc2_repair_self 路径下启动的 claude 进程都走了 40001 (legacy_cc_1)
5. legacy_cc_1 → legacy_ms_litellm → ModelScope 链路大量 ABORT-NO-FALLBACK (MS 全 key 429/RD)
6. claude 请求超时/出错, plan mode 下卡在等待一个 10min timeout 的 Bash tool_use

### 铁证
- `ss -tnp | grep 2891257`: `ESTAB 127.0.0.1:40001` (legacy_cc_1), 不是 4101 (cc4101)
- cc4101 日志: 最后请求 15:24:35, 之后 5h+ 无流量
- nv_requests 表: `caller=cc4101-primary` 连续 9+ 轮零行
- legacy_cc_1 日志: 142 条 claude-opus-5 请求 + 95 条 ABORT-NO-FALLBACK (60min 窗口)
- 所有 settings.json.bak.* 都指向 4101, 只有当前 settings.json 指向 40001

### 为什么 watchdog 没杀
- R2258 webui watchdog (`CLAUDE_STREAM_IDLE_TIMEOUT_MS=900000`): claude 在执行 600000ms Bash 命令,
  idle timer 不触发 (进程 "活动" 中)
- cc2-longwatch.timer: disabled (cc2-resume 模式不用 long session)

## 二、修复

### 执行
1. `kill 2908180 2908182 2891257 2930856` — 杀掉所有卡住的 claude 进程
2. 修 `~/cc_ps/cc2_repair_self/.claude/settings.json`:
   - `ANTHROPIC_BASE_URL`: `http://127.0.0.1:40001` → `http://127.0.0.1:4101`
   - `ANTHROPIC_API_KEY`: `sk-litellm-local` → `cc4101-token`
   - 备份为 `settings.json.bak.R-legacy-40001-stray`
3. `systemctl --user restart cloudcli-webui.service` — 重启 webui
4. `docker compose stop legacy_cc_1 legacy_ms_litellm` — 停掉 legacy 容器, 根除陷阱

### 验证
- cc2-resume 新 claude (PID 2935829) `ss -tnp`: `ESTAB 127.0.0.1:4101` ✅
- cc4101 日志从 20:50:39 恢复: `model=glm5.2_cc→glm5_2_nv cc_stream=True` ✅
- nv_requests 表: 4 条新 `caller=cc4101-primary` 行 ✅
- legacy_cc_1 已停止 ✅

## 三、系统性预防

### 3.1 legacy 容器已停
40001/41001 端口已关闭。即使配置错误也连不上, fail-fast。

### 3.2 配置漂移检测 (建议后续)
在 `cc2_resume.sh` 开头加 settings.json BASE_URL 校验:
```bash
BASE_URL=$(python3 -c "import json; print(json.load(open('$HOME/cc_ps/cc2_repair_self/.claude/settings.json'))['env']['ANTHROPIC_BASE_URL'])")
if [[ "$BASE_URL" != *"4101"* ]]; then
  echo "[ALERT] settings.json BASE_URL=$BASE_URL, expected 4101!"
fi
```

### 3.3 webui 绝对超时 (建议后续)
当前 watchdog 只看 idle timeout, 不看 wall-clock。一个 10min timeout 的 Bash 命令可以让
session 卡 10min+。建议在 webui 层面加绝对超时 (如 30min)。

## 四、参数变化

| 参数 | 修复前 (错误) | 修复后 |
|---|---|---|
| cc2 settings.json ANTHROPIC_BASE_URL | http://127.0.0.1:40001 | http://127.0.0.1:4101 |
| cc2 settings.json ANTHROPIC_API_KEY | sk-litellm-local | cc4101-token |
| legacy_cc_1 (40001) | Up (running) | Exited |
| legacy_ms_litellm (41001) | Up (running) | Exited |
