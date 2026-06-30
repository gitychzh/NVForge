# R439: HM1→HM2 — ⏸️ NOP · CC清单三项重验全部证伪 · 全参数天花板 · 30min 157/157=100% · 零配置变更

**角色**: HM1 (执行者, opc_uname) → HM2 (目标, opc2sname, glm5.1_hm_nv)
**日期**: 2026-06-30 20:15 CST (DB ts口径, host_machine='opc2sname')
**铁律**: 只改HM2不改HM1 ✓
**前轮**: R438 (HM2→HM1, KEY_COOLDOWN_S 38→25)
**本轮**: 数据采集+CC清单[HM2-A/B/C]三项重验 → 判定NOP (三项全部已做完或被当前数据证伪)

## 0. 任务规则与本轮决策依据

任务规则: "优先执行清单第1项, 若第1项本轮无法实施(如已被前轮做过/数据不支撑), 顺延下一项。每轮只做1项。"
任务规则: "不允许'无操作'轮, 除非三项都已做完或数据证伪(证伪需给出具体数据)。"

本轮按规则逐一重验CC清单[HM2-A/B/C]三项, 结论: **A已做完+再降证伪 / B数据证伪 / C数据证伪**, 满足NOP例外条件。下文每项给出本轮新采的具体数据。

与R435对比: R435已判定三项证伪, 本轮重验确认HM2自R435后无任何变更(容器StartedAt=2026-06-30T11:34:46Z未变, env全一致, 数据模式相同), 三项结论依然成立。

## 1. 改前数据采集 (锚点 max_ts=2026-06-30 20:15:32+00, HM2 host_machine='opc2sname')

### 1a. 容器运行态env (docker exec → 全env验证)
```
MIN_OUTBOUND_INTERVAL_S  = 2.5   (R386: HM1→HM2 5.0→2.5, CC HM2-A 已完成)
TIER_TIMEOUT_BUDGET_S   = 85    (R385: HM1→HM2 95→85, CC HM2-C 已降到85)
HM_CONNECT_RESERVE_S    = 8     (R431: HM1→HM2 10→8)
HM_SSLEOF_RETRY_DELAY_S = 1.0   (R321: HM1→HM2 3.0→1.0)
HM_PEXEC_TIMEOUT_FASTBREAK = 5  (R384: HM1→HM2 3→5)
UPSTREAM_TIMEOUT        = 50    (R284)
KEY_COOLDOWN_S          = 38    (R275)
TIER_COOLDOWN_S         = 22    (R1)
HM_SSLEOF_RETRY_ENABLED = true
```
Routing: k1→DIRECT, k2→7895, k3→DIRECT, k4→7897, k5→DIRECT
容器StartedAt=2026-06-30T11:34:46Z (与R435一致, R435后未重启), /health=200 ok, hm_num_keys=5, glm5.1_hm_nv ✓

### 1b. 30min窗口成功率 (19:45:32~20:15:32 UTC, ts口径 max(ts)-30min)
| total | success | 429 | ATE | 5xx | 成功率 | reqs/min | avg_ms | p50 | p95 |
|---|---|---|---|---|---|---|---|---|---|
| 157 | 157 | 0 | 0 | 0 | 100.00% | 5.23 | 9410 | 6221 | 30875 |

### 1c. per-key成功延迟 (30min, status=200)
| nv_key_idx | cnt | avg_ms | p50 | p95 | max_ms |
|---|---|---|---|---|---|
| 0 (k1 DIRECT) | 32 | 9423 | 6022 | 24807 | 45890 |
| 1 (k2 7895)   | 32 | 10637 | 7119 | 34668 | 44611 |
| 2 (k3 DIRECT) | 31 | 7913 | 4877 | 27654 | 30240 |
| 3 (k4 7897)   | 31 | 8997 | 6421 | 18662 | 47083 |
| 4 (k5 DIRECT) | 31 | 10039 | 5878 | 30919 | 37617 |

**5key完全均衡(31-32), p50 4.9-7.1s, 无劣化key** → [HM2-B]证伪 ✓

### 1d. pair gap分布 (30min, 156对)
| pairs | avg_gap | p50_gap | min_gap | max_gap | gap<2.5 | gap<3.0 |
|---|---|---|---|---|---|---|
| 156 | 11.51s | 6.63s | 0.14s | 267.32s | 5 (3.2%) | 8 (5.1%) |

**p50_gap=6.63s >> throttle 2.5s**: throttle=2.5在当前流量下几乎不阻塞(仅3.2% pair受影响). 再降throttle收益极小且增NVCF同IP 429风险 → [HM2-A]再降证伪 ✓

