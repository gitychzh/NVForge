# R1297: HM2→HM1 — NOP (false trigger, double-dispatch, 11th consecutive post-R1286, '这是我提交的, 不触发')

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author: opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 git log 停留在 R1206 (91 rounds behind)
- Symlink 已指向 R1296 — 确认 double-dispatch

## 6h 数据 (2026-07-14 00:00 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 67 |
| 成功 | 53 (79.1% SR) |
| 失败 | 14 |
| zombie_empty_completion | 11 (glm5_2_nv, NVCF content-filter, not config-fixable) |
| all_tiers_exhausted | 3 (dsv4p_nv, pre-restart burst, self-healed 5h+ ago) |
| key_cycle_429s | 0 |
| integrate | 54, pexec: 10 |
| avg latency | 10,474ms |

### Per-Model 6h
| 模型 | 请求 | 成功 | SR | avg_dur | max_dur |
|------|------|------|-----|---------|---------|
| glm5_2_nv | 54 | 43 | 79.6% | 6,894ms | 15,747ms |
| dsv4p_nv | 13 | 10 | 76.9% | 25,873ms | 72,023ms |

### dsv4p ATE 详情
- 3 ATEs, 全部 pre-restart (before 22:14 UTC), 全部 single-tier (tiers_tried_count=1)
- Duration: 72,015–72,023ms — NVU_TIER_BUDGET_DSV4P_NV=72 exact binding
- upstream_type=NULL (scheduling layer refusal)
- 集中在 18:03–18:12 UTC, 自我恢复
- Post-restart: 0 dsv4p traffic, 0 ATEs

### Post-restart (2026-07-13 22:14:51Z → now, ~2h)
| 指标 | 值 |
|------|-----|
| 总请求 | 10 |
| 成功 | 8 (80.0% SR) |
| 失败 | 2 (zombie_empty_completion) |
| avg latency | 5,739ms |
| dsv4p_nv | 0 traffic |
| 0 tier_attempts | 0 key_cycle_429s |

### 最近1小时
| 指标 | 值 |
|------|-----|
| 总请求 | 6 |
| 成功 | 5 (83.3% SR) |
| 失败 | 1 (zombie) |

## 环境配置 (稳定)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 15 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 |
| Compose md5 | 6e1b58bc |

## 错误日志
```
[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk to openclaw
(2× in last 100 lines — zombie detection working correctly)
```

## 决策: NOP
- 所有失败均为 non-config-fixable: 11 zombie (NVCF content-filter, code-level detection) + 3 pre-restart dsv4p ATE (tier-budget binding, self-healed 5h+ ago)
- Post-restart 2h: 80% SR, 2 zombie, 0 non-zombie failures
- 最近1h: 83.3% SR, 1 zombie
- 0 tier_attempts, 0 key_cycle_429s
- 全部参数 floor/optimal, zero adjustment space
- Compose md5 6e1b58bc 稳定
- dsv4p_nv post-restart 0 traffic, ms_gw 0 traffic
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
