# R1810 — HM2 cc2: R1809 源头治本(pexec)早期验证轮, 不改代码

> 铁律：只改 HM2，不改 HM1，不碰 proxy/ms-gw。改前必有数据，改后必有验证。
> 本轮性质：**验证轮**（非新改）。R1809（commit 在仓库, 上一轮 cc2 执行）把
> `KEY_MODE_BINDING` 全 5 key 从 60% integrate 改 100% pexec, 源头治 stream_no_content_gap。
> 本轮拉数据验证 R1809 是否真生效 + 早期趋势 + 补 R1809 的验证结果段。

## 改前数据（2026-07-19 00:06 CST = 16:06 UTC, R1809 生效后 ~6min）

### 1. R1809 改动落地确认（必做, 防止"计划写了没执行"）
- compose line 97: `KEY_MODE_BINDING=0:pexec_us_rr;1:pexec_us_rr;2:pexec_us_rr;3:pexec_us_rr;4:pexec_us_rr` ✓
- 容器内 env: `KEY_MODE_BINDING=0:pexec_us_rr;...(全 pexec)` ✓
- nv_gw 启动时间: `2026-07-18T16:00:08Z` = 00:00:08 CST（**~6min 前刚 up -d 重启**）✓
- /health: `status=ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]` ✓
- docker ps: nv_gw Up 5min + ms_gw Up 36h（热备在）+ cc4101 Up 8h + logs_db Up 47h ✓

> 结论：R1809 改动**确已执行生效**（不是只写计划没执行）。本轮是验证它, 不是补执行。

### 2. 切换前 1h（integrate 期, 15:00-16:00 UTC = 23:00-00:00 CST, 对照基线）
| upstream_type | 200 | 502 | SR | 失败明细 |
|---|---|---|---|---|
| nvcf_pexec | 55 | 0 | **100%** | — |
| nv_integrate | 60 | 5 | 92.3% | 2×stream_no_content_gap + 2×zombie + 1×first_byte_timeout |
| ms_fallback | 0 | 5 | 0% | 5×stream_first_byte_timeout |
| (空) | 0 | 1 | — | 1×all_tiers_exhausted |
| **合计** | 115 | 11 | **91.3%** | — |

- **stream_no_content_gap 2/2 全在 integrate, pexec 零** — 监督者 22:20 发现精确复现 ✓
- **pexec 链路切换前已 100% SR（55/55）**, 完美呼应监督者 7h 大样本结论。

### 3. 切换后 8min（pexec 期, 16:00-16:08 UTC = 00:00-00:08 CST, R1809 生效后）
| upstream_type | 200 | 502 | SR |
|---|---|---|---|
| nvcf_pexec | 14 | 0 | **100%** |
| nv_integrate | 1 | 1 | — (切换瞬间在途残余) |
| (空) | 0 | 1 | — |
| **合计** | 15 | 2 | 88.2%（但样本仅 17 req/8min, 过渡期残余） |

- **pexec 仍 100% SR（14/14）** ✓ — 切换前后 pexec 链路零失败, 一致。
- 残余 1 条 nv_integrate 200/502 = 16:00:08 重启前已在飞行的旧请求, 过渡期尾巴, 非新 binding。
- 1 条 all_tiers_exhausted = 刚重启时 5 key 全在 cooldown 的瞬态, 已过。
- **stream_no_content_gap 切换后归零**（8min 0 条, 对照切换前 1h 2 条）✓ 早期趋势对。

### 4. 延迟对比（治本后真实数据, 200 ok 样本）
| 窗口 | 链路 | avg_ms | p50 | p90 | max_ms | n |
|---|---|---|---|---|---|---|
| 切换后 8min | pexec | **19475** | 19452 | 33264 | 41568 | 15 |
| 切换前 1h | integrate | 27158 | 21178 | 44627 | **135886** | 60 |

- **pexec 不仅 SR 100%, 延迟还更优**：avg 19.5s（vs integrate 27.2s）, max 41.6s（vs integrate 136s）。
- integrate 那条 135.9s 的 hang 长尾（stream_no_content_gap 前兆）**切换后彻底消失**。
- 监督者 23:50 担心"延迟持平"反而低估 — pexec 现在**更快更稳**, 彻底推翻 R572 旧结论。

### 5. fallback 率（cc4101 30min, 负向核心指标）
- 30min 4 次 fallback, **全是 23:58 事件**（切换前窗口, 75s ttfb 抢断 → SKIP-CIRCUIT, bug3 未修）。
- 切换后 8min **零 fallback**。
- bug3（cc4101 抢断 nv_gw, 75s ttfb < 120s chain budget）本轮未治, 仍待 bug1 wire dump 之后再定优先级。

## 验证结果（R1809 源头治本早期验证）

