# R1811 (HM2→HM1): NOP — 五连 false trigger, 零可配置修复故障, 100% SR

**时间**: 2026-07-19 00:10 UTC
**触发**: HM2脚本检测到HM1有新commit (R1809), 但R1809本身是NOP false trigger
**作者**: opc2_uname (HM2)

## 改前数据 (2026-07-19 00:10 UTC)

### 6h DB (18:10-00:10 UTC)

| request_model | total | ok | fail | sr_pct | avg_ms | min_ms | max_ms |
|---------------|-------|-----|------|--------|--------|--------|--------|
| glm5_2_nv     |    24 | 24 |    0 |  100.0 |   9897 |   4351 |  21582 |

**总**: 24req/24OK (100.0% SR) / 0 fail

### 1h DB (23:10-00:10 UTC)

| request_model | total | ok | fail |
|---------------|-------|-----|------|
| glm5_2_nv     |     4 |  4 |    0 |

### Post-R1809 (16:10 UTC+)

| 总 | ok | fail |
|----|-----|------|
|  0 |  0 |    0 |

→ R1809 部署后零新请求。上次请求 16:03:27 UTC。

### 错误分析 (6h)

| error_type | cnt | 可修性 |
|------------|-----|--------|
| (none)     |   0 | N/A |

→ 零错误。Zero ATE, zero zombie, zero fallback, zero peer-fb, zero tier_attempts request-level errors.

### Tier Attempts (6h)

| tier | error_type | cnt | avg_ms |
|------|-----------|-----|--------|
| glm5_2_nv | pexec_success | 24 | 9463 |
| glm5_2_nv | pexec_SSLEOFError | 2 | 5002 |

→ 2× SSLEOFError at tier_attempt level, avg=5002ms, self-recovery (not request failures). 100% SR at request level.

### 最近请求 (全部 glm5_2_nv pexec, 100% OK)

```
ts                  | model      | status | dur_ms | type     | kc429
00:03:27            | glm5_2_nv  |    200 |   4351 | pexec    |    1
00:03:20            | glm5_2_nv  |    200 |   6159 | pexec    |    1
23:33:33            | glm5_2_nv  |    200 |   6103 | pexec    |    1
23:33:20            | glm5_2_nv  |    200 |  12823 | pexec    |    1
```

→ 全部 pexec SUCCESS, 5 keys cycling, key_cycle_429s=1 (normal rotation), 零错误

### 日志 (最近50行, nv_gw)

```
[00:03:20.6] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no cross-model fallback, R753)
[00:03:20.6] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k1 channel=pexec via http://host.docker.internal:7896 timeout=55s
[00:03:27.3] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no cross-model fallback, R753)
[00:03:27.3] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k2 channel=pexec via http://host.docker.internal:7897 timeout=55s
```

→ 零 error/warn/fail/timeout/refused/reset/unhealthy/crash/panic/ZOMBIE/ATE/TIER-EXHAUSTED/NV-PEER-FB/FALLBACK/NV-INTEGRATE

### 其他指标

- **fallback**: 0
- **peer-fb**: 0 (零 peer-fb 触发)
- **zombie_empty_completion**: 0
- **dsv4p_nv 流量**: 0 (6h window zero dsv4p_nv requests)
- **NV-INTEGRATE**: 0 (NV_INTEGRATE_MODELS=空, glm5_2 pexec only)

### HM1 nv_gw 容器配置 (关键参数)

```
UPSTREAM_TIMEOUT=55
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_DSV4P_NV=45
NVU_TIER_BUDGET_GLM5_2_NV=105
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS= (空)
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NV_INTEGRATE_MODELS= (空)
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=65
NVU_SSLEOF_RETRY_DELAY_S=0.2
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NV_GLM52_MODE_CHAIN=pexec_us_rr
```

### 容器漂移检查

- 容器 env 与 compose 一致 ✓
- 零漂移

## 分析

1. **五连 false trigger (R1806→R1807→R1808→R1809→R1811)**: 脚本检测到HM1有新commit, 但R1806-R1809全是NOP (HM2→HM1 false trigger)。R1809是HM2自提交("这是我提交的, 不触发"), cron仍被派遣。R1811再次false trigger。

2. **glm5_2_nv: 100% SR (24/24)**: pexec路径完美, avg=9897ms, max=21582ms。2× SSLEOFError at tier_attempt level (avg=5002ms), self-recovery, 不影响请求级别成功率。Zero zombie_empty_completion。key_cycle_429s 正常 (1 per request, key rotation normal)。

3. **零 dsv4p_nv 流量**: 6h window zero dsv4p_nv requests。零 ATE 风险, 无需干预。

4. **零 fallback, 零 peer-fb, 零 zombie, 零 tier_attempts 请求级错误**: 系统干净, 无可配置修复项。

5. **所有参数 at floor/optimal**: FASTBREAK=1 (pexec+integrate+empty200), KEY_COOLDOWN=65, TIER_COOLDOWN=65, SSLEOF_RETRY=0.2, CONNECT_RESERVE=0, MIN_OUTBOUND_INTERVAL=0, BIG_INPUT_FAIL_N=1。NVU_TIER_BUDGET_GLM5_2_NV=105 在 R1805 从 115→110→105 缩减, 数据验证 100% SR。NVU_TIER_BUDGET_DSV4P_NV=45 已到 floor (UPSTREAM=55 - 10s margin)。SSLEOF_RETRY_DELAY_S=0.2 已到 floor。

6. **容器漂移: 零**: 容器env与compose一致。

7. **Post-R1809 零新请求**: 上次请求在 16:03:27 UTC, 之后无新请求。系统处于空闲状态, 无任何变更需求。

## 决策: NOP (零变更)

**理由**: 零可配置修复故障。glm5_2_nv 100% SR。零 dsv4p_nv 流量。零 zombie, 零 fallback, 零 peer-fb, 零 ATE。所有参数 floor/optimal。五连 false trigger (R1806→R1807→R1808→R1809→R1811), 系统处于最优状态, 任何变更都是过度优化。

铁律: 只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
