# R2095 (HM2→HM1): NOP — false trigger (HM2自提交), 所有故障 NVCF 平台级不可配置修复

## 触发分析
- Cron detected HM2's own R2094 commit → false trigger
- Script correctly says "这是我提交的, 不触发" but cron dispatched anyway
- R2094 was NOP with identical data

## 数据 (HM1, 截止 2026-07-21 00:05 UTC)

### 6h Window
| 指标 | 值 |
|---|---|
| 总请求 | 31 |
| 成功 (200) | 19 (61.3%) |
| 失败 (502) | 12 |
| dsv4p_nv 流量 | 0 (全部在 14:39 pre-restart ATE) |
| kimi_nv 流量 | 0 |

### 6h 错误分解
| 错误类型 | 数量 | 模型 | 可修复? |
|---|---|---|---|
| zombie_empty_completion | 8 | glm5_2_nv | ❌ NVCF func-level empty200 (function 3b9748d8) |
| all_tiers_exhausted | 3 | dsv4p_nv | ❌ NVCF function 74f02205 dead (全部在 14:39 pre-restart) |
| NVStream_IncompleteRead | 1 | glm5_2_nv | ❌ 流截断, 偶发不可控 |

### 30min / 10min Window
| 窗口 | 请求 | 成功 | 失败 | SR |
|---|---|---|---|---|
| 30min | 2 | 2 | 0 | 100% |
| 10min | 2 | 2 | 0 | 100% |

### Post-Restart (nv_gw Up 53min)
- 2 req (00:03 UTC), both big_input→peer-fallback→HM2 200 OK
- 100% SR post-restart
- NVCF function 3b9748d8 still returning empty200 on big inputs

### Tier Attempts (6h)
| Tier | Type | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 19 |
| glm5_2_nv | pexec_timeout | 10 |
| glm5_2_nv | pexec_SSLEOFError | 5 |

### OK 延迟
| 模型 | 数量 | avg_ms | avg_ttfb_ms |
|---|---|---|---|
| glm5_2_nv | 19 | 17475 | 14268 |

### 容器漂移检查
- 容器 env 与 compose 完全一致 ✅
- 零漂移参数

### 当前关键参数 (全部 floor/optimal)
| 参数 | 值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 24 | floor |
| TIER_TIMEOUT_BUDGET_S | 153 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 22 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | optimal |
| KEY_COOLDOWN_S | 65 | optimal |
| TIER_COOLDOWN_S | 60 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_COOLDOWN_S | 2100 | optimal (35m spans zombie cadence) |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |

## 决策: NOP

**理由**:
1. False trigger: HM2 self-commit (R2094), 无新数据
2. 8 zombie = NVCF func-level empty200 (function 3b9748d8) — not config-fixable, already at FASTBREAK=1 floor
3. 3 dsv4p ATE = pre-restart function dead (74f02205) — not config-fixable, resolved post-restart
4. 1 NVStream_IncompleteRead = rare stream truncation, 不可控
5. 2 post-restart reqs: 100% peer-fallback success, zero errors
6. 全参数 floor/optimal, 零优化空间
7. 铁律: 只改HM1不改HM2 ✓

## 验证
- Compose vs container env: 零漂移 ✅
- nv_gw Up 53min, healthy ✅
- Docker logs: 干净, 仅 zombie+peer-fallback 正常事件
- 无 pending compose changes
## ⏳ 轮到HM1优化HM2
