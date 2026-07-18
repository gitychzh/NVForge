# R1741 (HM2→HM1): NOP — false trigger, 零可配置修复故障, KEY=TIER=65待验证

## 1. 触发分析

- 最新 commit `3518c61 R1740` author=opc2_uname (HM2自提交)
- 脚本输出: `"这是我提交的, 不触发"` — 正确识别自提交
- cron 仍被派遣 → false trigger / double-dispatch
- 6h 数据全部为 pre-R1740 (KEY=TIER=60→65部署后零流量)

## 2. 改前数据 (2026-07-18 08:20 UTC, 6h)

### 2.1 nv_requests 概览

| 窗口 | 总 | OK | Err | SR |
|------|-----|-----|------|------|
| 6h | 26 | 20 | 6 | 76.9% |

### 2.2 Per-tier 明细

| Tier | 总 | OK | Err | SR | avg_ms | avg_ttfb_ms |
|------|-----|-----|------|------|--------|-------------|
| glm5_2_nv | 26 | 20 | 6 | 76.9% | 8,336 | 5,888 |

→ dsv4p_nv/kimi_nv/minimax_m3_nv: 0流量 (6h) — 仅 openclaw 活跃

### 2.3 Error 分类 (6h)

| 错误类型 | 数量 | 可修性 |
|----------|------|--------|
| zombie_empty_completion | 6 | 代码级, 不可配置修复 |

→ 零 ATE, 零 tier_attempts 错误, 零 fallback

### 2.4 key_cycle_429s

| key_cycle_429s | 数量 |
|----------------|------|
| 0 | 2 |
| 1 | 23 |
| 2 | 1 |

→ 92.3% 请求 key_cycle_429s — **全部 pre-R1740** (KEY=TIER=60 边界对齐 NVCF 窗口)

### 2.5 nv_tier_attempts (6h)

全部 10 条 pexec_success, 零错误。所有 glm5_2_nv pexec 请求 first-attempt 成功。

### 2.6 fallback

fallback_occurred = false on all 26 requests. 零 fallback 触发。

### 2.7 实时日志 (tail 100)

容器最近重启 (06:16 UTC), 日志仅启动信息, 零流量。
```
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])
```

### 2.8 HM1 nv_gw 当前配置 (容器env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 55 | R1729 |
| TIER_TIMEOUT_BUDGET_S | 195 | R1735 |
| KEY_COOLDOWN_S | 65 | **R1740** (60→65) |
| TIER_COOLDOWN_S | 65 | **R1740** (60→65) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | stable |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FALLBACK_TIMEOUT | 124 | R1739 (125→124) |
| NVU_PEER_FALLBACK_URL | http://100.109.57.26:40006 | HM2 |
| NVU_PEER_FB_SKIP_MODELS | (空) | R1646 清空, dsv4p_nv peer-fb enabled |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | stable |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | |
| NVU_STREAM_TOTAL_DEADLINE_S | 30 | |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | (空) | 无 integrate |
| NVU_TIER_BUDGET_DSV4P_NV | 60 | |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | |
| NVU_BIG_INPUT_FAIL_N | 1 | |
| NVU_BIG_INPUT_COOLDOWN_S | 5400 | |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | |
| NVU_BIG_INPUT_THRESHOLD | 250000 | |

### 2.9 漂移检测

容器 env vs compose (grep 总参数行): 全部匹配。零漂移。
- KEY_COOLDOWN_S: compose=65, container=65 ✓
- TIER_COOLDOWN_S: compose=65, container=65 ✓
- UPSTREAM_TIMEOUT: compose=55, container=55 ✓
- TIER_TIMEOUT_BUDGET_S: compose=195, container=195 ✓
- PEER_FALLBACK_TIMEOUT: compose=124, container=124 ✓
- 所有其他参数: 一致 ✓

## 3. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 55 | optimal | max_ok << 55, buffer ≥ 3s |
| TIER_TIMEOUT_BUDGET_S | 195 | R1735 | 195=70+125, peer-fb 124s usable |
| KEY_COOLDOWN_S | 65 | R1740 待验证 | 60→65 +5s, 零 post-R1740 流量 |
| TIER_COOLDOWN_S | 65 | R1740 待验证 | KEY=TIER=65 per iron law |
| NVU_PEER_FALLBACK_TIMEOUT | 124 | R1739 | 124 ≥ HM2_BUDGET+2=122 ✓ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | |
| NVU_EMPTY_200_FASTBREAK | 1 | floor | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 |
| 其他参数 | - | stable/floor | |

## 4. 决策: NOP (零变更)

**理由**:
1. **False trigger**: R1740 是 HM2 自提交, 无 HM1 实际变更需要评估
2. **零可配置修复故障**: 6 error 全部 zombie_empty_completion (代码级检测功能, 不可配置修复)
3. **R1740 KEY=TIER=65 零后流量**: 无法验证 429 级联修复效果, 需等待流量
4. **零 dsv4p_nv 流量**: 无法验证 peer-fb rescue (R1735-R1739 系列)
5. **所有参数 at floor/optimal**: 零优化空间
6. **零漂移**: compose = container env, 所有参���一致
7. **铁律**: 只改HM1不改HM2

- 稳定优先: 等待流量验证 R1740 KEY=TIER=65 的 429 修复效果
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
