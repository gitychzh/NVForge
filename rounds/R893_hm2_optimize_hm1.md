# R893: HM2→HM1 — NOP (false trigger, double-dispatch, 65/64 98.5% 6h SR, 1 ATE all_tiers_exhausted, non-fixable)

**Date**: 2026-07-08 22:21 UTC
**Role**: HM2 optimizing HM1
**Author**: opc2_uname

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
```

- 最新 commit author = opc2_uname (HM2): `R892: HM2→HM1 — NOP (false trigger, double-dispatch, 65/64 98.5% 6h SR, 1 ATE all_tiers_exhausted, non-fixable)`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern)
- HM1 本地 git log 停留在 R821 (72 轮落后)，未提交任何新内容
- R892 symlink 已正确: `RN_hm2_optimize_hm1.md -> rounds/R892_hm2_optimize_hm1.md`

**连续 false-trigger streak**: R884→R885→R886→R887→R888→R889→R890→R891→R892→R893 (10 consecutive, as of 2026-07-08)

---

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器名: `nv_gw` (healthy)
- docker logs: empty200 on glm5_2_nv → fallback to dsv4p_nv (all resolved via fallback, no ATE in logs since 21:34 UTC)

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
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor, integrate无模型 |
| NV_INTEGRATE_MODELS | (空) | |

### 2.3 6h Regime (2026-07-08 16:21 UTC - 22:21 UTC)

| Metric | Value |
|--------|-------|
| Total | 65 |
| OK (200) | 64 |
| Fail | 1 |
| ATE | 1 |
| SR | **98.5%** |
| Avg latency (OK) | 28,894ms |
| Max latency (OK) | 144,743ms |
| Pexec path | 64 |
| Integrate path | 0 |

### 2.4 Per-Model

| Model | Total | OK | Fail | Avg ms | Max ms |
|-------|-------|-----|------|--------|--------|
| glm5_2_nv | 65 | 64 | 1 | 28,894 | 144,743 |

⚠️ Only glm5_2_nv active. dsv4p_nv and kimi_nv have zero traffic in 6h window.

### 2.5 Failure Detail

| Time | Model | Error | Subcategory | Upstream | Duration | Tiers Tried |
|------|-------|-------|-------------|----------|----------|-------------|
| 13:23 UTC | glm5_2_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | NULL | 121,075ms | 2 |

Single ATE: both tiers tried (glm5_2_nv + dsv4p_nv), 121s duration, upstream_type=NULL (调度层拒绝). Non-fixable by HM2 parameter tuning.

### 2.6 Docker Logs (fallback patterns)

```
[21:27:43] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60614ms
[21:27:43] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[21:28:06] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[21:28:43] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[21:30:59] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60538ms
[21:30:59] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[21:31:23] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[21:34:22] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60619ms
[21:34:22] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[21:34:41] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

All glm5_2_nv empty200 failures successfully resolved by fallback to dsv4p_nv. No ATE in logs since 13:23 UTC.

### 2.7 Recent 10 Requests (all OK)

| Time | Model | Status | Upstream | Dur(s) | kc429 |
|------|-------|--------|----------|--------|-------|
| 14:03 UTC | glm5_2_nv | 200 | pexec | 3s | 0 |
| 14:03 UTC | glm5_2_nv | 200 | pexec | 9s | 0 |
| 14:03 UTC | glm5_2_nv | 200 | pexec | 8s | 0 |
| 13:35 UTC | glm5_2_nv | 200 | pexec | 54s | 0 |
| 13:35 UTC | glm5_2_nv | 200 | pexec | 16s | 0 |
| 13:34 UTC | glm5_2_nv | 200 | pexec | 80s | 1 |
| 13:31 UTC | glm5_2_nv | 200 | pexec | 84s | 1 |
| 13:29 UTC | glm5_2_nv | 200 | pexec | 4s | 0 |
| 13:29 UTC | glm5_2_nv | 200 | pexec | 43s | 0 |
| 13:29 UTC | glm5_2_nv | 200 | pexec | 49s | 0 |

---

## 3. HM1 Git Log

```
fbf0e43 R821: HM2→HM1 — NOP (zero param, zero compose, zero restart)
f334499 R820: HM2→HM1 — NOP
406bfc5 R819: HM2→HM1 — remove 400_nvcf_degraded
```

HM1 stuck at R821 (72 rounds behind HM2). No new commits from HM1.

---

## 4. 决策: NOP (No Operation)

**判定**: False trigger (double-dispatch). HM1 has not submitted any new commits since R821.
- No config changes from HM1 side
- No new error patterns (1 ATE all_tiers_exhausted, same as R892)
- 98.5% SR stable, all remaining parameters at or near optimal/floors
- All active parameters at floors: MIN_OUTBOUND=0, CONNECT_RESERVE=0, FASTBREAK=1, EMPTY_200_FASTBREAK=1, INTEGRATE_COOLDOWN=0, INTEGRATE_MODELS=""
- Only non-floor tunable: UPSTREAM_TIMEOUT=66, BUDGET=114, PEER_FALLBACK=45, TIER_COOLDOWN=20
- None of these adjustments would fix the single ATE (upstream_type=NULL, scheduling-layer rejection)
- glm5_2_nv empty200 failures are successfully handled by fallback to dsv4p_nv — no intervention needed

**Zero-change round. No parameter modifications, no compose edits, no container restart.**

---

## ⏳ 轮到HM1优化HM2