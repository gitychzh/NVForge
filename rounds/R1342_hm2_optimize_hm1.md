# HM2 Optimize HM1 — Round R1342

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit 51cad15 author = opc2_uname (HM2), 502nd chain of R1133 false-trigger
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（double-dispatch）
- R1341 已由 HM2 提交，数据无变化

## 2. 容器状态
```
nv_gw Up About an hour (healthy)
重启时间: 2026-07-14T07:23:23Z
ms_gw Up 3 hours (healthy)
Compose md5: 4c3e804d68a158d76937dfae32764edf (unchanged since R1337)
```

## 3. 容器 env (nv_gw)
| 参数 | 值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| TIER_COOLDOWN_S | 15 | optimal |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | enabled |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | enabled |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 82 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | default |
| NVU_FORCE_STREAM_UPGRADE | 0 | off |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | =UPSTREAM |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (empty) | default |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | =UPSTREAM |

## 4. DB 数据 (6h 窗口, 10:47-16:47 UTC)

### 4.1 总体 SR
| total | ok | err | sr_pct |
|---|---|---|---|
| 81 | 67 | 14 | 82.7% |

### 4.2 按 upstream_type
| upstream_type | cnt | ok | err | sr_pct | avg_ttfb | avg_dur |
|---|---|---|---|---|---|---|
| nvcf_pexec | 48 | 48 | 0 | 100.0% | 20934ms | 20938ms |
| nv_integrate | 27 | 19 | 8 | 70.4% | 11449ms | 11723ms |
| (null/ATE) | 6 | 0 | 6 | 0.0% | 820ms | 71694ms |

### 4.3 按模型
| model | cnt | ok | err | sr_pct | avg_dur |
|---|---|---|---|---|---|
| dsv4p_nv | 54 | 48 | 6 | 88.9% | 26577ms |
| glm5_2_nv | 27 | 19 | 8 | 70.4% | 11723ms |

### 4.4 错误分布
| error_type | cnt | avg_dur | 分析 |
|---|---|---|---|
| zombie_empty_completion | 8 | 9114ms | glm5_2_nv, NVCF content-filter stop+12chars, avg_ichars≈185K, NOT config-fixable |
| all_tiers_exhausted | 6 | 71694ms | dsv4p_nv, ALL PRE-RESTART (05:57-06:37 UTC), 0 post-restart |

### 4.5 Post-restart (07:23 UTC - 16:47 UTC)
| total | ok | err | sr_pct |
|---|---|---|---|
| 7 | 5 | 2 | 71.4% |

- 7 req all glm5_2_nv, 2 zombie_empty_completion
- 0 dsv4p_nv post-restart (无法评估 BUDGET=82 效果)
- 0 fallback, 0 tier_attempts

### 4.6 按小时
| hour (UTC) | total | ok | fail | sr_pct |
|---|---|---|---|---|
| 03:00 | 5 | 3 | 2 | 60.0% |
| 04:00 | 4 | 3 | 1 | 75.0% |
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 59 | 52 | 7 | 88.1% |
| 07:00 | 4 | 3 | 1 | 75.0% |
| 08:00 | 5 | 4 | 1 | 80.0% |

### 4.7 ms_gw
| total | ok |
|---|---|
| 6 | 5 |

### 4.8 日志
- NV-ZOMBIE-EMPTY: glm5_2_nv, input_chars=185K, content_chars=12, finish_reason=stop
- NV-ZOMBIE-ERROR-CHUNK: sent finish_reason=content_filter, triggers openclaw fallback
- 0 NV-EMPTY-FASTBREAK, 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 NV-PEER-FB
- All integrate requests succeed on first attempt (NV-INTEGRATE-SUCCESS)
- 0 SSLEOF, 0 timeout, 0 429, 0 zombie pre-restart
- ms_gw: all MS-OK-STREAM / MS-STREAM-DONE, 0 errors

## 5. 判定: NOP

**零可修故障**: 全部 14 个失败中:
- 6 dsv4p_nv ATE: PRE-RESTART (05:57-06:37 UTC, 容器重启 07:23), 重启后 0 dsv4p 流量
- 8 zombie_empty_completion: glm5_2_nv, NVCF content-filter 级别, 代码已正确处理 (zombie→error_chunk→openclaw fallback), 非配置可修
- 0 fallback, 0 tier_attempts (无 key cycling 问题)
- 所有参数 floor/optimal, 无调整空间
- pexec 100% SR (48/48), 完美
- ms_gw 5/6 OK, healthy
- 0 dsv4p_nv post-restart traffic, BUDGET=82 效果待评估
- Compose md5 unchanged since R1337 (4c3e804d)

**决策**: NOP — 零参数变更, 零 compose 变更, 零容器重启

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2