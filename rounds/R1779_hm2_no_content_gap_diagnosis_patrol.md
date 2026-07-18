# R1779 — HM2 cc2 诊断巡检轮：不改代码，确认 R1774 burn-in + 锁定 no_content_gap 优化候选

> 铁律：只改 HM2，不改 HM1。本轮性质 = 诊断巡检，不改任何代码。
> 依据：STATE(R1776) 指示"下轮拉数据凑够 ≥30 req 真实 burn-in 态，确认请求级 SR 持续 ≥95%，
> 看 cc4101 breaker 是否在失败密度够时正确 OPEN/恢复，看 tier SSLEOFError 是否仍被 failover 全吸收"。

## 一、数据（2026-07-18 16:14 CST 拉，UTC 08:14）

### 1. 总览窗
| 窗 | total | ok(200) | fail | SR |
|----|-------|---------|------|----|
| 30min | 22 | 20 | 2 | 90.9% |
| 32min 纯净(排除15:34-15:38重启churn) | 25 | 22 | 3 | 88.0% |
| 120min | 179 | 157 | 21 | 87.7% |
| 近18min(15:57-16:14) | 32 | 29 | 3 | 90.6% |

**SR 仍在 88-91% 区间，未爬到 ≥95% 目标。** R1774 burn-in 已 41min（nv_gw Up 41min），仍未达 95%。

### 2. 失败分类（近 18min 3 条，按 db status=502）
| ts(UTC) | error_type | fallback_occurred | fallback_to | ttfb_ms | duration_ms |
|---------|-----------|----|------|---------|---------|
| 08:00:28 | stream_no_content_gap | **f** | — | 67123 | **194499** |
| 08:04:48 | stream_no_content_gap | **f** | — | 66258 | **210629** |
| 08:10:12 | stream_first_byte_timeout | **t** | glm5_2_ms | (空) | 65365 |

**关键区分**：
- **2 条 `stream_no_content_gap` 真请求级挂死**：fb=f（**没触发 ms fallback**），duration 194s / 210s（**超 TIER_TIMEOUT_BUDGET_S=180 与 UPSTREAM_TIMEOUT=66，流式阶段未受总预算约束**），用户真没拿到内容。
- **1 条 `stream_first_byte_timeout` 被 peek→ms fallback 救回**：fb=t，fallback_to=glm5_2_ms，nv_gw 侧 db 记 502（peek 失败信号）但实际 NV-MS-FB-OK 成功转发 ms 流（日志 16:11:17 NV-MS-FB-OK + NV-PEEK-MS-OK）。**用户实际拿到 ms 内容，但 db 记 502 + cc4101 看到 api_error SSE 触发 CC4101-UPSTREAM-ERROR-SEEN**（记账/状态机次优，但用户视角有内容）。

### 3. fallback 率（cc4101 30min）
- cc4101 `15:59:03` START fallback ms_gw（breaker-OPEN triggered，60min 日志边界最早一条，OPEN 触发更早）
- `16:11:17` CC4101-UPSTREAM-ERROR-SEEN（passthrough detected nv_gw api_error SSE, ttfb=65386ms）→ breaker failure 计数 +1
- 30min fallback 事件计数 = 1（08:10:12 那条 ms 救援）

### 4. nv_gw breaker 轨迹（60min）
- `16:03:43` NV-ANTH-BREAKER-FAIL no_content_gap → state=('CLOSED',1,0) req=ddb742e2
- `16:08:19` NV-ANTH-BREAKER-FAIL no_content_gap → state=('CLOSED',2,0) req=8aba7394
- `16:11:14` NV-PEEK-SOFTFAIL stream_first_byte_timeout after 62569ms → attempting ms_gw fallback req=0531b93c
- `16:11:17` NV-MS-FB-OK ms_gw fallback success after 2794ms req=0531b93c
- `16:11:17` NV-ANTH-BREAKER-FAIL stream_first_byte_timeout → state=('CLOSED',2,0) req=0531b93c（**未递增到 3，跨 300s 窗重置或同 req dedup**）

**nv_gw 自身 breaker 未 OPEN**（count 卡在 2，未到 NVU_MS_FALLBACK_FAIL_THRESHOLD=5）——符合"失败密度不够 5/300s 不 OPEN"设计。

### 5. R1774 三层修复持续有效性
- **修复 A（wire graceful end）**：60min SSE 病根日志零复现 ✓
- **修复 B（breaker 时间窗）**：cc4101 breaker 真触发过 UPSTREAM-ERROR-SEEN（非永 CLOSED，时间窗语义在）✓；nv_gw breaker 失败密度低未 OPEN 属正常 ✓
- **修复 C（stall 观测）**：60min STREAM-STALL-FAIL/UPSTREAM-ERROR-SEEN 仅 1 条（16:11 那条）——失败密度低未触发属正常 ✓

