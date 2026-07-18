# R1806 (HM2→HM1): NOP — false trigger, 零可配置修复故障, 100% SR, 改前必有数据铁律触发

**时间**: 2026-07-18 23:30 UTC
**触发**: HM2自提交 R1805 (`这是我提交的, 不触发` — false trigger)
**作者**: opc2_uname (HM2)

## 改前数据 (2026-07-18 23:30 UTC)

### 6h DB (17:30-23:30 UTC)

| request_model | total | ok | fail | sr_pct | avg_ms | min_ms | max_ms |
|---------------|-------|-----|------|--------|--------|--------|--------|
| glm5_2_nv     |    24 | 24 |    0 |  100.0 |  10269 |   5480 |  21582 |

**总**: 24req/24OK (100.0% SR) / 0 fail

### 1h DB (22:30-23:30 UTC)

| request_model | total | ok | fail |
|---------------|-------|-----|------|
| glm5_2_nv     |     4 |  4 |    0 |

### 错误分析 (6h)

| error_type | cnt | 可修性 |
|------------|-----|--------|
| (none)     |   0 | N/A |

→ 零错误。Zero ATE, zero zombie, zero fallback, zero peer-fb, zero tier_attempts errors.

### Tier Attempts (6h)

| tier | error_type | cnt | avg_ms |
|------|-----------|-----|--------|
| glm5_2_nv | pexec_success | 24 | 9835 |
| glm5_2_nv | pexec_SSLEOFError | 2 | 5002 |

→ 2× SSLEOFError at tier_attempt level, avg=5002ms, self-recovery (not request failures). 100% SR at request level.

### 最近20条请求 (全部 glm5_2_nv pexec, 100% OK)

```
ts                  | model      | status | dur_ms | ttfb_ms | type     | kc429
15:03:27            | glm5_2_nv  |    200 |   9730 |    9729 | pexec    |    1
15:03:20            | glm5_2_nv  |    200 |   6259 |    6259 | pexec    |    1
14:33:35            | glm5_2_nv  |    200 |  11806 |   11806 | pexec    |    2
14:33:20            | glm5_2_nv  |    200 |  14130 |   14130 | pexec    |    1
14:03:28            | glm5_2_nv  |    200 |   7220 |    7219 | pexec    |    1
14:03:20            | glm5_2_nv  |    200 |   7303 |    7303 | pexec    |    1
13:33:42            | glm5_2_nv  |    200 |   8960 |    8959 | pexec    |    1
13:33:20            | glm5_2_nv  |    200 |  21582 |   21582 | pexec    |    1
13:03:40            | glm5_2_nv  |    200 |   9107 |    9106 | pexec    |    1
13:03:20            | glm5_2_nv  |    200 |  19093 |   19093 | pexec    |    1
12:33:30            | glm5_2_nv  |    200 |   9462 |    9462 | pexec    |    1
12:33:20            | glm5_2_nv  |    200 |   9774 |    9774 | pexec    |    1
12:03:29            | glm5_2_nv  |    200 |  13392 |   13391 | pexec    |    1
12:03:20            | glm5_2_nv  |    200 |   8351 |    8351 | pexec    |    1
11:33:36            | glm5_2_nv  |    200 |   6205 |    6204 | pexec    |    1
11:33:20            | glm5_2_nv  |    200 |  15814 |   15814 | pexec    |    2
11:03:27            | glm5_2_nv  |    200 |   6780 |    6779 | pexec    |    1
11:03:20            | glm5_2_nv  |    200 |   6748 |    6747 | pexec    |    1
10:33:26            | glm5_2_nv  |    200 |  10903 |   10902 | pexec    |    1
10:33:20            | glm5_2_nv  |    200 |   5480 |    5480 | pexec    |    1
```

→ 全部 pexec SUCCESS, 5 keys cycling, key_cycle_429s=1-2 (normal rotation), 零错误

### 日志 (最近100行)

