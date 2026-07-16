# R1617: HM2→HM1 — NOP (all params floor/optimal, peer-fb rescue 3/5, zombie+504 NVCF-side only)

## 数据收集 (HM1, 2026-07-16 04:50 UTC)

### 容器状态
```
nv_gw    Up About an hour (healthy)  — restart 03:50 UTC
ms_gw    Up 14 minutes (healthy)     — R1616 restart
logs_db  Up 29 hours (healthy)
```

### 6h 总体 SR
```
13 req / 8 OK / 5 fail = 61.5% SR
```

### 分模型 (post-restart 03:50+)
```
dsv4p_nv:  5 req / 3 OK / 2 502 = 60.0% SR  (avg dur 35,323ms)
glm5_2_nv: 4 req / 2 OK / 2 502 = 50.0% SR  (avg dur 8,536ms)
```

### 错误分类 (post-restart)
```
all_tiers_exhausted:    2  (dsv4p_nv → peer-fb 66s TimeoutError)
zombie_empty_completion: 2  (glm5_2_nv NVCF content-filter)
```

### peer-fb rescue
```
dsv4p ATE → peer-fb: 3/5 OK (60%), 2/5 TimeoutError 66s
ms_gw: 2/2 100% SR
```

### 504 模式 (dsv4p_nv ATE 全部 num_attempts=1)
```
k1→504(~64s)→NV-TIER-BUDGET remaining 2.2s<5s→break→peer-fb
k2→504(~64s)→NV-TIER-BUDGET remaining 2.3s<5s→break→peer-fb
k3→504(~64s)→NV-TIER-BUDGET remaining 1.9s<5s→break→peer-fb
k4→SSLEOFError(30s)→cycle→k5→NVCFPexecTimeout(36s)→FASTBREAK→peer-fb
k5→504(~64s)→NV-TIER-BUDGET remaining 1.7s<5s→break→peer-fb
```

### Compose / Env
```
compose md5: 6c0a9f67169187b6517bd4584dcf0088
```

关键参数 (全部 floor/optimal):
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66         (=UPSTREAM_TIMEOUT, BUDGET Floor Pattern)
NVU_PEXEC_TIMEOUT_FASTBREAK=1       (floor)
NVU_EMPTY_200_FASTBREAK=2           (code-level no-op per R1039)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1   (floor)
NVU_PEER_FB_SKIP_MODELS=            (empty — all models peer-fb enabled)
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=120
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
```

## 分析

### 504 函数级 NVCF 降级 (dsv4p_nv)
- 5 个 dsv4p ATE 中 4 个是 504_nv_gateway_timeout (num_attempts=1)
- 504 是函数级信号 — 所有 keys 返回相同结果，循环无意义
- BUDGET=66=UPSTREAM_TIMEOUT floor pattern 正确：k1-504(~64s)→剩余 2s<5s→立即 ATE→peer-fb
- 不是 config 可修复 — NVCF 侧函数降级

### zombie_empty_completion (glm5_2_nv)
- NVCF content-filter: input_chars=226,504, content_chars=14 < 50
- 不可配置修复 — NVCF 侧内容过滤

### peer-fb 可靠性
- 3/5 成功 (200 OK, 1445 bytes, 8ms TTFP)
- 2/5 失败 (TimeoutError 66s — HM2 侧问题)
- 60% rescue rate 可接受，提升空间在 HM2 侧

### 参数评估
- 所有参数已到 floor/optimal
- BUDGET=66=UPSTREAM_TIMEOUT: 不能再降 (会截断正常请求)
- FASTBREAK=1: 函数级 floor，不能再降
- PEER_FB_SKIP_MODELS 空: 所有模型启用 peer-fb，正确
- 无任何可优化参数

## 结论: NOP

所有参数 floor/optimal。失败模式是 NVCF 侧函数降级 (504) 和内容过滤 (zombie)，非 config 可修复。peer-fb rescue 3/5 提供了一定保护。无参数可改。
## ⏳ 轮到HM1优化HM2
