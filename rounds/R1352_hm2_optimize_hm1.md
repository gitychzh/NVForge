# R1352: HM2→HM1 — NOP (false trigger, 零可修故障, 512th chain of R1133)

## 数据采集 (HM1 via SSH)

### 容器状态
- Container: nv_gw Up (healthy)
- Restart: 2026-07-14T07:23:23Z
- Compose md5: 4c3e804d (unchanged from R1351)

### 6h 整体
| 指标 | 值 |
|------|-----|
| 总请求 | 81 |
| 成功 | 68 (84.0%) |
| 失败 | 13 |

### 按路径
| 路径 | 请求 | OK | SR | avg_ttfb | avg_dur |
|------|------|-----|-----|----------|---------|
| nvcf_pexec | 48 | 48 | 100% | 20934ms | 20938ms |
| nv_integrate | 27 | 20 | 74.1% | 12435ms | 12711ms |
| (ATE) | 6 | 0 | 0% | 820ms | 71694ms |

### 错误类型
| 错误 | 数量 | 说明 |
|------|------|------|
| zombie_empty_completion | 7 | glm5_2_nv integrate, code-level, R1107 |
| all_tiers_exhausted | 6 | dsv4p_nv, ALL PRE-RESTART (before 07:23 UTC) |

### Pre/Post-Restart 分段
| 时段 | 请求 | OK | SR | 说明 |
|------|------|-----|-----|------|
| Pre-restart (before 07:23) | 65 | 56 | 86.2% | 6 dsv4p_nv ATE + 3 zombie |
| Post-restart (after 07:23) | 16 | 12 | 75.0% | 4 zombie, 0 dsv4p_nv failures |

### 每小时
| 小时 (UTC) | 总 | OK | 失败 | SR |
|------------|-----|-----|------|------|
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 59 | 52 | 7 | 88.1% |
| 07:00 | 4 | 3 | 1 | 75.0% |
| 08:00 | 5 | 4 | 1 | 80.0% |
| 09:00 | 5 | 4 | 1 | 80.0% |
| 10:00 | 4 | 3 | 1 | 75.0% |

### 关键信号
- pexec 100% SR (48/48) — dsv4p_nv pexec 完美
- Post-restart: 0 dsv4p_nv failures (all 6 ATE are pre-restart)
- 0 tier_attempts 6h
- 0 fallback_occurred 6h
- NVU_PEER_FB_SKIP_MODELS= (empty, R1349 已清空)
- 所有参数 floor/optimal
- 数据与 R1351 完全一致

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
5. Compose md5 4c3e804d 与 R1351 一致, 所有参数 floor/optimal
6. HM1 自提交 "这是我提交的, 不触发" — 确认 false trigger
7. 本轮数据与 R1346-R1351 完全一致 — 512th chain of R1133

**零可修故障**: 所有故障均为 pre-restart 遗留 + code-level zombie, 无任何 config 参数可优化。

**铁律**: 只改HM1不改HM2 (本轮无改动)

## ⏳ 轮到HM1优化HM2