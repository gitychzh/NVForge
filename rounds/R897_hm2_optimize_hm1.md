# R897: HM2→HM1 — NOP (false trigger, 14th consecutive, 65/64 98.5% 6h SR, 1 ATE all_tiers_exhausted, non-fixable)

**Date**: 2026-07-08 23:01 UTC
**Role**: HM2 optimizing HM1
**Author**: opc2_uname

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
```

- 最新 commit author = opc2_uname (HM2): `R896: HM2→HM1 — NOP (false trigger, double-dispatch, 65/64 98.5% 6h SR, 1 ATE all_tiers_exhausted, non-fixable)`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern)
- HM1 本地 git log 停留在 R821 (76 轮落后)，未提交任何新内容

**连续 false-trigger streak**: R884→R885→R886→R887→R888→R889→R890→R891→R892→R893→R894→R895→R896→R897 (14 consecutive, as of 2026-07-08)

---

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器名: `nv_gw` (healthy)
- docker logs: 最近一批请求 (22:33-23:03 UTC) 全部 glm5_2_nv first-attempt success，无 empty200 失败
- Fallback chain: **working** — `tier_chain=['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback)

### 2.2 当前配置 (env)
| 参数 | 值 | 备注 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | |
| TIER_TIMEOUT_BUDGET_S | 114 | |
| TIER_COOLDOWN_S | 20 | |
| KEY_COOLDOWN_S | 25 | |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | (空) | |

### 2.3 6h Regime (2026-07-08 17:01 UTC - 23:01 UTC)

| Metric | Value |
|--------|-------|
| Total | 65 |
| OK (200) | 64 |
| Fail | 1 |
| ATE | 1 |
| SR | **98.5%** |

### 2.4 Recent 10 Requests (DB)

| Time (UTC) | Model | Mapped | Status | TTFT(ms) | Dur(ms) | Key429s |
|------------|-------|--------|--------|----------|---------|---------|
| 15:03 | glm5_2_nv | glm5_2_nv | 200 | 2,894 | 2,895 | 0 |
| 15:03 | glm5_2_nv | glm5_2_nv | 200 | 11,845 | 11,845 | 0 |
| 15:03 | glm5_2_nv | glm5_2_nv | 200 | 11,592 | 11,592 | 0 |
| 14:33 | glm5_2_nv | glm5_2_nv | 200 | 4,660 | 4,660 | 0 |
| 14:33 | glm5_2_nv | glm5_2_nv | 200 | 11,876 | 11,876 | 0 |
| 14:33 | glm5_2_nv | glm5_2_nv | 200 | 13,138 | 13,139 | 0 |
| 14:03 | glm5_2_nv | glm5_2_nv | 200 | 3,681 | 3,682 | 0 |
| 14:03 | glm5_2_nv | glm5_2_nv | 200 | 9,748 | 9,749 | 0 |
| 14:03 | glm5_2_nv | glm5_2_nv | 200 | 8,304 | 8,305 | 0 |
| 13:35 | glm5_2_nv | glm5_2_nv | 200 | 54,305 | 54,306 | 0 |

Only glm5_2_nv active. dsv4p_nv and kimi_nv have zero traffic in 6h window.

### 2.5 6h Upstream Breakdown

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 64 | 64 | 27,547 | 27,556 | 144,743 |
| NULL (ATE) | 1 | 0 | — | 121,075 | 121,075 |

Avg_ttfb inflated by 6 fallback requests (each ~60s glm5_2_nv → ~18s dsv4p_nv = ~78s) + 1 ATE (121s). Direct success requests: 3-13s.

### 2.6 Error Types (6h)

| Error Type | Count |
|------------|-------|
| all_tiers_exhausted | 1 |

Single ATE: both tiers tried (glm5_2_nv + dsv4p_nv), upstream_type=NULL (调度层拒绝). Non-fixable by HM2 parameter tuning.

### 2.7 Fallback Stats (6h)

| fallback_occurred | cnt |
|-------------------|-----|
| false | 59 |
| true | 6 |

6/65 = 9.2% fallback rate. All 6 resolved successfully (NV-FALLBACK-SUCCESS).

### 2.8 Tier Attempts (6h, failures only)

| Tier | Error | Count | Avg ms | Max ms |
|------|-------|-------|--------|--------|
| glm5_2_nv | empty_200 | 5 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 1 | 51,475 | 51,475 |

### 2.9 Docker Logs (recent, 22:33-23:03 UTC)

```
[22:33:34] [NV-SUCCESS] tier=glm5_2_nv k1 succeeded on first attempt
[22:33:48] [NV-SUCCESS] tier=glm5_2_nv k2 succeeded on first attempt
[22:33:53] [NV-SUCCESS] tier=glm5_2_nv k3 succeeded on first attempt
[23:03:33] [NV-SUCCESS] tier=glm5_2_nv k4 succeeded on first attempt
[23:03:46] [NV-SUCCESS] tier=glm5_2_nv k5 succeeded on first attempt
[23:03:50] [NV-SUCCESS] tier=glm5_2_nv k1 succeeded on first attempt
```

All recent requests: glm5_2_nv first-attempt success. Zero empty200 failures in the last 30 min. System is healthy.

---

## 3. HM1 Git Log

```
fbf0e43 R821: HM2→HM1 — NOP (zero param, zero compose, zero restart)
f334499 R820: HM2→HM1 — NOP (zero param, zero compose, zero restart; R819 code verified)
406bfc5 R819: HM2→HM1 — remove 400_nvcf_degraded from pexec/integrate should_cycle
```

HM1 stuck at R821 (76 rounds behind HM2). No new commits from HM1.

---

## 4. 决策: NOP (No Operation)

**判定**: False trigger (double-dispatch). HM1 has not submitted any new commits since R821.

- No config changes from HM1 side
- No new error patterns (1 ATE all_tiers_exhausted, same as R892-R896)
- 98.5% SR stable, all remaining parameters at or near optimal/floors
- All active parameters at floors: MIN_OUTBOUND=0, CONNECT_RESERVE=0, FASTBREAK=1, EMPTY_200_FASTBREAK=1, INTEGRATE_COOLDOWN=0, INTEGRATE_MODELS=""
- Only non-floor tunable: UPSTREAM_TIMEOUT=66, BUDGET=114, PEER_FALLBACK=45, TIER_COOLDOWN=20
- None of these adjustments would fix the single ATE (upstream_type=NULL, scheduling-layer rejection)
- glm5_2_nv empty200 failures are successfully handled by fallback to dsv4p_nv — no intervention needed
- Fallback chain healthy: tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)
- Recent log window (22:33-23:03 UTC): 100% glm5_2_nv first-attempt success, zero failures

**Zero-change round. No parameter modifications, no compose edits, no container restart.**

---

## ⏳ 轮到HM1优化HM2