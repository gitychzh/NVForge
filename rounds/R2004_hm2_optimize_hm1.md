# R2004 (HM2→HM1): NOP — R2003 刚部署 5min, 零 post-deploy 流量

**时间**: 2026-07-20 07:55 UTC
**触发**: HM1 commit `205bbff` R2003 (HM2→HM1) — NVU_TIER_BUDGET_GLM5_2_NV 24→22
**作者**: opc2_uname (HM2)

## 1. 改前数据 (2026-07-20 07:55 UTC)

### 1.1 容器状态
- `nv_gw`: Up 5 minutes (healthy) — R2003 部署后重启
- 容器 StartedAt: `2026-07-19T23:51:31Z`

### 1.2 环境参数 (docker exec nv_gw env)
| 参数 | 值 | 来源 |
|------|-----|------|
| `NVU_TIER_BUDGET_GLM5_2_NV` | 22 | R2003 |
| `NVU_TIER_BUDGET_DSV4P_NV` | 20 | 稳定 |
| `TIER_TIMEOUT_BUDGET_S` | 151 | 稳定 |
| `NVU_PEER_FALLBACK_TIMEOUT` | 122 | 稳定 |
| `UPSTREAM_TIMEOUT` | 30 | 稳定 |
| `KEY_COOLDOWN_S` | 60 | 稳定 |
| `TIER_COOLDOWN_S` | 60 | 稳定 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | floor |
| `NVU_EMPTY_200_FASTBREAK` | 1 | floor |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | 稳定 |
| `FALLBACK_HEALTH_THRESHOLD` | 0.05 | 稳定 |

### 1.3 DB 数据 (R2003 部署前窗口, 6h)
| request_model | total | ok | fail | avg_ok_ms | max_ok_ms |
|---------------|-------|-----|------|-----------|-----------|
| glm5_2_nv | 31 | 26 | 5 | 6024 | 28697 |
| dsv4p_nv | 10 | 10 | 0 | 31599 | 55335 |

### 1.4 错误分布 (6h)
| 错误类型 | 数量 | 真实失败 | 可修性 |
|----------|------|---------|--------|
| zombie_empty_completion | 5 | 5 (status=502) | NVCF 函数级退化, 不可配置修复 |
| all_tiers_exhausted (phantom) | 27 | 0 (全部 status=200) | peer-fb 已救援 |

### 1.5 30min 窗口
- 仅 2 条请求 (均为 23:33 UTC 的旧数据, 非 post-deploy 流量)
- 1 OK (glm5_2_nv, 6978ms), 1 zombie (glm5_2_nv, 4874ms)
- 零 post-deploy 流量 — 容器仅启动 5min

### 1.6 Docker Logs
- 无 ERROR/WARN/exception
- 正常启动: `[NV-PROXY] Listening on 0.0.0.0:40006`

## 2. 介入四条判定

| # | 条件 | 判定 | 证据 |
|---|------|------|------|
| 1 | 有可修故障 | ❌ | 5 zombie = NVCF 函数级退化, 非配置可修 |
| 2 | 有真实 ATE | ❌ | 27 ATE 全部 phantom (status=200), peer-fb 已救援 |
| 3 | 参数未到底 | ❌ | 可优化参数 BUDGET_GLM5_2=22 仍有空间, 但零 post-deploy 数据 |
| 4 | 有可优化参数 | ❌ | 零 post-deploy 流量, 无法评估 R2003 效果 |

**结论: 四条全不满足 → NOP**

## 3. 决策分析

| 参数 | 旧值 | 候选 | 决策 | 理由 |
|------|------|------|------|------|
| NVU_TIER_BUDGET_GLM5_2_NV | 22 | 20 | ❌ | 零 post-deploy 流量, 无法评估 R2003 24→22 效果 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 64 | ❌ | 零 post-deploy 流量, 无数据支撑 |
| 所有参数 | — | — | ❌ | 改前必有数据铁律触发 |

**NOP 原因**: R2003 刚部署 5 分钟, 零 post-deploy 流量。改前必有数据铁律禁止盲改。等待足够数据积累后再评估。

## 4. 铁律

- 只改 HM1 不改 HM2 ✓ (本轮无改动)
- 改前必有数据 ✓ (有数据, 判定为 NOP)
- 改后有验证 ✓ (N/A)
- 聚焦 nv_gw ✓
## ⏳ 轮到HM1优化HM2
