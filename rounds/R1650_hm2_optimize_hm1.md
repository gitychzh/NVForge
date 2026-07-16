# R1650 — HM2→HM1: NOP (false trigger, HM1 pulled HM2's R1649 NOP, zero new traffic)

## 触发原因

Cron detected HM1 commit `e51f125` and triggered HM2→HM1 optimization. This commit is actually HM1 pulling HM2's R1649 NOP — a false trigger identical to R1649's scenario. HM2's own commit should not trigger HM2→HM1 optimization.

## 数据 (HM1, same window as R1649)

### 6h 总览 (no new traffic since R1649)

| Metric | Value |
|--------|-------|
| Total requests | 25 |
| Success rate | 14/25 (56.0%) |
| glm5_2_nv OK | 7 (avg ~6.6s) |
| glm5_2_nv zombie | 6 (NVCF server-side content-filter) |
| dsv4p_nv OK | 7 (avg 24.6s, max 37.2s) |
| dsv4p_nv ATE | 5 (tiers_tried=1, no peer-fb) |
| key_cycle_429s | 13 (all glm5_2_nv) |
| fallback_occurred | 0 |
| nv_gw logs | 零 error/warn |

### 1h 总览

| Metric | Value |
|--------|-------|
| Total | 6 req / 3 OK (50.0%) / 3 fail |
| Failures | 3× glm5_2_nv zombie |

### dsv4p_nv ATE 详情

| ts | duration_ms | tiers_tried | fallback_tiers_used |
|---|---|---|---|
| 18:04:07 | 64280 | 1 | {dsv4p_nv} |
| 18:03:58 | 61652 | 1 | {dsv4p_nv} |
| 18:02:56 | 61533 | 1 | {dsv4p_nv} |
| 18:01:45 | 61822 | 1 | {dsv4p_nv} |
| 18:00:40 | 62107 | 1 | {dsv4p_nv} |

所有 ~62s, tiers_tried=1, 无 peer-fallback。NVCF function-level degradation。

### tier_attempts 6h

| tier | error_type | count |
|------|-----------|-------|
| glm5_2_nv | pexec_success | 13 |

零 tier-level 错误，所有失败在调度层。

### env 验证 (docker exec)

| 参数 | 值 | 状态 |
|------|-----|------|
| NVU_TIER_BUDGET_DSV4P_NV | 76 | ✓ R1648 |
| TIER_TIMEOUT_BUDGET_S | 195 | ✓ R1647 |
| KEY_COOLDOWN_S | 60 | ✓ R1643 |
| TIER_COOLDOWN_S | 60 | ✓ R1643 |
| UPSTREAM_TIMEOUT | 66 | ✓ stable |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | ✓ R1622 |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✓ |
| NVU_PEER_FB_SKIP_MODELS | (空) | ✓ R1646 |
| NVU_EMPTY_200_FASTBREAK | 2 | ✓ R1031 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✓ floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | ✓ stable |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | ✓ stable |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | ✓ stable |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✓ floor |
| NVU_CONNECT_RESERVE_S | 0 | ✓ floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✓ floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | ✓ stable |

所有参数 compose=env 一致，无漂移。

## 决策: NOP

### 不可修错误
- **6× glm5_2_nv zombie**: NVCF server-side content-filter (stop+12chars), 非本地参数可修
- **5× dsv4p_nv ATE**: NVCF function-level degradation, 单 tier 穷尽, 非本地参数可修

### 参数状态
- dsv4p_nv BUDGET=76: R1648 刚部署 (78→76), 需观察 24h+ 数据再评估
- TIER_BUDGET_S=195: R1647 从 205→195, 所有 per-tier budget 合计 < 195
- KEY/TIER_COOLDOWN=60: R1643 刚设, NVCF 60s rate-limit 窗口对齐, 不可回调
- UPSTREAM=66: NVCFPexecTimeout max binding, 不可回调
- PEER_FALLBACK=72: 已对齐 HM2 BUDGET=70+2s buffer, 不可回调
- EMPTY_200_FASTBREAK=2: 已足够, 3 浪费 pexec 时间
- 所有其他参数 floor/optimal

### 预算验证
- dsv4p_nv + peer-fb = 76+72 = 148 < 195 ✓
- glm5_2_nv + peer-fb = 120+72 = 192 < 195 ✓
- 2nd-key rescue: 76-62 = 14s > 13.6s minimum ✓

## 评判

NOP (false trigger, 零新数据)。HM1 的 e51f125 是 pull HM2 的 R1649 NOP commit。所有失败均为 NVCF upstream degradation, 非本地参数可修。dsv4p_nv BUDGET=76 刚部署需观察 24h+。所有参数 at floor/optimal。零变更, 零重启。

铁律: 只改HM1不改HM2 单参数 改前有数据改后有验证 所有修改写入仓库
## ⏳ 轮到HM1优化HM2
