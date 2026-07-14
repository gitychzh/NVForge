# HM2 Optimize HM1 — Round R1310

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2, 自提交)
- 脚本正确检测到自提交并标记 "不触发", cron 仍被派遣 — 误触发 (double-dispatch)
- R1309 已由预运行脚本提交为 NOP, symlink 已指向 R1309

## 数据收集 (改前必有数据)

### HM1 容器状态
- nv_gw: Up 4 hours (healthy)
- ms_gw: Up 17 hours (healthy)
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` (stable, 与 R1308/R1309 一致)

### 6h DB 数据 (nv_gw)
- 总计: 59req/51OK(86.4%SR)/8fail
- 失败: 8× zombie_empty_completion (glm5_2_nv integrate only), avg 4,864ms
- 0 tier_attempts, 0 ATE, 0 IncompleteRead
- dsv4p_nv: 0 traffic, kimi_nv: 0 traffic

### 逐小时 SR
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 20:00 | 3 | 2 | 1 | 66.7 |
| 21:00 | 6 | 4 | 2 | 66.7 |
| 22:00 | 7 | 5 | 2 | 71.4 |
| 23:00 | 6 | 5 | 1 | 83.3 |
| 00:00 | 6 | 5 | 1 | 83.3 |
| 01:00 | 29 | 28 | 1 | 96.6 |
| 02:00 | 2 | 2 | 0 | 100.0 |

### ms_gw
- 13req/13ok(100%SR), all MS-OK-STREAM + MS-STREAM-DONE, 0 errors

### 容器 env (nv_gw)
```
UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_PEER_FALLBACK_TIMEOUT=66
NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FB_SKIP_MODELS="" (peer-fb fully enabled)
NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
MIN_OUTBOUND_INTERVAL_S=0, NVU_SSLEOF_RETRY_DELAY_S=1.0
```

### 日志诊断
- 所有请求 glm5_2_nv integrate, 全部首次尝试成功 (NV-INTEGRATE-SUCCESS)
- 1× zombie_empty_completion (09:33:26, content_chars=12 < 50, input_chars=175K, 3-4s fast abort)
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 预期状态 (R832 FALLBACK_GRAPH={})
- 0 NV-TIER-FAIL, 0 NV-ALL-TIERS, 0 NV-MS-FB, 0 NV-PEER-FB
- 0 error/warn 日志

## 决策

### NOP — 24th consecutive post-R1286

**理由**: 所有失败均为 zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, 3-4s fast abort)。这是代码级特性 (R1107), 非 config 可修复。所有参数已达 floor/optimal。ms_gw 100% SR。0 tier_attempts 0 ATE。Compose md5 稳定不变。无需修改任何参数。

### 参数状态
- 所有参数 floor/optimal: UPSTREAM=66, BUDGET=205, TIER_COOLDOWN=15, FASTBREAK=1/2/1
- dsv4p_nv 0 traffic 6h+ — 无优化信号
- 铁律: 只改HM1不改HM2 — 本轮无改动

## ⏳ 轮到HM1优化HM2
