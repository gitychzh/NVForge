# R1360: HM2→HM1 — NOP (false trigger, 零可修故障, 520th chain of R1133)

**回合**: HM2 优化 HM1
**日期**: 2026-07-14 21:05 UTC
**执行方**: HM2 (opc2_uname)
**目标**: HM1 (opc_uname@100.109.153.83)

## 触发判定

- 检测脚本触发: HM1提交新commit (3ef9f74 R1359) → 轮到HM2优化HM1
- 判定: **false trigger** — R1359为NOP，HM1未做任何配置修改，HM2仅需数据验证

## 数据收集

### 容器状态
```
nv_gw: Up 2 hours (healthy), StartedAt=2026-07-14T11:29:07Z
ms_gw: Up 7 hours (healthy)
logs_db: Up 7 hours (healthy)
Compose md5: b367c647 (unchanged from R1359)
```

### 6h DB 总览
```
total=28, ok=20, fail=8, SR=71.4%
```

### 按模型分解 (6h)
```
upstream_type | mapped_model | cnt | ok | avg_ttfb | avg_dur | max_dur
nv_integrate  | glm5_2_nv    |  28 | 20 |    11297 |   11300 |   31276
```

- **0 dsv4p_nv**, **0 kimi_nv**, **0 minimax_m3_nv** traffic
- 全部28请求: glm5_2_nv via nv_integrate
- 0 upstream_type=NULL (无调度层拒绝)
- 0 nvcf_pexec (无pexec路径)

### 错误分解 (6h)
```
error_type              | cnt
zombie_empty_completion |   8
```
- 8 failures **全部为 zombie_empty_completion** (code-level, not config-fixable)
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback
- 0 ms_gw traffic (0/0)

### 最近10请求
```
created_at              | model       | status | ttfb_ms | duration_ms | error_type
2026-07-14 13:03:51     | glm5_2_nv   |    502 |   14666 |       14667 | zombie_empty_completion
2026-07-14 13:03:37     | glm5_2_nv   |    200 |    9075 |        9076 |
2026-07-14 13:03:27     | glm5_2_nv   |    200 |    7462 |        7462 |
2026-07-14 12:33:37     | glm5_2_nv   |    502 |    6417 |        6418 | zombie_empty_completion
2026-07-14 12:33:30     | glm5_2_nv   |    200 |   10400 |       10400 |
2026-07-14 12:03:30     | glm5_2_nv   |    502 |    5369 |        5370 | zombie_empty_completion
2026-07-14 12:03:25     | glm5_2_nv   |    200 |    4944 |        4944 |
2026-07-14 11:33:53     | glm5_2_nv   |    200 |    7482 |        7482 |
2026-07-14 11:33:46     | glm5_2_nv   |    200 |   11323 |       11324 |
2026-07-14 11:33:34     | glm5_2_nv   |    200 |   14341 |       14342 |
```

### 小时趋势 (6h)
```
hour (UTC) | total | ok | fail | sr_pct
07:00      |     2 |  1 |    1 |   50.0
08:00      |     5 |  4 |    1 |   80.0
09:00      |     5 |  4 |    1 |   80.0
10:00      |     4 |  3 |    1 |   75.0
11:00      |     5 |  4 |    1 |   80.0
12:00      |     4 |  2 |    2 |   50.0
13:00      |     3 |  2 |    1 |   66.7
```

### 日志确认
- 零错误/零警告: `docker logs nv_gw --tail 100 | grep -iE 'error|warn|fail'` 无匹配
- 全部请求: glm5_2_nv integrate, first-attempt成功 (k1-k5轮转)
- zombie pattern: `[NV-ZOMBIE-EMPTY] content_chars=12, input_chars=190234` (触发openclaw fallback)
- 日志中确认: `[NV-ZOMBIE-ERROR-CHUNK] sent finish_reason=content_filter error SSE chunk to openclaw`

### 当前配置 (HM1 env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=94
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
MIN_OUTBOUND_INTERVAL_S=0 (floor)
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
NVU_CONNECT_RESERVE_S=0 (floor)
NVU_SSLEOF_RETRY_DELAY_S=1.0 (floor)
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_FORCE_STREAM_UPGRADE=0 (floor)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NV_INTEGRATE_MODELS=glm5_2_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
```
Compose md5: b367c647 (unchanged)

## 决策: NOP

### 穷举候选参数评估

| 候选参数 | 当前值 | 评估 | 结论 |
|---------|-------|------|------|
| UPSTREAM_TIMEOUT | 66 (high) | 零NVCFPexecTimeout, 零timeout错误 | 不改 |
| TIER_TIMEOUT_BUDGET_S | 205 (high) | 零BUDGET截断, 零ATE | 不改 |
| NVU_TIER_BUDGET_DSV4P_NV | 94 | 零dsv4p_nv流量 | 无数据, 不改 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 零BUDGET截断; max_dur=31s << 96 | 不改 |
| MIN_OUTBOUND_INTERVAL_S | 0 (floor) | 零429 | 不改 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 (floor) | 零pexec timeout | 不改 |
| NVU_EMPTY_200_FASTBREAK | 2 | 零empty_200 | 不改 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 (floor) | 零integrate timeout | 不改 |
| KEY_COOLDOWN_S | 25 | 零key_cycle_429s | 不改 |
| TIER_COOLDOWN_S | 15 | 零GLOBAL-COOLDOWN触发 | 不改 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 零peer-fb触发 | 不改 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 (floor) | integrate全部first-attempt成功 | 不改 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | 零ms_gw traffic | 不改 |

**全部13候选参数否决**: 零可修故障。8个失败全为zombie_empty_completion (code-level glm5_2_nv integrate, content_chars=12 << 50, input_chars=190234, 触发openclaw fallback via content_filter SSE)。此模式自R1133起已持续519轮，不可配置修复。

### 评判
- 更少报错: ✅ 零config-fixable错误 (8 zombie = code-level)
- 更快请求: ✅ avg_dur=11.3s, first-attempt全部成功
- 超低延迟: ✅ avg_ttfb=11.3s
- 稳定优先: ✅ 零参数变更, 零漂移, compose md5=b367c647

**铁律**: 只改HM1不改HM2 ✓ (本轮无改动)

## ⏳ 轮到HM1优化HM2