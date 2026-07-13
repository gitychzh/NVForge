# HM2 Optimize HM1 — Round R1267

## 触发分析

cron 脚本输出: `这是我提交的, 不触发`
- 最新 commit: `2ce23b8` (R1266, author=opc2_uname, HM2)
- 自提交 false trigger

## 6h 数据 (2026-07-14 02:45 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 68 |
| 成功 | 54 (79.4%) |
| 失败 | 14 |
| 容器重启 | 2026-07-13T18:24:22Z |

### 失败分类

| 错误类型 | 数量 | 模型 | 详情 |
|----------|------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv | integrate, avg 10,882ms, avg input 179K chars — NVCF content-filter stop+12chars, code-level zombie detection |
| all_tiers_exhausted | 3 | dsv4p_nv | single-tier, 72,019ms avg, pre-restart — NVU_TIER_BUDGET_DSV4P_NV=72 capping |
| NVStream_IncompleteRead | 1 | glm5_2_nv | pre-restart |

### 按模型

| 模型 | 总数 | OK | 失败 | SR |
|------|------|-----|------|----|
| glm5_2_nv | 54 | 43 | 11 | 79.6% |
| dsv4p_nv | 14 | 11 | 3 | 78.6% |

### 按路径

| 路径 | 总数 | OK | avg_dur |
|------|------|-----|---------|
| nv_integrate | 54 | 43 | 12,193ms |
| nvcf_pexec | 11 | 11 | 27,698ms |
| (ATE) | 3 | 0 | 72,019ms |

### tier_attempts

0 rows — no key-level failures.

### 实时日志

```
[NV-SUCCESS] tier=dsv4p_nv k3 on first attempt
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k1/k2/k3 on first attempt
[NV-ZOMBIE-EMPTY] (glm5_2_nv) finish_reason=stop, content_chars=12 < 50, input_chars=207621
[NV-ZOMBIE-ERROR-CHUNK] sent content_filter error SSE → openclaw fallback
```

Post-restart: 5/5 first-attempt success, 0 ATE, 0 IncompleteRead, 0 tier_attempts.

## 决策: NOP

**原因**:
1. 10 zombie_empty_completion — code-level NVCF content-filter (stop+12chars), gateway detection+error-chunk correct, not config-fixable
2. 3 dsv4p_nv ATE — all pre-restart (R1265 peer-fb routing already fixed), post-restart 0 ATE
3. 1 NVStream_IncompleteRead — pre-restart
4. 0 tier_attempts — zero key-level errors
5. All params floor/optimal: UPSTREAM=66, BUDGET=210, FASTBREAK=1, NVU_TIER_BUDGET_DSV4P_NV=72, NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_PEER_FB_SKIP_MODELS="", NVU_MS_GW_FALLBACK_TIMEOUT=200, TIER_COOLDOWN=15, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1

**Zero param change, zero compose change, zero container restart.**

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
