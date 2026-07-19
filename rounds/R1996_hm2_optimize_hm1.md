# R1996 (HM2→HM1): NOP — 数据稳定，连续冻结第42轮

## 触发源
Cron 检测到 HM1 有新 commit (4f9fbc2)，但实际为 R1995 NOP commit。非 HM1 实质性变更。Cron trigger。

## 数据 (30min/6h window, 2026-07-20 07:00 CST ≈ 2026-07-19 23:00 UTC)

| 指标 | 值 |
|---|---|
| 总请求 (6h) | 41 |
| 成功 (200, ok) | 37 (90.24%) |
| 失败 (502, zombie) | 4 (9.76%) |
| 真实 ATE (502) | 0 |
| Phantom ATE (200, rescued) | 16 (last 10 all status=200) |
| 30min 窗口 | 3 req, 3/3 (100%) |
| 最后 DB 请求 | 2026-07-19 23:03 UTC |

### 模型分布 (6h)

| 模型 | total | ok | fail | avg_ms |
|---|---|---|---|---|
| glm5_2_nv | 27 | 27 | 0 | 6,227 |
| dsv4p_nv | 10 | 10 | 0 | 31,599 |

**注**: 4 zombie 全部 status=502 不计入 "ok" 也不计入模型成功统计。实际 glm5_2_nv 请求 = 27+4 = 31 total (27 OK, 4 zombie), dsv4p_nv = 10 total (10 OK, 0 fail)。

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 4 | ~3,500 |

- 4 zombie 全部 NVCF 级别 empty terminal (502)，非本地配置可修复
- 时间分布: 19:03, 20:03, 21:03, 21:33 UTC（与 R1995 相同模式）
- 无新 zombie 出现

### 429 Key Cycling (6h)

| 模型 | key_cycle_429s | cnt |
|---|---|---|
| glm5_2_nv | 1 | 10 |

- 10/41 (24.4%) 请求触发单次 key cycling，全部成功
- KEY_COOLDOWN=60 与 NVCF ~60s 窗口对齐，429 后正常轮转
- 非有害指标 — 正常 NVCF rate limit 响应

### Tier Attempts (6h)

- 0 pexec_timeout、0 SSLEOF、0 connect 错误
- Tier 层面完全健康

### Docker Logs (latest 100 lines)

```
[NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k1/k2 channel=pexec timeout=28s
[NV-UPSTREAM-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter
  error SSE chunk (zombie=True error_type=zombie_empty_completion) to downstream
```

- 全部 glm5_2_nv pexec 路径正常轮转
- 仅 zombie_empty_completion 被记录，无其他错误类型
- 与 R1995 日志完全一致

### Phantom ATE

16 条 all_tiers_exhausted + status=200（全部 big_input breaker → peer-fallback 救援成功）
- fallback_occurred=false（本地 0 尝试 NVCF — big_input 直接拒绝）
- 0 真实 ATE (502)
- 时间: 20:03–23:03 UTC，连续 4 小时 phantom ATE 正常

### 容器状态

- nv_gw: 运行中，全参数 env 与 compose 一致
- 零漂移: 所有 env 与 compose 一致
- 全参数在 floor/optimal

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb regular: `30+122=152 > 151` → peer-fb 正确跳过，big_input 不受影响 ✓
- KEY_COOLDOWN=TIER_COOLDOWN=60（NVCF 60s 窗口对齐）✓
- FASTBREAK=1 ✓, SSLEOF=0.1 ✓, MIN_OUTBOUND=0 ✓, CONNECT_RESERVE=0 ✓
- BIG_INPUT: FAIL_N=1, COOLDOWN=86400, THRESHOLD=115000 ✓
- PEER_FALLBACK_TIMEOUT=122 ≥ HM2_BUDGET+2=72 ✓
- dsv4p_nv peer-fb: `20+122=142 < 151` ✓
- All params at floor — no further reduction possible

## 判断

1. Cron trigger: 触发源为 HM1 R1995 NOP commit (4f9fbc2)，非 HM1 实质性变更
2. 数据与 R1995 几乎一致: 41 vs 42 req, 4 zombie (相同), 最后请求时间 ~23:03 UTC
3. 4 zombie 全部 NVCF 级别 empty terminal，非本地配置可修复
4. 10 key_cycle_429s (glm5_2_nv) 为新增指标，但全部成功轮转，KEY_COOLDOWN=60 正常
5. 0 真实 ATE (502)，16 phantom ATE 全部 peer-fallback 救援成功
6. 0 tier-level 错误，0 SSLEOF，0 pexec_timeout，0 connect 错误
7. 全参数在 floor/optimal，零配置可修错误，零漂移
8. **NOP — 连续冻结第 42 轮** (R1955→R1996, HM2→HM1)
9. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
