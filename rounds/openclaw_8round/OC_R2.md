# OC-R2 (OpenClaw 8-Round Optimization) — 2026-07-01

## 流程
本轮起引入 cc2 反对者(HM2 claude 非交互 session)两轮审视:
- 第一轮: cc2 否决 A(改status code)/C(降budget), 选B(量化不动), 指出28min非重试造成, 杠杆在agent loop
- 第二轮: cc2 否决 D/E(调compaction timeout), 指出"在未量化杠杆上猜数值是赌", 要求先查清 durationMs 起算点

## OC-R2 全链路量化 (按 cc2 要求"量清 agent loop")
### 28min lane 完整还原 (feishu群 oc_0c8175e, runId=8477ff25)
```
00:31:37  resumed interrupted main session (lane 启动)
00:31:39  tool-result-truncation 21 results
00:42:58  stalled session (11min stall — lane 进展缓慢)
00:49:30  embedded run agent end + context overflow (attempt 1/3)
00:52:30  auto-compaction timed out (180s = compaction.timeoutSeconds 默认)
00:52:31  [context-overflow-recovery] Truncated 50 tool results; retrying prompt
00:52:31  → openclaw 日志此后 6.5min 无任何事件 (hang)
00:59:08  feishu 用户发 /new + /reset (改 session 文件)
00:59:45  EmbeddedAttemptSessionTakeoverError: session file changed → lane error durationMs=1687531
```

### 关键证据 (cc2 要求的三件)
1. **durationMs 起算点**: 1687531ms ≈ 28.1min = 00:31:37(lane resume)→ 00:59:45(lane error)。
   **28min 是 lane 全程时长, NOT takeover 后单独卡28min。** 假设1(cc2 提出)成立 → D/E(调 compaction timeout)打偏, 撤案。
2. **7min 缺口 (00:52:31→00:59:08)**: openclaw compaction 失败后 retry prompt, 但日志此后6.5min无事件 = **openclaw 内部 hang**。
   同期 hm40006 有39个请求(其他 caller, caller=None 因OC-R1前), 200成功, dur 4-100s, input_tokens 46K-63K。
   → openclaw 的 retry prompt 请求**未到达 hm40006**, hang 在 openclaw 内部 (compaction-retry 死锁/锁等待)。
3. **takeover 触发**: 用户 00:59:08 发 /new+/reset 改 session 文件, openclaw 检测到 session file changed → takeover error。
   是 openclaw 自生逻辑 (EmbeddedAttemptSessionTakeoverError), 非 hm40006/SNVCF。

### 根因 (最终)
28min 卡死 = openclaw agent loop 多因素叠加:
- NVCF 故障 + 大上下文(76K tokens) → 每轮 LLM 慢(30-100s)偶发502
- context overflow → compaction 调 hm40006 摘要, NVCF故障致 compaction 180s 超时
- compaction 失败后 retry prompt → **openclaw 内部 hang 6.5min** (未发出请求, 非 hm40006 问题)
- 用户中途 /new+/reset 改 session → takeover → lane 报错

**核心: openclaw 内部 compaction-retry 死锁是 6.5min hang 的直接原因, 这是 openclaw 自身 bug, 非 hm40006 参数可修。**

## 本轮改动: 无 (cc2 F — 不动数值, 仅量化)
OC-R1 已补 caller 字段。OC-R2 量化证据已足够指导后续。不改 hm40006/openclaw 任何参数。
(曾考虑 D 降 compaction.timeoutSeconds 180→60, 被 cc2 否决: 28min 非超时路径, 改了白改。)

## 验证
- openclaw 工作正常: `openclaw agent -m` 端到端回复正确 (OC-R1 验证 + 本轮多次 probe)
- NVCF 间歇故障期间 openclaw 成功率 50-60%, 恢复期 100%
- 28min 卡死是单次 compaction-retry hang + 用户操作触发的极端案例, 非 openclaw 不工作

## 下轮方向 (OC-R3 候选)
- 真正可改善的: openclaw 上下文过大(input 76K)是 compaction 触发源。降 openclaw 的 toolResultMaxChars / postCompactionMaxChars 可减少 compaction 频率 → 减少 hang 概率。
- 或: openclaw 的 midTurnPrecheck (默认 false) 可在工具循环中途提前检测上下文压力, 避免溢出到 compaction。
- 仍需 cc2 审视后再动。

## ⏳ 下一轮 OC-R3: 候选方向 — 降 openclaw 上下文/compaction 频率 (midTurnPrecheck 或 toolResultMaxChars), 经 cc2 审视后执行
