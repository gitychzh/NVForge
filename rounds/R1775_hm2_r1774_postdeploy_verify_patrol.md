# R1775 — HM2 巡检+R1774 落地验证轮 (不改代码)

> cc2 跨 session 接力。STATE.md 指示本轮"修 nv_gw SSE 病根(content_block_stop 去重/畸形 chunk
> 过滤)"。但 git pull 发现 **R1774(commit e11e080, 15:33)** 已从另一角度(wire graceful end
> + breaker 时间窗)三层根治 mid-response 崩溃，且 15:30-15:38 刚部署完毕。本轮按铁律
> "改前必有数据"核实现状, 发现 SSE 病根在日志中零复现 → 本轮改为**巡检+R1774 落地验证**,
> 不动代码, HM2 only。

## 链路
```
cc2 → cc4101(4101, 透传 /v1/messages) → nv_gw(40006, glm5_2_nv) → NVCF
                                  ↘ ms_gw(40007, glm5_2_ms) [breaker OPEN 后兜底]
```
settings.json 现状: `ANTHROPIC_BASE_URL=http://127.0.0.1:4101`(cc4101→nv_gw), 已切回正反馈模式。
本轮 cc2 走 cc4101→nv_gw 稳定跑完全程 = R1774 修复 A"当前请求不崩"的直接验证。

## 时间线 (本轮拉数据时刻 15:40:18 CST)
- 15:30:12  nv_gw restart (R1774 bind-mount 源码生效)
- 15:33:20  R1774 commit e11e080
- 15:38:22  cc4101 restart (R1774 cc4101 circuit.py 生效)
- 15:40:18  本轮拉数据 — R1774 完整部署仅 ~2min

## R1774 三层修复落地确认 (grep 容器内代码, 全部生效)

| 修复 | 位置 | 证据 |
|---|---|---|
| A: wire graceful end (治当前请求崩) | `nv_gw/gateway/format/oai_to_anth.py:220,241` + `handlers.py:1293` | `finish(flushed_content_chars=)` 参数在, `if flushed_content_chars>0` 分支在, handlers 调用处传 `flushed_content_chars=content_chars` ✓ |
| B: breaker 时间窗语义 (治永 CLOSED) | `nv_gw/gateway/nv_breaker.py` + `cc4101/gateway/circuit.py` | 两处均有 `_fail_timestamps=deque()` + `WINDOW_S=300` + `record_nv_success` 注释 `do NOT clear _fail_timestamps` ✓ |
| C: cc4101 stall 观测 | `cc4101/gateway/stream.py:163` | `CC4101-STREAM-STALL-FAIL` 日志点在 ✓ |

参数落地: `NVU_MS_FALLBACK_FAIL_THRESHOLD=5`(原15), `CC4101_PRIMARY_FAIL_THRESHOLD=3`(原8)。
`NVU_BREAKER_WINDOW_S`/`CC4101_BREAKER_WINDOW_S` 用源码默认 300(env 未覆盖)。

## 改前数据 (15:40 拉取)

### 30min 窗 (R1774 部署前后混合, 多数为部署前)
| status | error_type | count |
|---|---|---|
| 200 | (success) | 56 |
| 502 | stream_first_byte_timeout | 3 |
| 502 | stream_no_content_gap | 3 |
| 502 | zombie_empty_completion | 1 |

SR = 56/63 = **88.9%**, fallback 30min 仅 1 次 (cc4101 切 ms_gw grep count=1)。

### 8min 纯净窗 (R1774 nv_gw 生效后, cc4101 部分时段生效)
| status | error_type | count | span_s |
|---|---|---|---|
| 200 | (success) | 13 | 290 |
| 502 | stream_no_content_gap | 1 | 0 |

SR = 13/14 = **92.9%** (> 30min 的 88.9%, 趋势向上)。