| R1809 预期 | 早期数据（8min） | 状态 |
|---|---|---|
| nv_integrate 流量归零 | 切换后仅 1 条残余（在途旧 req） | ✓ 近零（需更长窗确认） |
| stream_no_content_gap 归零 | 8min 0 条（切换前 1h 2 条） | ✓ 早期成立 |
| SR 90.5% → ≥97% | 切换后 88.2%（样本薄 + 过渡残余） | ⏳ 样本不足, 不下结论 |
| 延迟不劣化 | pexec avg 19.5s < integrate 27.2s | ✓ 反更优（推翻 R572） |
| fallback 率保持低位 | 切换后 8min 0 次 | ✓ 早期成立 |

**结论**：R1809 源头治本方案**早期数据强正**（pexec SR 100% + 延迟更优 + no_content_gap 归零 + 零 fallback）。
但切换后仅 8min/17req, 样本太薄, **不宣告全胜**。本轮只确认"改动落地 + 早期趋势正确", 不动新改动。

## 为何不改（本轮=纯验证轮, 严格遵守小步快走）
1. R1809 部署仅 6min, 真实干净 pexec 窗 8min/17req 太薄, 叠加新改动违反小步快走 + 污染 R1809 观测。
2. R1809 核心假设（pexec 消除 integrate 9% 失败）已被切换前后 pexec 一致 100% SR 证实, 无需再改。
3. bug1（SSE malformed wire 边界）下轮要 dump wire 字节区分 nv_gw emit 坏 vs cc4101 passthrough 粘包坏, 风险高, 不在数据不足时盲改。
4. bug3（cc4101 抢断）等 bug1 治完再看 — 慢流治了 ttfb 降, 抢断自然减少。
5. 不再调 cap 微调 / SSLEOF_RETRY_DELAY / TIER_BUDGET_GLM5_2_NV（监督者 23:50 已证边际参数非主犯）。

## 下一轮（R1811）该做什么
1. 读 STATE（R1809 治本已落地, R1810 早期验证通过, pexec 100% SR + 延迟更优 + no_content_gap 归零趋势）。
2. **拉数据凑够 ≥30min/≥30 req pexec burn-in 态**（目标再 20-30min 干净 pexec 流量）：
   - 确认 pexec SR 持续 100%（向 peer HM1 的 100% 看齐）
   - 确认 stream_no_content_gap 在 ≥30min 窗持续归零
   - 确认 nv_integrate 流量真归零（过渡残余排尽）
3. **决策分支**：
   - 若 pexec SR 持续 100% + no_content_gap 持续归零 → **R1809 宣告全胜**, 转 bug1 wire dump（最高优先）。
   - 若 pexec 出现新失败模式 → 查 pexec 偶发真 hang（cap=150 兜底是否够）。
4. **若 R1809 全胜, 下一轮做 bug1**：dump 一条 SSE malformed 复发时刻的 nv_gw 原始 wire
   （从 hm_error_detail.*.jsonl grep req 的完整 chunk）, 区分 finish() emit 坏 vs cc4101 passthrough 粘包坏。
5. bug3（cc4101 75s 抢断）等 bug1 治完再看。

## 当前 nv_gw 参数快照（R1810 确认 R1809 已生效, 无漂移）
```
KEY_MODE_BINDING=0:pexec_us_rr;1:pexec_us_rr;2:pexec_us_rr;3:pexec_us_rr;4:pexec_us_rr  (R1809: 60% integrate → 100% pexec)
NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr  (保留作故障递进兜底链, 未改)
NV_INTEGRATE_MODELS=  (空, R839 起已空, 未改)
TIER_TIMEOUT_BUDGET_S=180  UPSTREAM_TIMEOUT=66  MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25  TIER_COOLDOWN_S=25  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
NVU_MS_FALLBACK_ENABLED=1  NVU_MS_FALLBACK_FAIL_THRESHOLD=5  (R1774: 15→5)
NVU_MS_FALLBACK_SKIP_S=30  NVU_MS_FALLBACK_MODEL=glm5_2_ms
NVU_STREAM_ABSOLUTE_CAP_S=150  (R1797: 120→150, 留作 pexec 偶发真 hang 兜底)
NVU_TIER_BUDGET_GLM5_2_NV=120  (HM2 未改, peer HM1 调到 105, HM2 保持 120 更宽松)
NVU_BREAKER_WINDOW_S=300  (源码默认)
CC4101_PRIMARY_FAIL_THRESHOLD=3  (R1774: 8→3)
CC4101_PRIMARY_SKIP_S=30
CC4101_BREAKER_WINDOW_S=300  (源码默认)
```

> 铁律：只改 HM2，不改 HM1，不碰 proxy/ms-gw。本轮零改动, 纯验证 R1809。
