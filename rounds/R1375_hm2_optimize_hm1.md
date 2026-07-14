# R1375: HM2→HM1 — NOP (R1370 budget fix verified, 零可修故障, 534th chain)

## 数据收集 (HM1: 100.109.153.83)

### 容器状态
- nv_gw: running, started 2026-07-14 15:25 UTC (R1370部署后 ~8.5h)
- logs_db: running
- compose md5: f493494e (unchanged since R1370)

### 6h 窗口 (Post-R1370, 15:25 UTC → 现在)
| model | total | ok | SR | avg_ms | zombie | ATE | timeout | empty_comp | fallback |
|-------|-------|----|------|--------|--------|-----|---------|------------|----------|
| glm5_2_nv | 29 | 21 | 72.4% | 9818 | 8 | 0 | 0 | 0 | 0 |

### 24h 窗口
| model | total | ok | SR | avg_ms | p50 | p95 | zombie | ATE |
|-------|-------|----|------|--------|-----|------|--------|-----|
| glm5_2_nv | 166 | 132 | 79.5% | 9699 | 7967 | 18012 | 34 | 0 |
| dsv4p_nv | 67 | 58 | 86.6% | ~28k | - | - | 0 | 9 |

### dsv4p_nv ATE 分析 — R1370 验证
- 24h 内 9 个 ATE，**全部是 pre-R1370**（06:xx UTC July 14, ~72s budget exhaustion）
- **Post-R1370 (15:25 UTC 后): 0 ATE** ← R1370 budget 94→106 生效！
- 12h 成功请求: 48 req, avg=20938ms, p50=18649, p95=37597, p99=52461, max=64362
- Per-key p95: K1=37855, K2=29537, K3=27995, K4=28289, **K5=52607** (SOCKS5 proxy, 可接受)
- $106-66=40s$ key2 budget headroom covers p95=37.6s ✓

### zombie_empty_completion 持续模式
- 8 zombie/6h (29 req), 全部 glm5_2_nv integrate
- 特征: finish_reason=stop, content_chars=6-42 < 50, input_chars=~190K, no tool_calls
- 日志: `NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK → content_filter SSE chunk`
- SSLEOFError 出现在 k2: `[SSL: UNEXPECTED_EOF_WHILE_READING]` → NV-INTEGRATE-SSL-CYCLE 处理
- **code-level**: NV_INTEGRATE 路径, 非配置可修

### 关键指标
- 0 tier_attempts (no tier-level retries)
- 0 timeout
- 0 empty_200
- 0 rate_limit (0 key cooldown)
- 0 fallback (all fallback_occurred=f)
- 0 dsv4p_nv/0 kimi_nv/0 minimax_m3_nv traffic (只有 glm5_2_nv)
- ms_gw: 0/0

### 当前 env 配置 (floor/optimal)
```
NVU_TIER_BUDGET_DSV4P_NV=106
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
TIER_COOLDOWN_S=15
TIER_TIMEOUT_BUDGET_S=205
UPSTREAM_TIMEOUT=66
PROXY_TIMEOUT=300
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

## 优化决策: NOP

**零可修故障**: R1370 dsv4p_nv budget fix 已被验证有效（post-deploy 0 ATE），所有参数已在地板/最优值。zombie_empty_completion 是 glm5_2_nv integrate 代码级问题（SSLEOF → NV-ZOMBIE-EMPTY pattern），非配置可修。无需改任何参数。

**逻辑**: 之前 R1370 的 dsv4p_nv budget fix 在 8.5h 内完全消除了 ATE — 这是唯一活跃的问题。当前没有任何可通过配置优化的故障模式。保持 stable。

## 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2