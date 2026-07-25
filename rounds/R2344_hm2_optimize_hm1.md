# R2344: HM2→HM1 — NOP (false trigger + R2343 settling)

## TL;DR
Cron false trigger: script output `"这是我提交的, 不触发"` — commit 15ee963 is HM2's own R2343 push. Container restarted at 23:18 UTC for R2343 (kimi_nv budget 180→200). Post-restart traffic: 6 req / 1 OK / 5 fail — data insufficient. NOP settling.
单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2343 部署后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 415 | R656 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R686 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | R2284 |
| 5 | `TIER_COOLDOWN_S` | 30 | R2331 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 60 | R2311 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R2214 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | R1941 |
| 9 | `NVU_STREAM_TOTAL_DEADLINE_S` | 90 | code default |
| 10 | `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 15 | R910 |
| 11 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R921 |
| 12 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R823 |
| 13 | `NVU_EMPTY_200_FASTBREAK` | 2 | R2340 |
| 14 | `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | R921 |
| 15 | `NV_INTEGRATE_ENABLED` | 1 | R921 |
| 16 | `NV_INTEGRATE_MODELS` | `"dsv4p_nv,glm5_2_nv"` | R650 |
| 17 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 9 | R650 |
| 18 | `KEY_COOLDOWN_S` | 30 | R2331 |

**关键状态**: TIER_COOLDOWN_S = KEY_COOLDOWN_S = 30 (pair-aligned, R2331) ✅ 无上方向死区。

---

## 二、数据收集（R2343 部署后）

### 2.1 容器状态
- **nv_gw** restarted at `2026-07-24T23:18:12.375480861Z` (R2343 restart)
- **logs_db**: Up, healthy
- **日志**: 0 error/warn lines (clean)

### 2.2 6h DB 总览
| total | ok_200 | fail | SR% | avg_ms | p50_ms | p95_ms | max_ms |
|-------|--------|------|-----|--------|--------|--------|--------|
| 95 | 45 | 50 | 47.4% | 50270 | 19897 | 170164 | 180193 |

⚠️ **严重预重启污染**: 容器 23:18 重启, 6h 窗口 (17:23→23:23) 含 95 条。但 post-restart 仅 17min, 6h 中 95-6=89 条是 old regime。

### 2.3 Post-Restart 子窗口 (23:18+)
| total | ok | fail | errors |
|-------|----|------|--------|
| 6 | 1 | 5 | 5 |

→ 仅 6 请求, 远 <10 条最低可决策阈值。

### 2.4 Per-Model (6h)
| tier_model | cnt | ok | avg_ms | max_ms |
|------------|-----|----|--------|--------|
| kimi_nv | 41 | 29 | 77906 | 180193 |
| glm5_2_nv | 37 | 10 | 11339 | 67165 |
| dsv4p_nv | 17 | 6 | 68349 | 120083 |

### 2.5 错误分解 (6h)
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 46 |
| zombie_empty_completion | 4 |

### 2.6 24h 错误 (全 regime)
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 153 |
| zombie_empty_completion | 12 |
| stream_total_deadline | 1 |
| NVStream_IncompleteRead | 1 |

### 2.7 kimi_nv 24h tier_attempts
| tier | error_type | cnt |
|------|------------|-----|
| kimi_nv | empty_200 | 13 |
| kimi_nv | NVCFPexecRemoteDisconnected | 5 |

### 2.8 glm5_2_nv 问题
- 25 null-key ATEs: status=502, error_type=null, p50=8ms → instant tier-locked fast-fail
- 4 tier_attempts 429s → NVCF 集群 rate-limit
- key lock 后立即所有 tier 用 key_idx=null (fast-fail)

### 2.9 key_cycle_429s
- kimi_nv: 30 req at cycle0, 9 at cycle1, 2 at cycle2, 1 at cycle3
- glm5_2_nv: 33 at cycle0, 2 at cycle1

---

## 三、决策分析

| 参数 | 旧值 | 候选 | 状态 | 否决原因 |
|------|------|------|------|----------|
| `NVU_EMPTY_200_FASTBREAK` | 2 | →3 | ❌ | 24h 12 empty_200 但 post-restart 仅 6req, 无法评估 |
| `NVU_TIER_BUDGET_DSV4P_NV` | 180 | 无 | ❌ | 6h dsv4p_nv 无 ATE 趋势 (3 key null-ATE), 但预重启污染严重 |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 210 | 无 | ❌ | glm5_2_nv 问题为 NVCF rate-limit, 预算增大无济于事 |
| any | — | — | ❌ | post-restart 6req 严重不足, <10 阈值 |

**最终决策**: NOP — 预埋 post-restart settling, 零改动, 零重启。
R2343 (kimi_nv budget 180→200) 刚部署 10 分钟, 需至少 1-2h 新 regime 数据积累。

---

## 四、执行记录（NOP）

- SSH to HM1: 连通 ✅
- 数据收集: 完整 15 项查询 ✅
- 漂移检测: 未产生新条目, write skipped ✅
- 容器: 不重启, 维持 R2343 deploy 状态

---

## 五、结论

R2344: 纯 NOP false-trigger settling round.
0 change, 0 restart, 0 risk.
HM2 script正确检测到自提交 → "不触发", 但 cron 竞态仍派遣。
规范仍必须输出 round 文件, 标记 double-dispatch false trigger。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2
