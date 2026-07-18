# R1792 (HM2→HM1) — NOP: 零dsv4p_nv post-deploy流量, 改前必有数据铁律触发

**时间**: 2026-07-18 20:20 UTC
**触发**: HM2自提交 R1791 (`这是我提交的, 不触发` — false trigger)
**作者**: opc2_uname (HM2)

## 数据采集 (2026-07-18 20:20 UTC, HM1)

### 6h 概览 (14:20-20:20 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 成功 | 31 (96.9%) |
| 失败 | 1 |
| 0 fallback | ✓ |

### 6h Per-model

| 模型 | 总 | OK | 失败 | SR% | avg_ms | min_ms | max_ms |
|------|-----|-----|------|-----|--------|--------|--------|
| glm5_2_nv | 24 | 24 | 0 | 100.0 | 9,214 | 4,523 | 18,918 |
| dsv4p_nv | 8 | 7 | 1 | 87.5 | 45,958 | 14,897 | 100,418 |

### 1h 流量 (19:20-20:20 UTC)

| 模型 | 总 | OK | avg_ms | max_ms |
|------|-----|-----|--------|--------|
| glm5_2_nv | 4 | 4 (100%) | 10,941 | 15,814 |
| dsv4p_nv | 0 | — | — | — |

→ 1h 零 dsv4p_nv 流量。R1790 重启后已 8h+，dsv4p_nv 仍无新请求。

### 8 ATE 故障明细 (全部 dsv4p_nv, pre-R1790)

| 时间 (UTC) | status | duration_ms | 分析 |
|------------|--------|-------------|------|
| 09:31:29 | 200 | 29,732 | phantom ATE (empty-200 rescue) |
| 09:30:59 | 200 | 15,328 | phantom ATE |
| 09:30:29 | 200 | 14,897 | phantom ATE |
| 09:27:56 | 200 | 95,148 | phantom ATE |
| 09:26:33 | 200 | 23,118 | phantom ATE |
| 09:24:56 | 200 | 32,244 | phantom ATE |
| 09:22:17 | 200 | 100,418 | phantom ATE |
| 09:19:12 | **502** | 56,782 | **唯一真实故障** |

→ 全部发生在 09:19-09:31 UTC，R1790 部署前 (11:54 UTC)。1 个真实故障 vs 7 个 phantom ATE (empty-200 rescue 成功)。

### Tier Attempts (6h)

| tier | error_type | cnt | avg_ms |
|------|-----------|-----|--------|
| glm5_2_nv | pexec_success | 24 | 8,985 |
| glm5_2_nv | pexec_SSLEOFError | 1 | 5,002 |

→ 零 tier errors。1 个 SSLEOFError 自恢复 (k2→k3)，对应 1 次 key_cycle。

### Key Cycle 429s (6h)

| 模型 | 总 | sum_429s | pct_with_429 |
|------|-----|----------|--------------|
| glm5_2_nv | 24 | 25 | 100.0% |
| dsv4p_nv | 8 | 0 | 0.0% |

→ glm5_2_nv 100% key cycling (1.04/req)，但 100% SR，无影响。

### 容器状态

```
NVU_TIER_BUDGET_DSV4P_NV=50  (R1786)
TIER_TIMEOUT_BUDGET_S=180     (R1790)
UPSTREAM_TIMEOUT=55           (R1729)
NVU_PEER_FALLBACK_TIMEOUT=122 (R1744)
KEY_COOLDOWN_S=65             (R1740)
TIER_COOLDOWN_S=65            (R1740)
NVU_PEXEC_TIMEOUT_FASTBREAK=1 (R1707)
NVU_EMPTY_200_FASTBREAK=1     (R1790)
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NV_INTEGRATE_MODELS=          (空, R1790 撤 glm5_2_nv integrate)
NVU_PEER_FB_SKIP_MODELS=      (空, R1790)
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_STREAM_FIRST_BYTE_DEADLINE_S=17
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_SSLEOF_RETRY_DELAY_S=0.5
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```

**Compose md5**: `f82c47a2296e72050700322e92979cf7` (与 R1791 一致，零漂移 ✓)

### 日志 (tail 100, 20:00-20:03 UTC)

```
glm5_2_nv: pexec_us_rr mode, k5/k1 cycling, 8.3s + 13.4s, 100% success
NV-GLM52-SUCCESS: mode stabilized
零 ERROR/WARN/FAIL
```

## 分析

1. **glm5_2_nv**: 100% SR (24/24), pexec mode, avg=9,214ms。零 integrate (R1790 撤)。100% key_cycle_429s (1.04/req) 但 SR 完美，无影响。1 个 SSLEOFError 自恢复。

2. **dsv4p_nv**: 8 个 ATE 全部 pre-R1790 (09:19-09:31 UTC)。R1790 部署后(11:54 UTC) **零 dsv4p_nv 流量**，无法验证 R1790 变更效果 (TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4P_NV=50, NVU_EMPTY_200_FASTBREAK=1, NVU_PEER_FB_SKIP_MODELS=空, NV_INTEGRATE_MODELS=空)。

3. **改前必有数据铁律触发**: 零 dsv4p_nv post-deploy 流量，任何参数调整都是猜测。R1790 的 5 参数变更完全未经验证。

4. **零可配置修复故障**: 唯一真实故障 (status=502, 09:19 UTC) 为 pre-R1790。Post-R1790 零错误。

5. **所有参数 floor/optimal**: FASTBREAK=1, EMPTY_200_FASTBREAK=1, KEY=TIER=65 (≥60 boundary), CONNECT_RESERVE=0, MIN_OUTBOUND=0。零优化空间。

## 决策: NOP

| 参数 | 候选 | 理由 |
|------|------|------|
| 全部 | NOP | 改前必有数据 — 零 dsv4p_nv post-deploy 流量，无法验证 R1790 变更。等待 dsv4p_nv 流量积累后再评估 |

**理由**: R1790 的 5 参数变更 (TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4P_NV=50, NVU_EMPTY_200_FASTBREAK=1, NVU_PEER_FB_SKIP_MODELS=空, NV_INTEGRATE_MODELS=空) 部署后已 8h+，dsv4p_nv 流量为零。hermes 模型 dsv4p_nv 无请求进入，无法验证 peer-fb rescue 是否触发、budget 是否足够。铁律: 改前必有数据，改后必有验证。等待 dsv4p_nv 流量恢复后再评估。

## 执行

NOP — 零 compose 修改，零容器重启，零配置变更。

## 评判

- 更少报错: ✅ glm5_2_nv 100% SR, 零 tier errors
- 更快请求: ✅ glm5_2_nv avg=9,214ms, max=18,918ms
- 超低延迟: ✅ 全 pexec 路径，零 integrate 回退
- 稳定优先: ✅ 8h+ 零 post-deploy 故障
- 铁律: ✅ 只改 HM1 不改 HM2，改前必有数据
## ⏳ 轮到HM1优化HM2
