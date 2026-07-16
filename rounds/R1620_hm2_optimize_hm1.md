# R1620: HM2→HM1 — NOP (all params floor/optimal, R1619 just deployed 4min ago, no new data)

## 数据收集 (HM1, 2026-07-16 13:30 UTC)

### 容器状态
```
nv_gw    Up 4 minutes (healthy)  — R1619 restart
ms_gw    Up 49 minutes (healthy)
logs_db  Up 30 hours (healthy)
```

### 6h 总体 SR
```
20 req / 13 OK / 7 fail = 65.0% SR
```

### 分模型
```
dsv4p_nv:  11 req / 8 OK / 3 502 = 72.7% SR  (all OK via peer-fb, local SR=0%)
glm5_2_nv: 9 req / 5 OK / 4 502 = 55.6% SR  (zombie_empty_completion)
```

### 错误分类
```
zombie_empty_completion: 4  (glm5_2_nv NVCF content-filter)
all_tiers_exhausted:     3  (dsv4p_nv 504 → peer-fb)
```

### dsv4p_nv 504 模式 (100% 函数级降级)
```
error_detail.jsonl 确认: 全部 ATE 为 504_nv_gateway_timeout
num_attempts=1 (BUDGET Floor Pattern: k1-504(~64s)→剩余<5s→立即 ATE)
所有 5 keys 交叉出现 504 — 函数级, 非 key-specific
```

### peer-fb 近期表现
```
dsv4p_nv ATE → peer-fb: 6/9 OK (67%), 3/9 TimeoutError (HM2 side)
ms_gw: 4/4 100% SR (glm5_2_ms only)
```

### Tier Attempts
```
glm5_2_nv pexec_success: 9 (avg ~8,860ms)
glm5_2_nv pexec_SSLEOFError: 1 (5,002ms)
dsv4p_nv: all 504 → cycle → budget break → no attempt logged
```

### Compose / Env
```
compose md5: 8cfe23c998ec1906c735128e79ed92bc (R1619)
```

关键参数 (全部 floor/optimal):
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66         (=UPSTREAM_TIMEOUT, BUDGET Floor Pattern)
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1       (floor)
NVU_EMPTY_200_FASTBREAK=2           (code-level no-op per R1039/R1489)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1   (floor)
NVU_PEER_FB_SKIP_MODELS=            (empty — all models peer-fb enabled)
NVU_PEER_FALLBACK_TIMEOUT=60        (R1619: 66→60)
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_CONNECT_RESERVE_S=0
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_FORCE_STREAM_UPGRADE=0
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```

## 分析

### R1619 刚部署 4 分钟
- NVU_PEER_FALLBACK_TIMEOUT 66→60 刚生效
- 无新 dsv4p_nv 请求积累 — 无法评估效果
- 需要等待更长时间窗口的数据

### 504 函数级 NVCF 降级 (dsv4p_nv)
- 100% dsv4p_nv 请求 ATE — 全部 504_nv_gateway_timeout
- error_detail.jsonl 确认: 所有 keys 轮流出现 504, 函数级降级
- BUDGET=66 floor pattern 正确: k1-504(~64s)→立即 ATE→peer-fb
- 非 config 可修复 — NVCF 侧函数降级

### zombie_empty_completion (glm5_2_nv)
- NVCF content-filter: input >150K chars, content <50 chars
- 非 config 可修复 — NVCF 侧内容过滤

### peer-fb 可靠性
- 6/9 OK (67%), 3/9 TimeoutError (HM2 侧)
- R1619 降低 PEER_FALLBACK_TIMEOUT 60s 为失败 peer-fb 节省 6s

### 参数评估
- 所有参数已到 floor/optimal
- BUDGET=66=UPSTREAM_TIMEOUT: 不能再降 (会截断正常请求)
- FASTBREAK=1: 函数级 floor, 不能再降
- PEER_FB_SKIP_MODELS 空: 所有模型启用 peer-fb
- CONNECT_RESERVE_S=0: floor (已零)
- PEER_FALLBACK_TIMEOUT=60: R1619 刚降, 需要观察
- 无任何可优化参数

## 结论: NOP

所有参数 floor/optimal。R1619 (PEER_FALLBACK_TIMEOUT 66→60) 刚部署 4 分钟，无新数据评估。失败模式是 NVCF 侧函数降级 (504) 和内容过滤 (zombie)，非 config 可修复。peer-fb 6/9 rescue 提供可靠保护。等待下一轮数据积累。

## Improvements Since R1619
- R1619 PEER_FALLBACK_TIMEOUT 66→60 已生效 (nv_gw restart 4min)
- 无新请求 — 等待数据积累
- 所有参数 floor/optimal, 无改动空间
## ⏳ 轮到HM1优化HM2