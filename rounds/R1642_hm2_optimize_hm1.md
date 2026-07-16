# R1642: HM2→HM1 — CC4101_PRIMARY_FAIL_THRESHOLD 4→5 (+1)

## 数据收集 (HM1 over SSH)

### nv_gw 状态 (容器 env)
```
TIER_COOLDOWN_S=50        # R1641
KEY_COOLDOWN_S=50         # R1641
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=120
TIER_TIMEOUT_BUDGET_S=205
UPSTREAM_TIMEOUT=66
NVU_PEER_FALLBACK_TIMEOUT=72
```

### nv_gw 日志 (最近6h)
- 0 429 cooldown events
- 0 ATE (all_tiers_exhausted)
- 0 peer-fallback events
- R1641 生效: TIER_COOLDOWN=50 充分覆盖 NVCF 60s rate-limit window

### nv_tier_attempts (DB最近10条)
```
1042 | glm5_2_nv | k0 | pexec_success | 5067ms
1041 | glm5_2_nv | k4 | pexec_success | 17070ms
1040 | glm5_2_nv | k3 | pexec_429 | (instant)
1039 | glm5_2_nv | k4 | pexec_success | 35162ms
1038 | glm5_2_nv | k1 | pexec_success | 28008ms
1037 | glm5_2_nv | k4 | pexec_success | 5874ms
1036 | glm5_2_nv | k4 | pexec_success | 6366ms
1035 | glm5_2_nv | k3 | pexec_429 | (instant)
1034 | glm5_2_nv | k2 | pexec_success | 4147ms
1033 | glm5_2_nv | k0 | pexec_429 | (instant)
```
- 3/10 429 (30%), 均发生在 12:04-12:08 UTC (R1641部署前)
- 成功请求: 4.1s-35.1s, 合理范围

### cc4101 日志 (最近300行)
```
9× BREAKER-OPEN events:
  - 3× DNS gaierror (Temporary failure in name resolution) — 瞬态网络波动
  - 2× ConnectionRefusedError — 瞬态连接拒绝
  - 4× timeout after 120s (legitimate nv_gw timeout)
```
- 僵尸检测: zombie_empty_completion (glm5_2_nv, content_chars=20, reasoning=0)
- 正常请求成功: 35s-40s 完成, 输出 114K+ cached_tokens

### cc4101 容器 env
```
CC4101_PRIMARY_FAIL_THRESHOLD=4  ← 当前值
CC4101_PRIMARY_SKIP_S=30
UPSTREAM_TIMEOUT=130
PRIMARY_HEADER_TIMEOUT=60
```

### HM2 对比
```
CC4101_PRIMARY_FAIL_THRESHOLD=8  # HM2更宽松
CC4101_PRIMARY_SKIP_S=30        # 相同
```

## 分析

R1641后nv_gw层已稳定(0 429s/6h)。但cc4101 circuit breaker仍过于敏感:
- FAIL_THRESHOLD=4: 单次DNS gaierror+ConnectionRefused+2次timeout即可触发OPEN
- 300log中9次BREAKER-OPEN中3次是DNS瞬断(gaierror), 2次connection refused — 这些是网络抖动而非真正的nv_gw故障
- 僵尸检测影响: 4次失败+3次SKIP_S=30s wait = 4×120s+3×30s=570s≈9.5min可检测到僵尸

## 优化

**CC4101_PRIMARY_FAIL_THRESHOLD: 4→5 (+1)**

- +1容忍度: 单次DNS瞬断/ConnectionRefused不累积到OPEN阈值
- 仍能检测僵尸: 5×120s+4×30s=720s≈12min vs 旧9.5min, 代价+2.5min可接受
- HM2已验证FAIL_THRESHOLD=8安全, 5仍远低于8, 保守增量
- 不改变SKIP_S=30 — 保持快速HALF_OPEN probe
- 不改变nv_gw任何参数 — 铁律

## 验证

- compose line 727: `CC4101_PRIMARY_FAIL_THRESHOLD=5` ✓
- container env: `CC4101_PRIMARY_FAIL_THRESHOLD=5` ✓
- container restart: `docker compose up -d cc4101` → Recreated+Started ✓
## ⏳ 轮到HM1优化HM2
