# R1406: HM1→HM2 — R1405 验证闭环 (zombie error chunk content_filter→timeout 已生效)

## 1. 目的
R1405 把 nv_gw zombie error SSE chunk 的 finish_reason 从 content_filter 改为 timeout,
意图让 openclaw `classifyFailoverClassificationFromMessage` 命中 timeout pattern →
failoverReason=timeout → shouldRotateAssistant=true → action=fallback_model, 而非
continue_normal 直接 isError 报 "Server error mid-response"。本轮验证此修复在生产流量
上是否生效。**只验不改; 不动 ms_gw/openclaw (铁律 3 聚焦 nv_gw + openclaw agent-owned)。**

## 2. 改前/改后对照 (2026-07-15, HM1 nv_gw, 全部 zombie chunks)

时间分界: handlers.py edit mtime 09:41 CST (R1405 apply); 之前为 pre-edit, 之后为 post-edit。

| 窗口 | zombie chunks 总数 | finish_reason=content_filter | finish_reason=timeout |
|---|---|---|---|
| PRE-edit (00:03–09:03) | 11 | **11 (100%)** ← bug | 0 |
| POST-edit (10:03–12:35) | 9 | **0** | **9 (100%)** ← fixed |

pre-edit 11 条全发 content_filter (旧 R840 逻辑, 不触发 openclaw fallback);
post-edit 9 条全发 timeout (R1405 逻辑, 触发 openclaw fallback)。**gateway 侧行为修复确认。**

## 3. openclaw 侧结果 (journalctl, 09:41 CST 起 post-edit 窗口)

| 指标 | 计数 | 说明 |
|---|---|---|
| decision=fallback_model | 15 | R1405 生效 → openclaw 走 fallback 链 |
| "Server error mid-response" | **0** | 用户报的旧错误形态 **post-edit 已消失** |
| "All models failed (3)" | 5 | fallback 链 3 个模型全失败 |

post-edit 典型流 (12:33:31):
```
zombie(glm5_2_nv, input_chars=209899) → finish_reason=timeout chunk
→ openclaw agent end isError=true rawError="Provider finish_reason: timeout"
→ failover decision: fallback_model reason=timeout from=nv_gw/glm5_2_nv
→ model fallback: glm5_2_nv→ms_gw/glm5_2_ms→nv_gw/dsv4p_nv
→ "All models failed (3): ... timeout | ms_gw request timed out | timeout"
```

## 4. 结论

**R1405 修复目标达成**: openclaw 不再在首个 zombie 上 continue_normal 直报
"Server error mid-response", 而是正确走 fallback_model 链。旧错误形态 post-edit
窗口内计数为 0。此为 nv_gw 侧能做且已做对的事。

**残留 "All models failed" 不在 nv_gw 修复范围** (已确认, 不改):
1. `nv_gw/dsv4p_nv` fallback 带 **同一份 ~210K 字符 context** → NVCF 同一 content-filter
   再触发 zombie → 再 timeout。NV 模型间 fallback 对 input-size 驱动的 zombie 注定无效。
2. `ms_gw/glm5_2_ms` (唯一非-NVCF 出口) 当前坏: request timed out / LLM idle timeout
   120s / choices_null。修它越出 nv_gw 聚焦范围 (port 40007), 铁律 3 禁止; 且 openclaw
   fallback 顺序是 agent-owned (铁律: Do not change model selection/fallback logic)。

**根因归属**: zombie 本身由 NVCF 对 ~210K input_chars 的 content-filter 触发, 是
后端行为 + agent 大上下文驱动, 非 nv_gw 可配置项 (R1206+ 连续 NOP 已确认)。
R1405 的价值: 把一个"静默硬停、用户直接见 mid-response"的契约缺陷, 转成"正常
fallback 链路触发"; 至于链路末端的 ms_gw 健康度, 属另一层。

## 5. 改后验证清单
- [x] nv_gw /health ok, container healthy (Up, healthy)
- [x] handlers.py live: finish_reason=timeout ×1, content_filter ×0 (md5 381448c1 host==container)
- [x] post-edit 9/9 zombie chunks emit timeout (0 content_filter)
- [x] openclaw 15× fallback_model decisions post-edit
- [x] 0× "Server error mid-response" post-edit
- [x] 备份 handlers.py.bak.R1397 在位
- [x] R1405 已 commit+push (7eaee49)
- 不改 ms_gw, 不改 openclaw (铁律)

## 6. 参数状态 (零改动)
本轮无参数变更, 所有 knob 维持 floor/optimal。R1405 是纯代码契约修复 (handlers.py:848
finish_reason 值), 不涉及 knob 调参。

铁律: 只改HM1不改HM2
