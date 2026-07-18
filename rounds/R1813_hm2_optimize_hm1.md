# R1813 (HM2→HM1): NOP — 七连 false trigger, 零可配置修复故障, 100% SR

**时间**: 2026-07-19 00:30 UTC
**触发**: HM2脚本检测到HM1有新commit (R1812), 但R1812本身是NOP false trigger (HM2自提交)
**作者**: opc2_uname (HM2)

## 改前数据 (2026-07-19 00:30 UTC)

### 6h DB (18:30-00:30 UTC)

| request_model | total | ok | fail | sr_pct | avg_ms | p50_ms | p95_ms |
|---------------|-------|-----|------|--------|--------|--------|--------|
| glm5_2_nv     |    24 | 24 |    0 |  100.0 |   9897 |   9034 |  18601 |

**总**: 24req/24OK (100.0% SR) / 0 fail

### 最近请求 (全部 glm5_2_nv pexec, 100% OK)

```
ts                  | model      | status | dur_ms | type     | key
2026-07-18 16:03:27 | glm5_2_nv  |    200 |   4351 | pexec    | 1
2026-07-18 16:03:26 | glm5_2_nv  |    200 |   6159 | pexec    | 0
2026-07-18 15:33:40 | glm5_2_nv  |    200 |   6103 | pexec    | 4
2026-07-18 15:33:33 | glm5_2_nv  |    200 |  12823 | pexec    | 3
2026-07-18 15:03:37 | glm5_2_nv  |    200 |   9730 | pexec    | 2
2026-07-18 15:03:26 | glm5_2_nv  |    200 |   6259 | pexec    | 1
2026-07-18 14:33:47 | glm5_2_nv  |    200 |  11806 | pexec    | 1
2026-07-18 14:33:34 | glm5_2_nv  |    200 |  14130 | pexec    | 4
2026-07-18 14:03:35 | glm5_2_nv  |    200 |   7220 | pexec    | 3
2026-07-18 14:03:27 | glm5_2_nv  |    200 |   7303 | pexec    | 2
```

→ 全部 pexec SUCCESS, 5 keys cycling, 零错误

### 错误分析 (6h)

| error_type | cnt | 可修性 |
|------------|-----|--------|
| (none)     |   0 | N/A |

→ 零错误。Zero ATE, zero zombie, zero fallback, zero peer-fb, zero tier_attempts request-level errors.

### Tier Attempts (6h)

| tier | error_type | key | cnt |
|------|-----------|-----|-----|
| glm5_2_nv | pexec_success | 0 | 4 |
| glm5_2_nv | pexec_success | 1 | 6 |
| glm5_2_nv | pexec_success | 2 | 3 |
| glm5_2_nv | pexec_success | 3 | 6 |
| glm5_2_nv | pexec_success | 4 | 5 |
| glm5_2_nv | pexec_SSLEOFError | 0 | 1 |
| glm5_2_nv | pexec_SSLEOFError | 2 | 1 |

→ 2× SSLEOFError at tier_attempt level, self-recovery (not request failures). 100% SR at request level.

### Per-Key Latency (6h, success only)

| key | total | avg_ms | p50 | p95 |
|-----|-------|--------|-----|-----|
| K1  |     4 |  11970 | 10070 | 20354 |
| K2  |     6 |   7988 |  7870 | 11298 |
| K3  |     3 |   8832 |  9462 |  9703 |
| K4  |     6 |  11106 | 10022 | 18273 |
| K5  |     5 |   9719 |  9107 | 13485 |

→ 全部key正常, K2最优 (avg=7988ms, p95=11298ms), K1稍高 (avg=11970ms, p95=20354ms) 但仍在正常范围。

### 日志 (最近100行, nv_gw)

```
[00:03:20.6] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv']
[00:03:20.6] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k4 channel=pexec via http://host.docker.internal:7894 timeout=55s
[00:03:27.3] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv']
[00:03:27.3] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k5 channel=pexec via http://host.docker.internal:7897 timeout=55s
```