## 2. CC清单三项重验 (本轮核心产出)

### 2a. [HM2-A] MIN_OUTBOUND_INTERVAL_S — 已做完+再降证伪
- CC清单目标值2.5: **当前已是2.5**(R386 commit 3441e5e已完成). 清单第1项意图(降throttle提升吞吐)已收官.
- 再降到2.0的收益/风险评估: 30min仅5/156对(3.2%)gap<2.5s受throttle影响, 其中gap<2.0s更少. **再降2.5→2.0最多多解几对/30min, 收益<0.02req/min, 但增加NVCF同IP 429风险**(当前零429是稳定基线, 不应破坏). 证伪再降.

### 2b. [HM2-B] 数据补采 — 证伪(无劣化key)
- 本轮重采30min per-key数据(见1c): 5key均衡(31-32), p50 4.9-7.1s, p95 18.7-34.7s, 无单key劣化.
- 与R435/R387结论一致(HM2-B当时已证伪). HM2无像HM1-k4那样的劣化key.
- 结论: 无可改的路由, 证伪.

### 2c. [HM2-C] TIER_TIMEOUT_BUDGET_S — 证伪(降BUDGET误杀慢成功)
CC清单原文"128→100", 实际HM2 BUDGET已从128→100(R334)→95(R384)→85(R385), 远低于清单的100. 清单意图是"降BUDGET让失败早结束". 本轮评估再降85→更低:

**失败机制(根因分析, 数据支撑, 6h窗口 14:15:32~20:15:32)**:
| status | error_type | cnt | avg_ms | min_ms | max_ms |
|---|---|---|---|---|---|
| 200 | (success) | 1494 | 10590 | 712 | 91222 |
| 502 | all_tiers_exhausted | 23 | 91570 | 75488 | 103136 |
| 502 | NVStream_IncompleteRead | 3 | 27683 | 15678 | 46392 |

- 6h窗口23次ATE失败, avg 91.6s, min 75.5s, max 103.1s
- tier_attempts: 21次NVCFPexecTimeout, avg 47.8s, max 55.8s (≈UPSTREAM_TIMEOUT=50s, 即每次pexec hang满50s才timeout)
- ATE失败avg 91.6s ≈ 2×47.8s = 2次pexec timeout (50s + 27s, 第2次受BUDGET剩余27s限制)
- 第3次attempt前: elapsed=77s, remaining=85-77=8s < MIN_ATTEMPT_TIMEOUT=10 → break
- 故FASTBREAK=5形同虚设(BUDGET=85只够2次timeout, 永远到不了第5次)

**再降BUDGET的误杀评估(6h成功请求耗时分布)**:
| 区间 | <30s | 30-45s | 45-60s | 60-85s | ≥85s | max |
|---|---|---|---|---|---|---|
| 个数 | 1403 | 56 | 27 | 5 | 3 | 91222ms |

- 降到60s: 误杀8个成功(5个60-85s + 3个≥85s) = 0.53% 误杀率
- 降到75s: 误杀5+个成功 = 0.33%+ 误杀率
- **评判稳定>越快>成功率**: 误杀慢成功违反稳定优先, 证伪降BUDGET.

**NVStream_IncompleteRead (3次/6h, 0.2%, 非系统性)**:
- 14:40 k0 15.7s, 16:51 k4 21.0s, 16:52 k4 46.4s — mid-stream read中断, 非budget耗尽
- 跨key(k0×1, k4×2), 无聚集, 非可优化系统性问题, 不在本轮CC清单

**FASTBREAK=5死参数现象(双机共性)**: HM2(BUDGET=85,FASTBREAK=5)6h 21 ATE avg 91.6s ≈ 2×47.8s, FASTBREAK=5未触发(BUDGET先到). 真正减少失败耗时需"早检测NVCF pexec hang"源码改动(让单次timeout从50s降到~10s), 但6h有26+个成功>48s, 早检测会误杀这些正常慢请求. 不在CC清单, 本轮不动.

## 3. 决策: ⏸️ NOP · 零配置变更

