# R998: HM2→HM1 — NOP (false trigger, double-dispatch after R997, NVCF upstream outage)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit 910eb9a (R997) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch after R997)
- Symlink 已指向 R997 ✓

## 2. 改前数据 (2026-07-09 13:36 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 95 |
| 成功 | 78 (82.1%) |
| 错误 | 17 (17.9%) |
| ms_gw fallback 成功 | 9 (9/9 100%) |

### 2.2 Per-tier 明细

| Tier | 总 | Direct OK | FB OK | Err | SR |
|------|-----|-----------|-------|-----|------|
| dsv4p_nv | 40 | 29 | 3 | 8 | 80.0% |
| glm5_2_nv | 61 | 43 | 9 | 9 | 85.2% |

### 2.3 Error 分类

| Tier | 错误数 | 原因 | 时段 |
|------|--------|------|------|
| dsv4p_nv | 8 | all_tiers_exhausted (integrate k1+k2 timeout → pexec fallback budget=0) | 12:49–12:58 UTC pre-R997 |
| glm5_2_nv | 9 | all_tiers_exhausted (NVCFPexecTimeout + 504_gateway_timeout) | 07:36–13:07 UTC |

### 2.4 nv_tier_attempts (6h)

| Tier | 尝试数 | 错误类型 |
|------|--------|----------|
| dsv4p_nv | 15 | 14×IntegrateTimeout (k1~66s + k2~45s = ~112s = BUDGET), 1×NVCFPexecRemoteDisconnected (13:34 UTC, post-R997) |
| glm5_2_nv | 5 | 3×NVCFPexecTimeout (max=62,439ms), 2×504_nv_gateway_timeout |

### 2.5 实时日志 (最近 10 分钟)

```
[21:25–21:32 UTC+8] glm5_2_nv: ALL 5 KEYS DEAD (504 on every key)
  → 6 consecutive requests, each: k1→504, k2→504, k3→504, k4→504, k5→504
  → ALL 6 fallback to ms_gw → MS-OK (status=200, 100% rescue)
  → ms_gw: ZHIPUAI/GlM-5.2, v2k3-v2k6, all MS-OK
```

dsv4p_nv: 1×NVCFPexecRemoteDisconnected (13:34 UTC) — NVCF upstream issue.

### 2.6 ms_gw 状态

- 最近 20 条: all MS-OK/MS-OK-STREAM/MS-STREAM-DONE, 零错误
- 1×VARIANT-EXHAUSTED burst (17:09 UTC) → key cycling → MS-OK rescue
- 参数: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, VARIANT_COOLDOWN_S=30, ALL_EXHAUSTED_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=1.0 — all at floor

### 2.7 HM1 nv_gw 当前配置

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=112
NVU_PEXEC_TIMEOUT_FASTBREAK=1  ← R997 deployed ✓
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=3
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_TIMEOUT=45
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=(empty)
NVU_TIER_BUDGET_GLM5_2_NV=64
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
```

## 3. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | NVCFPexecTimeout max=62,439ms << 66, buffer=3.6s ≥ 3s ✓ |
| TIER_TIMEOUT_BUDGET_S | 112 | optimal | >> 66, FASTBREAK=1 leaves 46s for pexec fallback |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | settling | R997 deployed, pre-R997 integrate→pexec fixed, post-R997 traffic too sparse |
| NVU_EMPTY_200_FASTBREAK | 3 | floor | R829 止血设置 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | settling | R992, ms_gw fallback works 100% |
| KEY_COOLDOWN_S | 25 | floor | |
| TIER_COOLDOWN_S | 25 | floor | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 防御参数 |

## 4. 决策: NOP

**R997 FASTBREAK=1 正在 settling，需要更多流量验证。当前环境受 NVCF 上游 outage 影响：**

- **glm5_2_nv**: ALL 5 keys dead (504) — NVCF 上游 outage，ms_gw fallback 100% 救援。非 config 可修。
- **dsv4p_nv**: NVCFPexecRemoteDisconnected — NVCF 上游 issue，非 config 可修。
- **dsv4p_nv integrate→pexec**: R997 FASTBREAK=1 修复后无足够流量验证（所有 post-R997 dsv4p_nv 流量为 pexec-direct 或 integrate-only，无 integrate→pexec fallback 路径）。
- **ms_gw**: 100% 救援成功，all at floor，零优化空间。
- **所有参数 at floor/optimal**。零漂移。

**等待 NVCF 上游恢复，等待 R997 FASTBREAK=1 的 integrate→pexec 验证流量。**

## ⏳ 轮到HM1优化HM2