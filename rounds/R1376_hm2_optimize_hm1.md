# R1376: HM2→HM1 — NOP (零dsv4p_nv流量, 零可修故障, 535th chain of R1133)

## 数据收集 (HM1: 100.109.153.83, 2026-07-15 ~00:15 UTC)

### 容器状态
- nv_gw: Up 54 min (healthy), started ~15:22 UTC Jul 14 (R1370部署后)
- ms_gw: Up 11 hours (healthy)
- logs_db: Up 11 hours (healthy)
- compose md5: f493494e (unchanged since R1370)

### 6h 窗口 (Post-R1370, ~10:00 UTC → 16:00 UTC Jul 14)
| model | total | ok | SR | avg_ok_ms | avg_ttfb_ms | max_ok_ms |
|-------|-------|----|------|-----------|-------------|-----------|
| glm5_2_nv | 29 | 21 | 72.4% | 9582 | 9579 | 15886 |

### 6h 错误分布
| mapped_model | error_type | cnt | avg_dur_ms | max_dur_ms |
|--------------|-----------|-----|------------|------------|
| glm5_2_nv | zombie_empty_completion | 8 | 10435 | 16567 |

### 关键指标
| 指标 | 6h | 24h |
|------|-----|-----|
| dsv4p_nv traffic | **0** | 67 req (58 OK, 9 ATE) |
| dsv4p_nv ATE | 0 | 9 (avg=71802ms, 全部 pre-R1370) |
| empty_200 | 0 | 0 |
| timeout | 0 | 0 |
| tier_attempts | 0 | 0 |
| fallback | 0 | 0 |
| ms_gw | 0/0 | - |
| zombie_empty_completion | 8 | 34 |

### dsv4p_nv ATE 时间分布 (24h)
| 小时 (UTC) | cnt | avg_dur_ms |
|-----------|-----|------------|
| 2026-07-13 18:00 | 3 | 72019 |
| 2026-07-14 05:00 | 1 | 72026 |
| 2026-07-14 06:00 | 5 | 71627 |
| **R1370部署后 (15:25 UTC Jul 14 → 现在)** | **0** | — |

### 日志分析
```
[23:33:20] k1 → integrate SUCCESS
[23:33:36] k2 → SSLEOFError (5002ms) → SSL-CYCLE → k3 SUCCESS
[23:33:48] NV-ZOMBIE-EMPTY glm5_2_nv: content_chars=12 < 50, input_chars=196384
[00:03:20] k3 → integrate SUCCESS
[00:03:32] k4 → integrate SUCCESS
[00:03:41] k5 → integrate SUCCESS
[00:03:49] NV-ZOMBIE-EMPTY glm5_2_nv: content_chars=42 < 50, input_chars=196980
```

- 1 SSLEOFError → SSL-CYCLE 成功恢复 → 正常
- 8 zombie_empty_completion (content_chars 12-42 < 50, input_chars ~196K) — 代码级缺陷, NV_INTEGRATE 路径
- 0 dsv4p_nv traffic in 6h — 无法验证 R1370 budget fix
- 0 ATE, 0 empty_200, 0 timeout, 0 tier_attempts, 0 fallback

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
NVU_PEER_FB_SKIP_MODELS=
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

**零可修故障**: 
1. 8 zombie_empty_completion — glm5_2_nv NV_INTEGRATE 代码级缺陷 (SSLEOF → NV-ZOMBIE-EMPTY pattern, content_chars < 50)，非配置可修
2. 0 dsv4p_nv traffic in 6h — 无法验证 R1370 budget fix (106)，但 24h 内 ATE 全部 pre-R1370 (Jul 13-14 06:00 UTC)，post-R1370 无 ATE
3. 所有参数已在地板/最优值，compose md5 f493494e 不变
4. 0 tier_attempts, 0 empty_200, 0 timeout, 0 fallback

**逻辑**: 没有活跃的配置可修故障。保持 stable。待 dsv4p_nv 流量恢复后验证 R1370 budget fix。

## 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
