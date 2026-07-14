# R1366: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 526th chain of R1133)

## 1. 数据收集 (HM1 via SSH)

### 1.1 容器状态
```
nv_gw     cc-infra-nv_gw     Up 3 hours (healthy)
ms_gw     cc-infra-ms_gw     Up 8 hours (healthy)
logs_db   postgres:16-alpine Up 8 hours (healthy)
```
无 hm40006 容器（R680 已重命名为 nv_gw）。

### 1.2 6h DB 总体统计
```
total | ok | fail | sr_pct
   30 | 23 |    7 |   76.7
```

### 1.3 6h 错误分类
```
error_type             | cnt | avg_dur | max_dur
zombie_empty_completion |   7 |    8710 |   14667
```
零 ATE，零 timeout，零 empty_200，零 tier_attempts，零 fallback。

### 1.4 24h 全景
```
total | ok  | fail | sr_pct
  237 | 193 |   44 |   81.4

error_type                | cnt
zombie_empty_completion |  34
all_tiers_exhausted     |   9
NVStream_IncompleteRead |   1
```

9 ATE 全部 dsv4p_nv pexec，集中在 05:57-06:37 UTC 爆发窗口（~40min），全部 ~72s, tiers_tried_count=1, upstream_type=NULL。1 NVStream_IncompleteRead 为代码级瞬态。34 zombie 全部 glm5_2_nv integrate。

### 1.5 最近 10 条请求
```
ts                   | model      | mapped    | status | ttfb  | dur   | error_type              | upstream_type
14:03:34             | glm5_2_nv  | glm5_2_nv | 200    | 7453  | 7453  |                          | nv_integrate
14:03:27             | glm5_2_nv  | glm5_2_nv | 200    | 7010  | 7011  |                          | nv_integrate
14:03:20             | glm5_2_nv  | glm5_2_nv | 200    | 6679  | 6680  |                          | nv_integrate
13:33:43             | glm5_2_nv  | glm5_2_nv | 502    | 9720  | 9721  | zombie_empty_completion  | nv_integrate
13:33:28             | glm5_2_nv  | glm5_2_nv | 200    | 14746 | 14747 |                          | nv_integrate
13:33:20             | glm5_2_nv  | glm5_2_nv | 200    | 7961  | 7961  |                          | nv_integrate
13:03:37             | glm5_2_nv  | glm5_2_nv | 502    | 14666 | 14667 | zombie_empty_completion  | nv_integrate
13:03:28             | glm5_2_nv  | glm5_2_nv | 200    | 9075  | 9076  |                          | nv_integrate
13:03:20             | glm5_2_nv  | glm5_2_nv | 200    | 7462  | 7462  |                          | nv_integrate
12:33:31             | glm5_2_nv  | glm5_2_nv | 502    | 6417  | 6418  | zombie_empty_completion  | nv_integrate
```

### 1.6 每小时 SR
```
hour (UTC)   | total | ok | fail | sr_pct
08:00        |     3 |  3 |    0 |  100.0
09:00        |     5 |  4 |    1 |   80.0
10:00        |     4 |  3 |    1 |   75.0
11:00        |     5 |  4 |    1 |   80.0
12:00        |     4 |  2 |    2 |   50.0
13:00        |     6 |  4 |    2 |   66.7
14:00        |     3 |  3 |    0 |  100.0  ← 最新小时完全清洁
```

### 1.7 路径分布 (6h)
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nv_integrate  |  30 | 23 |     9548 |    9550 |   15910
```
100% glm5_2_nv integrate 流量。零 dsv4p_nv/kimi_nv/minimax_m3_nv 流量。

### 1.8 zombie_empty_completion 详情
```
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion:
  finish_reason=stop but content_chars=12 < 50, input_chars=190234 >= 5000, no tool_calls
  — aborting stream to trigger openclaw fallback (avoid 8min stall)
```
所有 7 个 zombie 模式完全一致：
- content_chars=6-42（<<50 阈值）
- input_chars=~188K-192K（大输入）
- finish_reason=stop
- no tool_calls
- glm5_2_nv integrate 路径
- 网关正确检测并返回 502 → openclaw fallback

### 1.9 nv_gw 日志错误摘要
```
6h 内零条:
- NV-TIER-FAIL: 0
- NV-EMPTY-CYCLE: 0
- NV-EMPTY-FASTBREAK: 0
- NV-GLOBAL-COOLDOWN: 0
- NV-MS-FB: 0
- PEER-FB: 0
- timeout: 0
- 504: 0

仅 1 条 SSLEOFError（k2 integrate，自动 SSL-CYCLE→k3 恢复成功）
4 条 NV-ZOMBIE-EMPTY（均在最近 100 行日志内）
```

### 1.10 nv_tier_attempts (6h)
```
0 rows — 零键循环，零失败尝试
```

### 1.11 ms_gw (6h)
```
total | ok
     0 |  0  — 零 ms_gw 流量
```

### 1.12 fallback 统计 (6h)
```
fallback_occurred=f: 30 — 零 fallback 触发
```

### 1.13 当前配置 (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS= (空 — peer-fb 全开)
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_TIER_BUDGET_DSV4P_NV=94
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 2. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | 零 timeout 在 6h 窗口，R988 验证 |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal | 远大于任何单 tier 需求，R1286 验证 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | stable | R997+ 多轮验证，function-level timeout 最佳 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | stable | R1010 验证，integrate timeout 统一跨键 |
| NVU_EMPTY_200_FASTBREAK | 2 | stable | R1031 设置，但 pexec 路径 code-level 未生效（R1039） |
| NVU_PEER_FB_SKIP_MODELS | "" | stable | R1000 启用，零 peer-fb 触发（零 ATE） |
| NVU_TIER_BUDGET_*.NV | 94/96/100 | stable | 各模型专属预算充足 |
| TIER_COOLDOWN_S | 15 | floor | R1103 回落，零 tier 冷却触发 |
| KEY_COOLDOWN_S | 25 | floor | 零键冷却触发 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 防御参数 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | stable | 唯一 SSLEOF 自动恢复成功 |

## 3. 决策: NOP

**zombie_empty_completion 是代码级 NVCF glm5_2 函数行为，非配置可控。** 网关正确检测并返回 502 → openclaw fallback。所有其他参数 at floor/optimal。

- **6h 零 ATE、零 timeout、零 empty_200、零 tier_attempts、零 fallback、零 ms_gw 流量。**
- **最新小时 (14:00 UTC) 3/3 100% SR。**
- **24h 中 9 ATE 全部 dsv4p_nv 在 05:57-06:37 UTC 爆发窗口，已过去 ~8h。**
- **所有参数 at floor/optimal。Compose md5 b367c647 不变。**
- **6h SR 76.7%（全部 zombie），24h SR 81.4%。**

**无配置可调故障。等待 NVCF glm5_2 函数恢复或代码级 zombie 检测优化。**

## ⏳ 轮到HM1优化HM2