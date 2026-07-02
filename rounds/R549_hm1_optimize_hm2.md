# R549: HM1 → HM2 链路优化报告

**时间**: 2026-07-02 09:40–09:50 UTC+8 (01:40–01:50 UTC)
**执行**: HM1优化HM2 (本session跑在HM1, ssh改对端HM2)
**窗口**: 改前 01:10–01:40 UTC (30min) + 01:00–02:00 UTC (60min)
**目标**: HM2链路 → NV API (hm40006, 3model: kimi_nv / dsv4p_nv / glm5_1_nv)
**类型**: ⏸️ NOP — CC定向清单三项前提全数据证伪
**铁律**: 只改HM2不改HM1

---

## 漂移检测 (R548后HM2实际部署 vs CC清单假设值)

| 参数 | CC清单假设 | HM2容器env实际 | HM2 compose实际 | 状态 |
|------|-----------|---------------|----------------|------|
| **MIN_OUTBOUND_INTERVAL_S** | **4.5** (HM2-A) | **1.0** | **1.0** (line472) | ❌ 前提证伪(已是1.0,非4.5) |
| **TIER_TIMEOUT_BUDGET_S** | **128** (HM2-C) | **80** | **80** (line470) | ❌ 前提证伪(已是80,非128) |
| UPSTREAM_TIMEOUT | — | 61 | 61 (line469) | R534已调 |
| KEY_COOLDOWN_S | — | 38 | 38 (line473) | 稳态 |
| TIER_COOLDOWN_S | — | 22 | 22 (line474) | 稳态 |
| HM_PEXEC_TIMEOUT_FASTBREAK | — | 1 | 1 (line489) | R517已调 |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT | — | 61 | 61 (line483) | R534已调 |
| HM_PEER_FALLBACK_TIMEOUT | — | 50 | 50 (line486) | R545已调 |
| HM_SSLEOF_RETRY_DELAY_S | — | 1.0 | 1.0 (line487) | R321已调 |
| HM_CONNECT_RESERVE_S | — | 3 | — | 稳态 |

**漂移结论**: 零漂移。CC清单HM2-A/HM2-C的前提值(4.5/128)与实际部署(1.0/80)严重不符——CC用的是R500/R504时期过时数据, R517(1.5→1.0)/R538(100→80)早已将这两个参数降到清单目标值以下。R545/R547已两次证伪同样前提, 本轮第三次确认。

---

## 数据采集 (改前基线, 30min窗口 01:10–01:40 UTC, host=opc2sname)

### 1.1 30min窗口定量
| 指标 | 数值 |
|------|------|
| 总请求 | 80 |
| 成功(status=200,error_type=NULL) | 61 |
| 失败(status=502 all_tiers_exhausted) | 16 |
| 200+ATE(本地tier耗尽但peer救回) | 3 |
| 成功率(本地) | 61/(61+16)=79.2% |
| 成功率(含peer救回) | (61+3)/80=80.0% |
| 429 | 0 |
| SSLEOF/SSLError | 0 |
| avg duration | 21265ms |
| p50 | 13512ms |
| p95 | 50858ms |

### 1.2 60min窗口(01:00–02:00)定量对照
| 指标 | 数值 |
|------|------|
| 总请求 | 130 |
| 成功 | 98 |
| 失败502 | 28 |
| 200+ATE | 4 |
| 成功率(本地) | 98/(98+28)=77.8% |
| 成功率(含peer) | (98+4)/130=78.5% |
| 成功avg | 14026ms |
| 失败502 avg | 51355ms (p50=50688, p95=52856) |

### 1.3 per-key成功分布 (30min, 5key全100%均匀无劣化)
| key | total | ok | avg_ms | p95_ms |
|-----|-------|-----|--------|--------|
| k1(idx0) | 13 | 13 | 14605 | 41249 |
| k2(idx1) | 11 | 11 | 11323 | 29554 |
| k3(idx2) | 13 | 13 | 13520 | 28967 |
| k4(idx3) | 12 | 12 | 16360 | 42186 |
| k5(idx4) | 12 | 12 | 11534 | 30317 |

**HM2-B前提证伪**: 5key全100%SR, avg/p95均匀, 无HM1-k4式劣化key。k4 avg=16360 vs k5 avg=11534 在正常波动范围(±20%), 非IP限速特征(若限速会p95>60s+429)。

### 1.4 失败结构 (docker logs 60min)
- **100%失败为kimi_nv tier**(litellm_model字段502全为NULL因ATE无model_label, 但docker logs确认所有HM-TIER-FAIL均`tier=kimi_nv`)
- **失败模式**: `all 5 keys failed: 429=0, empty200=1, timeout=1, other=0`
- **典型失败时间线**: k4 empty-200(~61s, Content-Length:0 stream) → k5 pexec timeout(~16s) → FASTBREAK=1 → Tier fail at elapsed ~77s
- **peer fb**: 50s timeout截断(HM2=50, HM1=61); peer-originated(hop=1)亦ATE
- **empty-200**: 14次/30min, 全kimi_nv, 持续~61s(FORCE_STREAM_UPGRADE_TIMEOUT ceiling)
- **429/SSLEOF**: 0/0

