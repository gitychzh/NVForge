# HM2 Optimize HM1 — Round R1017

> **NOP (false trigger, double-dispatch). R1016 symlink already correct, data identical.**
> 6h: 244req/220OK(90.2%)/24ATE. All FASTBREAK=1 floor, UPSTREAM=66 non-binding, TIER_COOLDOWN=15 optimal, all params at floor/optimal. minimax NVCF degraded, dsv4p IntegrateTimeout code-level. Single param; iron rule: only change HM1 never HM2.

---

## 1. 触发判定

- **cron 脚本输出**: `这是我提交的, 不触发`
- **最新 commit author**: `opc2_uname` (HM2)
- **R1016 symlink**: `RN_hm2_optimize_hm1.md → rounds/R1016_hm2_optimize_hm1.md` ✓ (已正确)
- **判定**: 假触发 — HM2 自提交, 非 HM1 新提交
- **R1016 已处理**: TIER_COOLDOWN_S 25→15 (−10s)

## 2. HM1 数据收集 (改前必有数据)

### 2.1 容器状态

| 项目 | 值 |
|------|-----|
| 容器 | nv_gw |
| 重启时间 | 2026-07-09T18:15:19Z (R1016 deploy) |
| HEALTH_THRESHOLD | 0.1 (func_health.py) |
| FALLBACK_GRAPH | {} (R832 空设计) |

### 2.2 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 244 |
| 成功 (200) | 220 |
| 失败 (ATE) | 24 |
| SR | 90.2% |
| fallback_occurred | 8 true / 236 false |

### 2.3 按模型 SR

| 模型 | OK | ATE | SR |
|------|-----|-----|-----|
| glm5_2_nv | 124 | 6 | 95.4% |
| dsv4p_nv | 59 | 12 | 83.1% |
| kimi_nv | 24 | 0 | 100.0% |
| minimax_m3_nv | 13 | 6 | 68.4% |

### 2.4 ATE 分析 (24 全部 single-tier, all_tiers_failed)

| 模型 | ATE | 模式 | 根因 |
|------|-----|------|------|
| dsv4p_nv | 12 | 8×112,054ms BUDGET-bound, 3×~61s IntegrateTimeout, 2×2ms cooldown skip | BUDGET=112 绑定; NVCF IntegrateTimeout 代码级 |
| glm5_2_nv | 6 | 129-208s, NVCF degraded | NVCF 上游问题, 非配置可修 |
| minimax_m3_nv | 6 | 151-159s, NVCF degraded | NVCF 上游问题, 非配置可修 |

### 2.5 tier_attempts (6h)

| Tier | Error Type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | IntegrateTimeout | 14 | 56,021 | 67,086 |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134 | 9,134 |
| kimi_nv | empty_200 | 1 | - | - |

### 2.6 日志关键事件 (nv_proxy.2026-07-10.log)

```
[02:01:13] dsv4p_nv empty_200 k3 → NV-EMPTY-FASTBREAK (1≥1) → NV-TIER-FAIL (all 5 keys, empty200=1)
[02:01:13] NV-GLOBAL-COOLDOWN tier=dsv4p_nv all keys empty_200, cooling 25s
[02:02:17] dsv4p_nv NV-TIER-SKIP all keys in cooldown → 2ms ATE
[02:02:23] dsv4p_nv NV-TIER-SKIP all keys in cooldown → 2ms ATE
```

### 2.7 ms_gw 状态

- 6h: 18 请求, 全部成功 (MS-OK, MS-STREAM-DONE)
- 无错误, 无 MS-ALL-EXHAUSTED

## 3. 当前配置 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 地板 (floor) |
| NVU_EMPTY_200_FASTBREAK | 1 | 地板 (floor) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 地板 (floor) |
| UPSTREAM_TIMEOUT | 66 | 非绑定 (NVCFPexecTimeout max << 66) |
| TIER_TIMEOUT_BUDGET_S | 112 | 绑定 (dsv4p_nv ATE 精确 112,054ms) |
| TIER_COOLDOWN_S | 15 | R1016 刚优化 (25→15) |
| KEY_COOLDOWN_S | 25 | KEY≥TIER 不变量保留 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | 有效参数 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 对齐 UPSTREAM |
| NVU_MS_GW_FALLBACK_TIMEOUT | 45 | 标准 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 地板 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 地板 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | 已设置 |

## 4. 优化决策

### 4.1 无优化空间

- **所有 FASTBREAK=1** (floor): PEXEC, EMPTY_200, INTEGRATE — 无法再降
- **UPSTREAM_TIMEOUT=66**: NVCFPexecTimeout 非绑定, 无需调整
- **TIER_COOLDOWN_S=15**: R1016 刚优化, 需观察多轮数据验证
- **BUDGET=112**: dsv4p_nv ATE 精确 112,054ms 表明 BUDGET 绑定, 但根因是 NVCF IntegrateTimeout (代码级: dsv4p_nv 不在 NV_INTEGRATE_MODELS 中却走 integrate 路径) — 非配置可修
- **minimax_m3_nv**: NVCF 函数级降级, 非配置可修
- **glm5_2_nv**: NVCF 上游问题, 非配置可修
- **ms_gw**: 健康, 无优化需求

### 4.2 决策: NOP

数据与 R1016 完全一致 (90.2% SR, 24 ATE), 所有可优化参数均在地板值或最优值。幸存 ATE 均为 NVCF 上游问题或代码级缺陷, 非配置可修。

## 5. 验证清单

- [x] 改前数据完整 (6h DB, 容器 env, 日志, tier_attempts)
- [x] 所有 FASTBREAK=1 地板验证
- [x] TIER_COOLDOWN=15 刚优化, KEY≥TIER 不变量保留
- [x] FALLBACK_GRAPH={} 符合 R832 设计
- [x] ms_gw 健康 (18/18 成功)
- [x] 铁律: 只改 HM1 不改 HM2 (NOP — 无改动)

## ⏳ 轮到HM1优化HM2
