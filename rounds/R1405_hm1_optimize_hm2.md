# R1405: HM1→HM2 — FIX nv_gw zombie error chunk finish_reason content_filter→timeout (触发 openclaw fallback)

## 1. 触发分析
- 用户报 "API Error: Server error mid-response. The response above may be incomplete." (openclaw 流式中途断)
- 深挖根因: 非瞬时, 是 gateway↔openclaw 契约缺陷. 真实可修故障 (代码级, R569 授权架构改动).

## 2. 改前数据 (2026-07-15 ~09:03 UTC, HM1)

### 现象
- nv_gw 日志 09:03:40: `[NV-ZOMBIE-EMPTY] (glm5_2_nv) finish_reason=stop but content_chars=49 < 50, input_chars=206887 >= 5000, no tool_calls — aborting stream`
- `[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk to openclaw, should trigger fallback`
- openclaw journal 09:03:40: `embedded run agent end: isError=true model=glm5_2_nv provider=nv_gw error=LLM request failed. rawError=Provider finish_reason: content_filter`
- DB: nv_requests 09:03:30 status=502 error_type=zombie_empty_completion finish_reason=stop input_chars=206887
- **关键**: openclaw isError=true 直接结束, **未 fallback** (没有 fallback_model 决策, 没有 ms_gw/dsv4p_nv 流量)

### 根因 (openclaw 源码逐行追踪 /usr/lib/node_modules/openclaw/dist/)
1. nv_gw 发 SSE chunk `{"choices":[{"delta":{},"finish_reason":"content_filter"}]}` + `[DONE]`
2. openclaw `mapOpenAIStopReason("content_filter")` → `{stopReason:"error", errorMessage:"Provider finish_reason: content_filter"}` (openai-completions-DTj6G8AI.js:351)
3. openclaw `classifyAssistantFailoverReason` → `failoverReasonFromClassification(classifyFailoverSignal(...))`
4. `classifyFailoverClassificationFromMessage("Provider finish_reason: content_filter")` (errors-C4-qHiKh.js:634): 该消息 **不匹配任何 pattern** — 无 HTTP status, 无 rate_limit/timeout/server_error/overloaded/auth 关键词 → 返回 `null`
5. → `failoverReason=null` → `isFailoverAssistantError(msg)=classifyAssistantFailoverReason(msg)!==null` = **false** (errors-C4-qHiKh.js:915)
6. → `failoverFailure=false` (embedded-agent-Cv8lGIPa.js:3873)
7. `shouldRetrySilentErrorAssistantTurn` = false (assistantTexts.length>0, 已转发 49 chars) (selection-CVIPXpKT.js:2474)
8. `resolveRunFailoverDecision`: `shouldRotateAssistant = !aborted && failoverFailure(false) || timeoutFailure(false)` = **false** → `return {action:"continue_normal"}` (embedded-agent-Cv8lGIPa.js:723,743)
9. continue_normal → run 以 isError=true 结束 → 用户见 "Server error mid-response"

**R840 假设错误**: 原注释称 "content_filter → mapOpenAIStopReason→error→throw → runFallbackCandidate catch → coerceToFailoverError → fallback 链生效". 实际 openclaw 不把 unclassified stopReason=error 当 failover failure, 走 continue_normal. R1206..R1404 连续 NOP 均判 "Gateway detection+error-chunk correct" — 只看了 gateway 侧日志 (NV-ZOMBIE-ERROR-CHUNK 已发 ✓), 未看 openclaw 侧结果 (isError=true 无 fallback).

## 3. 修改 (只改 HM1 nv_gw, 源码)

**handlers.py:848 zombie error chunk `finish_reason` content_filter → timeout**
- 备份: `handlers.py.bak.R1397`
- 改前: `data: {"choices":[{"index":0,"delta":{},"finish_reason":"content_filter"}]}\n\n`
- 改后: `data: {"choices":[{"index":0,"delta":{},"finish_reason":"timeout"}]}\n\n`
- 日志行同步改 (NV-ZOMBIE-ERROR-CHUNK 描述)

**根因验证 (为何 timeout 能触发 fallback)**:
- `mapOpenAIStopReason("timeout")` → `{stopReason:"error", errorMessage:"Provider finish_reason: timeout"}`
- `classifyFailoverClassificationFromMessage("Provider finish_reason: timeout")` 命中 `ERROR_PATTERNS.timeout` 的 "timeout" 子串 (sanitize-user-facing-text-CRgdQ8Wr.js:209) → `toReasonClassification("timeout")`
- → `failoverReason="timeout"` → `isFailoverAssistantError=true` → `failoverFailure=true`
- `shouldRotateAssistant`: harnessOwnsTransport = (agentHarness.id!=="openclaw") = false (embedded-agent:2323), 故 timeout 的 harnessOwnsTransport 特例 (embedded-agent:726) 不阻断 → `return !aborted && failoverFailure(true) || timeoutFailure` = **true**
- → `assistantShouldRotate=true && fallbackConfigured=true` → `action:"fallback_model"` (embedded-agent:787)
- → `handleAssistantFailover` 返回 `{action:"throw", error: new FailoverError(reason:"timeout")}` (embedded-agent:952) → 外层 model fallback 链生效 → 切 ms_gw/glm5_2_ms 或 nv_gw/dsv4p_nv

**未改**: 所有 nv_gw 调优参数 (UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, KEY_COOLDOWN_S=25 等) 不变. compose md5 不变.

## 4. 改后验证
- `docker restart nv_gw` → Up healthy, /health ok
- 容器内 handlers.py: `finish_reason":"timeout"` ×1, `finish_reason":"content_filter"` ×0 (live)
- 无法主动构造 zombie (需 ~200K input_chars 的 NVCF content-filter 触发, 非 agent 真实上下文难复现) → 依赖生产流量观察
- fallback 链: openclaw fallbacks=['ms_gw/glm5_2_ms','nv_gw/dsv4p_nv']. ms_gw/glm5_2_ms 当前 choices_null (另案), nv_gw/dsv4p_nv pexec 可用
- 监控: openclaw journal 等待下一次自然 zombie, 预期见 `fallback_model` 决策 + fallback 模型流量 (而非 isError=true 直报错)

## 5. 判定
- 真实可修故障: openclaw "Server error mid-response" 根因 = nv_gw zombie error chunk 用了 openclaw 不可分类的 finish_reason=content_filter. 改为 timeout 使 openclaw 判 failoverReason=timeout → 触发 model fallback.
- 单点源码修改, 零参数变更. 铁律: 只改HM1不改HM2 (本轮改 HM1 nv_gw handlers.py).

## 6. 回合链
R1133→R1405: 本轮打破 NOP 链 — 深挖定位 openclaw "Server error mid-response" 根因 (gateway↔openclaw 契约: content_filter 不可分类 → 无 fallback). 修复: zombie error chunk finish_reason content_filter→timeout.
Remote main was at R1404 (7dba3ea). HM1 git at R1206. 提交经 HM2 仓库 (HM1 无法直连 github).
## ⏳ 轮到HM2优化HM1