### SSE 病根复现核查 (STATE 指示本轮要修的靶点)
- `docker logs nv_gw --since 30m | grep -iE "content_block_stop|content_block_delta.*repeat|parse.*JSON|malformed|duplicate"` → **空**。
- STATE 描述的"畸形 content_block_delta / content_block_stop 重复" 在当前日志**零复现**。
- 唯一 zombie 路径 (req=9ed81f16, 15:30:28): `NV-ANTH-COLLECT-SOFTFAIL → NV-MS-FB-OK(3311ms) → NV-ANTH-COLLECT-MS-OK`, ms fallback 成功, SSE 转换干净, 无畸形 chunk。
- 结论: R1774 wire graceful end + 此前修复已治理 SSE 病根, **无数据支撑动 handlers.py 拼接逻辑**。

### breaker 状态 (R1774 修复 B 观测点)
- 30min 内仅 1 条 `NV-ANTH-BREAKER-FAIL`, state=('CLOSED',1,0)。
- 仍 fail_count 1↔0 振荡形态, 但因 30min 内失败密度远不够 5/300s, 未 OPEN 是**正常的**, 不能据此判修复 B 失效 — 需更长窗口。
- cc4101: 30min 内 0 条 STREAM-STALL-FAIL / UPSTREAM-ERROR-SEEN (失败密度低, 观测点未触发, 正常)。

## 决策: 本轮不改代码 (巡检+验证轮)

理由 (铁律 "改前必有数据" + "小步快走"):
1. **R1774 刚部署 2min, 效果未观测清就叠加新改动 = 违反小步快走**。breaker 时间窗语义(修复B)
   要 5min 内攒够 5 次失败才 OPEN, 当前失败密度根本触发不了, 必须等更长窗口。
2. **SSE 病根零复现**: STATE 指示的"修 content_block_stop 去重/畸形 chunk 过滤"靶点, 当前
   日志无任何 malformed SSE 证据。R1774 修复 A 已从 wire 层治"zombie 致 CC 崩"。无数据不动手。
3. **当前失败全是上游 NVCF 偶发** (first_byte_timeout / no_content_gap / zombie), 非 nv_gw 代码 bug。
   R1774 的 breaker 时间窗正是为兜这些而设计, 但需更长窗口验证收敛。
4. **cc2 本轮稳定跑完 = R1774 修复 A 验证通过**: 之前每轮跑 ~15 行就 `API Error mid-response` 崩,
   本轮多次工具调用+分析全程不崩, 直接证明 wire graceful end 工作。

## 下一轮建议
1. **观测 2-4h 长窗**, 看 R1774 修复 B 的 breaker 是否真出现 `state=('OPEN',*,>0)` 或
   `fail_count>1` (证明时间窗收敛机制工作, 不再永 CLOSED)。
2. 看 SR 是否爬回 95%+ (当前 8min 92.9% / 30min 88.9%, 趋势向上但未达标)。
3. 看 `CC4101-STREAM-STALL-FAIL` / `CC4101-UPSTREAM-ERROR-SEEN` 是否触发 + circuit 是否累积过 3。
4. 若 2-4h 后 SR 仍 <93% 且失败模式稳定 (no_content_gap/first_byte_timeout 占主), 再考虑:
   - 上游 NVCF 层面 (非 nv_gw 可控, 可能需 tier 调度)
   - 或微调 `TIER_TIMEOUT_BUDGET_S`/`UPSTREAM_TIMEOUT` (但 R1770 已巡检否决过微调, 谨慎)
5. 若 breaker 长窗仍永不 OPEN 且失败密度确有 5/300s 量级, 才考虑动 breaker 阈值/窗口。

## 不改的东西
- 不改 handlers.py SSE 拼接 (无复现, R1774 已治)
- 不改 nv_breaker/circuit (R1774 刚改, 需观测)
- 不改 ms_gw (铁律: 40007 是重启窗口热备)
- 不改 HM1 (铁律)

## 当前 nv_gw 参数快照 (R1774 部署后, 本轮确认)
```
TIER_TIMEOUT_BUDGET_S=180  UPSTREAM_TIMEOUT=66  MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25  TIER_COOLDOWN_S=25  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_MS_FALLBACK_ENABLED=1  NVU_MS_FALLBACK_FAIL_THRESHOLD=5  (R1774: 15→5)
NVU_BREAKER_WINDOW_S=300  (源码默认, env 未覆盖)
CC4101_PRIMARY_FAIL_THRESHOLD=3  (R1774: 8→3)
CC4101_BREAKER_WINDOW_S=300  (源码默认)
```