```
[NV-GLM52-IDX] restored: idx=0
[NV-RR] restored: nv_dsv4p=2576, nv_kimi=83, nv_glm5_2=913, nv_minimax_m3_nv=1, nv_minimax_m3=19
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] role=passthrough, tiers=['kimi_nv','dsv4p_nv','glm5_2_nv'] default=dsv4p_nv
[NV-PROXY] Listening on 0.0.0.0:40006
```

→ 零 error/warn/fail/timeout/refused/reset/unhealthy/crash/panic/ZOMBIE/ATE/TIER-EXHAUSTED/NV-PEER-FB/FALLBACK/NV-INTEGRATE

### 其他指标

- **fallback**: 0 (全部 f)
- **peer-fb**: 0 (零 peer-fb 触发)
- **zombie_empty_completion**: 0
- **key_cycle_429s**: glm5_2_nv key rotation normal (1-2 per request)
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

- Compose md5: 7738f1a3f1fbc5c7299c1729ebe75e27
- 容器 env 与 compose 一致 ✓
- 零漂移

### HM2 Compose (peer-fb约束验证)

```
TIER_TIMEOUT_BUDGET_S=180
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.153.83:40006
NVU_TIER_BUDGET_DSV4P_NV=70
```

→ HM1 peer-fb: dsv4p tier budget 45 + PEER_FALLBACK_TIMEOUT 122 = 167 < 180 ✓
→ Peer-fb constraint: PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET(70)+2=72 ✓

## 分析

1. **False trigger**: R1805 是 HM2 自提交 (`NVU_TIER_BUDGET_GLM5_2_NV 110→105`), 脚本正��识别 "这是我提交的, 不触发" 但 cron 仍被派遣。

2. **glm5_2_nv: 100% SR (24/24)**: pexec路径完美, avg=10269ms, max=21582ms。2× SSLEOFError at tier_attempt level (avg=5002ms), self-recovery, 不影响请求级别成功率。Zero zombie_empty_completion。key_cycle_429s 正常 (1-2 per request, key rotation normal)。

3. **零 dsv4p_nv 流量**: 6h window zero dsv4p_nv requests。R1801 (NVU_TIER_BUDGET_DSV4P_NV=45) 无法验证效果。但零 dsv4p 流量意味着无 ATE 风险, 无需干预。

4. **零 fallback, 零 peer-fb, 零 zombie, 零 tier_attempts errors**: 系统干净, 无可配置修复项。

5. **所有参数 at floor/optimal**: FASTBREAK=1 (pexec+integrate+empty200), KEY_COOLDOWN=65, TIER_COOLDOWN=65, SSLEOF_RETRY=0.2, EMPTY_200=1, CONNECT_RESERVE=0, MIN_OUTBOUND_INTERVAL=0, INTEGRATE_KEY_COOLDOWN=0, BIG_INPUT_FAIL_N=1。NVU_TIER_BUDGET_GLM5_2_NV=105 刚在 R1805 从 110 缩减, 需等待数据验证效果。NVU_TIER_BUDGET_DSV4P_NV=45 已到 floor (UPSTREAM=55 - 10s margin)。

6. **容器漂移: 零**: compose md5一致, 容器env与compose一致。

7. **SSLEOF_RETRY_DELAY_S=0.2**: 已到 floor (R1799 0.3→0.2)。0.2s 仍为 retry gap 提供最低间隔, 降至 0.1s 收益极小 (2×SSLEOF/6h, 节省 0.2s/6h), 且 0s 可能在 SSLEOF 突发时导致 tight-loop retry。保持 0.2s。

## 决策: NOP (零变更)

**理由**: 零可配置修复故障。glm5_2_nv 100% SR。零 dsv4p_nv 流量。零 zombie, 零 fallback, 零 peer-fb。所有参数 floor/optimal。NVU_TIER_BUDGET_GLM5_2_NV=105 刚在 R1805 缩减需等待验证。NVU_SSLEOF_RETRY_DELAY_S=0.2 已到 floor。零漂移。

铁律: 只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
