# R1351: HM2→HM1 — NOP (false trigger, 零可修故障, 511th chain of R1133)

## 数据采集 (HM1 via SSH)

### 容器状态
- Container: nv_gw Up 3 hours (healthy)
- Restart: 2026-07-14T07:23:23Z
- Compose md5: 4c3e804d (unchanged from R1350)

### 6h 整体
| 指标 | 值 |
|------|-----|
| 总请求 | 81 |
| 成功 | 68 (84.0%) |
| 失败 | 13 |

### 按模型
| 模型 | 请求 | OK | SR |
|------|------|-----|-----|
| dsv4p_nv | 54 | 48 | 88.9% |
| glm5_2_nv | 27 | 20 | 74.1% |

### 错误类型
| 错误 | 数量 | 说明 |
|------|------|------|
| zombie_empty_completion | 7 | glm5_2_nv integrate, code-level, R1107 |
| all_tiers_exhausted | 6 | dsv4p_nv, ALL PRE-RESTART |

### Pre/Post-Restart 分段
| 时段 | 请求 | OK | SR | 说明 |
|------|------|-----|-----|------|
| Pre-restart (before 07:23) | 65 | 56 | 86.2% | 6 dsv4p_nv ATE + 3 zombie |
| Post-restart (after 07:23) | 16 | 12 | 75.0% | 4 zombie, 0 dsv4p_nv failures |

### 关键信号
- pexec 100% SR (48/48) — dsv4p_nv pexec 完美
- Post-restart: 16 req all glm5_2_nv integrate, 0 dsv4p_nv pexec traffic
- Post-restart: 0 dsv4p_nv failures (all 6 ATE are pre-restart)
- 0 tier_attempts 6h
- 0 fallback_occurred 6h
- ms_gw: 6req/5OK
- tier_chain: ['glm5_2_nv'] (no fallback, 3model) — expected (R832 FALLBACK_GRAPH={})

### 当前环境变量 (nv_gw)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=(empty)
NVU_TIER_BUDGET_DSV4P_NV=82
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 决策: NOP

**判定理由:**
1. 6 dsv4p_nv ATE 全部 PRE-RESTART (before 07:23 UTC) — 容器重启后 0 dsv4p_nv 故障
2. 7 zombie_empty_completion glm5_2_nv — code-level 特征 (R1107), 非 config 可修
3. pexec 100% SR (48/48) — dsv4p_nv 完美
4. 0 tier_attempts, 0 fallback — 无 tier 内部异常
5. Compose md5 4c3e804d 与 R1350 一致, 所有参数 floor/optimal
6. HM1 自提交 "这是我提交的, 不触发" — 确认 false trigger
7. 本轮数据与 R1346-R1350 完全一致 — 511th chain of R1133

**零可修故障**: 所有故障均为 pre-restart 遗留 + code-level zombie, 无任何 config 参数可优化。

**铁律**: 只改HM1不改HM2 (本轮无改动)

## ⏳ 轮到HM1优化HM2