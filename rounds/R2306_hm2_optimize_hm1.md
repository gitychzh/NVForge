# R2306: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 160→170 (+10s)

## TL;DR
NVU_TIER_BUDGET_DSV4P_NV 160→170 (+10s). dsv4p_nv ATE @ 160,041ms hit budget ceiling exactly. KEY_COOLDOWN=10 + UPSTREAM=24 = 34s per key cycle. 5 keys x 34s = 170s. 170 < 415 TIER_TIMEOUT_BUDGET safe. Single param; iron law: only HM1.

---

## 一、触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `e7a9036` author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (HM2 自提交 R2305 + opclaw4103 配置)
- HM1 本地未提交任何新内容

## 二、当前配置快照（R2306 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | UPSTREAM_TIMEOUT | 24 | R2025 |
| 2 | TIER_TIMEOUT_BUDGET_S | 415 | R2294 (275→370→415) |
| 3 | NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | R2284 (1→2) |
| 4 | NVU_EMPTY_200_FASTBREAK | 3 | R2303 (2→3) |
| 5 | NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| 6 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 |
| 7 | KEY_COOLDOWN_S | 10 | R2297 (5→10) |
| 8 | TIER_COOLDOWN_S | 15 | R2305 (0→15) |
| 9 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| 10 | NVU_CONNECT_RESERVE_S | 0 | floor |
| 11 | NVU_SSLEOF_RETRY_DELAY_S | 0.1 | floor |
| 12 | NVU_MS_GW_FALLBACK_TIMEOUT | 120 | R2220 |
| 13 | NVU_PEER_FALLBACK_TIMEOUT | 122 | R2295 |
| 14 | NVU_TIER_BUDGET_GLM5_2_NV | 210 | R2291 (200→210) |
| 15 | **NVU_TIER_BUDGET_DSV4P_NV** | **160 → 170** | **R2306 (本轮)** |
| 16 | NVU_TIER_BUDGET_KIMI_NV | 200 | R2303 (170→200) |
| 17 | NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 |
| 18 | NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | R1008 |
| 19 | NVU_STREAM_TOTAL_DEADLINE_S | 25 | R2296 |
| 20 | KEY_AUTHFAIL_COOLDOWN_S | 0 | R2257 |
| 21 | NVU_PEER_FB_SKIP_MODELS | (empty) | R2295 |
| 22 | NV_INTEGRATE_MODELS | (empty) | R2258 |
| 23 | NVU_FORCE_STREAM_UPGRADE | 0 | R692 |

## 三、数据收集

### 3.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 76 |
| 成功 | 39 (51.3%) |
| 失败 | 37 |
| 平均 OK 延迟 | 28,924ms |
| 平均 fail 延迟 | 48,688ms |

### 3.2 30m 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 16 |
| 成功 | 10 (62.5%) |
| 失败 | 6 |

### 3.3 按模型分组 (6h)
| 模型 | 请求 | 成功 | 失败 | SR | avg_ok | avg fail |
|------|------|------|------|-----|--------|----------|
| glm5_2_nv | 31 | 10 | 21 | 32.3% | 22,031ms | 13,634ms |
| dsv4p_nv | 30 | 22 | 8 | 73.3% | 31,539ms | 70,955ms |
| kimi_nv | 15 | 7 | 8 | 46.7% | 30,551ms | 142,000ms |

### 3.4 错误分类 (6h)
| 错误类型 | 数量 | 模型 |
|----------|------|------|
| all_tiers_exhausted (429) | 14 | glm5_2_nv |
| all_tiers_exhausted (502) | 5 | glm5_2_nv |
| all_tiers_exhausted (502) | 7 | kimi_nv |
| all_tiers_exhausted (502) | 4 | dsv4p_nv |
| zombie_empty_completion (502) | 4 | dsv4p_nv |
| zombie_empty_completion (502) | 2 | glm5_2_nv |
| NVStream_IncompleteRead (502) | 1 | kimi_nv |

### 3.5 ATE 详情 (6h)
| 模型 | 数量 | avg_dur | 特征 |
|------|------|---------|------|
| glm5_2_nv | 22 | 13,634ms | 429 风暴 (tier_attempts: 16×429), TIER_COOLDOWN=15 阻断 |
| kimi_nv | 7 | 142,000ms | 4×124-126s (2 empty_200), 2×161-167s (1 timeout) |
| dsv4p_nv | 5 | 70,955ms | 1×160,041ms at budget ceiling, 3×50-51s, 1×42.9s |

### 3.6 nv_tier_attempts (6h)
| 模型 | 键 | 错误 | 数量 |
|------|-----|------|------|
| glm5_2_nv | k0-4 | 429_nv_rate_limit | 16 (all keys) |
| glm5_2_nv | k2 | NVCFPexecTimeout | 2 (25s avg) |
| dsv4p_nv | k0,3 | NVCFPexecSSLEOFError | 3 (5s avg) |
| dsv4p_nv | k0,2 | empty_200 | 2 |
| dsv4p_nv | k4 | 504_nv_gateway_timeout | 1 |
| kimi_nv | k4 | empty_200 | 2 |

