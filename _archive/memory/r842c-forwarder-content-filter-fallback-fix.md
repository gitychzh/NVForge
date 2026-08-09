---
name: r842c-forwarder-content-filter-fallback-fix
description: "opclaw4103 forwarder拦截content_filter SSE信号切ms_gw fallback,修R840 zombie后fallback断链,3/3成功"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

# R842c: opclaw4103 forwarder 拦截 content_filter 切 ms_gw fallback (方案2)

**日期**: 2026-07-11
**对象**: HM2 远程 opclaw4103 forwarder (/opt/cc-infra/proxy/cc-adapter/gateway/forwarder.py)
**状态**: 已应用+验证,3/3 成功

## 问题回顾

R840 在 nv_gw 检测空僵尸响应 → 发 `finish_reason=content_filter` SSE chunk 给 openclaw,期望"mapOpenAIStopReason→error→throw→fallback"。但 openclaw 源码分析确认这条链断了:

1. `mapOpenAIStopReason("content_filter")` → `{stopReason:"error", errorMessage:"Provider finish_reason: content_filter"}` (openai-completions-DTj6G8AI.js:351)
2. `classifyAssistantFailoverReason(msg)` 对 "Provider finish_reason: content_filter" **返回 null** (errors-C4-qHiKh.js:756) — 该文本不匹配任何已知 failover 模式(rate_limit/auth/timeout/server_error/context_overflow/overloaded 等)
3. `isFailoverAssistantError = false` (reason=null)
4. empty-error-retry 命中条件 `failoverReason ∈ {null, no_error_details, unclassified, unknown}` → **retry 同 provider 3 次**(embedded-agent-Cv8lGIPa.js:3889),不切 fallback model
5. `resolveRunFailoverDecision` 即使 fallbackConfigured=true,也需 `failoverFailure=true` 才 fallback_model → content_filter 永不 fallback

**结论:即使给 main agent 配 fallbacks,content_filter 也不触发 openclaw 层 model fallback。** 唯一可行路径 = 在 opclaw4103 层拦截。

## R842c 修复(2处改动,forwarder.py)

### 改动1: `_stream_from_upstream` 检测 content_filter 发信号
在无条件 `yield ("message", chunk_data)` 前,检测 `finish_reason == "content_filter"`:
```python
if fr == "content_filter":
    _log("CONTENT_FILTER_ZOMBIE", "primary 流中检测到 content_filter (R840 zombie), 切 ms_gw fallback")
    yield ("content_filter_zombie", None)  # 特殊信号
    return
yield ("message", chunk_data)
```
不透传 content_filter chunk 给 openclaw(避免其走 empty-error-retry 重试同 provider)。

### 改动2: `forward_stream` 捕获信号切 fallback
```python
else:
    content_filter_zombie = False
    for ev in _stream_from_upstream(resp, conn, FALLBACK_NOTICE, False):
        if ev[0] == "content_filter_zombie":
            content_filter_zombie = True
            break  # 中断 primary 流
        yield ev
    if content_filter_zombie:
        _log("PRIMARY-ZOMBIE-FALLBACK", "nv_gw 返回 content_filter zombie, 切 ms_gw fallback 流式")
        _circuit.record_primary_failure()
        # 落到下面的 fallback 流逻辑 (ms_gw 从头流式 + 插 notice)
    else:
        _circuit.record_primary_success()
        return
```

## 验证结果(3/3 成功)

实测 main agent (input_chars 100683-101907, 仍在死亡窗口 88-105k):
```
14:32:32 nv_gw:    [NV-ZOMBIE-EMPTY] content_chars=2 input=100843 → zombie
14:32:32 nv_gw:    [NV-ZOMBIE-ERROR-CHUNK] 发 content_filter SSE
14:32:32 opclaw4103: [CONTENT_FILTER_ZOMBIE] 检测到 → 切 fallback  ← R842c 新增
14:32:32 opclaw4103: [PRIMARY-ZOMBIE-FALLBACK] 切 ms_gw 流式        ← R842c 新增
14:32:32 ms_gw:    [MS-RR] glm5_2_ms 接管
14:32:38 opclaw4103: [FALLBACK-STREAM] 插 notice, 完成
结果: status=ok usage_total=24212 payload="⚠️ 已 fallback 到 glm5_2_ms... 好的"
```

**对比**:
- 修前: content_filter → openclaw retry 3 次同 provider → 全 zombie → LLM failed(27s, 飞书无回复)
- 修后: content_filter → opclaw4103 拦截 → 切 ms_gw → 成功回复(6s, 飞书收到"好的"+notice)

## 关键设计点

1. **不透传 content_filter chunk**: 避免 openclaw 走 empty-error-retry(对 content_filter 无效,只重试同 provider)
2. **已发的 content delta 不收回**: nv_gw zombie 时 content_chars<=50(实际2-3 chars 噪音),影响可忽略;切 fallback 后 ms_gw 完整回复接在后面
3. **插 notice**: opclaw4103 在 ms_gw 首 content delta 前插 "⚠️ primary 故障/超时, 已 fallback 到 glm5_2_ms" 提醒(已有机制复用)
4. **circuit 记录 primary failure**: 下次请求仍先试 primary(下一轮回 primary),不永久切走

## 时序细节

- nv_gw 逐 chunk 解析后再 write,检测 zombie 时 break **不 write 本 finish chunk**,但之前的 content delta chunks 已 write 给 opclaw4103
- opclaw4103 `_stream_from_upstream` 同样边读边 yield,检测到 content_filter 时之前的 content delta 已 yield 给 app.py → openclaw
- 所以 openclaw 收到: 少量 content delta(2-3 chars) + ms_gw 完整回复 + done(无 content_filter 终末信号)
- openclaw 正常处理,不触发 empty-error-retry,不 throw

## 部署

- 文件: `/opt/cc-infra/proxy/cc-adapter/gateway/forwarder.py` (bind mount 到容器 /app/gateway)
- 备份: `forwarder.py.bak.preR842c`
- 代码是 bind mount,改宿主机文件 + `docker restart opclaw4103` 即生效,无需 rebuild 镜像
- 8 处 `content_filter_zombie/CONTENT_FILTER_ZOMBIE/PRIMARY-ZOMBIE-FALLBACK` 引用确认落地

## 死亡窗口精确数据(修正之前粗分桶)

| input_chars | n | zombie | rate |
|---|---|---|---|
| <88k | 44 | 0 | 0% |
| 88-100k | 74 | 62 | 83.8% |
| 100-105k | 15 | 10 | 66.7% ← 仍死亡 |
| 105-110k | 25 | 0 | 0% ← 安全区 |
| 110k+ | 1 | 0 | 0% |

真正死亡窗口 = **88k-105k chars**,105k+ 才安全。main agent 当前 100-102k,仍在死亡窗口,但 R842c fallback 兜底成功。

关联: [[r842-88k-zombie-window-root-cause]]  [[r840-openclaw-zombie-empty-stall-fix]] [[r841b-openclaw-deep-fix]]