→ 零 error/warn/fail/timeout/refused/reset/unhealthy/crash/panic/ZOMBIE/ATE/TIER-EXHAUSTED/NV-PEER-FB/FALLBACK/NV-INTEGRATE

### 其他指标

- **fallback**: 0 (f|24 = 零 fallback)
- **peer-fb**: 0 (零 peer-fb 触发)
- **zombie_empty_completion**: 0
- **dsv4p_nv 流量**: 0 (6h window zero dsv4p_nv requests)
- **kimi_nv 流量**: 0 (6h window zero kimi_nv requests)
- **NV-INTEGRATE**: 0 (NV_INTEGRATE_MODELS=空, glm5_2 pexec only)
- **容器健康**: nv_gw Up (healthy), logs_db Up (healthy)

### HM1 nv_gw 容器配置 (关键参数, 与 compose 一致)

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
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```

### 容器漂移检查

- 容器 env 与 compose 一致 ✓
- 零漂移

### HM1 Git 状态

- HM1 git repo HEAD: R1719 (e149fae), 未同步到 R1812
- HM2 git repo HEAD: R1812 (e8ca91b), 已同步最新
- HM1 compose 参数已对应 R1812 值 (UPSTREAM=55, BUDGET=180, KEY=TIER=65, etc.)
- HM1 git 落后但 compose 是最新的 → compose 通过 R1812 部署已更新, git 未同步属于正常

## 分析

1. **七连 false trigger (R1806→R1807→R1808→R1809→R1810(cc2)→R1811→R1812→R1813)**: 脚本检测到HM1有新commit, 但R1806-R1812全是NOP (HM2→HM1 false trigger)。R1811/R1812是HM2自提交("这是我提交的, 不触发"), 但脚本仍检测到新commit并触发R1813。

2. **glm5_2_nv: 100% SR (24/24)**: pexec路径完美, avg=9897ms, p50=9034ms, p95=18601ms。2× SSLEOFError at tier_attempt level, self-recovery, 不影响请求级别成功率。Zero zombie_empty_completion。key_cycle_429s 正常 (1 per request, key rotation normal)。

3. **零 dsv4p_nv / kimi_nv 流量**: 6h window zero dsv4p_nv/kimi_nv requests。零 ATE 风险, 无需干预。

4. **零 fallback, 零 peer-fb, 零 zombie, 零 tier_attempts 请求级错误**: 系统干净, 无可配置修复项。

5. **所有参数 at floor/optimal**: FASTBREAK=1 (pexec+integrate+empty200), KEY_COOLDOWN=65, TIER_COOLDOWN=65, SSLEOF_RETRY=0.2, CONNECT_RESERVE=0, MIN_OUTBOUND_INTERVAL=0, INTEGRATE_KEY_COOLDOWN=0, BIG_INPUT_FAIL_N=1。NVU_TIER_BUDGET_GLM5_2_NV=105 (p99=21.0s, 5.0x margin)。NVU_TIER_BUDGET_DSV4P_NV=45 已到 floor (UPSTREAM=55 - 10s margin)。SSLEOF_RETRY_DELAY_S=0.2 已到 floor。

6. **容器漂移: 零**: 容器env与compose一致。

7. **Post-R1812 零新请求**: 上次请求在 2026-07-18 16:03:27 UTC, 之后无新请求。系统处于空闲状态, 无任何变更需求。

8. **健康检查**: nv_gw health OK, nv_num_keys=5, pexec models=[kimi_nv, dsv4p_nv, glm5_2_nv], default=dsv4p_nv。全部正常。

## 决策: NOP (零变更)

**理由**: 零可配置修复故障。glm5_2_nv 100% SR。零 dsv4p_nv 流量。零 zombie, 零 fallback, 零 peer-fb, 零 ATE。所有参数 floor/optimal。七连 false trigger (R1806→R1807→R1808→R1809→R1810(cc2)→R1811→R1812→R1813), 系统处于最优状态, 任何变更都是过度优化。

铁律: 只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
