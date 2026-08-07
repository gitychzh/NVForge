# R1135: dsv4f0731_nv self-opt NOP

**日期**: 2026-08-08 04:02 UTC
**容器**: dsvf0731_nv40666 (port 40666)
**轮次类型**: NOP (数据正常，不改参数)

## 当前参数（live env 实测）
| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| TIER_COOLDOWN_S | 90 |
| KEY_COOLDOWN_S | 30 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NV_INTEGRATE_EGRESS_IPS | 134.195.101.197,197,193,195,180 |
| NV_INTEGRATE_PROXY_URLS | 5× socks5h://172.18.0.1:789x |

## 数据（30min 窗口）
- **总量**: 201 | **成功**: 201 | **错误**: 0 | **fallback**: 0 → **SR = 100%**
- **延迟**: avg=9577ms, p50=8201ms, p95=23168ms
- **错误分类**: (无)
- **per-key 200 延迟**（全部健康，无错误）:
  - key0: 41 req, avg=10308ms
  - key1: 40 req, avg=8310ms
  - key2: 39 req, avg=10137ms
  - key3: 39 req, avg=8297ms
  - key4: 40 req, avg=10850ms
- **upstream_type**: nvcf_pexec 199/199 OK (100%)，无 integrate 流量
- **finish_reason**: tool_calls=177, stop=22
- **429 计数**: 0
- **tier_attempts**: (无)

## 趋势
- **6h**: 1836 total / 1826 ok / 10 err / 0 fb = **99.5%**
- **3h 每小时**:
  - 17:00: 267/261 (97.8%)
  - 18:00: 347/346 (99.7%)
  - 19:00: 349/348 (99.7%)
  - 20:00: 16/16 (100%)
- **24h all_tiers_exhausted**: 110（历史累积，本窗口为 0）
- **fallback 日志（hm4104, 最近5min）**: 无

## 容器状态
- dsvf0731_nv40666: Up 2 hours
- nv_gw: Up 25 hours
- /health: status ok

## 结论
30min SR=100%，零错误、零 fallback、零 429，per-key 延迟/负载均匀（无劣化 key），all upstream=pexec 100% 成功，6h SR=99.5%。链路完全健康，无异常信号。

**决策：NOP，不改任何参数。**

## 下一步建议
链路上游近期无异常。继续观察 30min 窗口；若出现 integrate 流量可对比 pexec 延迟；关注 24h 内 110 次 all_tiers_exhausted 是否在更宽窗口（如 6-24h）内有回升趋势，若某 key 出现瞬时 429 突发可评估 NVU_KEYMGR_429_BASE_COOLDOWN (120) 是否需微调。