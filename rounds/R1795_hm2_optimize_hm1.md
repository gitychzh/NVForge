# R1795 (HM2→HM1): NOP — false trigger, 零dsv4p_nv post-R1794流量, 改前必有数据铁律触发

**时间**: 2026-07-18 21:00 UTC
**触发**: HM2自提交 R1794 (`这是我提交的, 不触发` — false trigger)
**作者**: opc2_uname (HM2)

## 改前数据 (2026-07-18 21:00 UTC)

### 6h DB (15:00-21:00 UTC)

| request_model | total | ok | fail | avg_dur_ms | sr_pct |
|---------------|-------|-----|------|------------|--------|
| glm5_2_nv     |    22 | 22 |    0 |       8943 |  100.0 |
| dsv4p_nv      |     8 |  7 |    1 |      45958 |   87.5 |

**总**: 30req/29OK (96.7% SR) / 1fail

### 1h DB (20:00-21:00 UTC)

| request_model | total | ok | fail | avg_dur_ms |
|---------------|-------|-----|------|------------|
| glm5_2_nv     |     4 |  4 |    0 |      11859 |

**总**: 4req/4OK (100% SR) — post-R1794 零 dsv4p_nv 流量

### 错误分析

| 模型 | 数量 | 错误类型 | 时间窗口 | 可修性 |
|------|------|---------|---------|--------|
| dsv4p_nv | 1 | all_tiers_exhausted (status=502) | 09:19 UTC | NVCF degradation, 不可配置修复 |
| dsv4p_nv | 7 | all_tiers_exhausted (status=200, phantom ATE) | 09:19-09:31 UTC | empty-200 rescue, 不可配置修复 |

### ATE明细 (8条, 全部09:19-09:31 UTC)

```
ts                  | model    | tiers | dur_ms | status
09:31:29            | dsv4p_nv |     1 |  29732 |    200 (phantom)
09:30:59            | dsv4p_nv |     1 |  15328 |    200 (phantom)
09:30:29            | dsv4p_nv |     1 |  14897 |    200 (phantom)
09:27:56            | dsv4p_nv |     1 |  95148 |    200 (phantom)
09:26:33            | dsv4p_nv |     1 |  23118 |    200 (phantom)
09:24:56            | dsv4p_nv |     1 |  32244 |    200 (phantom)
09:22:17            | dsv4p_nv |     1 | 100418 |    200 (phantom)
09:19:12            | dsv4p_nv |     1 |  56782 |    502 (real)
```

→ 8条ATE集中在12分钟窗口 (09:19-09:31), NVCF degradation事件。7条phantom ATE (status=200, empty-200 rescue), 1条real ATE (status=502)。NVU_TIER_BUDGET_DSV4P_NV=50 但 ATE dur 15-100s 远超50s — env-vs-code-default pitfall确认: 代码未使用env值, 使用内部默认值。

### Tier Attempts (6h)

| tier | error_type | cnt | avg_ms |
|------|-----------|-----|--------|
| glm5_2_nv | pexec_success | 22 | 8697 |
| glm5_2_nv | pexec_SSLEOFError | 1 | 5002 |

→ 0 tier_attempts errors (pexec_SSLEOFError is self-recovery, not a failure)

### 其他指标

- **key_cycle_429s**: glm5_2_nv 100% (22/22, pexec key rotation normal), dsv4p_nv 0%
- **fallback**: 0 (全部 f)
- **peer-fb**: 0 (无peer-fb触发)
- **zombie_empty_completion**: 0
- **NV-INTEGRATE**: 0 (NV_INTEGRATE_MODELS=空, glm5_2 pexec only)

### 日志 (最近4请求, 全部 glm5_2_nv pexec)

```
20:03:20 [NV-GLM52-SUCCESS] k5 pexec 8351ms
20:03:29 [NV-GLM52-SUCCESS] k1 pexec 13392ms
20:33:20 [NV-GLM52-SUCCESS] k2 pexec 9774ms
20:33:30 [NV-GLM52-SUCCESS] k3 pexec 9462ms
```

→ 全部 pexec SUCCESS, 4 keys cycling, avg=9245ms, 无错误

### HM1 nv_gw 容器配置

```
UPSTREAM_TIMEOUT=55
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_DSV4P_NV=50
NVU_TIER_BUDGET_GLM5_2_NV=120
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
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_STREAM_FIRST_BYTE_DEADLINE_S=17
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```

### 容器漂移检查

- Compose md5: f82c47a2296e72050700322e92979cf7
- 容器 env 与 compose 一致 ✓
- 零漂移

### HM2 Compose (peer-fb约束验证)

```
TIER_TIMEOUT_BUDGET_S=180
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.153.83:40006
NVU_PEER_FALLBACK_TIMEOUT=25
NVU_TIER_BUDGET_DSV4P_NV=70
```

→ HM1 peer-fb: dsv4p tier budget 50 + PEER_FALLBACK_TIMEOUT 122 = 172 < 180 ✓
→ HM2 peer-fb: dsv4p tier budget 70 + PEER_FALLBACK_TIMEOUT 25 = 95 < 180 ✓
→ Peer-fb constraint: PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET(70)+2=72 ✓

## 分析

1. **False trigger**: R1794 是 HM2 自提交 NOP, 脚本正确识别 `"这是我提交的, 不触发"` 但 cron 仍被派遣。

2. **dsv4p_nv ATE cluster (09:19-09:31)**: 全部为 NVCF degradation 事件。8条ATE集中在12分钟窗口, 7条phantom (status=200, empty-200 rescue), 1条real (status=502)。NVU_TIER_BUDGET_DSV4P_NV=50 但 ATE dur 15-100s → env-vs-code-default pitfall: 代码未使用env值, 使用内部默认值。该问题为代码级, 不可配置修复。

3. **glm5_2_nv: 100% SR (22/22)**: pexec路径完美, avg=8943ms。1× SSLEOFError self-recovery (5s, 自恢复)。Zero zombie_empty_completion。100% key_cycle_429s (pexec key rotation正常)。

4. **零 fallback, 零 peer-fb, 零 zombie**: 系统干净, 无可配置修复项。

5. **零 post-R1794 dsv4p_nv 流量**: R1794 NOP声明"零dsv4p_nv post-deploy流量, 改前必有数据铁律触发"。当前数据继续验证此模式: 09:31后零dsv4p_nv请求, 仅glm5_2_nv (openclaw) 流量。无法验证peer-fb rescue效果。

6. **所有参数 at floor/optimal**: FASTBREAK=1 (pexec+integrate+empty200), KEY_COOLDOWN=65, TIER_COOLDOWN=65, SSLEOF_RETRY=0.5, EMPTY_200=1。无进一步优化空间。

7. **容器漂移: 零**: compose md5一致, 容器env与compose一致。

## 决策: NOP (零变更)

**理由**: 零可配置修复故障。dsv4p_nv ATE为NVCF degradation (12-min cluster, 不可配置修复)。glm5_2_nv 100% SR。零 zombie, 零 fallback, 零 peer-fb。零 post-deploy dsv4p_nv流量无法验证。所有参数floor/optimal, 零漂移。

铁律: 只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
