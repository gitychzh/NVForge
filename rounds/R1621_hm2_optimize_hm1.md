# R1621: HM2→HM1 — NOP (all params floor/optimal, 504 NVCF function-level degradation, zombie content-filter)

## 数据收集 (HM1, 2026-07-16 13:50 UTC)

### 容器状态
```
nv_gw    Up 23 minutes (healthy)  — R1619 重启
ms_gw    Up ~1 hour (healthy)
logs_db  Up 30 hours (healthy)
```

### 6h 总体 SR
```
23 req / 14 OK / 9 fail = 60.9% SR
```

### 分模型
```
dsv4p_nv:  12 req / 8 OK / 4 fail = 66.7% SR  (all ATE: 504_nv_gateway_timeout)
glm5_2_nv: 11 req / 6 OK / 5 fail = 54.5% SR  (all ATE: zombie_empty_completion)
```

### 错误分类
```
zombie_empty_completion: 5  (glm5_2_nv NVCF content-filter)
all_tiers_exhausted:     4  (dsv4p_nv 504 → peer-fb)
```

### Post-Restart (23min)
```
3 req / 1 OK / 2 fail = 33.3% SR
dsv4p_nv:  1/1 ATE (all_tiers_exhausted, 63,706ms) → peer-fb TimeoutError 60,080ms
glm5_2_nv: 2 req (1 OK 13,708ms, 1 zombie 13,061ms)
```

### dsv4p_nv 504 模式 (100% 函数级降级)
```
error_detail.jsonl 确认: 全部 dsv4p_nv ATE 为 504_nv_gateway_timeout
num_attempts=1 (BUDGET Floor Pattern: k1-504(~64s)→剩余<5s→立即 ATE)
所有 5 keys 交叉出现 504 — 函数级, 非 key-specific
日志: [NV-CYCLE] tier=dsv4p_nv k5 → 504 (504_nv_gateway_timeout), cycling to next key
     [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=0, other=1, elapsed=63703ms
```

### peer-fb 表现
```
Post-restart: 1/1 TimeoutError at 60,080ms (=NVU_PEER_FALLBACK_TIMEOUT=60 binding)
R1619 前: 6/9 OK (67%), 3/9 TimeoutError at 66s boundary
R1619 后: 1/1 TimeoutError at 60s boundary (仅 1 数据点)
```

### ms_gw
```
5/5 100% SR (glm5_2_ms only)
dsv4p_ms 在 MODEL_REGISTRY 中 (_disabled=False) 但不在 MODELMAP (R1609 移除)
```

### Tier Attempts
```
glm5_2_nv pexec_success: 11 (avg 9,029ms, max 13,694ms)
glm5_2_nv pexec_SSLEOFError: 1 (5,002ms)
dsv4p_nv: 504 → cycle → budget break → no attempt logged
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
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
KEY_AUTHFAIL_COOLDOWN_S=60
```

## 分析

### 504 NVCF 函数级降级 (dsv4p_nv)
- 100% dsv4p_nv 请求 ATE — 全部 504_nv_gateway_timeout
- error_detail.jsonl 确认: 所有 5 keys 交叉出现 504, 函数级降级
- BUDGET=66=UPSTREAM_TIMEOUT floor pattern: k1-504(~64s)→剩余<5s→立即 ATE→peer-fb
- 非 config 可修复 — NVCF 侧函数降级
- 即使 peer-fb HOLDS (R1609 移除 dsv4p_nv from MODELMAP, peer-fb 是唯一救援路径)

### zombie_empty_completion (glm5_2_nv)
- NVCF content-filter: input >150K chars, content <50 chars
- 代码级 zombie 检测 (R1107): 3-15s fast abort, 优于旧 96s hang
- 非 config 可修复 — NVCF 侧内容过滤

### peer-fb 可靠性
- Post-restart: 1/1 TimeoutError at 60,080ms (=NVU_PEER_FALLBACK_TIMEOUT=60)
- R1619 前: 6/9 OK (67%), 3/9 TimeoutError at 66s
- R1619 的 -6s 节省了每个失败 peer-fb 的 6s, 但 1 数据点不足以评估
- TimeoutError 是 HM2 侧响应慢 — 非 HM1 config 可修复

### 参数评估
- 所有参数已到 floor/optimal
- BUDGET=66=UPSTREAM_TIMEOUT: 不能再降 (会截断正常请求)
- FASTBREAK=1: 函数级 floor, 不能再降
- PEER_FB_SKIP_MODELS 空: 所有模型启用 peer-fb
- CONNECT_RESERVE_S=0: floor (已零)
- PEER_FALLBACK_TIMEOUT=60: R1619 刚降 23min, 需要更多数据
- MODELMAP 无 dsv4p_nv: R1609 移除 (ms_gw dsv4p_ms 流同步缺陷, 100% TimeoutError)
- 无任何可优化参数

## 结论: NOP

所有参数 floor/optimal。R1619 (PEER_FALLBACK_TIMEOUT 66→60) 部署 23min, 仅 1 个新 dsv4p_nv 请求 (peer-fb TimeoutError at 60s 边界)。失败模式是 NVCF 侧函数降级 (504) 和内容过滤 (zombie)，非 config 可修复。peer-fb 是 dsv4p_nv 唯一救援路径 (R1609 移除 MODELMAP 中的 dsv4p_nv)。等待下一轮数据积累。

## Improvements Since R1619
- R1619 PEER_FALLBACK_TIMEOUT 66→60 已生效 (nv_gw restart 23min)
- 仅 1 个新 dsv4p_nv 请求 — 数据不足, 无法评估 R1619 效果
- 所有参数 floor/optimal, 无改动空间
## ⏳ 轮到HM1优化HM2