### 6. 健康
- nv_gw /health ok（passthrough, 5 keys, glm5_2_nv in tiers）
- docker ps：nv_gw Up 41min, cc4101 Up 12min, ms_gw Up 28h, logs_db Up 39h
- tier 级 30min：integrate_success×14, pexec_success×6, pexec_empty_200×2, IntegrateTimeout×1（全被 tier failover 吸收，请求级 200）

## 二、诊断结论 — 锁定 no_content_gap 为 nv_gw 侧优化候选（本轮不动手）

### 失败模式归因
3 条失败**全是上游 NVCF 偶发**（连接级 SSL 流断 / 首 62-67s 不出字节），非 nv_gw 代码 bug。但**nv_gw 对两类失败的处理不对称**：

| 失败类型 | 处理路径 | ms fallback? | 用户结果 |
|---------|---------|------|---------|
| stream_first_byte_timeout | peek path (handlers.py ~1027) | **是，直接重放 ms** | 拿到 ms 内容（db 记 502 次优） |
| stream_no_content_gap | anth mid-stream (handlers.py ~1310) | **否，只 record nv_breaker** | 真挂死（194/210s） |

### 候选优化点（待评估，本轮不改）
**让 anth mid-stream `stream_no_content_gap` 也尝试 ms fallback 重放**（像 peek path 那样），救回当前请求。

### 为何本轮不改（铁律小步快走 + 设计冲突需谨慎）
1. **R1719 设计意图明确反对重放**：handlers.py 1300 行注释 — "Current req 200 already sent still interrupts (CC reports mid-response), but subsequent same-class reqs no longer go nv"。即**当前请求认了中断（已有部分 content emit，重放会重复内容），只靠 breaker 累积保护后续请求**。重放 no_content_gap 请求 = 给用户吐重复 content，可能比直接中断更糟。**这是设计权衡点，不是明显 bug**。
2. **样本太薄**：no_content_gap 当前只 2 条样本（18min），不足以支撑改这个有设计冲突的逻辑。
3. **更根本的疑点**：db 显示 no_content_gap 请求 duration 194/210s，**疑似流式阶段未受 TIER_TIMEOUT_BUDGET_S=180 约束**（_no_content_gap_s 是 per-gap 90s，多个 gap 累加才超 180）。若真如此，更小的改是**让 stream 总预算也 cap 在 180s 强制 fail→502（不重放，但更早释放 + 早给用户明确失败）**，而非重放 ms。需先在 handlers.py 1622 行附近确认 budget 是否对流式生效。
4. R1774 burn-in 仅 41min，叠加 handlers.py 改动违反"不污染 R1774 观测"。
5. R1770 已否决 timeout 微调，本轮 no_content_gap 的 budget 问题属不同维度，需独立数据支撑，不冲突但也不急。

## 三、本轮改动
**无。** 诊断巡检轮，不改任何代码/env，不 restart nv_gw。

## 四、下一轮（R1780）建议
1. **拉数据攒 no_content_gap 样本**（目标再 30-60min，凑 ≥5 条 no_content_gap）：
   - 确认 no_content_gap duration 是否稳定 >180s（即流式 budget 未生效）
   - 若稳定超 180s → 确认是 nv_gw 侧可调点，**优先级**高于重放 ms
2. **handlers.py 1622 行附近精读**：确认 stream 阶段是否有总 budget 检查；若无，候选改 = 加一个 `if time.time()-t_start > TIER_TIMEOUT_BUDGET_S: break+502`（不重放，早释放，早给失败）。这是**比重放 ms 更小步、更安全**的改法。
3. **若 SR 持续 <93% 且 no_content_gap 是主因** → R1780 在 handlers.py 加 stream 总 budget cap（cp .bak.R1780, 改一处, restart, 验证）
4. **若 SR 回升 ≥95%** → R1774 正式宣告成功，转纯巡检
5. 别碰 ms_gw，别碰 HM1

## 五、参数快照（本轮未变，R1774 部署后无漂移）
```
TIER_TIMEOUT_BUDGET_S=180  UPSTREAM_TIMEOUT=66  MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25  TIER_COOLDOWN_S=25  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
NVU_MS_FALLBACK_ENABLED=1  NVU_MS_FALLBACK_FAIL_THRESHOLD=5
NVU_MS_FALLBACK_SKIP_S=30  NVU_MS_FALLBACK_MODEL=glm5_2_ms
NVU_MS_FALLBACK_TIMEOUT=120
NVU_BREAKER_WINDOW_S=300  (源码默认, env 未覆盖)
CC4101_PRIMARY_FAIL_THRESHOLD=3  CC4101_PRIMARY_SKIP_S=30
CC4101_BREAKER_WINDOW_S=300  PRIMARY_HEADER_TIMEOUT=60
```

铁律：只改 HM2，不改 HM1。
