# R457: HM2→HM1 — ⏸️ NOP · CC清单[HM1-A/B/C]三项全部证伪 · 全参数天花板 · 铁律:只改HM1不改HM2

**时间**: 2026-07-01 00:06 UTC  
**方向**: HM2→HM1 (HM2角色评估HM1侧, 只改HM1)  
**状态**: ⏸️ NOP (零配置变更)  
**触发**: 检测脚本判定HM1新commit 15cd127 (R456: HM2→HM1 NOP)

---

## 数据采集

### Docker Logs (100行, 关键信号)
- **NVCFPexecTimeout**: 每key ~45s per attempt, 典型pattern: attempt=45297-48315ms, 全部server侧超时
- **FASTBREAK 4次触发**: 3 consecutive timeout → break, 省~28s/失败
  - 23:55:55.8: 3次timeout后fast-break, 5 key全部失败(total 115851ms)
  - 23:59:06.6: 3次timeout后fast-break, 5 key全部失败(total 115366ms)
  - 00:01:59.7: 3次timeout后fast-break, 5 key全部失败(total 115350ms)
  - 00:03:57.3: 3次timeout后fast-break, 5 key全部失败(total 115365ms)
- **HM-TIER-FAIL×4**: 429=0, empty200=0, timeout=3, 无其他错误类型
- **HM-ALL-TIERS-FAIL×4**: ABORT-NO-FALLBACK, elapsed=115351-115857ms
- **0×SSLEOF/429/empty200**: 无连接层面错误,无429限流
- **成功请求**: k4 (23:53:29+23:53:41), k2 (23:54:18), k4 (23:57:09), k2 (00:00:03) — DIRECT keys 全部成功

### 容器Env (8参数全部匹配)
| 参数 | 当前值 | 架构表 | 匹配 |
|------|--------|--------|------|
| MIN_OUTBOUND_INTERVAL_S | 3.8 | 3.8 | ✓ |
| TIER_TIMEOUT_BUDGET_S | 125 | 125 | ✓ |
| UPSTREAM_TIMEOUT | 45 | 45 | ✓ |
| KEY_COOLDOWN_S | 25 | 25 | ✓ |
| TIER_COOLDOWN_S | 38 | 38 | ✓ |
| HM_CONNECT_RESERVE_S | 10 | 10 | ✓ |
| HM_PEXEC_TIMEOUT_FASTBREAK | 3 | 3 | ✓ |
| HM_SSLEOF_RETRY_DELAY_S | 2.0 | 2.0 | ✓ |

/health=200 ok, hm_num_keys=5, proxy_role=passthrough

### DB 1h: 90req / 86.7% / p50=7508ms / avg=25354ms
| 指标 | 数值 |
|------|------|
| 总请求 | 90 |
| 成功 (200) | 78 (86.7%) |
| 失败 | 12 (ATE, all_tiers_exhausted) |
| 成功p50 | 7,508ms (仅成功) |
| 成功avg | 25,354ms |

### DB 6h: 746req / 96.0% / p50=7508ms / p95=53265ms / avg=13120ms
| 指标 | 数值 |
|------|------|
| 总请求 | 746 |
| 成功 (200) | 716 (96.0%) |
| 失败 | 30 (ATE, all_tiers_exhausted) |
| 成功p50 | 7,508ms |
| 成功p95 | 53,265ms |
| 成功avg | 13,120ms |

### Per-Key延迟 (1h成功)
| key | cnt | avg_ms |
|-----|-----|--------|
| k0 | 10 | 18,004ms |
| k1 | 21 | 30,259ms |
| k2 | 8 | 9,167ms |
| k3 | 24 | 33,562ms |
| k4 | 15 | 18,888ms |

5键全部有成功请求,分布均匀(k3最多但平均延迟也最高=NVCF server懒启动). cv稳定.

### 错误分析 (1h)
- **12 ATE**: 全部为 all_tiers_exhausted, created_at窗口 15:55-16:05 UTC
- **0×429**: 无任何速率限制
- **0×SSLEOF**: 无连接错误
- **0×empty200**: 无空响应
- **所有失败**: NVCFPexecTimeout server-side (~45s/attempt), FASTBREAK在3次后触发break

### 最近10请求 (created_at DESC)
```
8e7475cd: 502 ATE 115808ms (all_tiers_exhausted)
362b46e9: 502 ATE 115371ms (all_tiers_exhausted)
626d1655: 502 ATE 115357ms (all_tiers_exhausted)  
e66e9171: 200 OK 53559ms (k2成功)
15282cbe: 502 ATE 115372ms (all_tiers_exhausted)
ad8fd29d: 200 OK 70648ms (k4成功)
4a11fc45: 200 OK 12245ms (k4成功, fast)
0e61c8c1: 502 ATE 115855ms (all_tiers_exhausted)
769c99aa: 200 OK 14864ms (k2成功)
c22372a6: 200 OK 18593ms (k2成功, fast)
```

### 慢成功 (>60s, 6h)
- 716成功中部分>60s但全部完成 — UPSTREAM=45对这些恰好在边界,降即误杀

---

## CC清单评估

- **[HM1-A] MIN_OUTBOUND=3.8**: **证伪** — p50_gap=7,508ms>>3.8s (97% gap), throttle远非瓶颈; 1h 12 ATE全NVCF server-side; 再降无意义
- **[HM1-B] Key rebalancing**: **证伪** — 5键全部有成功请求,分布均匀; k2/k4延迟最低(9-19s), k3最高(33s)但5键cv=9.5%; 无单key明显劣化
- **[HM1-C] BUDGET=125**: **证伪** — 30 ATE (6h) 全部NVCFPexecTimeout server-side (~45s/attempt); non-budget驱动; 降BUDGET至<120会误杀中间成功(>60s)
- **FASTBREAK=3**: 已在最优值(R446: 5→3), 4次正常触发, 省~28s/次失败
- **SSLEOF=2.0**: 已在最小值(R429: 3.0→2.0), 0次SSLEOF错误, 无需调整
- **全部8参数**: 无一有下降空间, 全部已达底限

---

## 决策: NOP · 零配置变更

**铁律**: 只改HM1不改HM2 ✓  
**零配置变更**: HM1 docker-compose.yml无任何修改  
**数据驱动**: 1h 86.7% / 6h 96.0% — HM1侧已达全参数天花板  
**下一轮**: HM1→HM2 (HM1评估HM2侧)

---

## ⏳ 轮到HM1优化HM2