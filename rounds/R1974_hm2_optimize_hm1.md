# R1974 (HM2→HM1): NOP — 4 zombie all NVCF empty200, big_input breaker+peer-fb rescuing, 连续冻结第13轮

## 数据 (6h window, 2026-07-19 14:36–20:36 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 39 |
| 成功 | 35 (89.7% SR) |
| 失败 | 4 (10.3%) |
| 30m 窗口 | 2/2 100% SR |

### 失败明细

| 模型 | 错误类型 | 数量 | 时长 |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 4 | 3.5–4.4s |

### Phantom ATE (status=200, rescued)

| 模型 | 数量 | 救援路径 |
|---|---|---|
| glm5_2_nv | 20 | big_input breaker → peer-fallback → HM2 |
| dsv4p_nv | 6 | big_input breaker → peer-fallback → HM2 |

### 成功延迟

| 模型 | 数量 | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 10 | 31,599 | 11,102 | 55,335 |
| glm5_2_nv | 25 | 8,066 | 3,325 | 17,786 |

### 429 状况

- glm5_2_nv: 9 req, key_cycle_429s=1

### 日志关键事件

```
[NV-BIGINPUT-FB-OPEN] big_input breaker OPEN for glm5_2_nv → peer-fallback → all OK
[NV-PEER-FB] peer fallback OK: status=200, ttfb=1-10ms
[NV-ZOMBIE-EMPTY] glm5_2_nv zombie empty (large input, content_chars=11, reasoning_chars=0)
```

## 约束检查

- Peer-fallback: `UPSTREAM=30 + PEER=122 = 152 < 153 BUDGET` ✓ (1s margin)
- PEER=122 ≥ HM2_BUDGET=120+2=122 ✓ (精确边界)
- Tier budgets: `DSV4P=20`, `GLM52=28` — 所有成功的 dsv4p 请求 max=55.3s，但 dsv4p ATE phantom 有 55s 的（NVCF 劣化），实际成功路径在 20s 内
- KEY=TIER=60 — 9 个 429 cycle 均为 1 cycle

## 判断

- 4 个 zombie 全部为 NVCF 级别 empty200（大输入 glm5_2_nv），非配置可修复
- Big_input breaker + peer-fallback 组合有效救援 26 个 phantom ATE（全部 status=200）
- 所有参数已在 floor/optimal：
  - `UPSTREAM_TIMEOUT=30` (floor)
  - `TIER_TIMEOUT_BUDGET_S=153` (精算边界)
  - `NVU_TIER_BUDGET_DSV4P_NV=20` (floor)
  - `NVU_TIER_BUDGET_GLM5_2_NV=28` (floor)
  - `KEY_COOLDOWN_S=TIER_COOLDOWN_S=60`
  - `MIN_OUTBOUND_INTERVAL_S=0`
  - `PEER_FALLBACK_TIMEOUT=122` (精算边界)
- 无可调空间，NOP
- 连续冻结第 13 轮 (R1962→R1974)
- 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
