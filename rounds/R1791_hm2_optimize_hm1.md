# R1791 (HM2→HM1) — NOP: 零dsv4p_nv post-deploy流量, 改前必有数据铁律触发

## 数据采集 (2026-07-18 20:00 UTC, HM1)

### 容器状态
- **nv_gw 重启时间**: 2026-07-18 11:54:20 UTC (R1790 deploy, ~8h ago)
- **零容器漂移**: 全参数与 compose 一致 ✓
- **TIER_TIMEOUT_BUDGET_S=180** (R1790), **NVU_TIER_BUDGET_DSV4P_NV=50** (R1786)
- **NVU_PEER_FALLBACK_TIMEOUT=122** (R1744), **UPSTREAM_TIMEOUT=55** (R1729)
- **NVU_PEXEC_TIMEOUT_FASTBREAK=1** (R1707), **KEY=TIER=65** (R1740)

### DB 6h 窗口
```
total | ok | fail502 | avg_ok_ms
  31  | 30 |    1    |   17209
```

### 按模型 (6h)
| model | total | ok | fail | avg_ok_ms |
|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 0 | 9214 |
| dsv4p_nv | 8 | 7 | 1 | 44412 |

### dsv4p_nv ATE 明细 (6h, 全部 pre-R1790)
| ts | status | duration_ms | tiers_tried | fallback |
|---|---|---|---|---|
| 09:31 | 200 | 29732 | 1 | f |
| 09:30 | 200 | 15328 | 1 | f |
| 09:30 | 200 | 14897 | 1 | f |
| 09:27 | 200 | 95148 | 1 | f |
| 09:26 | 200 | 23118 | 1 | f |
| 09:24 | 200 | 32244 | 1 | f |
| 09:22 | 200 | 100418 | 1 | f |
| 09:19 | 502 | 56782 | 1 | f |

全部 8 条 dsv4p ATE 均为 09:19-09:31 UTC 的 pre-R1790 数据。R1790 重启后 (11:54 UTC) **零 dsv4p_nv 流量**。

### Post-R1790 流量 (11:54 UTC 至今)
| ts | model | status | duration_ms | key_cycle_429s |
|---|---|---|---|---|
| 12:03 | glm5_2_nv | 200 | 13392 | 1 |
| 12:03 | glm5_2_nv | 200 | 8351 | 1 |

仅 2 条 glm5_2_nv 请求，全部 OK。零 dsv4p_nv 请求。

### Peer-Fallback 现状
- **docker logs nv_gw**: 0 次 `NV-PEER-FB` (R1790 重启后)
- **DB**: 0 行 `fallback_occurred=true` (R1790 重启后)
- **无法验证**: 零 dsv4p_nv 流量 → 无法判断 peer-fb 是否触发

### 24h 错误分布
| error_type | count |
|---|---|
| zombie_empty_completion (glm5_2) | 15 |
| all_tiers_exhausted (dsv4p) | 3 (real 502) |

### 24h 429 统计
| model | 429s reqs | total 429s |
|---|---|---|
| glm5_2_nv | 139 | 147 |

### Tier Attempts (6h)
| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 23 |
| glm5_2_nv | pexec_SSLEOFError | 1 |

### Error Logs (最近100行)
- 零 ERROR/WARN
- 零 zombie/ATE 触发

## 分析

### 改前必有数据铁律
R1790 将 BUDGET 175→180 以启用 dsv4p_nv peer-fallback (55+122=177<180 ✓)。但重启后 ~8 小时零 dsv4p_nv 流量，无法验证 peer-fb 是否实际触发。

glm5_2_nv: 100% SR (24/24)，零 zombie，零 ERROR。无需优化。

### 潜在风险
- dsv4p_nv NVCF 全量 degradation 持续 (5 key 全 fail，100% ATE)
- 若 peer-fb 仍不触发（如 R1786 env-vs-code-default pitfall: 实际 tier budget=70s 而非 50s），则 dsv4p ATE 仍无救援路径
- 但无法验证 → 改前必有数据铁律禁止改动

## 决策

| 参数 | 候选 | 理由 |
|---|---|---|
| 全部 | NOP | 改前必有数据 — 零 dsv4p_nv 流量无法验证 peer-fb 是否生效 |

**最终决策: NOP。** 待 dsv4p_nv 流量积累后判断 peer-fb 是否触发。若 peer-fb 仍被跳过（实际 tier 耗时为 70s 而非 55s），则需 BUDGET ≥ 70+122+1=193 → 195。

**下轮预判:**
- 若 dsv4p peer-fb 触发: BUDGET=180 足够，继续观察
- 若 dsv4p peer-fb 仍跳过 (R1786 pitfall: 实际 70s): BUDGET 180→195 (+15s), 70+122=192<195 ✓

## 执行

NOP — 无配置修改。

## 验证

| 指标 | 数值 | 状态 |
|---|---|---|
| glm5_2_nv SR | 100% (24/24) | ✅ |
| dsv4p_nv 流量 | 0 post-R1790 | ⚠️ 无法验证 |
| 容器漂移 | 零 | ✅ |
| /health | status=ok | ✅ |
| 零 ERROR/WARN | 0 | ✅ |
| 429 级别 | 每请求 1 次 (正常轮转) | ✅ |

## 评判
更少报错: 96.8% SR (6h), 1 ATE 502 为 pre-R1790
更快请求: glm5_2_nv avg=9214ms
超低延迟: 正常
稳定优先: 零漂移，零ERROR，等待数据验证 peer-fb

单参数少改多轮。铁律: 只改 HM1 不改 HM2。改前必有数据。
## ⏳ 轮到HM1优化HM2
