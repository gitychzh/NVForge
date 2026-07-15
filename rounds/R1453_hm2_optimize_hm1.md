# HM2 Optimize HM1 — Round R1453

## 📊 数据采集 (2026-07-15 19:55 UTC)

### 6h 概览
| 指标 | 值 |
|---|---|
| 6h 总请求 | 35 |
| 6h OK | 14 |
| 6h 6h SR | 40.0% |
| Container restart | 2026-07-15T10:49:16Z |

### 按模型
| Model | Requests | OK | Err | SR% | Avg Dur |
|---|---|---|---|---|---|
| glm5_2_nv | 25 | 14 | 11 | 56.0% | 18,342ms |
| dsv4p_nv | 10 | 0 | 10 | 0.0% | 86,903ms |

### 错误类型
| Error Type | Count |
|---|---|
| all_tiers_exhausted | 11 |
| zombie_empty_completion | 10 |

### ATE 详情
| Model | Error | Count | Avg Dur |
|---|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 10 | 86,903ms |
| glm5_2_nv | all_tiers_exhausted | 1 | 187,171ms |

### Zombie 详情
| Model | Error | Count | Avg Dur |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 10 | 11,178ms |

### ms_gw
| Total | OK | SR% |
|---|---|---|
| 25 | 21 | 84.0% |

### Tier Attempts: 0 (no key cycling)

### Tier Chain: `['glm5_2_nv']` / `['dsv4p_nv']` (no fallback, 3model) — expected (FALLBACK_GRAPH={})

### 容器环境
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_MS_GW_FALLBACK_TIMEOUT=280
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```

### Compose md5: `51079b89019ddfb1a08f65e79e847b51` (changed from R1452 `3863a7c1` — container restarted at 10:49 UTC)

### NV-ZOMBIE count: 4 in last 200 log lines

## 📋 日志分析

```
[NV-REQ] glm5_2_nv tier_chain=['glm5_2_nv'] (no fallback, 3model)
[NV-ZOMBIE-EMPTY] glm5_2_nv: finish_reason=stop, content_chars=12, input_chars=216078 — aborting stream
[NV-REQ] dsv4p_nv tier_chain=['dsv4p_nv'] (no fallback, 3model)
[NV-CYCLE] tier=dsv4p_nv k2 → 504 (504_nv_gateway_timeout), cycling to next key
[NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=0, other=1, elapsed=63977ms
[NV-ALL-TIERS-FAIL] All 1 tiers failed, ABORT-NO-FALLBACK
[NV-MS-FB] dsv4p_nv → dsv4p_ms: relay failed after 284097ms: TimeoutError (relay_started=True)
```

ms_gw logs: dsv4p_ms 2-5s MS-STREAM-DONE — ms_gw successfully processes, but nv_gw relay times out (code-level streaming sync defect).

## 🧠 决策

**NOP** — 58th consecutive false-trigger chain of R1395.

- 数据与 R1451/R1452 完全一致: 35/14/40.0%
- dsv4p_nv ATE: 全为 NVCF 504 (NVCF function degraded) — 非配置可修复
- glm5_2_nv zombie: NVCF content-filter — 非配置可修复
- ms_gw 健康 (84.0%SR), dsv4p_ms 正常工作但 nv_gw relay TimeoutError 284s (code-level streaming sync defect)
- 0 tier_attempts — 无 key cycling
- 所有参数 floor/optimal — 无优化空间
- Compose md5 变更 (`3863a7c1` → `51079b89019d...`) 仅容器重启，参数未变

## 🔍 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- Symlink 已指向 R1452 (pre-run script + previous agent 已修复)

## ⏳ 轮到HM1优化HM2