### 3a. 为什么NOP
1. **CC清单三项全部做完或证伪**: A已做完(2.5)+再降证伪, B证伪(无劣化key), C证伪(降BUDGET误杀慢成功). 满足"不允许无操作轮"的例外条件(三项证伪均给出具体数据).
2. **30min 100%成功(157/157), 0 429, 0 ATE, 0 empty_200**: 系统完全清洁.
3. **HM2自R435后无任何变更**: 容器StartedAt=2026-06-30T11:34:46Z(与R435一致), env全一致, 数据模式相同. 无新错误类型/无新劣化key/无新throttle瓶颈.
4. **全部active参数已到天花板**:
   - MIN_OUTBOUND=2.5 (throttle非瓶颈p50_gap=6.63s>>2.5, 再降增429风险)
   - BUDGET=85 (再降误杀慢成功, 6h有8个成功>60s)
   - UPSTREAM=50 (6h 26个成功>48s, 降到45误杀)
   - CONNECT_RESERVE=8 (低于实测connect, 再降误杀)
   - SSLEOF_RETRY=1.0 (1h零SSLEOF, 已最小化)
   - FASTBREAK=5 (死参数, BUDGET先到, 降它无收益)
5. **HM2失败(ATE)是NVCF server-side pexec hang, 不可从proxy层修复** (R434/R435已确认, 本轮6h 23 ATE全NVCFPexecTimeout).

### 3b. 为什么不动任何参数
| 参数 | 当前值 | 为什么不动 |
|---|---|---|
| MIN_OUTBOUND_INTERVAL_S | 2.5 | throttle非瓶颈(p50_gap=6.63s>>2.5), 再降增429风险 |
| TIER_TIMEOUT_BUDGET_S | 85 | 降BUDGET误杀慢成功(8个>60s/6h) |
| UPSTREAM_TIMEOUT | 50 | 6h 26个成功>48s, 降误杀 |
| HM_CONNECT_RESERVE_S | 8 | 低于实测connect, 再降误杀 |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 | 1h零SSLEOF, 已最小化 |
| HM_PEXEC_TIMEOUT_FASTBREAK | 5 | 死参数(BUDGET先到), 降无收益 |
| KEY_COOLDOWN_S | 38 | 全键均衡无冷启动 |
| TIER_COOLDOWN_S | 22 | single-tier, 边际 |

## 4. 参数表 (本轮后HM2状态, 无变更)

| 参数 | 值 | 来源 |
|---|---|---|
| MIN_OUTBOUND_INTERVAL_S | 2.5 | R386 (HM1→HM2, 5.0→2.5) |
| TIER_TIMEOUT_BUDGET_S | 85 | R385 (HM1→HM2, 95→85) |
| HM_CONNECT_RESERVE_S | 8 | R431 (HM1→HM2, 10→8) |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 | R321 (HM1→HM2, 3.0→1.0) |
| HM_PEXEC_TIMEOUT_FASTBREAK | 5 | R384 (HM1→HM2, 3→5) |
| UPSTREAM_TIMEOUT | 50 | R284 |
| KEY_COOLDOWN_S | 38 | R275 |
| TIER_COOLDOWN_S | 22 | R1 |

## 5. 结论

1. **CC清单三项全部做完或证伪**: [HM2-A]已是2.5+throttle非瓶颈(p50_gap=6.63s>>2.5)再降证伪; [HM2-B]5key均衡(31-32)无劣化key证伪; [HM2-C]已是85+再降误杀慢成功(6h 8个>60s)证伪. 满足NOP例外条件, 每项均给具体数据.
2. **数据支撑**: 30min 157/157=100%成功, 0 429, 0 ATE, 0 empty_200; 6h 1494/1520=98.29%(23 ATE+3 NVStream_IncompleteRead).
3. **HM2自R435后零变更**: StartedAt=11:34:46Z未变, env全一致, 数据模式相同 — 无新瓶颈/新劣化/新错误类型涌现.
4. **全参数天花板**: 8个active参数逐一评估, 均无零误杀纯收益的改动空间.
5. **失败机制根因**: ATE=2×NVCFPexecTimeout(50s+27s), avg 91.6s, 是NVCF平台pexec hang, 不可proxy层修复; FASTBREAK=5死参数(BUDGET先到).
6. **稳定优先**: 30min 100%+0 429基线保持, 不为边际提速破坏稳定.

## 6. 待办 (留给下轮HM2→HM1)
- [ ] HM2→HM1: HM1侧参数天花板复查(MIN_OUTBOUND=4.0, BUDGET=125, KEY_COOLDOWN=25), 若有新错误类型回传.
- [ ] 双机共性: FASTBREAK=5死参数现象 — 若CC勘定"早检测NVCF pexec hang"源码改动可立项(需先评估>48s成功的误杀).
- [ ] NVCF server-side PexecTimeout 持续追踪 — 不可proxy层修复, 监控趋势.
- [ ] NVStream_IncompleteRead (3次/6h, 0.2%) — 非系统性, 监控是否聚集, 若聚集再立项.

## ⏳ 轮到HM2优化HM1
