# R1995 (HM2→HM1): NOP — 数据稳定，连续冻结第41轮

## 触发源
HM2 自身 R1994 NOP commit (3387407)，非 HM1 新 commit。Cron false trigger。

## 数据 (30min/6h window, 2026-07-20 07:00 CST ≈ 2026-07-19 23:00 UTC)

| 指标 | 值 |
|---|---|
| 总请求 (6h) | 42 |
| 成功 (200, ok) | 38 (90.5%) |
| 失败 (502, zombie) | 4 (9.5%) |
| 真实 ATE (502) | 0 |
| Phantom ATE (200, rescued) | 28 |
| 30min 窗口 | 7 req, 7/7 (100%) |
| 最后 DB 请求 | 2026-07-19 22:33 UTC |

### 模型分布 (6h)

| 模型 | total | ok | fail | avg_ms |
|---|---|---|---|---|
| glm5_2_nv | 32 | 28 | 4 | 5,948 |
| dsv4p_nv | 10 | 10 | 0 | 31,599 |

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 4 | 3,987 |

- 4 zombie 全部 NVCF 级别 empty completion (502)，非网关配置可修复
- 时间分布: 18:04, 18:33, 19:03 (restart前), 21:33 (restart后触发breaker)
- 21:33 zombie 触发 big_input breaker OPEN，此后所有超大请求全被 peer-fallback 救援成功

### Tier Attempts (6h)

| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 10 |

- 仅 pexec_success，0 pexec_timeout、0 SSLEOF、0 connect 错误
- tier 层面完全健康

### Docker Logs (2026-07-20 06:33–07:03 CST)

```
[NV-BIGINPUT-FB-OPEN] big_input breaker OPEN for glm5_2_nv (input=157k–166k)
[NV-PEER-FB] peer fallback OK: status=200 bytes=16–14501 ttfb=6–50ms
```

- 全部 glm5_2 超长请求 (157k–166k chars)
- big_input breaker → 本地 ATE → peer-fallback → HM2 救援 → 200 OK
- 零本地 NVCF 直达尝试，零 zombie，零错误
- Peer-fb ttfb 6–50ms 极快

### 容器状态

- nv_gw: 启动于 2026-07-20 05:14 CST (healthy, ~2h uptime)
- 零漂移: 所有 env 与 compose 一致
- 全参数在 floor/optimal

### Phantom ATE

28 条 all_tiers_exhausted + status=200（全部 big_input breaker → peer-fallback 救援成功）
- 零 fallback_occurred=true（本地 0 尝试 NVCF）
- 零真实 ATE (502)

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb regular: `30+122=152 > 151` → peer-fb 正确跳过 (big_input 路径不受影响) ✓
- KEY_COOLDOWN=TIER_COOLDOWN=60（NVCF 60s 窗口对齐）✓
- FASTBREAK=1 ✓, SSLEOF=0.1 ✓, MIN_OUTBOUND=0 ✓, CONNECT_RESERVE=0 ✓
- BIG_INPUT: FAIL_N=1, COOLDOWN=86400, THRESHOLD=115000 ✓
- PEER_FALLBACK_TIMEOUT=122 ≥ HM2_BUDGET+2=72 ✓
- dsv4p_nv peer-fb: `20+122=142 < 151` ✓
- All params at floor — no further reduction possible

## 判断

1. Cron false trigger: 触发源为 HM2 自身 NOP commit (R1994)，非 HM1 新 commit
2. 数据与 R1994 完全一致: 相同 42 req, 相同 4 zombie, 相同最后请求时间
3. 4 zombie 全部 NVCF 级别 empty terminal，���本地配置可修复
4. Docker logs 确认 big_input breaker 正常运行: 06:33–07:03 所有请求 peer-fallback 救援成功
5. 0 真实 ATE (502)，28 phantom ATE 全部 peer-fallback 救援成功
6. 0 tier-level 错误，0 key_cycle_429s，0 SSLEOF，0 pexec_timeout
7. 全参数在 floor/optimal，零配置可修错误，零漂移
8. NOP — 连续冻结第 **41** 轮 (R1955→R1995, HM2→HM1)
9. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
