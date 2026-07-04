# R700: HM2 cloudcli webui (3001) 修复 — cc4101 容器恢复 + legacy 链路两处 bug

**日期**: 2026-07-04 / 2026-07-05
**主机**: HM2 (opc2_uname @ 100.109.57.26)
**触发**: 用户报告"远程 cc 的 webui(cloudcli) 能打开 http://100.109.57.26:3001/ 但不回复"

## 现象

cloudcli (3001) HTTP 200 能加载页面, 但用户消息无回复. claude-agent-sdk 报:
```
SDK query error: ReferenceError: Claude Code native binary at ... failed to launch
```
后续 binary 能 launch, 但 `claude -p` 返回空, SDK 日志显示 `api_retry ×7, error:"unknown", error_status:null`.

## 根因定位链

1. cloudcli .env: `ANTHROPIC_BASE_URL=http://127.0.0.1:40000` (dispatcher), `CLAUDE_CLI_PATH=.../claude`
2. 但 `~/.claude/settings.json` 覆盖: `ANTHROPIC_BASE_URL=http://127.0.0.1:4101`, `ANTHROPIC_API_KEY=cc4101-token`, `model=cc-glm5-2`
3. **4101 端口无监听** — cc4101 容器在 R699 BUG-7 被我误判为 orphan 删除
4. cc4101 实际是 cloudcli 专用网关 (PROXY_ROLE=cc4101), 把 `cc-glm5-2` 请求路由到 nv_gw(主) / ms_gw(备)
5. 删 cc4101 → claude binary 连不上 4101 → SDK 重试 7 次 → 静默失败 → webui 无回复

**这是 R699 BUG-7 的误判后果**. cc4101 不在当前 docker-compose.yml, 但 `~/.claude/settings.json` 仍指向它, 说明它是被前序 round 从 compose 移除但 settings 未同步, 容器靠旧 compose 起的残留实例存活, 我删除后彻底断了.

## 修复

### FIX-1: 恢复 cc4101 service 到 docker-compose.yml
- 从 `docker-compose.yml.bak.R694` 提取 cc4101 service 定义 (完整, 含 healthcheck/volumes/ports)
- 用 python yaml 合并到当前 compose, 插在 nv_gw 之后
- `docker compose up -d cc4101` → healthy
- `curl 127.0.0.1:4101/health` → `{"status":"ok","proxy_role":"cc4101","primary":"glm5_2_nv","fallback":"glm5_2_ms"}` ✅

### FIX-2: legacy_ms_litellm strip stream_options (legacy 链路潜在 bug)
- **数据**: 直接调 `legacy_ms_litellm:4000` v2k1 无 stream_options → reasoning 349 + content "Hello" ✅; 加 `stream_options:{include_usage:true}` → RemoteDisconnected ❌
- **根因**: ModelScope GLM-5.2 API 不支持 stream_options 字段, 收到即断连
- **影响**: legacy_cc_2 converters.py:300 对所有请求加 `stream_options:{include_usage:true}`, 导致 cc 链路 (40001/40005 → legacy_ms_litellm) 大量 RemoteDisconnected, 偶尔连上的也空响应
- **修复**: `/opt/cc-infra/proxy/legacy-ms-gateway/gateway/upstream.py` `call_modelscope()` 在 `body = dict(oai_body)` 后 strip `stream_options`:
  ```python
  if "stream_options" in body:
      del body["stream_options"]
  ```
- **部署**: 源文件改 + `docker cp` 进容器 + restart (容器非 bind-mount)
- **注**: 这个 bug 在 cc4101 恢复后不会触发 (cc4101 走 nv_gw/ms_gw, 不经 legacy_ms_litellm), 但 legacy 链路 (40000→40005→legacy_ms_litellm) 仍有, 修了以绝后患

### FIX-3: legacy_cc_2 stream.py thinking signature 空值 (legacy 链路潜在 bug)
- **根因**: `stream.py:222` `"signature": os.environ.get("THINKING_SIGNATURE", "")` 用空默认值, 而 collect_stream (line 481) 用 `THINKING_SIGNATURE_DEFAULT`. 不一致
- **影响**: stream 路径 (claude SDK 默认流式) 发的 thinking block 无 signature, Claude SDK 可能静默丢弃
- **修复**: line 222 改 `os.environ.get("THINKING_SIGNATURE", THINKING_SIGNATURE_DEFAULT)` 对齐 collect_stream
- **部署**: 源文件改 + `docker cp` + restart legacy_cc_2 (首次部署时 python 注释把 `}` 吃进注释导致 SyntaxError 崩溃循环, 修正注释位置后恢复)

## 验证

| 项 | 方法 | 结果 |
|---|---|---|
| cc4101 health | `curl 127.0.0.1:4101/health` | `{"proxy_role":"cc4101",...}` ✅ |
| claude -p (默认 settings→cc4101) | `claude -p "reply hello" --output-format=text` | 输出 "hello" ✅ |
| cloudcli /api/agent | `curl -X POST :3001/api/agent -d '{"message":"reply hello","provider":"claude","projectPath":"/home/opc2_uname"}'` | SSE `{"kind":"text","role":"assistant","content":"hello"}` ✅ |
| legacy 链路 /v1/messages 非流式 | `curl :40005/v1/messages` | `content:[thinking,text] text:"hello"` ✅ |
| legacy 链路 /v1/messages 流式 | `curl -sN :40005/v1/messages` | `content_block_start thinking + thinking_delta + text_delta` ✅ |
| webui 加载 | `curl :3001/` | HTTP 200 ✅ |

## 修改文件清单

| 文件 | 位置 | 改动 |
|---|---|---|
| `docker-compose.yml` | `/opt/cc-infra/` (HM2) | 加回 cc4101 service (从 R694 backup 恢复, 插在 nv_gw 后) |
| `proxy/legacy-ms-gateway/gateway/upstream.py` | `/opt/cc-infra/` (HM2) | `call_modelscope()` strip `stream_options` (R699 backup) |
| `proxy/legacy-cc/gateway/stream.py` | `/opt/cc-infra/` (HM2) | line 222 thinking signature 用 THINKING_SIGNATURE_DEFAULT (R699 backup) |

## 部署 artifacts

`deploy_artifacts/R700_hm2_cloudcli_cc4101_restore/`:
- `legacy-ms-gateway_upstream.py` (含 stream_options strip)
- `legacy-cc_stream.py` (含 signature 修复)

cc4101 的完整 service 定义在 `docker-compose.yml` 里, 不单独存 artifact.

## 教训

- **"orphan 容器" 判断不能只看 compose 是否有定义, 还要看是否有 config (settings.json/.env) 指向它**. R699 BUG-7 我只查 compose 和 grep 源码引用, 没查 `~/.claude/settings.json` / `~/.cloudcli/.env`, 误删了 cloudcli 的实际后端.
- 删容器前应 `grep -rn <container_name/port> ~/.claude ~/.cloudcli ~/.hermes ~/.openclaw ~/.config/opencode` 确认无 agent config 引用.

## 后续

- HM2 的 `~/.claude/settings.json` 指向 cc4101 (4101), cloudcli .env 指向 40000. 两处不一致但都工作 (cc4101 是 claude binary 实际后端, 40000 是 cloudcli .env 的 fallback). 暂不动.
- R699 BUG-7 的 "cc4101 orphan" 结论**废止**, 本 round 已恢复. memory 需更新.