### 3.7 429 循环 (6h)
| 模型 | 含 429 请求 | 总计 | % 429 | 最大循环 |
|------|------------|------|-------|----------|
| glm5_2_nv | 8 | 31 | 25.8% | 4 |
| dsv4p_nv | 4 | 30 | 13.3% | 3 |
| kimi_nv | 2 | 15 | 13.3% | 2 |

### 3.8 成功率分时 (6h)
| 小时 (UTC) | 总数 | OK | Fail | SR |
|------------|------|-----|------|-----|
| 12:00 | 7 | 3 | 4 | 42.9% |
| 13:00 | 11 | 9 | 2 | 81.8% |
| 14:00 | 17 | 6 | 11 | 35.3% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 7 | 4 | 3 | 57.1% |
| 17:00 | 10 | 3 | 7 | 30.0% |
| 18:00 | 18 | 12 | 6 | 66.7% |

### 3.9 最近 10 条请求
| 时间 (UTC) | 模型 | 状态 | 延迟 | 错误 |
|-----------|------|------|------|------|
| 18:13:34 | dsv4p_nv | 200 | 15,423ms | — |
| 18:13:18 | dsv4p_nv | 200 | 23,795ms | — |
| 18:12:53 | dsv4p_nv | 200 | 21,374ms | — |
| 18:12:32 | dsv4p_nv | 200 | 90,721ms | — |
| 18:11:01 | dsv4p_nv | 200 | 15,172ms | — |
| 18:10:44 | dsv4p_nv | 200 | 26,367ms | — |
| 18:09:02 | dsv4p_nv | 502 | 50,553ms | all_tiers_exhausted |
| 18:08:23 | dsv4p_nv | 502 | 160,041ms | all_tiers_exhausted ← budget ceiling |
| 18:08:16 | glm5_2_nv | 502 | 7ms | all_tiers_exhausted (all keys 429) |
| 18:06:08 | glm5_2_nv | 429 | 716ms | all_tiers_exhausted (all keys 429) |

### 3.10 容器状态
- `nv_gw`: Up ~1h (R2305 重启), StartedAt 17:21 UTC
- `ms_gw`: Up 9h (healthy)
- 18:00 小时 SR 66.7% — 429 风暴缓解中

### 3.11 nv_gw 日志 (最近 100 行)
- NVCF 429 风暴: glm5_2_nv 所有 5 键 429 → TIER_COOLDOWN=15 → all_tiers_fail
- dsv4p_nv: NVCFPexecTimeout (25s, 16s), empty_200, SSLEOF, 504_gateway_timeout
- Peer fallback: 3 次失败 (2×timeout 122s, 1×502 111s)
- Post-restart (18:00+) 日志: 干净的 dsv4p_nv 200，无新 ATE

## 四、分析

### 4.1 根因: dsv4p_nv budget ceiling
- 1 个 ATE 在 160,041ms — 确切命中 BUDGET=160s 天花板
- 5 keys × (UPSTREAM=24 + KEY_COOLDOWN=10) = 5 × 34s = 170s
- 160s budget 只够 4.7 个键周期，第 5 键被截断
- 到 160s 时: 4 键已用 = 136s，剩余 24s = 1 UPSTREAM 周期但不够 full key cycle

### 4.2 glm5_2_nv 429 风暴
- 16 次 tier_attempts 429 (分布在所有 5 键)
- 仅 8/31 请求含 429 循环 (25.8%) — 大多数请求 TIER_COOLDOWN=15 直接阻断
- R2305 的 TIER_COOLDOWN_S=15 有效：429 请求不再循环 hammer NVCF
- 22 个 ATE 中 14 个返回 429（TIER_COOLDOWN block），5 个返回 502（peer 也无法救回）
- 不可配置修复 — NVCF 限流是上游行为

### 4.3 kimi_nv ATE
- 7 ATE: 4×124-126s (2 empty_200), 2×161-167s (empty_200 + timeout)
- EMPTY_200_FASTBREAK=3 正确：2 empty_200 不触发 fastbreak，继续尝试第 3 键
- 161-167s 的 ATE: 第 3 键 timeout，BUDGET=200 足够
- 无配置参数可修复

### 4.4 预算安全
- 170 ≤ 415 TIER_TIMEOUT_BUDGET_S (245s margin)
- dsv4p_nv fallback: 170 + 160 = 330 ≤ 415 (85s margin for glm5_2 if cross-tier)

## 五、决策: NVU_TIER_BUDGET_DSV4P_NV 160→170

**单参数变更**: `NVU_TIER_BUDGET_DSV4P_NV=160` → `170`

**理由**:
1. 1 个 dsv4p_nv ATE 在 160,041ms 确切命中 BUDGET 天花板
2. KEY_COOLDOWN=10 + UPSTREAM=24 = 34s/cycle。5 keys = 170s 全覆盖
3. +10s 给第 5 键完整周期，不截断 UPSTREAM
4. 170 << 415 TIER_TIMEOUT_BUDGET 安全
5. 铁律: 只改 HM1 不改 HM2

## 六、变更记录

| 参数 | 旧值 | 新值 | 变更 |
|------|------|------|------|
| NVU_TIER_BUDGET_DSV4P_NV | 160 | 170 | +10s (+6.25%) |

容器重启: 18:42 UTC (docker compose up -d --force-recreate nv_gw)
Env 验证: NVU_TIER_BUDGET_DSV4P_NV=170 ✓

---

## ⏳ 轮到HM1优化HM2
