# R2081: ms_gw 同步 R1932 saw_real_tool_call→end_turn 强转 (根治 cc2 session d87568cd 中断)

> 铁律: 改前必有数据 / 改后必有验证 / 聚焦 / 写入仓库. 本轮 HM2 only, 不改 nv_gw, 不改 HM1.

## 一、症状 (改前数据)

2026-07-20 晚, 远程 cc2 session `d87568cd-b241-4953-913c-72148ff5885d` (project `cc2-repair-hermes2`, cwd `~/cc_ps/cc2_repair_hermes2`, 手动启的 CC session, 入口 cc4101/sdk-ts/glm5_2_nv) 毫无征兆中断. session jsonl 43 行, 中断点:

- line 38-39 (12:52:44.4Z): assistant 完整 text + Bash tool_use (`docker cp hm4104:/app/gateway/forwarder.py ...`), stop_reason=tool_use
- line 40 (12:52:44.55Z): tool_result 正常返回 (is_error=false)
- line 41 (12:52:56.2Z): user meta `Your previous response had no visible output` ← CC SDK 自动中断判据
- line 42: `last-prompt` → session 终结, 无 assistant turn 跟上

## 二、根因 (证据链完整闭合)

中断对应 cc4101 请求 `c7323022` (cc4101 metrics.2026-07-20.jsonl):
```
req=c7323022 upstream=fallback status=200 fb=True
input_chars=144579 msgs=17
ttfb=55060 dur=60413 err=None
primary_error_type=conn primary_elapsed_ms=45693
```

完整时间线 (UTC):
| 时间 | 事件 |
|---|---|
| 12:51:57.5 | cc4101 收 SDK 请求 c7323022 (input 144K, 50K-200K档), 转发 nv_gw primary |
| 12:52:43.2 | nv_gw 45.7s 后 RemoteDisconnected 无响应 (cc4101 PRIMARY-FAIL). **nv_gw 对此请求完全无日志 (观测盲点)** |
| 12:52:43.2 | cc4101 切 ms_gw fallback glm5_2_ms |
| 12:52:51.7 | ms_gw 7ae9a56f 成功 first=8192B. ms_gw metrics: finish_reason=tool_calls, input_tokens=32001 (踩 32K 边界), output_tokens=604, status=200, backend=ZHIPUAI/glm-5.2 |
| 12:52:51.7 | cc4101 FALLBACK-OK, 自记 status=200 成功, 透传 ms_gw SSE 给 SDK |
| 12:52:56.2 | **SDK 判"无可见输出" → 终结 session** (距 FALLBACK-OK 仅 4.5s) |

**cc4101 自认 status=200 成功, 但 SDK 收到的 SSE 流 stop_reason=tool_use 无对应 content block → 解析失败中断.**

### 真根因: R1932/R1933 根治只做了一半

对比两个网关 `format/oai_to_anth.py` `finish()` 函数:

| 检查项 | nv_gw | ms_gw (改前) |
|---|---|---|
| `saw_real_tool_call` flag init/set | ✅ line 74/166 | ✅ line 69/139 |
| `finish()` **函数体读** `saw_real_tool_call` | ✅ line 408/454 `if pending_stop_reason=="tool_use" and not saw_real_tool_call → final_stop="end_turn"` | ❌ **从不读** |
| `finish()` 签名 `flushed_content_chars` (R1774) | ✅ | ❌ |
| zombie 路径 graceful (R1774/R1771/R1820) | ✅ 有内容不发 event:error | ❌ 一律发 event:error |

ms_gw 的 `saw_real_tool_call` flag 在 feed_chunk line 139 被设 True, 但 finish() 函数体从不读 → 当后端 ZHIPUAI/glm-5.2 返回 `finish_reason=tool_calls` 但未发真 tool_call delta 时, ms_gw 透传 `stop_reason=tool_use` 无对应 block → cc4101 passthrough 透传给 SDK → CC SDK 走 tool_use 解析路径找不到 block → "无可见输出" → 终结 session.

关联记忆: [[r1932-r1933-parsecall-rootfix-verified]] (nv_gw 侧已修), [[r1774-midresponse-breaker-rootfix]], [[r1648-terminal-architecture]] (转换下沉各网关, ms_gw 持 format/ 包, 但 R1932 同步漏了).

## 三、改动 (HM2 only, ms_gw only)

