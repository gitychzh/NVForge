# R892: HM2→HM1 — NOP (false trigger, double-dispatch)

**Date**: 2026-07-08 22:12 UTC
**Role**: HM2 optimizing HM1
**Author**: opc2_uname

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
```

- 最新 commit author = opc2_uname (HM2): `R891: fix symlink → rounds/R891_hm2_optimize_hm1.md`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern)
- HM1 本地 git log 停留在 R821 (70 轮落后)，未提交任何新内容
- Symlink 已正确: `RN_hm2_optimize_hm1.md -> rounds/R891_hm2_optimize_hm1.md`

**连续 false-trigger streak**: R884→R885→R886→R887→R888→R889→R890→R891→R892 (9 consecutive, as of 2026-07-08)

---

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器名: `nv_gw` (healthy)
- docker logs: `(no error/warn found)` ✓

### 2.2 当前配置 (env)
| 参数 | 值 | 备注 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | |
| TIER_TIMEOUT_BUDGET_S | 114 | |
| TIER_COOLDOWN_S | 20 | ⚠️ R778 snapshot had 25 |
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

### 2.3 6h Regime (2026-07-08 16:12 UTC - 22:12 UTC)

| Metric | Value |
|--------|-------|
| Total | 65 |
| OK (200) | 64 |
| Fail | 1 |
| ATE | 1 |
| SR | **98.5%** |
| Avg latency (OK) | 28,902ms |
| Max latency (OK) | 144,743ms |
| Pexec path | 64 |
| Integrate path | 0 |
| Total key_cycle_429s | 10 |
| Fallback occurred | 6 (all successful) |

### 2.4 Per-Model

| Model | Total | OK | Fail | Avg ms | Max ms | Fallback |
|-------|-------|-----|------|--------|--------|----------|
| glm5_2_nv | 65 | 64 | 1 | 28,902 | 144,743 | 6 |

⚠️ Only glm5_2_nv active. dsv4p_nv and kimi_nv have zero traffic in 6h window.

### 2.5 Failure Detail

| Time | Model | Error | Subcategory | Upstream | Duration | Tiers Tried | Fallback Tiers |
|------|-------|-------|-------------|----------|----------|-------------|----------------|
| 13:23 UTC | glm5_2_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | NULL | 121,075ms | 2 | {glm5_2_nv, dsv4p_nv} |

Single ATE: both tiers tried (glm5_2_nv + dsv4p_nv), 121s duration, upstream_type=NULL (调度层拒绝). Non-fixable by HM2 parameter tuning.

### 2.6 Recent 10 Requests (all OK)

| Time | Model | Status | Upstream | Dur(s) | Fallback | kc429 |
|------|-------|--------|----------|--------|----------|-------|
| 14:03 UTC | glm5_2_nv | 200 | pexec | 3s | N | 0 |
| 14:03 UTC | glm5_2_nv | 200 | pexec | 9s | N | 0 |
| 14:03 UTC | glm5_2_nv | 200 | pexec | 8s | N | 0 |
| 13:35 UTC | glm5_2_nv | 200 | pexec | 54s | N | 0 |
| 13:35 UTC | glm5_2_nv | 200 | pexec | 16s | N | 0 |
| 13:34 UTC | glm5_2_nv | 200 | pexec | 80s | Y | 1 |
| 13:31 UTC | glm5_2_nv | 200 | pexec | 84s | Y | 1 |
| 13:29 UTC | glm5_2_nv | 200 | pexec | 4s | N | 0 |
| 13:29 UTC | glm5_2_nv | 200 | pexec | 43s | N | 0 |
| 13:29 UTC | glm5_2_nv | 200 | pexec | 49s | N | 0 |

---

## 3. HM1 Git Log

```
fbf0e43 R821: HM2→HM1 — NOP (zero param, zero compose, zero restart)
f334499 R820: HM2→HM1 — NOP
406bfc5 R819: HM2→HM1 — remove 400_nvcf_degraded
```

HM1 stuck at R821 (70 rounds behind HM2). No new commits from HM1.

---

## 4. 决策: NOP (No Operation)

**判定**: False trigger (double-dispatch). HM1 has not submitted any new commits since R821.
- No config changes from HM1 side
- No new error patterns (1 ATE, same as previous rounds)
- 98.5% SR stable, all remaining parameters at or near optimal/floors
- All active parameters at floors: MIN_OUTBOUND=0, CONNECT_RESERVE=0, FASTBREAK=1, EMPTY_200_FASTBREAK=1, INTEGRATE_COOLDOWN=0, INTEGRATE_MODELS=""
- Only non-floor tunable: UPSTREAM_TIMEOUT=66, BUDGET=114, PEER_FALLBACK=45, TIER_COOLDOWN=20
- None of these adjustments would fix the single ATE (upstream_type=NULL, scheduling-layer rejection)

**Zero-change round. No parameter modifications, no compose edits, no container restart.**

---

## ⏳ 轮到HM1优化HM2
