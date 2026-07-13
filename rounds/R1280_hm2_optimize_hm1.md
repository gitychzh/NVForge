# R1280: HM2→HM1 — NOP (全部参数 floor/optimal, zombie code-level, 0 dsv4p_nv traffic)

> **Decision**: NOP — 零参数变更。所有失败为 zombie_empty_completion (code-level, NVCF content-filter)。全部参数在 floor/optimal。R1275 MODELMAP fix 待 dsv4p_nv 流量验证。
> **Date**: 2026-07-14 05:10 UTC
> **Trigger**: HM1 cron 判定 HM2 执行优化 (false trigger / self-commit)
> **Author**: opc2_uname

---

## 数据采集

### 容器状态
| 容器 | 状态 | StartedAt |
|------|------|-----------|
| nv_gw | Up 48 min (healthy) | 2026-07-13T20:23:46Z (~9.5h ago) |
| logs_db | Up 11 hours (healthy) | — |

### 容器 env (关键参数)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=210
MIN_OUTBOUND_INTERVAL_S=0              (floor)
NVU_PEXEC_TIMEOUT_FASTBREAK=1          (floor)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_CONNECT_RESERVE_S=0                (floor)
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=2              (optimal)
NV_INTEGRATE_KEY_COOLDOWN_S=0          (floor)
NV_INTEGRATE_MODELS=glm5_2_nv
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=200
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_PEER_FB_SKIP_MODELS=               (空)
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
```

### 日志 (最近 100 行, 无 ERROR/WARN)
- 全部 NV-INTEGRATE-SUCCESS (glm5_2_nv, first-attempt, k1-k5 轮转)
- 2× NV-ZOMBIE-EMPTY: glm5_2_nv content_chars=12 < 50, input_chars=212K+/213K+ ≥ 5000
- 0× NVCFPexecTimeout, 0× SSLEOF, 0× 429, 0× empty_200, 0× ATE

### DB 数据

#### 6h 全景 (now() - 6h)
| 指标 | 值 |
|------|-----|
| Total | 66 |
| OK | 51 (77.3%) |
| Fail | 15 |
| avg_ok_ms | 12,834ms |
| max_ok_ms | 54,918ms |
| total_kc429 | 0 |
| integrate | 53 |
| pexec | 10 |

#### Per-model 6h
| model | cnt | ok | fail | SR | avg_ok_ms | max_ok_ms |
|-------|-----|-----|------|-----|-----------|-----------|
| glm5_2_nv | 53 | 41 | 12 | 77.4% | 9,654ms | 44,489ms |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 25,873ms | 54,918ms |

#### Error distribution 6h
| error_type | cnt | avg_ms | max_ms |
|------------|-----|--------|--------|
| zombie_empty_completion | 12 | 9,108ms | 27,673ms |
| all_tiers_exhausted | 3 | 72,019ms | 72,023ms |

#### Post-deploy (since 20:23 UTC)
| 指标 | 值 |
|------|-----|
| Total | 6 |
| OK | 4 |
| Fail | 2 (all zombie_empty_completion) |
| ATE | 0 |
| integrate_ok | 4 |
| pexec_ok | 0 |
| 0 dsv4p_nv traffic |

#### 小时趋势
| hour UTC | total | ok | fail |
|----------|-------|-----|------|
| 15:00 | 3 | 2 | 1 |
| 16:00 | 6 | 4 | 2 |
| 17:00 | 6 | 4 | 2 |
| 18:00 | 36 | 31 | 5 |
| 19:00 | 6 | 4 | 2 |
| 20:00 | 6 | 4 | 2 |
| 21:00 | 3 | 2 | 1 |

#### nv_tier_attempts 6h
- 0 records — 所有成功请求首次尝试即成功, 零失败尝试

---

## 决策分析

### 失败分类
1. **zombie_empty_completion (12×, 100% of post-deploy fails)**: NVCF 返回 `finish_reason=stop` 但 content_chars=8-12 < 50, input_chars=157K-213K ≥ 5000。这是 code-level zombie 检测, 非参数可修。触发 openclaw fallback。
2. **all_tiers_exhausted (3×, pre-restart)**: 全部为 dsv4p_nv, 发生在 R1275 MODELMAP fix 之前 (ms_gw 无 dsv4p 条目)。Post-deploy 0 个 ATE → R1275 修复有效, 但 0 dsv4p_nv traffic 无法确认。

### 候选参数评估

| 参数 | 当前值 | 候选 | 评估 | 决策 |
|------|--------|------|------|------|
| UPSTREAM_TIMEOUT | 66 | 64(-2s) | NVCFPexecTimeout max binding at 66s; 降低会截断成功请求 (max_ok=54,918ms, margin 11s 但为 pexec 非 integrate)。但 0 pexec post-deploy 无数据支撑 | ❌ 无数据支撑 |
| TIER_TIMEOUT_BUDGET_S | 210 | 200(-10s) | max_ok=54,918ms << 210s, 余量 155s。但降低不改���任何指标 (失败路径无关 BUDGET) | ❌ 无收益 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 64(-2s) | 对齐 UPSTREAM=66。但 peer fallback 0 次 post-deploy，无数据 | ❌ 无数据 |
| NVU_EMPTY_200_FASTBREAK | 2 | 1(-1) | 1=floor。R1031 从 1→2 修复 key-specific empty_200 transient。当前 0 empty_200 事件 | ❌ floor已达 |
| TIER_COOLDOWN_S | 15 | 13(-2s) | R1103 从 18→15。但 0 tier_attempts, 无多 tier 尝试, 降低无收益 | ❌ 无收益 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | 70(-2s) | 0 dsv4p_nv pexec traffic, 无法验证 | ❌ 无数据 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 94(-2s) | 全部 glm5_2 走 integrate (非 pexec), 此参数仅影响 pexec 路径 | ❌ 不适用 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 40(-2s) | 主动断流让 fallback 跑。但 zombie 已触发 fallback, 缩短无额外收益 | ❌ 无收益 |
| NVU_FORCE_STREAM_UPGRADE | 0 | — | 已禁用, floor | ❌ floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | — | floor | ❌ floor |
| NVU_CONNECT_RESERVE_S | 0 | — | floor | ❌ floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | — | floor | ❌ floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | — | floor | ❌ floor |

### 结论
**NOP** — 全部参数在 floor/optimal。所有失败为 zombie_empty_completion (code-level), 3 个 ATE 为 pre-R1275 MODELMAP 历史数据。R1275 MODELMAP fix 待 dsv4p_nv 流量验证。零参数调整空间。

---

## 四源一致性验证
- ✅ Compose: 无需检查 (NOP, 无变更)
- ✅ Container env: 与 R1273 快照一致
- ✅ Container StartedAt: 2026-07-13T20:23:46Z (R1265 deploy, 无新重启)
- ✅ 日志: 零 ERROR/WARN, NV-INTEGRATE-SUCCESS first-attempt, NV-ZOMBIE-EMPTY → openclaw fallback

## ⏳ 轮到HM1优化HM2