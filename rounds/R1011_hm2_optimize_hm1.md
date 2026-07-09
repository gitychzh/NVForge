# HM2 Optimize HM1 — Round R1011

**日期**: 2026-07-10 00:55 UTC
**角色**: HM2 (opc2_uname) → HM1 (opc_uname @ 100.109.153.83)
**触发**: False trigger — cron 脚本输出 "这是我提交的, 不触发", 最新 commit author = opc2_uname (HM2)
**类型**: NOP (false trigger, 无需变更)

---

## 1. 触发分析

- cron 脚本输出: `这是我提交的, 不触发` — 自提交检测正确
- 最新 commit: `2df6855 R1010: HM2→HM1 — NVU_INTEGRATE_TIMEOUT_FASTBREAK 2→1` (author=opc2_uname)
- HM2 提交了 R1010, HM1 尚未提交新内容 — 误触发
- R1010 已存在且正确, symlink 指向 `rounds/R1010_hm2_optimize_hm1.md`, 最后一行 `## ⏳ 轮到HM1优化HM2` ✓

---

## 2. HM1 容器状态

| 项目 | 状态 |
|------|------|
| nv_gw 容器 | Up 7 minutes (healthy), Started: 2026-07-09T16:49:14Z |
| ms_gw 容器 | healthy, 7 keys × 10 variants, no cooldowns |
| logs_db 容器 | 正常 |

---

## 3. nv_gw 关键参数 (全部 floor/optimal)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 112 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor (R1010) |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | R923 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | conservative |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |

---

## 4. 1h 数据 (2026-07-10 00:00:00 UTC → now)

| 指标 | 值 |
|------|-----|
| 总请求 | 42 |
| 成功 (200) | 40 |
| 错误 (502) | 2 |
| 成功率 | **95.2%** |

### 4.1 Per-tier 1h

| Tier | 请求 | OK | 错误 | SR |
|------|------|-----|------|-----|
| glm5_2_nv | 34 | 32 | 2 | 94.1% |
| kimi_nv | 4 | 4 | 0 | 100.0% |
| dsv4p_nv | 2 | 2 | 0 | 100.0% |
| minimax_m3_nv | 2 | 2 | 0 | 100.0% |

### 4.2 错误详情 (2 个, 全部 scheduler-gate ATE)

| 时间 | Tier | 状态 | 耗时 | 错误类型 | 上游 | 尝试tier数 |
|------|------|------|------|----------|------|-----------|
| 16:36:15 | glm5_2_nv | 502 | 174,716ms | all_tiers_exhausted | NULL | 1 |
| 16:34:00 | glm5_2_nv | 502 | 173,092ms | all_tiers_exhausted | NULL | 1 |

**诊断**: upstream_type=NULL → 请求从未被调度到任何 tier 键 (scheduler-gate)。不是 config-fixable。

### 4.3 延迟 (1h, status=200)

| Tier | 平均 | 最小 | 最大 | 样本 |
|------|------|------|------|------|
| kimi_nv | 1,977ms | 1,349ms | 3,002ms | 4 |
| dsv4p_nv | 3,263ms | 2,691ms | 3,834ms | 2 |
| minimax_m3_nv | 4,837ms | 4,577ms | 5,096ms | 2 |
| glm5_2_nv | 30,988ms | 4,929ms | 101,937ms | 32 |

---

## 5. nv_tier_attempts

### 1h: 0 行 — 干净, 无 tier 级错误

### 6h: 15 行

| Tier | 错误类型 | 次数 | 平均 | 最大 |
|------|----------|------|------|------|
| dsv4p_nv | IntegrateTimeout | 14 | 56,021ms | 67,086ms |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134ms | 9,134ms |
| kimi_nv | empty_200 | 1 | — | — |

**分析**: 6h dsv4p_nv IntegrateTimeout 14 次, max=67,086ms > UPSTREAM=66 — 分布在 6h 内, 属于正常 NVCF 上游波动。R1010 的 FASTBREAK=1 已覆盖 integrate timeout。

---

## 6. 6h ATE 分析

| tiers_tried_count | 次数 | 平均耗时 |
|-------------------|------|----------|
| 1 | 14 | 130,012ms |

| Tier | 次数 | 平均耗时 |
|------|------|----------|
| dsv4p_nv | 8 | 112,051ms |
| glm5_2_nv | 6 | 153,959ms |

全部 `fallback_actually_attempted=false` — FALLBACK_GRAPH={} (R832 空字典设计), ms_gw 同模型回退是预期路径。

---

## 7. ms_gw 状态

| 项目 | 值 |
|------|-----|
| 健康 | OK |
| EMPTY_200_FASTBREAK_THRESHOLD | 3 |
| UPSTREAM_TIMEOUT | 300 |
| KEY_COOLDOWN_S | 60 |
| VARIANT_COOLDOWN_S | 30 |
| 1h ms_requests | 2 |

ms_gw 稳定, 无优化空间。EMPTY_200_FASTBREAK_THRESHOLD=3 对 streaming 合理。

---

## 8. 决策

**NOP** — 无变更。

- 1h 95.2% SR, 2 个错误全部 scheduler-gate (upstream_type=NULL), 不 config-fixable
- 所有 4 个 tier 100% SR (除 glm5_2 scheduler-gate 外)
- 1h tier_attempts 0 行 — 干净
- 所有参数已 floor/optimal
- ms_gw 稳定无优化空间
- 铁律: 只改 HM1 不改 HM2

---

## 9. 变更

- **变更**: 无 (NOP)
- **验证**: 数据确认, 所有参数 floor/optimal, 无需调整
- **铁律**: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2