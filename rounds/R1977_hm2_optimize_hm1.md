# R1977 (HM2→HM1): NOP — 2 zombie all NVCF empty200, big_input breaker+peer-fb rescuing, 连续冻结第15轮

## 数据 (24h window, 2026-07-20 04:50 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 163 |
| 成功 (200 genuine) | 45 (27.6%) |
| 成功 (200 phantom ATE peer-fb) | 60 (36.8%) |
| 真实失败 (502 zombie) | 56 (34.4%) |
| 真实失败 (502 ATE) | 2 (1.2%) |
| 2h 窗口 | 7/8 (87.5% SR, 1 zombie) |

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 54 | 5,944 |
| dsv4p_nv | zombie_empty_completion | 2 | 19,603 |
| dsv4p_nv | all_tiers_exhausted (real) | 2 | 3 |

### Phantom ATE (status=200, rescued)

| 模型 | 数量 | 救援路径 |
|---|---|---|
| glm5_2_nv | 42 | big_input breaker → peer-fallback → HM2 |
| dsv4p_nv | 18 | big_input breaker → peer-fallback → HM2 |

### 成功延迟

| 模型 | 数量 | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 6 | 17,267 | 11,102 | 27,809 |
| glm5_2_nv | 39 | 9,973 | 1,916 | 27,809 |

### Tier Attempts (24h)

| 错误类型 | 数量 |
|---|---|
| pexec_success | 104 |
| pexec_429 | 3 |
| pexec_SSLEOFError | 2 |
| pexec_timeout | 1 |

### 日志关键事件

```
[NV-BIGINPUT-FB-OPEN] big_input breaker OPEN for glm5_2_nv (input=152K-154K chars) → peer-fallback
[NV-PEER-FB] peer fallback OK: status=200, ttfb=1-10ms
[NV-ZOMBIE-EMPTY] glm5_2_nv zombie empty (large input, content_chars=11, reasoning_chars=0)
```

### 容器状态

- 容器启动: 2026-07-19 18:35 UTC (Up 2 hours)
- 零漂移: 所有 env 与 compose 一致
- 全参数在 floor/optimal:
  - `KEY_COOLDOWN_S=60`, `TIER_COOLDOWN_S=60`
  - `UPSTREAM_TIMEOUT=30`
  - `TIER_TIMEOUT_BUDGET_S=153`
  - `NVU_PEER_FALLBACK_TIMEOUT=122`
  - `NVU_TIER_BUDGET_GLM5_2_NV=28`, `NVU_TIER_BUDGET_DSV4P_NV=20`
  - `NVU_PEXEC_TIMEOUT_FASTBREAK=1`, `NVU_EMPTY_200_FASTBREAK=1`
  - `NVU_BIG_INPUT_THRESHOLD=115000`, `FAIL_N=1`, `COOLDOWN=86400`
  - `MIN_OUTBOUND_INTERVAL_S=0`, `NVU_CONNECT_RESERVE_S=0`
  - `NVU_SSLEOF_RETRY_DELAY_S=0.1`
  - `NVU_STREAM_FIRST_BYTE_DEADLINE_S=15`, `NVU_STREAM_TOTAL_DEADLINE_S=25`

## 约束检查

- Peer-fallback: `UPSTREAM=30 + PEER=122 = 152 < 153 BUDGET` ✓ (1s margin)
- PEER=122 ≥ HM2_GLM_BUDGET=120+2=122 ✓ (精确边界)
- Tier budgets: `DSV4P=20`, `GLM52=28` — floor
- KEY=TIER=60 — 3 个 429 cycle 均为 1 cycle
- 与 R1975 相比: 0 漂移, 所有参数一致

## 判断

1. 56 个 zombie 全部为 NVCF 级别 empty200（大输入 glm5_2_nv + dsv4p_nv），非配置可修复
2. Big_input breaker + peer-fallback 组合有效救援 60 个 phantom ATE（全部 status=200）
3. 2h 窗口: 7/8, 仅 1 zombie（NVCF 级别）
4. Tier attempts 近乎纯净: 104 pexec_success, 仅 3 个 429 + 2 SSLEOF + 1 timeout（零配置可修错误）
5. 所有参数已在 floor/optimal，无进一步压缩空间
6. 无可调空间，NOP
7. 连续冻结第 15 轮 (R1963→R1977)
8. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2