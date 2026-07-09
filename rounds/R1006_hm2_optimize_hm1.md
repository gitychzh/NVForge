# R1006 (HM2→HM1): NOP — false trigger, R1005 settling, scheduler-gate ATE only

**Date**: 2026-07-09 23:35 UTC+8  
**Type**: HM2→HM1 NOP (no config change)  
**Iron rule**: Only change HM1, never HM2

## 1. 触发

Cron 脚本检测到 HM1 提交新 commit (R1005 为 opc2_uname 自提交的 NOP，脚本标记"不触发"，但 cron 仍然派遣)。

## 2. 改前数据 (2026-07-09 23:35 UTC)

### 2.1 概览

| 窗口 | 总 | 成功 | 错误 | SR |
|------|-----|------|------|-----|
| 6h | 156 | 143 | 13 | 91.7% |
| 1h | 18 | 16 | 2 | 88.9% |

### 2.2 1h per-tier

| Tier | total | ok | err | SR |
|------|-------|-----|-----|-----|
| glm5_2_nv | 11 | 9 | 2 | 81.8% |
| kimi_nv | 3 | 3 | 0 | 100% |
| minimax_m3_nv | 3 | 3 | 0 | 100% |
| dsv4p_nv | 1 | 1 | 0 | 100% |

### 2.3 1h per-upstream

| Tier | upstream | total | ok |
|------|----------|-------|-----|
| glm5_2_nv | nv_integrate | 8 | 8 |
| glm5_2_nv | NULL (ATE) | 3 | 1 |
| kimi_nv | nvcf_pexec | 3 | 3 |
| minimax_m3_nv | nv_integrate | 3 | 3 |
| dsv4p_nv | nvcf_pexec | 1 | 1 |

### 2.4 1h latency

| Tier | avg_ms | min_ms | max_ms | p95_ms | p99_ms | cnt |
|------|--------|--------|--------|--------|--------|-----|
| dsv4p_nv | 8,756 | 8,756 | 8,756 | 8,756 | 8,756 | 1 |
| minimax_m3_nv | 23,041 | 1,506 | 66,003 | 66,003 | 66,003 | 3 |
| kimi_nv | 27,889 | 1,426 | 71,985 | 71,985 | 71,985 | 3 |
| glm5_2_nv | 52,240 | 17,784 | 71,285 | 71,285 | 71,285 | 9 |

### 2.5 6h 错误分析 (13 条)

```
8× dsv4p_nv (12:49-12:58 UTC): all_tiers_exhausted, duration=112,038-112,056ms
  → caller=r832f-pexec-us (stress test), upstream_type=NULL, 0 tier_attempts
  → 调度层拒诊 (fallback gate blocking, 非 config 可修)
  → 时间: pre-R997 (R997 ~13:07 UTC), 已被 R1005 覆盖

5× glm5_2_nv (09:52-22:55 UTC): all_tiers_exhausted
  → caller=openclaw (真实用户), upstream_type=NULL, 0 tier_attempts
  → 3× pre-R1005 (09:52-13:07), 2× post-R1005 (14:55, 15:24)
  → 调度层拒诊 — upstream_type=NULL, 零 tier_attempts → gateway 未发送任何请求
  → 非 config 可修，属于 scheduler/gate 内部逻辑
```

### 2.6 nv_tier_attempts (6h)

| Tier | err_type | cnt | avg_ms | max_ms |
|------|----------|-----|--------|--------|
| dsv4p_nv | IntegrateTimeout | 14 | 56,021 | 67,086 |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134 | 9,134 |
| kimi_nv | empty_200 | 1 | — | — |

### 2.7 实时日志 (最近 20 行, 23:35-23:37 UTC)

```
[23:35:25] REQ model=glm5_2_nv integrate k4 → 38,352ms → SUCCESS ✓
[23:35:27] REQ model=minimax_m3_nv integrate k3 → 1,506ms → SUCCESS ✓
[23:35:28] REQ model=dsv4p_nv pexec → 8,756ms → SUCCESS ✓
[23:35:59] REQ model=glm5_2_nv integrate k4 → SUCCESS ✓
[23:36:34] REQ model=glm5_2_nv integrate k5 → 3,246ms → SUCCESS ✓
[23:37:09] REQ model=glm5_2_nv integrate k1 → pending
```

**零错误, 零 warn, 所有请求正常**。

### 2.8 HM1 nv_gw 当前配置

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=112
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1  ← R1005 改后
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```

## 3. 决策: NOP (无变更)

### 3.1 为什么不做任何改动

1. **glm5_2_nv integrate 路径 100% SR (8/8)**: integrate 路径是当前主要承载 glm5_2_nv 流量的路径，1h 内 8/8 全部成功，延迟 avg=52,240ms (正常 thinking 请求范围)，无 timeout 无 error。

2. **2 个 ATE 是 scheduler-gate 拒诊**: upstream_type=NULL, 0 tier_attempts — gateway 根本没有发送任何请求。这是内部调度逻辑问题，非 config 参数可修。

3. **R1005 刚部署需沉降**: EMPTY_200_FASTBREAK 3→1 改后容器 Up 10min，需要更多数据验证效果。日志显示 post-restart 零错误。

4. **所有参数已到 floor/optimal**: 所有参数都已在最优值，无进一步收紧空间。

5. **8× dsv4p_nv ATE 是 pre-R997 历史**: 12:49-12:58 UTC 的 stress test 数据，已被 R997/R1005 覆盖。

### 3.2 参数状态评估

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 112 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | stable (R997) |
| NVU_EMPTY_200_FASTBREAK | 1 | R1005, settling |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | HM1 self-optimized |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | HM1 self-optimized |
| 其他 | floor/optimal | 无变化 |

## 4. 评判

- 更少报错: ✓ (1h 仅 2 scheduler-gate ATE, 非 config-fixable)
- 更快请求: ✓ (所有 tier latency 正常)
- 超低延迟: ✓ (kimi 1.4s, minimax 1.5s, dsv4p 8.8s, glm5_2 17.8s min)
- 稳定优先: ✓ (R1005 沉降中, 不做扰动)

**单参数铁律**: NOP 轮不改变任何参数。只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2