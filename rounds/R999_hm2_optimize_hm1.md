# R999: HM2→HM1 — NOP (false trigger, post-R997 settling, 89.5% SR, all params at floor/optimal)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit c845d74 (R998) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch after R998)
- Symlink 已指向 R998 ✓

## 2. 改前数据 (2026-07-09 21:45 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 131 |
| 成功 | 116 (88.5%) |
| 错误 | 15 (11.5%) |
| ms_gw fallback 成功 | 9/11 (81.8%) |

### 2.2 2h 窗口 (post-R997)

| 指标 | 值 |
|------|-----|
| 总请求 | 86 |
| 成功 | 77 (89.5%) |
| 错误 | 9 (10.5%) |
| ms_gw fallback 成功 | 6/6 (100%) |

### 2.3 Per-tier 明细 (6h)

| Tier | 总 | OK | Err | SR | avg_ms | p95_ms |
|------|-----|-----|------|------|--------|--------|
| dsv4p_nv | 59 | 51 | 8 | 86.4% | 52,987 | 124,664 |
| glm5_2_nv | 72 | 65 | 7 | 90.3% | 16,314 | 64,071 |

### 2.4 Per-tier upstream_type 明细 (6h)

| Tier | upstream | 总 | OK |
|------|----------|-----|-----|
| dsv4p_nv | nvcf_pexec | 36 | 36 (100%) |
| dsv4p_nv | nv_integrate | 15 | 15 (100%) |
| dsv4p_nv | NULL (ATE) | 8 | 0 |
| glm5_2_nv | nv_integrate | 35 | 35 (100%) |
| glm5_2_nv | nvcf_pexec | 21 | 21 (100%) |
| glm5_2_nv | NULL (ATE) | 16 | 9 (fellback ms_gw) |

### 2.5 Error 分类 (6h)

| Tier | 错误数 | 原因 | 时段 |
|------|--------|------|------|
| dsv4p_nv | 8 | all_tiers_exhausted (IntegrateTimeout: k0~66s + k1~45s = ~112s = BUDGET) | 12:40–12:58 UTC pre-R997 |
| glm5_2_nv | 7 | all_tiers_exhausted (1×NVCFPexecTimeout, 6×ms_gw rescue) | 12:58–13:07 UTC |

### 2.6 nv_tier_attempts (6h)

| Tier | 尝试数 | 错误类型 |
|------|--------|----------|
| dsv4p_nv | 15 | 14×IntegrateTimeout (k0~66s + k1~45s ≈ 112s = BUDGET, all pre-R997), 1×NVCFPexecRemoteDisconnected (13:34 UTC, post-R997) |
| glm5_2_nv | 4 | 2×NVCFPexecTimeout (max=49,205ms), 2×504_nv_gateway_timeout |

### 2.7 关键发现: Post-R997 零错误 (13:07 UTC 后)

```
2h 窗口 9 errors 全部在 12:40–13:07 UTC (pre-R997)
13:07 UTC 后: 0 errors, ~40+ 分钟 clean traffic
dsv4p_nv pexec-direct: 34/34 100% (all post-R997)
dsv4p_nv integrate: 15/15 100% (no integrate→pexec fallback observed)
glm5_2_nv: 15/15 100% post-R997 window
```

### 2.8 实时日志 (最近 100 行)

```
[21:38–21:43 UTC+8] dsv4p_nv: all pexec, k1-k5 cycling, attempt 1/7, 零错误
  无 NVCFPexecTimeout, 无 504, 无 DEAD KEY
  健康状态: 极佳
```

### 2.9 HM1 nv_gw 当前配置

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
NV_INTEGRATE_MODELS=glm5_2_nv
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
| UPSTREAM_TIMEOUT | 66 | optimal | NVCFPexecTimeout max=49,205ms << 66, buffer=16.8s ≥ 3s ✓ |
| TIER_TIMEOUT_BUDGET_S | 112 | optimal | >> 66, FASTBREAK=1 leaves 46s for pexec fallback |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | settling | R997 deployed, 0 integrate→pexec traffic to verify yet |
| NVU_EMPTY_200_FASTBREAK | 3 | floor | R829 止血设置 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | settling | R992, ms_gw fallback works 100% |
| KEY_COOLDOWN_S | 25 | floor | |
| TIER_COOLDOWN_S | 25 | floor | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 防御参数 |

## 4. 决策: NOP

**R997 FASTBREAK=1 正在 settling，post-R997 窗口 89.5% SR + 零错误 (13:07 UTC 后)。**

- **dsv4p_nv**: Post-R997 pexec-direct 34/34 100%, integrate 15/15 100%. integrate→pexec fallback 路径无流量 — 无法验证 FASTBREAK=1 修复但系统健康。
- **glm5_2_nv**: 90.3% SR, NVCFPexecTimeout max=49s << UPSTREAM=66, buffer=16.8s ≥ 3s ✓.
- **ms_gw fallback**: 6/6 100% rescue in 2h window.
- **所有参数 at floor/optimal**。零漂移。
- **6h SR 88.5%** (↑6.4pp from R998's 82.1%), **2h SR 89.5%** (post-R997).

**等待 integrate→pexec 流量验证 R997 FASTBREAK=1 修复，等待更多流量积累。**

## ⏳ 轮到HM1优化HM2