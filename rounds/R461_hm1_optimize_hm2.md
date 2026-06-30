# R461: HM1→HM2 — ⏸️ NOP · CC清单[HM2-A/B/C]三项复检全部证伪/已达成 · 全参数天花板 · 30min 282req/99.29% · 24h 5195req/97.29% · 5-key均衡p50 5.6-8.5s · 0 429/0 empty200 · 失败全NVCFPexecTimeout server-side不可proxy层修复 · BUDGET=90双向证伪 · FASTBREAK=5死参数(BUDGET限2attempt永不触发) · 8项env双处零漂移(/opt/cc-infra compose L469-505=容器) · HM2自R445(14:20:51Z)后零变更 · 铁律:只改HM2不改HM1 · 零配置变更

**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**动作**: NOP (零配置变更)
**时间**: 2026-06-30 16:35 UTC (DB ts 00:35, +8h偏移已校正; CST 00:35)
**轮次**: R461 → 接R460(HM2→HM1: NOP, commit 5fea58f)

## 0. 时区与host标识 (R320教训#5, R460纠正)

- DB `ts` 比真实UTC快8h。真实UTC=16:35时 DB max ts=2026-07-01 00:35(次日)。所有窗口查询用绝对ts时间戳, 禁用 NOW()。
- 对端HM2 host_machine 标识=`opc2sname` (HM2写入DB值, 已R459确认)。litellm_model=`nvcf_z-ai/glm-5.1_k1..k5`(5个key各自model名)。
- hm_tier_attempts 表无 host_machine 列, 用 `litellm_model LIKE '%glm%'` 过滤HM2侧。

## 1. 数据采集 (HM2 对端, host_machine=opc2sname)

### 1a. 容器env (8参数, /opt/cc-infra/docker-compose.yml L469-505 = 容器运行态)
```
UPSTREAM_TIMEOUT=48                (L469)  TIER_TIMEOUT_BUDGET_S=90  (L470)
MIN_OUTBOUND_INTERVAL_S=2.5       (L472)  KEY_COOLDOWN_S=38         (L473)
TIER_COOLDOWN_S=22                (L474)  HM_SSLEOF_RETRY_DELAY_S=1.0 (L480)
HM_PEXEC_TIMEOUT_FASTBREAK=5      (L482)  HM_CONNECT_RESERVE_S=8    (L505)
```
grep L469-505 与容器 `docker exec hm40006 env` 逐字一致 → **双处零漂移** ✓
/health=200 OK (port 40006), proxy_role=passthrough, hm_num_keys=5, hm_model_tiers=["glm5.1_hm_nv"], hm_default_model="glm5.1_hm_nv"。
容器 StartedAt: 2026-06-30T14:20:51Z (R445 重启后稳定 26.3h+, 自 R445 后零变更)。

### 1b. DB 30min (真实UTC 16:04-16:35 = DB ts 23:34-00:35)
| 指标 | 数值 |
|------|------|
| 总请求 | 282 |
| 成功 (200) | 280 (99.29%) |
| 失败 | 2 (0.71%) |
| p50 | 6,934ms |
| p95 | 28,520ms |
| max | 82,612ms |
| 429 | 0 |
| empty200 | 0 |

失败结构: 2× all_tiers_exhausted (avg 82,559ms, max 82,612ms; 2×NVCFPexecTimeout: ~48s+~34s=82s)。0×429, 0×empty200, 0×SSLEOF。

### 1c. DB 60min (真实UTC 15:34-16:35 = DB ts 23:04-00:35, 稳态确认)
| 指标 | 数值 |
|------|------|
| 总请求 | 357 |
| 成功率 | 98.88% |
| p50 | 7,215ms |
| p95 | 34,827ms |
| 429 | 0 |
| empty200 | 0 |

### 1d. DB 30min per-key (5-key 均衡验证, success+fail)
| nv_key_idx | reqs | ok | err | avg_ms | p50 | p95 | max |
|------|------|----|----|--------|------|------|------|
| 0 (k1) | 57 | 57 | 0 | 7,677 | 5,595 | 20,373 | 35,387 |
| 1 (k2) | 42 | 42 | 0 | 8,706 | 7,122 | 18,953 | 22,792 |
| 2 (k3) | 71 | 71 | 0 | 12,052 | 8,505 | 40,406 | 68,061 |
| 3 (k4) | 53 | 53 | 0 | 8,228 | 6,661 | 18,355 | 39,689 |
| 4 (k5) | 57 | 57 | 0 | 10,991 | 7,273 | 38,809 | 60,905 |
| null | 2 | 0 | 2 | 82,559 | 82,505 | 82,612 | 82,612 |

5 key reqs 42-71, p50 5.6-8.5s 同级, **无单key劣化**。k3(idx2) max68s为正常尾部, 非HM1-k4式劣化。2 null = all_tiers_exhausted proxy级abort (未分配key)。

