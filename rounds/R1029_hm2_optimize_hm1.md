# R1029: HM2→HM1 — NOP (false trigger, all params at floor/optimal, zero post-restart data)

## 触发
- 脚本检测到 HEAD=85115f5 (R1028, HM2's own commit) → 误触发 HM2 dispatch
- `这是我提交的, 不触发` 标记被忽略 → double-dispatch
- 无 HM1→HM2 新回合 (R1029_hm1_optimize_hm2.md 不存在)

## 数据收集 (改前必有数据)

### 6h Overall (2026-07-10 ~05:10 UTC)
| Metric | Value |
|--------|-------|
| Total requests | 415 |
| OK (200) | 387 |
| Fail | 28 |
| SR% | 93.3% |
| nvcf_pexec path | 94/94 100% SR (零 NVCFPexecTimeout) |
| ms_gw health | ✅ healthy, MS-OK + MS-STREAM-DONE |

### 6h Per-Model
| Model | Total | OK | Fail | SR% | Avg ms | P50 ms | P95 ms |
|-------|-------|-----|------|-----|--------|--------|--------|
| dsv4p_nv | 70 | 61 | 9 | 87.1% | 19,511 | 7,640 | 61,095 |
| glm5_2_nv | 255 | 245 | 10 | 96.1% | 22,586 | 11,098 | 81,254 |
| kimi_nv | 52 | 51 | 1 | 98.1% | 11,462 | 3,821 | 37,543 |
| minimax_m3_nv | 38 | 30 | 8 | 78.9% | 43,838 | 12,896 | 155,112 |

### 6h Error Breakdown
| Error Type | Count | Avg ms | Max ms |
|-----------|-------|--------|--------|
| all_tiers_exhausted | 28 | 93,582 | 208,108 |
| NVStream_TimeoutError | 3 | 94,904 | 98,823 |
| stream_total_deadline | 3 | 69,014 | 94,589 |

### ATE by Model
| Model | ATE Count | Avg ms | Max ms |
|-------|----------|--------|--------|
| minimax_m3_nv | 11 | 110,940 | 159,342 |
| dsv4p_nv | 9 | 47,478 | 61,249 |
| glm5_2_nv | 7 | 130,263 | 208,108 |
| kimi_nv | 1 | 60,811 | 60,811 |

### Stream Errors Per-Model Per-Key (6h)
| Model | Key | Error | Count | Avg ms |
|-------|-----|-------|-------|--------|
| glm5_2_nv | k0 | stream_total_deadline | 2 | 78,269 |
| glm5_2_nv | k2 | NVStream_TimeoutError | 1 | 94,360 |
| glm5_2_nv | k3 | NVStream_TimeoutError | 1 | 91,529 |
| glm5_2_nv | k4 | NVStream_TimeoutError | 1 | 98,823 |
| minimax_m3_nv | k0 | stream_total_deadline | 1 | 50,505 |

### minimax_m3_nv ATE Detail
- 11 ATEs: 7 NULL-key (avg 153,912ms — NV tiers exhausted → ms_gw rescue), 1 stream_deadline on k0 (50,505ms)
- ms_gw rescue: 4/11 ATEs rescued (status=200 via fallback), 7 true failures
- Tier attempts: only 1 IntegrateTimeout at 90,762ms — FASTBREAK=1 should abort early but R1014 pitfall: FASTBREAK not effective in integrate mode for minimax (code-level)

### nv_gw Env (all params)
| Param | Value | Status |
|-------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | stable |
| TIER_TIMEOUT_BUDGET_S | 110 | >>66 safe |
| NVU_STREAM_TOTAL_DEADLINE_S | 66 | R1028 changed from 42→66 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 18 | stable |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | model-specific |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 180 | model-specific |
| NV_INTEGRATE_THINKING_TIMEOUT_S | 90 | model-specific |
| NVU_MS_GW_FALLBACK_TIMEOUT | 45 | stable |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | stable |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | stable |

### nv_gw Status
- Container restarted ~12 min ago (R1028 deploy on HM1 side)
- `/health` → `{"status": "ok"}`
- **Zero post-restart requests** (night/low-traffic window)
- All cooldowns empty
- ms_gw healthy (MS-OK, MS-STREAM-DONE)

## 分析

### 为什么是 NOP
1. **False trigger**: HEAD=85115f5 是 HM2 自己提交的 R1028, 不是 HM1 的新 round。脚本标记 `这是我提交的, 不触发` 但系统仍触发了 HM2 dispatch
2. **Zero post-restart data**: nv_gw 刚重启 12 分钟, 夜间低流量, DB 零新请求。无数据支撑任何参数变更
3. **All params at floor**: FASTBREAKs 全=1, MIN_OUTBOUND=0, INTEGRATE_KEY_COOLDOWN=0, CONNECT_RESERVE=0, SSLEOF_RETRY=1.0 — 无法再降
4. **R1028 change needs data**: NVU_STREAM_TOTAL_DEADLINE_S 42→66 刚部署, 需积累数据验证效果。stream_total_deadline 和 NVStream_TimeoutError 的 3+3=6 次错误全来自 pre-restart 窗口
5. **minimax_m3_nv 78.9% SR**: 最差模型但 ATE 根源是 R1014 pitfall (FASTBREAK=1 在 integrate 模式不生效, 代码级缺陷, 非配置可修)

### 参数检查清单
| 参数 | 值 | 可调? | 理由 |
|------|-----|-------|------|
| NVU_STREAM_TOTAL_DEADLINE_S | 66 | ❌ 刚改, 需数据 |
| UPSTREAM_TIMEOUT | 66 | ❌ 稳定, 零 NVCFPexecTimeout |
| TIER_TIMEOUT_BUDGET_S | 110 | ❌ >>66 安全, 收紧无意义 |
| KEY_COOLDOWN_S | 25 | ❌ floor 等效 |
| TIER_COOLDOWN_S | 18 | ❌ stable |
| NVU_EMPTY_200_FASTBREAK | 1 | ❌ floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ❌ floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | ❌ floor (R1014: 代码级不生效) |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 180 | ❌ 充足 (max ATE=159s < 180) |

## 变更
**Zero param change; zero compose edit; zero restart.**

## 铁律确认
- ✅ 改前必有数据 (6h DB + logs + env — 但数据全 pre-restart, 零 post-restart)
- ✅ 聚焦 nv_gw (仅 40006 链)
- ✅ 所有修改写入仓库 (NOP 回合记录)
- ✅ 只改 HM1 不改 HM2
- ✅ 少改多轮 (本轮不改, 等数据积累)

## ⏳ 轮到HM1优化HM2