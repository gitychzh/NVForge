# R1808 (HM2→HM1): NOP — false trigger, 零可配置修复故障, 100% SR

**时间**: 2026-07-18 23:50 UTC
**触发**: HM2自提交 R1807 (`这是我提交的, 不触发` — false trigger, cron 仍被派遣)
**作者**: opc2_uname (HM2)

## 改前数据 (2026-07-18 23:50 UTC)

### 6h DB (17:50-23:50 UTC)

| request_model | total | ok | fail | sr_pct | avg_ms | min_ms | max_ms |
|---------------|-------|-----|------|--------|--------|--------|--------|
| glm5_2_nv     |    24 | 24 |    0 |  100.0 |  10285 |   5480 |  21582 |

**总**: 24req/24OK (100.0% SR) / 0 fail

### 1h DB (22:50-23:50 UTC)

| request_model | total | ok | fail |
|---------------|-------|-----|------|
| glm5_2_nv     |     4 |  4 |    0 |

### 错误分析 (6h)

| error_type | cnt | 可修性 |
|------------|-----|--------|
| (none)     |   0 | N/A |

→ 零错误。Zero ATE, zero zombie, zero fallback, zero peer-fb, zero tier_attempts request-level errors.

### Tier Attempts (6h)

| tier | error_type | cnt | avg_ms |
|------|-----------|-----|--------|
| glm5_2_nv | pexec_success | 24 | 9851 |
| glm5_2_nv | pexec_SSLEOFError | 2 | 5002 |

→ 2× SSLEOFError at tier_attempt level, avg=5002ms, self-recovery (not request failures). 100% SR at request level.

### 24h DB

| 指标 | 值 |
|------|-----|
| 总请求 | 141 |
| 成功 | 129 (91.5%) |
| 失败 | 12 |
| 错误类型 | 9 zombie_empty_completion + 3 all_tiers_exhausted |
| 可修性 | 全部不可配置修复 (zombie=NVCF server-side, ATE=dsv4p server-side) |

### 最近20条请求 (全部 glm5_2_nv pexec, 100% OK)

```
ts                  | model      | status | dur_ms | type     | kc429
15:33:33            | glm5_2_nv  |    200 |   6103 | pexec    |    1
15:33:20            | glm5_2_nv  |    200 |  12823 | pexec    |    1
15:03:27            | glm5_2_nv  |    200 |   9730 | pexec    |    1
15:03:20            | glm5_2_nv  |    200 |   6259 | pexec    |    1
14:33:35            | glm5_2_nv  |    200 |  11806 | pexec    |    2
14:33:20            | glm5_2_nv  |    200 |  14130 | pexec    |    1
14:03:28            | glm5_2_nv  |    200 |   7220 | pexec    |    1
14:03:20            | glm5_2_nv  |    200 |   7303 | pexec    |    1
13:33:42            | glm5_2_nv  |    200 |   8960 | pexec    |    1
13:33:20            | glm5_2_nv  |    200 |  21582 | pexec    |    1
13:03:40            | glm5_2_nv  |    200 |   9107 | pexec    |    1
13:03:20            | glm5_2_nv  |    200 |  19093 | pexec    |    1
12:33:30            | glm5_2_nv  |    200 |   9462 | pexec    |    1
12:33:20            | glm5_2_nv  |    200 |   9774 | pexec    |    1
12:03:29            | glm5_2_nv  |    200 |  13392 | pexec    |    1
12:03:20            | glm5_2_nv  |    200 |   8351 | pexec    |    1
11:33:36            | glm5_2_nv  |    200 |   6205 | pexec    |    1
11:33:20            | glm5_2_nv  |    200 |  15814 | pexec    |    2
11:03:27            | glm5_2_nv  |    200 |   6780 | pexec    |    1
11:03:20            | glm5_2_nv  |    200 |   6748 | pexec    |    1
```

→ 全部 pexec SUCCESS, 5 keys cycling, key_cycle_429s=1-2 (normal rotation), 零错误

### 日志 (最近100行, nv_gw)

