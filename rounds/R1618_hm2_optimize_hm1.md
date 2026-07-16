# R1618: HM2→HM1 — NOP (all params floor/optimal, peer-fb rescue 4/6, zombie+504 NVCF-side only)

## 数据收集 (HM1, 2026-07-16 05:10 UTC)

### 容器状态
```
nv_gw    Up About an hour (healthy)  — restart 03:50 UTC
ms_gw    Up 26 minutes (healthy)     — R1616 restart
logs_db  Up 29 hours (healthy)
```

### 6h 总体 SR
```
16 req / 10 OK / 6 fail = 62.5% SR
```

### 分模型
```
dsv4p_nv:  7 req / 5 OK / 2 502 = 71.4% SR  (avg dur 35,323ms)
glm5_2_nv: 9 req / 5 OK / 4 502 = 55.6% SR  (avg dur 8,637ms)
```

### 错误分类
```
zombie_empty_completion: 4  (glm5_2_nv NVCF content-filter)
all_tiers_exhausted:     2  (dsv4p_nv → peer-fb TimeoutError 66s)
```

### dsv4p_nv ATE 全貌
```
7/7 ATE (all_tiers_exhausted):
  → 5/7 peer-fb OK (200, 1310-1311 bytes, 4-9ms TTFP)
  → 2/7 peer-fb TimeoutError 66s (HM2 side)
```

### peer-fb 近期表现
```
13:07:14 peer-fb OK: 200, 1311 bytes, 4ms TTFP
13:08:28 peer-fb OK: 200, 1311 bytes, 8ms TTFP
13:09:42 peer-fb OK: 200, 1310 bytes, 9ms TTFP
13:11:52 peer-fb FAILED: TimeoutError 66s (HM2 key pool exhaustion)
12:41:31 peer-fb FAILED: TimeoutError 66s
```

### ms_gw
```
4/4 100% SR (glm5_2_ms only)
dsv4p_ms NOT in MODELMAP (correct — R1488: ms_gw relay broken for dsv4p)
```

### Tier Attempts
```
glm5_2_nv pexec_success: 9 (avg 8,064ms)
glm5_2_nv pexec_SSLEOFError: 1 (5,002ms)
dsv4p_nv: none (all 504 → cycle → budget break → no attempt logged)
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
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_PEXEC_TIMEOUT_FASTBREAK=1       (floor)
NVU_EMPTY_200_FASTBREAK=2           (code-level no-op per R1039/R1489)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1   (floor)
NVU_PEER_FB_SKIP_MODELS=            (empty — all models peer-fb enabled)
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=120
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_FORCE_STREAM_UPGRADE=0
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
ms_gw EMPTY_200_FASTBREAK_THRESHOLD=2 (R1616)
```

## 分析

### 504 函数级 NVCF 降级 (dsv4p_nv)
- 所有 dsv4p_nv 请求 ATE — 5 keys 全部 504_nv_gateway_timeout
- BUDGET=66 floor pattern 正确: k1-504(~64s)→剩余 2s<5s→立即 ATE→peer-fb
- 非 config 可修复 — NVCF 侧函数降级

### zombie_empty_completion (glm5_2_nv)
- 4/9 glm5_2_nv zombie (NVCF content-filter: input >150K chars, content <50 chars)
- 非 config 可修复 — NVCF 侧内容过滤

### peer-fb 可靠性
- 4/6 近期成功 (67%), 2/6 TimeoutError (HM2 侧问题)
- HM2 nv_gw 健康 (`{"status":"ok"}`, 5 keys, UPSTREAM_TIMEOUT=66)
- Peer-fb TimeoutError 66s = HM2 也遇到 504 降级 (HM2 5 keys 全部超时)
- 提升空间在 HM2 侧 (HM2 nv_gw 参数优化)

### 参数评估
- 所有参数已到 floor/optimal
- BUDGET=66=UPSTREAM_TIMEOUT: 不能再降 (会截断正常请求)
- FASTBREAK=1: 函数级 floor, 不能再降
- PEER_FB_SKIP_MODELS 空: 所有模型启用 peer-fb, 正确
- MODELMAP 不含 dsv4p_nv: 正确 (R1488 — ms_gw relay broken for dsv4p)
- NVU_FORCE_STREAM_UPGRADE=0: 正确 (dsv4p thinking 模式不需要)
- 无任何可优化参数

## 结论: NOP

所有参数 floor/optimal。失败模式是 NVCF 侧函数降级 (504) 和内容过滤 (zombie)，非 config 可修复。peer-fb rescue 4/6 提供了可靠保护。ms_gw 4/4 100% SR 为 glm5_2_nv 提供后备。无参数可改。

## Improvements Since R1617
- R1616 ms_gw EMPTY_200_FASTBREAK_THRESHOLD 3→2 已生效 (ms_gw 重启 26min)
- ms_gw 4/4 100% SR 稳定
- 3 个新请求 (05:00 时): 2 glm5_2_nv OK, 1 zombie
- peer-fb 持续 rescue: 4/6 成功 (R1617 时 3/5)
## ⏳ 轮到HM1优化HM2
