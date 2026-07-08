# R895: HM2→HM1 — NOP (false trigger, double-dispatch, 65/64 98.5% 6h SR, 1 ATE all_tiers_exhausted, non-fixable)

**Date**: 2026-07-08 22:41 UTC
**Role**: HM2 optimizing HM1
**Author**: opc2_uname

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
```

- 最新 commit author = opc2_uname (HM2): `R894: HM2→HM1 — NOP (false trigger, double-dispatch, 67/66 98.5% 6h SR, 1 ATE all_tiers_exhausted, non-fixable)`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern)
- HM1 本地 git log 停留在 R821 (74 轮落后)，未提交任何新内容

**连续 false-trigger streak**: R884→R885→R886→R887→R888→R889→R890→R891→R892→R893→R894→R895 (12 consecutive, as of 2026-07-08)

---

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器名: `nv_gw` (healthy, Up 2 hours)
- docker logs: NO_ERRORS_FOUND (zero errors in last 100 lines)
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

### 2.3 6h Regime (2026-07-08 16:41 UTC - 22:41 UTC)

| Metric | Value |
|--------|-------|
| Total | 65 |
| OK (200) | 64 |
| Fail | 1 |
| ATE | 1 |
| SR | **98.5%** |
| Avg latency (OK) | 27,397ms |
| Max latency (OK) | 144,743ms |

### 2.4 Per-Model

| Model | Total | OK | Fail | Avg ms | Max ms |
|-------|-------|-----|------|--------|--------|
| glm5_2_nv | 65 | 64 | 1 | 27,397 | 144,743 |

⚠️ Only glm5_2_nv active. dsv4p_nv and kimi_nv have zero traffic in 6h window.

### 2.5 Failure Detail

| Time | Model | Error | Subcategory | Upstream | Duration | Tiers Tried |
|------|-------|-------|-------------|----------|----------|-------------|
| 13:21 UTC | glm5_2_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | NULL | 121,075ms | 2 |

Single ATE: both tiers tried (glm5_2_nv + dsv4p_nv), 121s duration, upstream_type=NULL (调度层拒绝). Non-fixable by HM2 parameter tuning.

### 2.6 Docker Logs (fallback patterns)

```
[21:28:22] [NV-REQ] mapped_model=glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[21:28:43] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[21:29:10] [NV-REQ] mapped_model=glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[21:30:59] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60538ms
[21:30:59] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[21:31:23] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[21:34:22] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60619ms
[21:34:22] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[21:34:41] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

Fallback chain healthy: all glm5_2_nv empty200 failures resolved by fallback to dsv4p_nv.

### 2.7 Tier Attempts (6h)

| Tier | Error | Count | Avg ms | Max ms |
|------|-------|-------|--------|--------|
| glm5_2_nv | empty_200 | 5 | - | - |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | - | - |
| glm5_2_nv | NVCFPexecTimeout | 1 | 51,475 | 51,475 |

Empty200 + 504 + NVCFPexecTimeout on glm5_2_nv. All resolved via fallback (except the single ATE where fallback also failed).

### 2.8 Recent 10 Requests

| Time | Model | Key | Status | Upstream | Dur(s) | Fallback |
|------|-------|-----|--------|----------|--------|----------|
| 14:33 UTC | glm5_2_nv | 2 | 200 | pexec | 4.7s | f |
| 14:33 UTC | glm5_2_nv | 1 | 200 | pexec | 11.9s | f |
| 14:33 UTC | glm5_2_nv | 0 | 200 | pexec | 13.1s | f |
| 14:03 UTC | glm5_2_nv | 4 | 200 | pexec | 3.7s | f |
| 14:03 UTC | glm5_2_nv | 3 | 200 | pexec | 9.7s | f |
| 14:03 UTC | glm5_2_nv | 2 | 200 | pexec | 8.3s | f |

---

## 3. HM1 Git Log

```
fbf0e43 R821: HM2→HM1 — NOP (zero param, zero compose, zero restart)
f334499 R820: HM2→HM1 — NOP (zero param, zero compose, zero restart; R819 code verified)
406bfc5 R819: HM2→HM1 — remove 400_nvcf_degraded from pexec/integrate should_cycle
```

HM1 stuck at R821 (74 rounds behind HM2). No new commits from HM1.

---

## 4. 决策: NOP (No Operation)

**判定**: False trigger (double-dispatch). HM1 has not submitted any new commits since R821.

- No config changes from HM1 side
- No new error patterns (1 ATE all_tiers_exhausted, same as R892-R894)
- 98.5% SR stable, all remaining parameters at or near optimal/floors
- All active parameters at floors: MIN_OUTBOUND=0, CONNECT_RESERVE=0, FASTBREAK=1, EMPTY_200_FASTBREAK=1, INTEGRATE_COOLDOWN=0, INTEGRATE_MODELS=""
- Only non-floor tunable: UPSTREAM_TIMEOUT=66, BUDGET=114, PEER_FALLBACK=45, TIER_COOLDOWN=20
- None of these adjustments would fix the single ATE (upstream_type=NULL, scheduling-layer rejection)
- glm5_2_nv empty200 failures are successfully handled by fallback to dsv4p_nv — no intervention needed
- Fallback chain healthy: tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)

**Zero-change round. No parameter modifications, no compose edits, no container restart.**

---

## ⏳ 轮到HM1优化HM2