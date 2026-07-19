# R1979 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 153→151 (-2s) — 6h 92.1%SR, 3 zombie glm5_2, 28+122=150<151 safe

## 数据 (6h window, 2026-07-20 05:00 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 38 |
| 成功 (200) | 35 (92.11%) |
| 失败 (502 zombie) | 3 (7.89%) |
| Phantom ATE (200) | 26 (18 glm5_2 + 8 dsv4p) |
| 30min | 2/2 (100%) |

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms | key_cycle_429s |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 3 | 4,180 | 1 each |

### 成功延迟

| 模型 | 数量 | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | 25 | 8,066 | 3,325 | 17,786 |
| dsv4p_nv | 10 | 31,599 | 11,102 | 55,335 |

### 429 分析

| 模型 | 429 请求数 | total_429s |
|---|---|---|
| glm5_2_nv | 8 | 8 |

### 日志关键事件

```
[NV-UPSTREAM-ERROR-CHUNK] glm5_2_nv sent finish_reason=content_filter error SSE chunk (zombie=True error_type=zombie_empty_completion)
```

### Tier Attempts (6h)

| 错误类型 | 数量 |
|---|---|
| pexec_success | 8 |
| pexec_429 | 0 |
| pexec_SSLEOFError | 0 |
| pexec_timeout | 0 |

## 变更

| 参数 | 旧值 | 新值 | 理由 |
|---|---|---|---|
| `TIER_TIMEOUT_BUDGET_S` | 153 | 151 | -2s fail path. 28+122=150<151 ✓ (1s margin). Peer-fb constraint: 30+122=152>151 → peer-fb triggers at 151 instead of 153, saves 2s per fail request. |

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb: `30+122=152 > 151` → peer-fb triggers at boundary, correctly
- PEER=122 ≥ HM2_GLM_BUDGET=120+2=122 ✓ (精确边界)
- KEY=TIER=60 — NVCF rate limit boundary
- FASTBREAK: pexec=1, empty200=1 — both floor
- All other params unchanged

## 判断

1. 3 zombie 全部 NVCF 级别 empty200 (glm5_2_nv)，非配置可修复
2. 26 phantom ATE via big_input+peer-fb → HM2 rescue (all status=200)
3. 8 glm5_2_nv 429 cycles — KEY=60 at NVCF boundary, minimal
4. Tier attempts 纯净: 0 pexec errors, 8 pexec_success
5. BUDGET 153→151: 节省 2s fail path，约束检查通过
6. 单参数，少改多轮
7. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