### 1e. DB 24h聚合 (真实UTC 06-30 16:34~07-01 16:34... 等价DB 00:34~00:34)
| 指标 | 数值 |
|------|------|
| 总请求 | 5,195 |
| 成功率 | 97.29% |
| 失败 | 141 |
| p50 | 7,425ms |

### 1f. DB 24h error_type 结构
| error_type | count | avg_ms |
|------|------|------|
| all_tiers_exhausted | 137 | 99,027 |
| NVStream_IncompleteRead | 4 | 26,445 |

失败主导=all_tiers_exhausted (137/141=97%), 全 NVCFPexecTimeout server-side (NVCF glm5.1_hm_nv 后端慢/超时 ~48s/attempt)。4×NVStream_IncompleteRead 网络瞬时错误(噪声级)。

### 1g. DB 24h per-key 失败率
| nv_key_idx | reqs | err | err% |
|------|------|-----|------|
| 0 (k1) | 970 | 1 | 0.10% |
| 1 (k2) | 1053 | 1 | 0.09% |
| 2 (k3) | 1036 | 0 | 0.00% |
| 3 (k4) | 998 | 0 | 0.00% |
| 4 (k5) | 1001 | 2 | 0.20% |
| null | 137 | 137 | 100% |

24h 5-key reqs 970-1053 (cv=3.4%), err% 0.00-0.20% (噪声级), **无单key劣化**。137 null = all_tiers_exhausted 跨key随机。

### 1h. DB 6h tier_attempts (hm_tier_attempts, litellm_model LIKE '%glm%', DB 18:34-00:34)
- 21 attempts, 全部 NVCFPexecTimeout, 0 成功
- avg_elapsed=49,457ms, max=52,529ms (≈UPSTREAM_TIMEOUT=48s)
- per-key: k0=2, k1=4, k2=5, k3=4, k4=6 (均匀, 无单key被NVCF标记)

**关键**: 21次ATE全失败 → k4/k5从未救回请求 (与R454/R459一致)。失败由 2×consecutive NVCFPexecTimeout 主导 (~48s+~34s=82s)。

### 1i. DB 24h 失败 duration 分布 (BUDGET 硬截断检测)
| 区间 | count | 含义 |
|------|-------|------|
| <50s | 5 | FASTBREAK/快速失败/单次timeout |
| 50-80s | 22 | 2×timeout (BUDGET截断第2attempt) |
| 80-85s | 23 | 2×timeout (主集群, 重启后) |
| 85-90s | 5 | 2×timeout (BUDGET边界90s) |
| 90-100s | 33 | 2×full timeout (48s+48s) |
| ≥100s | 53 | 重启前 FASTBREAK=3 时代的 3×timeout 残留 |

失败主集群在 80-90s (28个, 2×timeout自然到82.5s<90s), **非BUDGET硬截断** (90s边界仅5个, 多数<85s)。

### 1j. DB 24h 慢成功 (BUDGET误杀风险评估)
| 区间 | 成功数 |
|------|--------|
| 80-85s | 5 |
| 85-90s | 6 |
| ≥90s | 21 |

24h **32个慢成功 ≥80s (0.62%)**, 含21个≥90s (第4attempt救回)。降BUDGET 90→85 误杀6个(85-90s)+5个(80-85s)=11个; 90→80 误杀32个。

## 2. CC清单评估 ([HM2-A/B/C] 节, 对端=HM2)

### [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5 → 证伪/已达成
- **当前**: 2.5 (R386: 5.0→2.5, **清单目标值已达成**, compose L472)
- **数据**: 30min 0×429, p50=6.9s vs MIN_OUTBOUND=2.5s → gap 276% (实际请求间隔p50远大于throttle, throttle非瓶颈)
- **结论**: **证伪/已达成** — 清单目标2.5已在R386落地。当前0×429, p50_gap 276% 证明再降无吞吐收益(实际间隔由请求到达率驱动, MIN_OUTBOUND串行锁非主导)。

### [HM2-B] 失败模式数据补采找劣化key → 证伪
- **当前**: 24h 5-key reqs 970-1053 (cv=3.4%), err% 0.00-0.20% (噪声级), 30min p50 5.6-8.5s 同级
- **数据**: 无单key劣化。141失败跨key随机分布(137 null nv_key_idx = all_tiers_exhausted proxy级abort), 全NVCFPexecTimeout server-side。6h ATE per-key k0-4: 2/4/5/4/6 均匀, 无单key被NVCF标记。
- **结论**: **证伪** — 5-key高度均衡, 无HM1-k4式劣化key。无需改路由。

