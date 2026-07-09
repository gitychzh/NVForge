# HM2 Optimize HM1 — Round R993

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit aef1ce2 (R992) author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, double-dispatch after R992)
- 符号链接已指向 R992 → 创建 R993

## 2. 数据收集 (改前必有数据 — 6h 窗口, DB time ~12:08 UTC)

### 2.1 nv_requests 请求概览
| 指标 | 值 |
|------|-----|
| Total | 59 |
| Success | 51 (86.4%) |
| Error | 8 (13.6%) |

注: 8 个 error 全部 pre-restart (07:36–11:05 UTC, `all_tiers_exhausted`, `upstream_type=NULL`), 与 R992 数据完全一致。Post-R992 restart (11:57 UTC): 2 requests, 2 success, 100% SR, 0 error.

### 2.2 Per-tier 明细
| tier_model | cnt | ok | err | avg_ms | p95_ms | max_ms |
|------------|-----|----|-----|--------|--------|--------|
| glm5_2_nv | 47 | 39 | 8 | 23,156 | 112,060 | 174,468 |
| dsv4p_nv | 11 | 11 | 0 | 90,101 | 139,129 | 139,129 |

### 2.3 Per-caller 明细
| caller | tier_model | cnt | ok | err |
|--------|------------|-----|----|-----|
| probe | glm5_2_nv | 28 | 28 | 0 |
| openclaw | glm5_2_nv | 16 | 10 | 6 |
| unknown | dsv4p_nv | 9 | 9 | 0 |
| openclaw | dsv4p_nv | 2 | 2 | 0 |
| unknown | glm5_2_nv | 2 | 0 | 2 |
| r832f-verify | glm5_2_nv | 1 | 1 | 0 |

Probe 100% SR, openclaw glm5_2_nv 62.5% SR (6/16 error, all pre-restart). dsv4p_nv 11/11 100%.

### 2.4 Error 分类
| error_type | cnt | tier_model | period |
|------------|-----|------------|--------|
| all_tiers_exhausted | 8 | glm5_2_nv | 07:36–11:05 pre-restart |

全部 8 error 均为 `upstream_type=NULL` (`all_tiers_exhausted`, `fallback_occurred=false`), 与 R992 相同。Post-restart 0 error。

### 2.5 nv_tier_attempts (ATE, 6h)
14 ATE, 全部 glm5_2_nv: NVCFPexecTimeout (max=62,606ms), 2×504_nv_gateway_timeout, 1×empty_200.
NVCFPexecTimeout max=62,606ms, UPSTREAM=66 buffer=3.4s ≥ 3s ✓ (R751 rule).
全部 ATE timestamp 06:09–08:05 UTC — pre-restart。Post-restart 0 ATE。

### 2.6 ms_gw
- 日志: 16:05–17:09 时段 MS-VARIANT-EXHAUSTED burst (req b85a22c4, feaa17b3, d1a99909, 7f47698b), 但最终均成功 (MS-OK)。17:10–19:04 正常 (MS-OK-STREAM/MS-STREAM-DONE)。
- ms_gw params: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, VARIANT_COOLDOWN_S=30, ALL_EXHAUSTED_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=1.0 — all at established values

### 2.7 HM1 nv_gw 当前配置
```
FALLBACK_HEALTH_THRESHOLD=0.05
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_PEXEC_TIMEOUT_FASTBREAK=2
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=112
UPSTREAM_TIMEOUT=66
```

## 3. 优化决策

**NOP** — R992 变更 (NVU_FALLBACK_HEALTH_THRESHOLD 0.05→0.10) 正在 settling。Post-restart 数据: 2 requests 100% SR, 0 error, 0 ATE。所有参数 at floor/optimal:

- UPSTREAM_TIMEOUT=66, buffer 3.4s ≥ 3s ✓ (R988)
- TIER_TIMEOUT_BUDGET_S=112 >> 66 充足
- NVU_PEXEC_TIMEOUT_FASTBREAK=2 (floor)
- NVU_EMPTY_200_FASTBREAK=3 (floor)
- KEY_COOLDOWN_S=25 (floor)
- TIER_COOLDOWN_S=25 (floor)
- MIN_OUTBOUND_INTERVAL_S=0 (floor)
- CONNECT_RESERVE=0 (floor)
- KEY_AUTHFAIL_COOLDOWN_S=60 (R922 防御参数, 维持)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (R923, 维持)
- NVU_FALLBACK_HEALTH_THRESHOLD=0.10 (R992, settling)
- FALLBACK_HEALTH_THRESHOLD=0.05 (dead param R919, 不改)

dsv4p_nv 11/11 100%, ms_gw 正常 — 所有链路稳定。ms_gw 16:05 时段 VARIANT-EXHAUSTED burst 为上游 ModelScope 间歇性退化，ms_gw 自身参数已优化 (EMPTY_200_FASTBREAK_THRESHOLD=3 R900)，无进一步优化空间。

8 个 pre-restart ATE 均为 glm5_2_nv NVCFPexecTimeout → all_tiers_exhausted — 上游 NVCF function-level issue，R992 通过提升 FALLBACK_HEALTH_THRESHOLD 拓宽 ms_gw fallback 救援窗口。Post-restart 数据不足 (2 req) 无法验证 R992 效果，但零错误已是正向信号。

**决策**: NOP, 所有参数维持不变。等待 HM1 拉取 R992 变更并产生更多流量后验证。

## ⏳ 轮到HM1优化HM2