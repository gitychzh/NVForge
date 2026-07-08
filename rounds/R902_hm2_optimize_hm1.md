# R902: HM2→HM1 — NOP (false trigger, 19th consecutive, no optimization space)

**Date**: 2026-07-09 00:20 UTC
**Role**: HM2 optimizing HM1
**Author**: opc2_uname

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
```

- 最新 commit author = opc2_uname (HM2): `R901: HM2→HM1 — NOP (false trigger, 18th consecutive)`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch #19)
- Symlink 已指向 R901，本轮创建 R902

**连续 false-trigger streak**: R884→R885→R886→R887→R888→R889→R890→R891→R892→R893→R894→R895→R896→R897→R898→R899→R900→R901→R902 (19 consecutive)

---

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态

| 容器 | 状态 |
|------|------|
| nv_gw | Up 3 hours (healthy) |
| ms_gw | Up 20 minutes (healthy) |
| logs_db | Up 4 days (healthy) |

### 2.2 nv_gw 日志 (最近100行 error/warn)

```
[21:31:23.8] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[21:34:22.1] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60619ms
[21:34:41.9] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[23:34:36.5] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60584ms
[23:34:49.1] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[23:35:51.9] [NV-CYCLE] tier=glm5_2_nv k4 → 504 (504_nv_gateway_timeout), cycling to next key
```

- 2 次 NV-TIER-FAIL: empty200 触发 fallback → dsv4p_nv 全部 fallback 成功
- 1 次 504_nv_gateway_timeout → key cycle
- 零 429、零 config 相关错误
- FALLBACK_GRAPH healthy: bidirectional working

### 2.3 ms_gw 日志 (最近50行 error/warn)

```
(no error/warn in ms_gw)
```

- R900 修改后 ms_gw 持续零错误，EMPTY_200_FASTBREAK_THRESHOLD=3 正常工作

### 2.4 DB 统计 (6h 窗口, nv_gw)

| 指标 | 值 |
|------|-----|
| 6h total | 63 |
| 6h OK | 62 |
| 6h fail | 1 |
| 6h SR | 98.4% |
| 6h avg TTFB | 28,038ms |
| 6h avg duration | 28,046ms (pexec) / 121,075ms (ATE) |
| Fallback count | 6 (all successful → dsv4p_nv) |

### 2.5 按模型统计 (nv_gw, 6h)

| Model | Total | OK | SR | Avg Duration |
|-------|-------|-----|-----|--------------|
| glm5_2_nv | 63 | 62 | 98.4% | 29,523ms |

- 仅 glm5_2_nv 有流量，dsv4p_nv 仅作为 fallback（6次成功）

### 2.6 1h 窗口 (nv_gw)

| 指标 | 值 |
|------|-----|
| 1h total | 4 |
| 1h OK | 4 |
| 1h SR | 100.0% |
| key_cycle_429s | 0 |

### 2.7 唯一 ATE 详情 (6h)

| Field | Value |
|-------|-------|
| error_type | all_tiers_exhausted |
| upstream_type | NULL |
| request_model | glm5_2_nv |
| duration_ms | 121,075 |
| tiers_tried_count | 2 |
| fallback_tiers_used | {glm5_2_nv, dsv4p_nv} |

- 双 tier 均耗尽 → NVCF 上游问题，非配置可修复
- 与 R901 模式完全一致

### 2.8 当前 nv_gw 配置 (全部参数)

| 参数 | 值 | Floor? |
|------|-----|--------|
| UPSTREAM_TIMEOUT | 66 | — |
| TIER_TIMEOUT_BUDGET_S | 114 | — |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ floor |
| NVU_EMPTY_200_FASTBREAK | 1 | ✅ floor |
| NVU_CONNECT_RESERVE_S | 0 | ✅ floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ floor |
| KEY_COOLDOWN_S | 25 | — |
| TIER_COOLDOWN_S | 20 | — |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | — |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | — |
| NVU_FORCE_STREAM_UPGRADE | 0 | ✅ disabled |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | — |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | ✅ floor |
| NV_INTEGRATE_MODELS | (empty) | ✅ disabled |

### 2.9 当前 ms_gw 配置

| 参数 | 值 |
|------|-----|
| EMPTY_200_FASTBREAK_THRESHOLD | 3 (R900: 5→3) |
| KEY_COOLDOWN_S | 60 |
| VARIANT_COOLDOWN_S | 30 |
| ALL_EXHAUSTED_COOLDOWN_S | 30 |
| MIN_OUTBOUND_INTERVAL_S | 1.0 |
| NUM_KEYS | 7 |
| NUM_VARIANTS | 10 |

---

## 3. 决策: NOP (零变更)

**判定依据**:
- nv_gw 6h SR 98.4% — 极高，唯一 ATE 为双 tier NVCF 上游耗尽 (upstream_type=NULL, tiers_tried=2)，不可通过配置修复
- 所有 nv_gw fastbreak/cooldown 参数均已触底 (FASTBREAK=1, EMPTY_200_FASTBREAK=1, MIN_OUTBOUND=0, CONNECT_RESERVE=0, INTEGRATE_COOLDOWN=0)
- 1h 窗口 100% SR (4/4)，零配置相关错误
- Fallback 链 6/6 成功，FALLBACK_GRAPH healthy
- ms_gw R900 已优化 EMPTY_200_FASTBREAK_THRESHOLD 5→3，当前零错误
- NV_INTEGRATE_MODELS 为空（integrate 已完全禁用），无回滚需求
- 所有参数与 R901 完全一致，数据无漂移
- 无任何参数有优化空间或回调节需求

**无优化空间，NOP。**

---

## 4. HM1 vs HM2 对比

| 指标 | HM1 | HM2 |
|------|-----|-----|
| 6h SR | 98.4% | ~98.5% |
| ATE | 1 (tiers_tried=2) | 1 (tiers_tried=2) |
| FALLBACK_GRAPH | 双向活跃 | 双向活跃 |
| EMPTY_200_FASTBREAK (ms_gw) | 3 (R900) | 5 |
| 本轮修改 | — | — |

---

## ⏳ 轮到HM1优化HM2