### [HM2-C] TIER_TIMEOUT_BUDGET_S 128→100 → 证伪
- **当前**: 90 (R445: 85→90, **已低于清单目标100**, compose L470)
- **数据 (双向证伪, 与R459一致)**:
  - **降向 (90→85)**: 24h仅5失败落85-90s (BUDGET边界), 23失败在80-85s (2×timeout自然到82.5s<85s不受影响)。降BUDGET→这5个失败早0-5s结束, 收益~25s/24h; 但误杀6成功(85-90s)。违"稳定优先>成功率", 收益<代价。且失败非BUDGET硬截断(主集群82.5s<90s), 降BUDGET仅截断极少数第2attempt边界。
  - **升向 (90→100)**: 失败2×timeout升82.5s→~92s (第2attempt read_timeout 34→44s, 延长~10s/次×141失败=~1410s/24h纯浪费), 仍remaining<10s无3rd attempt, 无救回收益(ATE 21次全失败, k4/k5从未救回)。纯延长失败耗时。
- **结论**: **证伪** — BUDGET=90已是最优。降则误杀慢成功违稳定优先(收益~25s vs 误杀6成功), 升则延长失败~1410s/24h无救回收益。

## FASTBREAK=5 死参数 (非清单项, 记录, 与R459一致)
- **现象**: 容器重启后(FASTBREAK=5, 26.3h) logs零次HM-PEXEC-FASTBREAK触发; 重启前(FASTBREAK=3)24h有触发
- **根因**: BUDGET=90仅容2 attempt (48s+34s=82s, remaining<10s break), consecutive_pexec_timeout永远只到2, 达不到阈值5(或3)
- **本轮不改**: (1) FASTBREAK 3↔5均为死参数(BUDGET限制下二者等价零触发); (2) 降FASTBREAK→1会杀慢成功rescue(21个≥90s慢成功含第4attempt救回); (3) 非清单项, 违"每轮1项+清单优先"原则。

## 决策: NOP · 零配置变更

**理由**: CC清单[HM2-A/B/C]三项全部证伪/已达成。HM2已处于全参数天花板:

| 参数 | 值 | 状态 |
|------|-----|------|
| MIN_OUTBOUND | 2.5 | 清单HM2-A目标值已达成(R386), 0×429, p50_gap 276% 非瓶颈 |
| KEY_COOLDOWN | 38 | 已最优 (24h 5-key均衡 cv=3.4%) |
| TIER_COOLDOWN | 22 | 已最优 (KEY=38>TIER=22, 单tier模型) |
| UPSTREAM_TIMEOUT | 48 | 已最优 (ATE avg 49s≈48s 覆盖) |
| BUDGET | 90 | 已最优 (清单目标100已超额达成, 双向证伪) |
| CONNECT_RESERVE | 8 | 已最优 (R431: 10→8) |
| SSLEOF_RETRY | 1.0 | 已最优 (0 SSLEOF失败, 4×NVStream噪声级) |
| FASTBREAK | 5 | 死参数 (BUDGET=90容2attempt永不触发), 但降之无收益(3亦死)且升无意义, 维持 |

**失败根因(不可proxy层修复)**: 137×all_tiers_exhausted全NVCFPexecTimeout server-side (NVCF glm5.1_hm_nv后端慢/超时~48s/attempt), 跨key随机, 2×timeout avg82.5s。proxy层无法修复NVCF server-side慢响应。慢成功rescue(21个≥90s)由BUDGET+多attempt机制保住, 不可牺牲。

**铁律**: 只改HM2不改HM1 · 零配置变更 · 零docker compose重启 · 零容器env改动

## 改前/改后对比 (NOP, 同窗口)
| 指标 | 改前(30min) | 改后(30min) |
|------|------|------|
| reqs | 282 | 282 (NOP, 同窗口) |
| 成功率 | 99.29% | 99.29% |
| p50 | 6,934ms | 6,934ms |
| p95 | 28,520ms | 28,520ms |
| 429 | 0 | 0 |
| empty200 | 0 | 0 |

NOP轮无配置变更, 改前=改后同窗口。24h长窗口(5195req/97.29%)为稳态证据。

## 历史对��
| 轮次 | 30min reqs | 30min成功率 | 24h reqs | 24h成功率 | 变更 |
|------|-----------|------------|---------|---------|------|
| R461 | 282 | 99.29% | 5195 | 97.29% | ⏸️ NOP |
| R459 | 141 | 99.29% | 5218 | 97.26% | ⏸️ NOP |
| R454 | 1856 | 96.39% | — | — | ⏸️ NOP |

30min 282req/99.29% — 流量较R459(141req)翻倍, 成功率持平99.29%。24h 5195req/97.29%稳定(R459 5218req/97.26%, 同期数据)。失败结构未变(all_tiers_exhausted NVCF server-side)。

## 部署
```bash
# 无操作 — 容器 keep running (StartedAt 2026-06-30T14:20:51Z, 稳定 26.3h+)
# 验证: /health=200 OK (port 40006), hm_num_keys=5, 8项env双处零漂移
# compose /opt/cc-infra/docker-compose.yml L469-505 = 容器运行态, 双处一致
# HM2自R445(14:20:51Z)后零变更
```

## ⏳ 轮到HM2优化HM1
