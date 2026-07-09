# HM2 Optimize HM1 — Round R958

**时间**: 2026-07-09 11:15 UTC
**触���**: False trigger (cron 脚本输出: "这是我提交的, 不触发"，最新 commit author=opc2_uname)
**类型**: Double-dispatch NOP (75th consecutive false-trigger dispatch since R884)

## 1. 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `8f6c8b9 R957: fix symlink → rounds/R957_hm2_optimize_hm1.md` (author=opc2_uname)
- R957 已正确写为 NOP，symlink 已指向 R957
- 本轮为 double-dispatch：cron 在 R957 已提交后再次派遣

## 2. 数据收集 (改前必有数据)

### 2.1 Docker 日志 (nv_gw, tail 100)

```
[08:33:22.0] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[09:03:21.6] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[10:03:21.5] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[10:04:24.2] [NV-CYCLE] tier=glm5_2_nv k4 → 504 (504_nv_gateway_timeout), cycling
[10:05:15.5] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[10:05:45.4] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv
[10:33:21.3] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[10:34:35.4] [NV-CYCLE] tier=glm5_2_nv k1 → 504 (504_nv_gateway_timeout), cycling
[10:35:26.9] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[10:35:40.3] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv
[11:03:21.4] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[11:04:24.0] [NV-CYCLE] tier=glm5_2_nv k2 → 504 (504_nv_gateway_timeout), cycling
[11:05:15.8] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[11:05:34.0] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv
```

- tier_chain 健康: 双向 dynamic fallback (glm5_2_nv ↔ dsv4p_nv)
- 3 次 fallback 全部成功 (NV-FALLBACK-SUCCESS)
- 无 ATE、无 error 日志
- 3 次 504_nv_gateway_timeout (glm5_2_nv key 超时) → fallback 成功救援

### 2.2 容器环境变量

```
FALLBACK_HEALTH_THRESHOLD=0.05
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_PEXEC_TIMEOUT_FASTBREAK=1
TIER_TIMEOUT_BUDGET_S=114
UPSTREAM_TIMEOUT=64
```

- 容器运行时间: 2026-07-08T20:42:53Z (~14h)

### 2.3 DB 查询 (6h 窗口)

**总体统计**:
```
total | ok | fail | sr_pct
    34 | 34 |    0 |  100.0
```

**上游路径**:
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nvcf_pexec    |  34 | 34 |    25866 |   25866 |  143949
```

**错误**: 无 (0 rows)

**ATE**: 无 (0 rows)

**Fallback**:
```
fallback_occurred | cnt
f                 |  31
t                 |   3
```

**Tier 尝试 (6h)**:
```
tier       | error_type                   | cnt | avg_ms | max_ms
glm5_2_nv  | 504_nv_gateway_timeout       |   3 |        |
glm5_2_nv  | NVCFPexecTimeout             |   2 |  51406 |  51498
glm5_2_nv  | budget_exhausted_after_connect|   1 |  51838 |  51838
glm5_2_nv  | empty_200                    |   1 |        |
```

- NVCFPexecTimeout max=51,498ms << UPSTREAM=64s (非绑定)
- 3 次 504_nv_gateway_timeout + 2 次 NVCFPexecTimeout → fallback 成功救援

**24h 错误**:
```
error_type           | cnt
all_tiers_exhausted  |   1
```
仅 1 次 ATE（24h 内），与上轮 (R957) 一致。

**ms_gw (6h)**: 0 请求，无需优化。

## 3. 分析

- nv_gw: 6h 100.0% SR，零错误，零 ATE
- FALLBACK_GRAPH 双向正常 (glm5_2_nv ↔ dsv4p_nv)
- 3 次 fallback 全部成功救援
- NVCFPexecTimeout max=51.5s << UPSTREAM=64s (非绑定，headroom=12.5s)
- 所有参数在 floor/稳定值，零调整空间
- 24h 仅 1 次 ATE，与 R957 一致

## 4. 决策: NOP

零参数变更。系统稳定，100% SR，无优化空间。

## 5. 参数变更: 无

零参数变更。本轮纯 NOP。

## ⏳ 轮到HM1优化HM2
