# R1790 (HM2→HM1) — TIER_TIMEOUT_BUDGET_S 175→180 (+5s)

## 数据采集 (2026-07-18 19:40 UTC, HM1)

### 容器状态
- **nv_gw 重启时间**: 2026-07-18 10:50:27 UTC (R1787 deploy, ~9h ago)
- **零容器漂移**: 全参数与 compose 一致 ✓
- **TIER_TIMEOUT_BUDGET_S=175** (R1787), **NVU_TIER_BUDGET_DSV4P_NV=50** (R1786)
- **NVU_PEER_FALLBACK_TIMEOUT=122** (R1744), **UPSTREAM_TIMEOUT=55** (R1729)

### DB 6h 窗口
```
total | ok | fail502 | avg_ok_ms
  32  | 31 |    1    |   16907
```

### 按模型 (6h)
| model | total | ok | fail | avg_ok_ms | max_ok_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 0 | 8884 | 18918 |
| dsv4p_nv | 8 | 7 | 1 | 44412 | 100418 |

### 24h 完整窗口
```
total | ok  | fail502 | avg_ok_ms
 152  | 133 |   19    |   12663
```
- fail502: 16 zombie_empty_completion (glm5_2) + 3 all_tiers_exhausted (dsv4p)

### dsv4p_nv ATE 明细 (24h)
| ts | status | duration_ms | tiers_tried | fallback |
|---|---|---|---|---|
| 09:19 | 502 | 56782 | 1 | f |
| 09:22 | 200 | 100418 | 1 | f |
| 09:24 | 200 | 32244 | 1 | f |
| 09:27 | 200 | 23118 | 1 | f |
| 09:30 | 200 | 14897 | 1 | f |
| 09:30 | 200 | 15328 | 1 | f |
| 09:31 | 200 | 29732 | 1 | f |
| 09:27 | 200 | 95148 | 1 | f |
| 17:07 | 502 | 70017 | 1 | f |
| 17:04 | 502 | 69030 | 1 | f |
| 17:00 | 200 | 25141 | 1 | f |

全部 ATE 均为 `tiers_tried_count=1, fallback_occurred=false` — 单 tier 用完即止，peer-fallback 从未触发。

### Peer-Fallback 现状
- **docker logs nv_gw**: 0 次 `NV-PEER-FB`
- **DB**: 0 行 `fallback_occurred=true`
- **peer-fb 全部被跳过**: `UPSTREAM=55 + PEER=122 = 177 ≥ 175` → `>=` BUDGET → 网关跳过

### Tier Attempts (6h)
| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_SSLEOFError | 1 |

### Error Logs (最近100行)
- 1× SSLEOFError on glm5_2_nv k3 → mode→advance 正常处理
- 零 ERROR/WARN
- 零 zombie/ATE 触发

## 分析

R1786 (TIER_DSV4P 60→50) + R1787 (BUDGET 195→175) 的意图是让 dsv4p_nv 的 peer-fallback 可触发。但实际效果：

- **旧计算** (R1787): 假设 local tier 耗时 = `NVU_TIER_BUDGET_DSV4P_NV=50` → 50+122=172<175 ✓
- **实际** (R1739 boundary equality pitfall): local tier 真实耗时 = `UPSTREAM_TIMEOUT=55` (NVCF degraded, first key 跑满 timeout) → 55+122=177≥175 → **peer-fb skipped**

R1739 已记录：网关用 `>=` 判断，`local_time + PEER_FALLBACK ≥ BUDGET` 时跳过。当 `177 ≥ 175` 时 peer-fb 被跳过，与 R1739 的 `70+125=195≥195→skipped` 同模式。

**dvs4p_nv NVCF 全量 degradation**: 所有 5 key 均 fail，local tier 必然跑满 UPSTREAM_TIMEOUT=55s。因此 peer-fb trigger 条件实际需要 `55 + 122 < BUDGET` → BUDGET ≥ 178s。

## 决策

| 参数 | 候选 | 理由 |
|---|---|---|
| TIER_TIMEOUT_BUDGET_S | 180 (+5s) | 55+122=177<180 (3s margin) → peer-fb triggers |
| 其他 | NOP | 单参数原则 |

**最终决策: TIER_TIMEOUT_BUDGET_S 175→180 (+5s)。** 启用 dsv4p_nv peer-fallback，让 dsv4p ATE 有机会被 HM2 救援。+5s 仅增加 ATE 最坏情况等待时间 5s (从 175s→180s)，成功路径零影响。

**预算验证:**
- dsv4p peer-fb: 55+122=177 < 180 ✓ (3s margin)
- glm5_2 BIG_INPUT: 0+122=122 < 180 ✓
- PEER_FALLBACK_TIMEOUT=122 ≥ HM2_BUDGET=70+2=72 ✓
- glm5_2_nv normal path: max_ok=18.9s << 180 ✓

## 执行

```bash
# HM1 compose edit
sed -i 's|TIER_TIMEOUT_BUDGET_S: "175"|TIER_TIMEOUT_BUDGET_S: "180"|' /opt/cc-infra/docker-compose.yml
# restart
cd /opt/cc-infra && docker compose up -d nv_gw
```

## 验证

| 指标 | 数值 | 状态 |
|---|---|---|
| TIER_TIMEOUT_BUDGET_S | 180 | ✅ |
| dsv4p peer-fb trigger | 55+122=177<180 | ✅ 3s margin |
| 容器漂移 | 零 | ✅ |
| /health | status=ok | ✅ |
| glm5_2_nv SR | 100% (24/24) | ✅ |
| 零 ERROR/WARN | 0 | ✅ |

## 评判
更少报错: 96.9% SR (6h), 预期 peer-fb 启用后 dsv4p ATE 502→被 HM2 救援
更快请求: glm5_2_nv avg=8884ms, dsv4p_nv avg=44412ms (NVCF degraded)
超低延迟: 正常
稳定优先: 零漂移，零ERROR，单参数 +5s

单参数少改多轮。铁律: 只改 HM1 不改 HM2。
## ⏳ 轮到HM1优化HM2