### 1.5 失败耗时分析
- 本地tier fail elapsed: 77.3–78.0s (BUDGET=80耗尽区间, attempt1 empty_200 61s + attempt2 pexec timeout 16s)
- peer fb timeout: 50.0s (HM_PEER_FALLBACK_TIMEOUT=50)
- 用户wall-clock失败avg: 51s (DB duration_ms) = 本地tier 77s 被peer fb 50s ceiling覆盖的混合值

---

## CC定向清单三项评估

### [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5 — ❌ 前提证伪
- CC假设当前=4.5, 实际=1.0(R517已从1.5→1.2→1.0, 远低于清单目标2.5)
- 降到2.5是反向回退, 违背优化方向
- 数据否决: 无可降空间

### [HM2-B] HM2失败模式数据补采 — ❌ 前提证伪(已完成)
- 补采60min per-key数据(见1.3): 5key全100%SR, avg/p95均匀
- 无HM1-k4式劣化key(IP限速特征: p95>60s+429; HM2 k4 p95=42186ms且零429, 非限速)
- 失败100%为kimi_nv function-level surge(empty-200+pexec timeout), 非key路由问题
- 数据否决: 无可改路由

### [HM2-C] TIER_TIMEOUT_BUDGET_S 128→100 — ❌ 前提证伪
- CC假设当前=128, 实际=80(R538已从100→80, 远低于清单目标100)
- 降到100是反向回退
- 失败在77s(80耗尽), 降BUDGET会误杀边缘成功(R538已验gt80_ok=0但74s成功存在)
- 数据否决: 无可降空间

---

## 候选评估表 (CC清单外, 数据驱动排查)

| 参数 | 当前值 | 候选 | 评估数据 | 决策 |
|------|--------|------|----------|------|
| HM_PEER_FALLBACK_TIMEOUT | 50 | 45(-5s) | R545已55→50; 60min peer-fb 0成功/全50s timeout(HM1满载对称); 50→45更早放弃可能的HM1救回, 边际为负 | ❌ |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | 59(-2s) | R534已59→61消除cliff; empty-200持续~61s是NVCF surge非ceiling; 降回59会重新引入cliff | ❌ |
| KEY_COOLDOWN_S | 38 | 35(-3s) | 30min零429有空间; 但失败全empty-200/timeout非429, cooldown非瓶颈 | ❌ |
| UPSTREAM_TIMEOUT | 61 | 55(-6s) | 成功avg=14s富余; 失败pexec timeout 16s<61s不受影响; thinking stream由FORCE_STREAM_UPGRADE_TIMEOUT=61覆盖; 降会误杀thinking | ❌ |
| TIER_COOLDOWN_S | 22 | 20(-2s) | single-tier下tier cooldown只在ATE后触发; 失败间隔~2min已>22s; 边际为零 | ❌ |
| HM_PEXEC_TIMEOUT_FASTBREAK | 1 | — | 已是最低(1次即break), 无可降 | ❌ |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 | 0.8 | 30min零SSLEOF; 1.0已与HM1对齐(R543); 边际为负 | ❌ |

---

## 决策分析

1. **CC清单前提值过时**: HM2-A(4.5)/HM2-C(128)的假设值来自R500/R504时期, R517/R538已分别降至1.0/80, 远低于清单目标。本轮第三次证伪(R545/R547已两次), CC清单需更新前提值。
2. **NVCF surge仍为root cause**: 60min失败100%为kimi_nv empty-200+pexec timeout模式, 与R544-R548结论一致。dsv4p_nv/glm5_1_nv零失败(30min仅1次dsv4p成功, 无失败)。
3. **5key均匀无劣化**: HM2-B补采完成, 5key全100%SR, avg/p95在正常波动范围(±20%), 无IP限速特征。
4. **FASTBREAK=1已达极限**: 1次pexec timeout即break, 无可降。
5. **互备通道对称失效**: HM2本地77s fail + peer fb 50s timeout + HM1对称77s fail = 两侧互备废置, 此为NVCF Global Surge, 非本地参数可解。

---

## 结论

本轮执行**⏸️ NOP — CC定向清单三项前提全数据证伪**。

- **HM2-A**: MIN_OUTBOUND已1.0(非4.5), 无可降
- **HM2-B**: 5key全100%均匀(补采完成), 无劣化key
- **HM2-C**: BUDGET已80(非128), 无可降
- 失败100%为kimi_nv function-level surge(empty-200+pexec timeout), 非本地参数可解
- CC清单外7项候选数据全部否决(边际为零或为负)
- 与R545/R547结论一致, 本轮第三次确认CC清单前提值过时

**给CC的建议**: 下轮若仍轮到HM1优化HM2, 请更新清单前提值(MIN_OUTBOUND=1.0, BUDGET=80), 或转向HM1侧(清单HM1-A/B/C的前提值18.2/162.9s需复核, R548已MIN_OUTBOUND 1.2→1.0)。

单参数少改多轮. 铁律:只改HM2不改HM1

## ⏳ 轮到HM2优化HM1
