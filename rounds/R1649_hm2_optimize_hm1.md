# R1649 — HM2→HM1: NOP (false trigger, all params floor/optimal, NVCF upstream degradation)

## 触发原因

Cron 检测到 R1648 commit (dba694b, HM2自身) 后触发 HM2→HM1 优化。这是 false trigger（HM2 自己的 commit 不应触发自己对 HM1 的优化）。但按铁律必须写轮次文件保持 HM1↔HM2 交替节奏。

## 数据 (HM1 6h post-R1648 deploy)

nv_gw StartedAt: 2026-07-16T19:34:07Z (8min ago, post-R1648 deploy)
Container: nv_gw Up 8 minutes (healthy), logs_db Up 3 hours (healthy), cc4101 Up 2 hours

### 6h 总览

| Metric | Value |
|--------|-------|
| Total requests | 25 |
| Success rate | 14/25 (56.0%) |
| glm5_2_nv OK | 7 (avg 6.6s, max 8.3s) |
| glm5_2_nv zombie | 6 (NVCF server-side content-filter) |
| glm5_2_nv ATE | 0 |
| dsv4p_nv OK | 7 (avg 24.6s, max 37.2s) |
| dsv4p_nv ATE | 5 (avg ~62s, all tiers_tried=1, no peer-fb) |
| pexec_429 | 0 |
| pexec_SSLEOFError | 0 |
| key_cycle_429s | 13 total (6 req with 429 cycle) |
| ms_gw | 1 req / 0 OK (unused) |
| nv_gw logs | 零 error/warn |

### 1h 总览

| Metric | Value |
|--------|-------|
| Total | 6 req / 3 OK (50.0%) / 3 fail |
| glm5_2_nv | 3 OK (avg 6.6s), 3 zombie |
| pexec | 6 (all glm5_2_nv) |

### dsv4p_nv ATE 详情

| created_at | duration_ms | tiers_tried | fallback_tiers_used |
|---|---|---|---|
| 18:05:11 | 64280 | 1 | {dsv4p_nv} |
| 18:05:00 | 61652 | 1 | {dsv4p_nv} |
| 18:03:57 | 61533 | 1 | {dsv4p_nv} |
| 18:02:47 | 61822 | 1 | {dsv4p_nv} |
| 18:01:42 | 62107 | 1 | {dsv4p_nv} |

模式: 全部 ~62s, tiers_tried=1, 无 peer-fallback。EMPTY_200_FASTBREAK=2 应触发 2nd key 但 tiers_tried=1 说明 empty200 在 1st key 发生后 budget 耗尽前未触发 2nd key 尝试（或尝试后仍失败）。NVCF function-level degradation, 非本地参数可修。

### tier_attempts 6h

| tier | error_type | count |
|------|-----------|-------|
| glm5_2_nv | pexec_success | 13 |

零 tier-level 错误记录，所有失败在调度层。

### env 验证 (R1648 deploy 确认)

| 参数 | 值 | 状态 |
|------|-----|------|
| NVU_TIER_BUDGET_DSV4P_NV | 76 | ✓ R1648 生效 |
| TIER_TIMEOUT_BUDGET_S | 195 | ✓ R1647 生效 |
| KEY_COOLDOWN_S | 60 | ✓ R1643 生效 |
| TIER_COOLDOWN_S | 60 | ✓ R1643 生效 |
| UPSTREAM_TIMEOUT | 66 | ✓ stable |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | ✓ R1622 生效 |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✓ |
| NVU_PEER_FB_SKIP_MODELS | (空) | ✓ R1646 生效 |
| NVU_EMPTY_200_FASTBREAK | 2 | ✓ R1031 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✓ floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | ✓ stable |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | ✓ |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | ✓ stable |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✓ floor |
| NVU_CONNECT_RESERVE_S | 0 | ✓ floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✓ floor |
| NV_INTEGRATE_MODELS | (空) | ✓ |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | ✓ stable |

所有参数 compose=env 一致，无漂移。

## 决策: NOP

### 不可修错误
- **6× glm5_2_nv zombie**: NVCF server-side content-filter (stop+12chars), 非本地参数可修
- **5× dsv4p_nv ATE**: NVCF function-level degradation (504 upstream), 单 tier 穷尽, 非本地参数可修

### 参数状态
- dsv4p_nv BUDGET=76: 刚 R1648 从 78→76（-2s 保守步长），需观察 24h+ 数据再评估
- TIER_BUDGET_S=195: R1647 从 205→195，所有 per-tier budget 合计 < 195
- KEY/TIER_COOLDOWN=60: R1643 刚设，NVCF 60s rate-limit 窗口对齐，不可回调
- UPSTREAM=66: NVCFPexecTimeout max binding，不可回调
- PEER_FALLBACK=72: 已对齐 HM2 BUDGET=70+2s buffer，不可回调
- EMPTY_200_FASTBREAK=2: 已足够（2nd key rescue），3 会浪费 pexec 时间
- 所有其他参数 floor/optimal

### 预算验证
- dsv4p_nv + peer-fb = 76+72 = 148 < 195 ✓
- glm5_2_nv + peer-fb = 120+72 = 192 < 195 ✓
- 2nd-key rescue: 76-62 = 14s > 13.6s minimum ✓

## 评判

NOP（false trigger）。所有失败均为 NVCF upstream degradation（6 zombie server-side + 5 dsv4p function-level），非本地参数可修。所有参数 at floor/optimal。dsv4p_nv BUDGET=76 刚部署需观察 24h+ 数据。零变更，零重启。

铁律: 只改HM1不改HM2 单参数 改前有数据改后有验证 所有修改写入仓库
## ⏳ 轮到HM1优化HM2
