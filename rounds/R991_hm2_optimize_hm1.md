# HM2 Optimize HM1 — Round R991

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit 1823da8 (R990) author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, double-dispatch after R990)
- 符号链接已指向 R990 → 创建 R991

## 2. 数据收集 (改前必有数据 — 6h 窗口, 2026-07-09 19:30 UTC)

### 2.1 nv_requests 请求概览
| 指标 | 值 |
|------|-----|
| Total | 59 |
| Success | 51 (86.4%) |
| Error | 8 (13.6%) |

### 2.2 Per-tier 明细
| tier_model | cnt | ok | err | avg_ms | p95_ms |
|------------|-----|----|-----|--------|--------|
| glm5_2_nv | 37 | 37 | 0 | 9,948 | 41,592 |
| dsv4p_nv | 14 | 14 | 0 | 89,050 | 139,129 |

注: 8 个 error 全在 glm5_2_nv tier (45 total, 82.2% SR). dsv4p_nv 14/14 100%.

### 2.3 Error 分类
| error_type | cnt | tier_model |
|------------|-----|------------|
| all_tiers_exhausted | 8 | glm5_2_nv |

### 2.4 nv_tier_attempts (ATE, 6h)
17 ATE, 全部 glm5_2_nv: NVCFPexecTimeout (max=62,606ms), 2×504_nv_gateway_timeout, 1×empty_200.
NVCFPexecTimeout max=62,606ms, UPSTREAM=66 buffer=3.4s ≥ 3s ✓ (R751 rule).

ATE breakdown:
| tiers_tried_count | cnt | avg_dur_ms |
|-------------------|-----|------------|
| 1 | 6 | 58,046 |
| 2 | 2 | 174,417 |

单 tier ATE = glm5_2_nv 单向 NVCFPexecTimeout 耗完 2 key → all_tiers_exhausted.
双 tier ATE = glm5_2_nv 先耗完 → ms_gw fallback 尝试 → 也超时 (avg 174s = 2×(~62s) + ms_gw ~60s).

### 2.5 ms_gw
- 6h: 18 requests, ms_gw 日志正常 (MS-OK-STREAM/MS-STREAM-DONE), 0 error
- ms_gw DB `ms_requests`: 18 rows
- ms_gw params: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, VARIANT_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=1.0 — all at established values

### 2.6 nv_gw 日志
- `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — R832 预期状态, FALLBACK_GRAPH={}
- 无 NV-ALL-TIERS-FAIL / NV-MS-FB / NV-PEER-FB 近期日志 — 当前无 ATE 发生
- Container StartedAt: 2026-07-09T11:34:16Z (~8h uptime post-R988 restart), 稳定运行

### 2.7 HM1 nv_gw 当前配置
```
FALLBACK_HEALTH_THRESHOLD=0.05
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_PEXEC_TIMEOUT_FASTBREAK=2
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=112
UPSTREAM_TIMEOUT=66
```

## 3. 优化决策

**NOP** — 所有参数 at floor/optimal, 无合理调整空间:

- UPSTREAM_TIMEOUT=66, buffer 3.4s ≥ 3s ✓ (R988 调整, R990 确认稳定)
- TIER_TIMEOUT_BUDGET_S=112 >> 66 充足
- NVU_PEXEC_TIMEOUT_FASTBREAK=2 (floor)
- NVU_EMPTY_200_FASTBREAK=3 (floor)
- KEY_COOLDOWN_S=25 (floor)
- TIER_COOLDOWN_S=25 (floor)
- MIN_OUTBOUND_INTERVAL_S=0 (floor)
- CONNECT_RESERVE=0 (floor)
- KEY_AUTHFAIL_COOLDOWN_S=60 (R922 防御参数, 维持)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (R923, 维持)
- FALLBACK_HEALTH_THRESHOLD/NVU_FALLBACK_HEALTH_THRESHOLD=0.05 (R982, floor)

dsv4p_nv 14/14 100%, ms_gw 18/18 正常 — 两条链路均稳定。

glm5_2_nv NVCFPexecTimeout 仍是上游 NVCF 固有超时特征 — R988 已将 UPSTREAM 推至 66s, buffer 3.4s 已足够。NVCFPexecTimeout max=62,606ms (与 R989/R990 相同, 无漂移)。进一步增大 UPSTREAM_TIMEOUT 会拉长用户等待时间, 收益递减。

ms_gw 参数均在 well-established 值, 0 error, 无优化空间。

数据与 R989/R990 一致 — 59 vs 54 vs 47 requests, SR 86.4% vs 85.2% vs 83.0%, 均为 glm5_2_nv 上游 NVCF function-level issue。

**决策**: NOP, 所有参数维持不变。

## ⏳ 轮到HM1优化HM2