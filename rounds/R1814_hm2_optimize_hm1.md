# R1814 (HM2→HM1): NOP — 八连 false trigger, 零可配置修复故障, 100% SR

## 数据收集

### HM1 nv_gw Logs (最近100行)
- 零 error/warn/panic/exception
- 零 zombie/fallback/peer-fb
- 2 SSLEOF tier self-recovery (k0: 5.0s, k2: 5.0s)
- 全部 glm5_2_nv pexec, RR 均匀分布, timeout=55s

### HM1 nv_gw Env Config
```
UPSTREAM_TIMEOUT=55
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=65
TIER_TIMEOUT_BUDGET_S=180
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_SSLEOF_RETRY_DELAY_S=0.2
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_TIER_BUDGET_DSV4P_NV=45
NVU_TIER_BUDGET_GLM5_2_NV=105
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_KEY1-5: 全部 pexec via SOCKS5 mihomo 7894-7899
```

### DB Stats

| Window | Total | OK | Fail | SR | Avg | P50 | P95 | Min | Max |
|--------|-------|-----|------|------|------|------|------|------|------|
| 6h | 24 | 24 | 0 | 100% | 10.0s | 9.0s | 18.6s | 4.4s | 21.6s |
| 12h | 56 | 55 | 1 | 98.2% | 14.7s | 9.0s | 38.4s | — | — |
| 24h | 125 | 114 | 11 | 91.2% | 12.5s | — | — | — | — |

**6h per-key per-model:**
| Model | Key | Req | OK | Avg | P50 |
|-------|-----|-----|-----|------|------|
| glm5_2_nv | k0 | 4 | 4 | 12.0s | 10.1s |
| glm5_2_nv | k1 | 6 | 6 | 8.0s | 7.9s |
| glm5_2_nv | k2 | 4 | 4 | 9.5s | 9.6s |
| glm5_2_nv | k3 | 6 | 6 | 11.6s | 10.6s |
| glm5_2_nv | k4 | 4 | 4 | 9.4s | 8.7s |

**6h hourly trend:**
| Hour (UTC) | Req | Avg |
|-----------|-----|------|
| 11:00 | 4 | 8.9s |
| 12:00 | 4 | 10.2s |
| 13:00 | 4 | 14.7s |
| 14:00 | 4 | 10.1s |
| 15:00 | 4 | 8.7s |
| 16:00 | 4 | 7.6s |

**12h errors:**
- 1 ATE (status=502): dsv4p_nv, 09:22 UTC, 56.8s, tiers_tried=1 (~10h ago, 旧残余)
- 7 phantom ATE (status=200, empty-200 rescue): 全部 dsv4p_nv, 09:22-09:32 UTC (~10h ago)
- 零 zombie/fallback/peer-fb/429/timeout (6h window)

**12h tier_attempts:**
- 2 SSLEOF: k0(5.0s), k2(5.0s) — 全部 tier self-recovery
- 24 pexec_success 均匀分布在 k0-k4

## 分析

1. **6h 100% SR**: 24/24 OK, 零可配置修复故障. 系统处于最优状态.

2. **12h 1 ATE**: dsv4p_nv 在 ~10h 前的旧事件, 6h 窗口内无新故障. 属上游 NVCF 间歇挂, 非配置可修复.

3. **SSLEOF tier self-recovery**: 2次 SSLEOF (k0, k2) 已通过 tier 内重试自愈, 无需干预. NVU_SSLEOF_RETRY_DELAY_S=0.2 已是 floor.

4. **延迟稳定**: P50=9.0s, P95=18.6s, 无异常长尾. k1 最优 (avg=8.0s), k3 稍慢 (avg=11.6s), 属正常节点质量方差.

5. **零 dsv4p_nv 流量**: 6h 内全部 glm5_2_nv, 无 dsv4p_nv 请求. dsv4p_nv 的所有 ATE 均为 ~10h 前旧事件.

6. **所有参数 floor/optimal**: 无漂移, 无需调整.

## 决策: NOP

八连 false trigger (R1807-R1814). HM1 新 commit 到 GitHub 触发脚本检测, 但 6h 数据 100% SR, 零可配置修复故障. 无参数需调整.

## 评判

| 指标 | 6h | 评价 |
|------|------|------|
| 成功率 | 100% (24/24) | ✅ |
| 平均延迟 | 10.0s | ✅ |
| P50 延迟 | 9.0s | ✅ |
| P95 延迟 | 18.6s | ✅ |
| 错误数 | 0 | ✅ |
| zombie/fallback/peer-fb | 0 | ✅ |
| 429/超时 | 0 | ✅ |
| SSLEOF | 2 (自愈) | ✅ |
| 参数漂移 | 0 | ✅ |

铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