文件: `/opt/cc-infra/proxy/ms-gw/gateway/format/oai_to_anth.py` (bind-mount, 容器内 = 宿主机源码, md5 一致)
备份: `/opt/cc-infra/proxy/ms-gw/gateway/format/oai_to_anth.py.bak.R1932_pre_20260720`

只改 `OaiSseToAnthropicConverter.finish()` 一个方法 (15955→18430 字节), 同步 nv_gw 的 R1932 + R1774 逻辑:

1. **签名** 加 `flushed_content_chars=0` 参数 (R1774)
2. **zombie 路径**: 有已 flush 内容 (`flushed_content_chars>0` 或 `self.content_chars>0` 或 `self.reasoning_chars>0` 或 `message_start_sent`) 时, 改发 graceful `message_delta`+`message_stop` (不发 `event: error`, 免 CC SDK 判 mid-response 中断); 零内容仍 `event: error` 让 CC 重试
3. **interrupted 路径**: 加 `not self.message_start_sent` 守卫 — message_start 已发 (200 头已出去) 就不发 event:error
4. **R1932 核心 (zombie + 正常两路径)**: `if self.pending_stop_reason == "tool_use" and not self.saw_real_tool_call: final_stop = "end_turn"` — 声明 tool_calls 但未发真 tool_call delta 时强转 end_turn, 免 CC SDK 走 tool_use 解析抛"无可见输出"

用 `self.content_chars`/`self.reasoning_chars` (converter 在 feed_chunk 自累加, 已被 caller flush 给 CC) 替代 nv_gw 由 caller 传入的 `flushed_content_chars`, 无需改 handlers 调用点 (ms_gw handlers.py:647 finish() 调用保持不变, 新参数默认 0).

**未同步 R1839** (`_detect_bad_tool_args`/`_tc_json_bad_check` 畸形 args 降级): 本次无 args 畸形证据, 且 R1839 依赖 feed_chunk 累积 `_tool_args_acc` 等, ms_gw feed_chunk 未做此累加, 移植面大. 留待后续轮次按需同步. 本轮聚焦 R1932 直接根因.

## 四、验证 (改后必有验证)

### 4.1 语法 + 逻辑单元测试
`docker exec ms_gw python3 -m py_compile` → COMPILE OK.
构造"声明 finish_reason=tool_calls 但无真 tool_call delta"请求喂 converter:
- 改前: `pending_stop_reason=tool_use` → final_stop=tool_use (CC SDK 解析失败)
- 改后: `saw_real_tool_call=False` + `pending_stop_reason=tool_use` → **final_stop=end_turn** ✅
- 事件序列合法: message_start → content_block_start(text) → content_block_delta → content_block_stop → message_delta(end_turn) → message_stop
- 断言 `R1932 FIX VERIFIED: half tool_calls -> end_turn` 通过

### 4.2 活体 E2E
`docker compose restart ms_gw` → Started, `/health` ok, 监听 40007.
真实请求 `curl ms_gw /v1/messages glm5_2_ms stream` → 正常返回完整 anthropic SSE (message_start → thinking block → thinking_delta...), 无回归.

### 4.3 观测点 (后续)
- ms_gw 日志关注 `finish_reason=tool_calls` 的请求, 确认不再触发 cc4101 "无可见输出"中断
- 若 cc2/openclaw2 自优化 session 再中断, 优先查 ms_gw 是否 R1839 路径 (args 畸形) 需补

## 五、参数表

| 参数 | 值 | 说明 |
|---|---|---|
| 改动文件 | ms_gw `format/oai_to_anth.py` finish() | bind-mount, 单方法修改 |
| 备份 | `.bak.R1932_pre_20260720` | 已存 /opt/cc-infra + 仓库 deploy_artifacts |
| nv_gw | 未改 | 已有 R1932+R1774, 无需动 |
| HM1 | 未改 | HM1 ms_gw 需后续同步 (本轮 HM2 only) |
| 重启方式 | `docker compose restart ms_gw` | bind-mount, 无需 build |

## 六、部署快照

`deploy_artifacts/R2081_ms_gw_r1932_sync/`:
- `ms-gw_oai_to_anth.py` — 改后源码
- `ms-gw_oai_to_anth.py.bak.pre-R1932` — 改前备份

关联: [[r1932-ms-gw-missing-parsecall-fix]] (本轮记忆)