```
[NV-GLM52-IDX] restored from /app/logs/glm52_mode_idx.json: idx=0
[NV-RR] restored from /app/logs/rr_counter.json: {'nv_dsv4p': 2576, 'nv_kimi': 83, 'nv_glm5_2': 913, 'nv_minimax_m3_nv': 1, 'nv_minimax_m3': 19}
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] PROXY_ROLE=passthrough NVU_NUM_KEYS=5 NVCF_pexec_models=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'] tiers=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'] default=dsv4p_nv
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])
[23:33:20.5] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no cross-model fallback, R753)
[23:33:20.5] [NV-GLM52-CHAIN] tier=glm5_2_nv start_mode_idx=0 (=pexec_us_rr) start_key=k4 modes=['pexec_us_rr']
[23:33:20.5] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k4 channel=pexec via http://host.docker.internal:7894 timeout=55s
[23:33:33.3] [NV-GLM52-SUCCESS] tier=glm5_2_nv mode=pexec_us_rr k4 succeeded (mode stabilized, next req keeps this mode)
[23:33:33.3] [NV-STREAM-BUFFER-FLUSH] (glm5_2_nv) full-buffer flushed 954b to downstream (content_chars=0c reasoning=0c, dur=12823ms)
[23:33:33.9] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no cross-model fallback, R753)
[23:33:33.9] [NV-GLM52-CHAIN] tier=glm5_2_nv start_mode_idx=0 (=pexec_us_rr) start_key=k5 modes=['pexec_us_rr']
[23:33:33.9] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k5 channel=pexec via http://host.docker.internal:7895 timeout=55s
[23:33:40.0] [NV-GLM52-SUCCESS] tier=glm5_2_nv mode=pexec_us_rr k5 succeeded (mode stabilized, next req keeps this mode)
[23:33:40.0] [NV-STREAM-BUFFER-FLUSH] (glm5_2_nv) full-buffer flushed 4385b to downstream (content_chars=195c reasoning=0c, dur=6103ms)
```

→ 零 error/warn/fail/timeout/refused/reset/unhealthy/crash/panic/ZOMBIE/ATE/TIER-EXHAUSTED/NV-PEER-FB/FALLBACK/NV-INTEGRATE

### 其他指标

- **fallback**: 0 (全部 f)
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

1. **False trigger**: R1807 是 HM2 自提交 (NOP, "这是我提交的, 不触发"), 脚本正确识别但 cron 仍被派遣。R1808 再次 false trigger。

2. **glm5_2_nv: 100% SR (24/24)**: pexec路径完美, avg=10285ms, max=21582ms。2× SSLEOFError at tier_attempt level (avg=5002ms), self-recovery, 不影响请求级别成功率。Zero zombie_empty_completion。key_cycle_429s 正常 (1-2 per request, key rotation normal)。

3. **零 dsv4p_nv 流量**: 6h window zero dsv4p_nv requests。零 ATE 风险, 无需干预。

4. **零 fallback, 零 peer-fb, 零 zombie, 零 tier_attempts 请求级错误**: 系统干净, 无可配置修复项。

5. **所有参数 at floor/optimal**: FASTBREAK=1 (pexec+integrate+empty200), KEY_COOLDOWN=65, TIER_COOLDOWN=65, SSLEOF_RETRY=0.2, CONNECT_RESERVE=0, MIN_OUTBOUND_INTERVAL=0, BIG_INPUT_FAIL_N=1。NVU_TIER_BUDGET_GLM5_2_NV=105 在 R1805 从 110 缩减, 数据验证 100% SR。NVU_TIER_BUDGET_DSV4P_NV=45 已到 floor (UPSTREAM=55 - 10s margin)。SSLEOF_RETRY_DELAY_S=0.2 已到 floor。

6. **容器漂移: 零**: 容器env与compose一致。

7. **24h 错误**: 9 zombie_empty_completion (NVCF server-side content_filter, 不可配置修复) + 3 dsv4p ATE (server-side, 不可配置修复)。全部不影响 6h 100% SR。

## 决策: NOP (零变更)

**理由**: 零可配置修复故障。glm5_2_nv 100% SR。零 dsv4p_nv 流量。零 zombie, 零 fallback, 零 peer-fb, 零 ATE。所有参数 floor/optimal。三连 false trigger (R1806→R1807→R1808), 系统处于最优状态, 任何变更都是过度优化。

铁律: 只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
