# R1800 (HM2→HM1) — NOP: 零dsv4p_nv post-R1799流量, 改前必有数据铁律触发

## 数据采集 (2026-07-18 22:15 UTC, HM1)

### 容器状态
- **nv_gw 重启时间**: 2026-07-18 13:56:26 UTC (R1799 deploy, ~8.3h ago)
- **零容器漂移**: 全参数与 compose 一致 ✓
- **SSLEOF_RETRY_DELAY_S=0.2** (R1799), **TIER_TIMEOUT_BUDGET_S=180** (R1790)
- **NVU_TIER_BUDGET_DSV4P_NV=50** (R1786), **NVU_PEER_FALLBACK_TIMEOUT=122** (R1744)
- **UPSTREAM_TIMEOUT=55** (R1729), **NVU_PEXEC_TIMEOUT_FASTBREAK=1** (R1707)
- **KEY=TIER=65** (R1740), **EMPTY_200_FASTBREAK=1** (R1707)
- **/health**: status=ok ✓

### DB 6h 窗口
```
total | ok | fail | ate502 | zombie | s504 | cascade429 | avg_ok_ms
  32  | 31 |   1  |    1   |    0   |   0  |        1   |   17667
```

### 按模型 (6h)
| model | cnt | ok | fail | avg_ok_ms |
|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 0 | 9867 |
| dsv4p_nv | 8 | 7 | 1 | 44412 |

### dsv4p_nv ATE 明细 (6h, 全部 pre-R1799)
| ts | status | duration_ms | tiers_tried | fallback |
|---|---|---|---|---|
| 09:31 | 200 | 29732 | 1 | f |
| 09:31 | 200 | 15328 | 1 | f |
| 09:30 | 200 | 14897 | 1 | f |
| 09:28 | 200 | 95148 | 1 | f |
| 09:26 | 200 | 23118 | 1 | f |
| 09:25 | 200 | 32244 | 1 | f |
| 09:22 | 200 | 100418 | 1 | f |
| 09:19 | 502 | 56782 | 1 | f |

全部 8 条 dsv4p ATE 均为 09:19-09:31 UTC 的 pre-R1799 数据 (NVCF degradation cluster)。R1799 重启后 (13:56 UTC) **零 dsv4p_nv 流量**。

### Post-R1799 流量 (13:56 UTC 至今)
| ts | model | status | duration_ms | key_cycle_429s |
|---|---|---|---|---|
| 14:03 | glm5_2_nv | 200 | 7220 | 1 |
| 14:03 | glm5_2_nv | 200 | 7303 | 1 |
| 13:33 | glm5_2_nv | 200 | 8960 | 1 |
| 13:33 | glm5_2_nv | 200 | 21582 | 1 |
| 13:03 | glm5_2_nv | 200 | 9107 | 1 |
| 13:03 | glm5_2_nv | 200 | 19093 | 1 |
| 12:33 | glm5_2_nv | 200 | 9462 | 1 |
| 12:33 | glm5_2_nv | 200 | 9774 | 1 |
| 12:03 | glm5_2_nv | 200 | 13392 | 1 |
| 12:03 | glm5_2_nv | 200 | 8351 | 1 |

仅 glm5_2_nv 请求，全部 OK。零 dsv4p_nv 请求。

### Peer-Fallback 现状
- **docker logs nv_gw**: 0 次 `NV-PEER-FB` (R1799 重启后)
- **DB**: 0 行 `fallback_occurred=true` (R1799 重启后)
- **无法验证**: 零 dsv4p_nv 流量 → 无法判断 peer-fb 是否触发

### 24h 错误分布
| error_type | error_subcategory | cnt |
|---|---|---|
| zombie_empty_completion | | 11 |
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 3 |

### 24h 429 统计
| model | 429s reqs | total 429s |
|---|---|---|
| glm5_2_nv | 100% (24/24) | 24 |

### Tier Attempts (6h)
| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_SSLEOFError | 1 |

### Error Logs (最近100行)
- 零 ERROR/WARN
- 零 zombie/ATE 触发
- 零 NV-PEER-FB

## 分析

### 改前必有数据铁律
R1799 将 SSLEOF_RETRY_DELAY 0.3→0.2 以节省 0.1s/SSLEOF。重启后 ~8.3 小时零 dsv4p_nv 流量，无法验证 peer-fb 是否实际触发。glm5_2_nv: 100% SR (24/24)，零 zombie，零 ERROR。无需优化。

### 潜在风险
- dsv4p_nv NVCF 全量 degradation 持续 (5 key 全 fail，100% ATE in 09:19-09:31 cluster)
- 若 peer-fb 仍不触发（如 R1786 env-vs-code-default pitfall: 实际 tier budget=70s 而非 50s），则 dsv4p ATE 仍无救援路径
- 但无法验证 → 改前必有数据铁律禁止改动

### SSLEOF 状态
- 1 SSLEOF in 6h (glm5_2_nv pexec), 4.2% rate
- 请求仍成功 (tier_attempts=SSLEOFError 但 request status=200 → 自动重试成功)
- SSLEOF_RETRY_DELAY=0.2s 已近 floor (0.1s 风险重试连接未完全重置)
- 0.2s 已足够提供 retry gap，继续观察

## 决策

| 参数 | 候选 | 理由 |
|---|---|---|
| 全部 | NOP | 改前必有数据 — 零 dsv4p_nv 流量无法验证 peer-fb 是否生效 |

**最终决策: NOP。** 待 dsv4p_nv 流量积累后判断 peer-fb 是否触发。若 peer-fb 仍被跳过（R1786 pitfall: 实际 tier 70s 而非 env 50s），则需 BUDGET ≥ 70+122+1=193 → 195。

**下轮预判:**
- 若 dsv4p peer-fb 触发: BUDGET=180 足够，继续观察
- 若 dsv4p peer-fb 仍跳过 (R1786 pitfall: 实际 70s): BUDGET 180→195 (+15s), 70+122=192<195 ✓

## 执行

NOP — 无配置修改。

## 验证

| 指标 | 数值 | 状态 |
|---|---|---|
| glm5_2_nv SR | 100% (24/24) | ✅ |
| dsv4p_nv 流量 | 0 post-R1799 | ⚠️ 无法验证 |
| 容器漂移 | 零 | ✅ |
| /health | status=ok | ✅ |
| 零 ERROR/WARN | 0 | ✅ |
| 429 级别 | 每请求 1 次 (正常轮转) | ✅ |

## 评判
更少报错: 96.9% SR (6h), 1 ATE 502 为 pre-R1799
更快请求: glm5_2_nv avg=9867ms
超低延迟: 正常
稳定优先: 零漂移，零ERROR，等待数据验证 peer-fb

单参数少改多轮。铁律: 只改 HM1 不改 HM2。改前必有数据。
## ⏳ 轮到HM1优化HM2
