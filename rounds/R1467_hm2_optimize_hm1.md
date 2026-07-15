# HM2 Optimize HM1 — Round R1467

## 0. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` / `已处理过此commit(45a32cb), 等待新提交`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交 — **FALSE TRIGGER**
- 双调度: pre-run 已写入 R1466 NOP，已同步推送到 GitHub
- HM1 git log 停留在 R1206（261 轮落后），无新提交
- 这是 R1395 以来的第 47 次 false trigger dispatch

## 1. 数据收集 (6h 窗口)

### nv_requests 概览
| 指标 | 值 |
|------|-----|
| 总请求 | 42 |
| 200 OK | 19 |
| 失败 | 23 |
| 成功率 | 45.2% |
| compose md5 | 45c1f284 |
| 容器重启 | 2026-07-15T13:09:29Z |

### 错误分类
| 错误类型 | 数量 | 平均延迟 |
|---------|------|---------|
| zombie_empty_completion | 14 | 20,028ms |
| all_tiers_exhausted | 9 | 77,567ms |

### 按模型分布
| 模型 | 总计 | OK | 失败 | SR |
|------|------|-----|------|-----|
| glm5_2_nv | 27 | 15 | 12 | 55.6% |
| dsv4p_nv | 15 | 4 | 11 | 26.7% |

### zombie 按模型
| 模型 | 数量 | 平均延迟 |
|------|------|---------|
| glm5_2_nv | 11 | 12,083ms |
| dsv4p_nv | 3 | 49,159ms |

### ATE 按模型
| 模型 | 数量 | 平均延迟 | fallback_attempted |
|------|------|---------|-------------------|
| dsv4p_nv | 8 | 63,867ms | 0 (全部 false) |
| glm5_2_nv | 1 | 187,171ms | 0 |

### 每小时 SR
| 小时 (UTC) | 总计 | OK | 失败 | SR |
|-----------|------|-----|------|-----|
| 08:00 | 2 | 1 | 1 | 50.0% |
| 09:00 | 8 | 4 | 4 | 50.0% |
| 10:00 | 6 | 2 | 4 | 33.3% |
| 11:00 | 6 | 2 | 4 | 33.3% |
| 12:00 | 7 | 3 | 4 | 42.9% |
| 13:00 | 9 | 5 | 4 | 55.6% |
| 14:00 | 4 | 2 | 2 | 50.0% |

### ms_gw
- 总计: 24 请求, 20 OK
- ms_gw SR: 83.3%
- 4 error (无 normalized_backend_model)
- ms_gw params: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, VARIANT_COOLDOWN_S=30, UPSTREAM_TIMEOUT=300, MIN_OUTBOUND_INTERVAL_S=1.0 — all floor/optimal

### nv_tier_attempts
- 0 tier_attempts (6h)

### NV-MS-FB
- 0 total matches in nv_gw logs (since container restart)
- ms_gw fallback not triggered in 6h window

### nv_gw 日志分析
- `tier_chain=['dsv4p_nv']` / `['glm5_2_nv']` (no fallback, 3model) — EXPECTED: FALLBACK_GRAPH={} by R832 design
- 4× NV-ZOMBIE-EMPTY: glm5_2_nv integrate (content_chars=12-32, input_chars=218K+), dsv4p_nv pexec (content_chars=14-29, input_chars=218K+)
- NV-ZOMBIE-ERROR-CHUNK correctly sent → openclaw fallback trigger
- 0 NV-TIER-FAIL, 0 NV-FALLBACK, 0 NV-PEER-FB

### nv_gw 环境变量
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FALLBACK_ENABLED | 1 | optimal |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | optimal |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |
| PROXY_TIMEOUT | 360 | optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |

## 2. 决策

**NOP — 零参数变更，零 compose 变更，零容器重启。**

### 理由
1. **FALSE TRIGGER**: cron 脚本输出 `"这是我提交的, 不触发"` — HM2 自身提交，无 HM1 变更
2. **数据与 R1466 完全一致**: 42req/19OK/23fail, 14 zombie, 9 ATE, ms_gw 24/20 OK, 0 tier_attempts
3. **所有参数 floor/optimal**: UPSTREAM=66, FASTBREAK=1, BUDGET=205, 所有 cooldown=0/floor
4. **zombie_empty_completion (14)**: NVCF content-filter 行为 — 代码级检测正确，非配置可修复
5. **all_tiers_exhausted (9)**: FALLBACK_GRAPH={} (R832 design), NV-MS-FB=0 → ms_gw fallback 未触发
   - dsv4p_nv ATE: 8× ~63,867ms, fallback_actually_attempted=false
   - NVU_MS_GW_FALLBACK_TIMEOUT=120, BUDGET=205, NVU_TIER_BUDGET_DSV4P_NV=66
   - ms_gw fallback budget = 205 - 66 = 139s > 120s timeout → budget OK
   - 但 NV-MS-FB 0 次匹配 → ms_gw fallback 未进入代码路径
   - 可能原因: NVCF content-filter 导致 zombie 在 ms_gw 也能触发同样行为
6. **ms_gw at floor**: EMPTY_200_FASTBREAK_THRESHOLD=3, UPSTREAM=300, all cooldown optimal
7. **HM1 git 停在 R1206** (261 轮落后): 正常，HM1 未执行任何优化

## 3. 铁律

只改 HM1 不改 HM2 — 本轮无改动。
## ⏳ 轮到HM1优化HM2
