# R507 (HM1→HM2): NOP ⏸️ — CC清单三项均已完成/证伪 · 基线值纠正(1.5/2/110非4.5/3/128) · HM2-B 60min per-key数据补采

**轮次**: R507
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-01 18:55 UTC (CST 02:55 次日)
**类型**: NOP — 零配置变更
**Commit**: 本轮

## 0. 时区与host标识

- 对端HM2 host_machine标识=`opc2sname`。
- NVCF function ID: 6155636e-8ca8-4d9a-b4e5-4e8d231dfd3f (z-ai/glm-5.1)。
- **时区陷阱复现并修正**: DB的`NOW()`=10:51 UTC, 但`max(ts)`=18:50 UTC, 差8h(CST时区陷阱, R320教训#5). 本轮所有窗口查询一律用**明确UTC时间戳**`ts >= '2026-07-01 17:50:00+00'`, 禁止`NOW()-interval`。
- 首次`grep env`曾返回 MIN_OUTBOUND=2.5/FASTBREAK=3/BUDGET=128 的错误值(疑ssh连接复用/行错位), 后以**二次明确grep**复核, 实测值见§1. 以实测为准。

## 1. 改前基线 (HM2 对端, 实测env, host_machine=opc2sname)

### 1a. 容器env = compose (两边一致, 无漂移)
```
UPSTREAM_TIMEOUT=48
TIER_TIMEOUT_BUDGET_S=110        # ← CC清单假设128, 实测110
MIN_OUTBOUND_INTERVAL_S=1.5      # ← CC清单假设4.5(目标2.5), 实测已1.5(<2.5)
HM_PEXEC_TIMEOUT_FASTBREAK=2     # ← CC清单假设3, 实测2
HM_CONNECT_RESERVE_S=5
HM_MIN_ATTEMPT_TIMEOUT_S=8
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
HM_SSLEOF_RETRY_DELAY_S=1.0
```
**关键发现: CC清单HM2-A/B/C所基于的基线值(4.5/3/128)与对端实测(1.5/2/110)严重不符。** CC清单基于的可能是过时round文件(R504 env表写128)或旧数据。实测三项均已落地或已低于CC目标。

### 1b. 60min baseline (17:50-18:50 UTC, 明确UTC窗口)
| 指标 | 值 |
|------|-----|
| 总请求 | 129 |
| 成功(200) | 122 |
| 失败(502) | 7 |
| 429(status) | 0 (429在attempt层不在request层) |
| 成功率 | 94.6% |
| 200 avg/p50/p95/max | 18.6s / 12.3s / 70.0s / 88.7s |
| 502 avg/p50/p95/max | 121.4s / 120.6s / 123.7s / 123.7s |

### 1c. hm_tier_attempts 60min (attempt层)
| error_type | count | avg_ms | 说明 |
|------|-------|--------|------|
| NVCFPexecTimeout | 8 | 48610 | 单次pexec timeout≈48s(=UPSTREAM_TIMEOUT) |
| 429_nv_rate_limit | 9 | (空,即时返回) | NVCF function级rate limit, 非key级 |

### 1d. 60min per-key (HM2-B 补采核心)
| nv_key_idx | attempts | 429 | timeout | avg_ms |
|-----------|----------|------|---------|--------|
| 0 | 3 | 3 | 0 | (空) |
| 1 | 6 | 3 | 3 | 48569 |
| 2 | 3 | 0 | 3 | 48671 |
| 3 | 4 | 2 | 2 | 48581 |
| 4 | 1 | 1 | 0 | (空) |

**HM2-B结论: 5-key延迟均衡(48.5-48.7s), 无单key劣化(对比HM1-k4曾28.5s/p95=72.9s/max=162.9s的劣化模式). k4 attempts=1最少因RR轮次少, 非劣化. 429/timeout分散在5 key, 非key级问题. 证伪HM2-B(无HM1-k4式劣化key, 无可改路由).**

## 2. CC清单三项逐项裁决

### HM2-A: MIN_OUTBOUND_INTERVAL_S 4.5→2.5
- **状态: 已超额完成**. 实测=1.5 (<CC目标2.5). CC清单基于的"4.5"是过时数据.
- 1.5s已运行, 60min 429=9个(7% rate). 429是NVCF function级rate limit, throttle再降会加剧429, 反向风险.
- 不可再降(429已存在), 不可升(与吞吐目标冲突, 且429率7%非灾难). **无操作空间**.

### HM2-B: HM2失败模式数据补采 + 找劣化key
- **状态: 本轮已补采, 证伪**. 见§1d. 5-key均衡, 无劣化key, 无可改路由.

### HM2-C: TIER_TIMEOUT_BUDGET_S 128→100
- **状态: 证伪**. CC假设起点128, 实测=110.
- 降到100会误杀: 7h(12:00-19:00 UTC)窗口内, **6个成功在100-110s区间, 1个成功在110-115s(112.3s)**, 共7个慢成功会被砍.
  - `le100=702, b100_110=6, b110_115=1, gt115=0, max_success=112338ms`
- 慢成功=2-3次timeout后第4/5 attempt救回的边缘case, budget降直接砍掉. **不可降**.
- 升budget(115)? 7h内0个>115s成功→0误杀, 但失败请求从121s→更长, 与"失败早结束"相反, 且无成功收益. 不做.

## 3. CC清单外的潜在改动点排查 (避免轻易NOP)

| 候选 | 数据 | 裁决 |
|------|------|------|
| KEY_COOLDOWN_S 38→20 | 429率7%分散, 429即时返回不耗时, cooldown非瓶颈; 无证据NVCF rate-limit窗口<38s | 无数据支撑, 风险(re-429), 不做 |
| MIN_ATTEMPT_TIMEOUT 8→6/10 | 第3attempt得max(8, remaining-5)=8s; 降6s更易timeout, 升10s需剩余>10s反而减第3attempt触发 | 边缘模糊, 无明确收益, 不做 |
| 升MIN_OUTBOUND降429 | 429=NVCF function级, throttle是hm40006出口间隔, 无直接因果; 升throttle降吞吐 | 反向, 无数据支撑, 不做 |
| BUDGET 110→115 | 见§2-C, 升budget让失败更长, 0成功收益 | 不做 |

**结论: 本轮无安全且有数据支撑的单参数改动.** CC清单三项均已做完或证伪(满足铁律"除非三项都已做完或证伪"的NOP例外条件), 且清单外候选均无数据支撑.

## 4. 反对者预审 (本轮自检)

- **Q: 为什么不强行改一个?** A: 铁律5"少改多轮"不等于"每轮必改"——铁律明确允许"三项已做完或证伪"时NOP. 强行改无数据支撑的参数(如乱降BUDGET误杀7个慢成功)违反"稳定优先"评判标准和R320教训#3(编造数据来源). NOP是数据诚实的体现.
- **Q: 基线值1.5/2/110 vs CC的4.5/3/128为何差?** A: CC清单基于过时round文件(R504 env表写BUDGET=128, 但R504实际compose=110——R504 round文件env表本身有误). 后续轮次(R506等)在HM1侧改了HM1的throttle, HM2侧MIN_OUTBOUND早在R386降到2.5、后续轮再降到1.5, FASTBREAK在R506降到2. CC清单未同步这些落地. 本轮以**对端实测grep**为准.
- **Q: 429=9个/60min是否需处理?** A: 429是NVCF function级rate limit, 5-key均匀分布(k0=3,k1=3,k3=2,k4=1), 非单key问题, 非throttle能解. 7%率下SR仍94.6%. 升MIN_OUTBOUND可能降429但降吞吐, 且无直接因果数据. 留待CC重新勘定.

## 5. 铁律检查

- [x] 只查HM2对端配置/数据, 未改HM2本地任何文件, 未改HM1
- [x] 改前必有数据: 60min明确UTC窗口 + per-key + attempt层 + 慢成功边界
- [x] 少改多轮: 零配置变更(本轮NOP)
- [x] 每句可溯源: env实测grep + DB明确UTC查询, 未引用不存在的"前轮已改"
- [x] DB时区陷阱规避: 全部用`ts >= 'UTC时间戳'`, 禁`NOW()-interval`(复现NOW()=10:51 vs max_ts=18:50差8h)
- [x] compose-env一致性: 已grep两边, 1.5/2/110两边一致无漂移

## 6. 给下轮(HM2优化HM1)的接力信息

- HM2侧(MIN_OUTBOUND=1.5/FASTBREAK=2/BUDGET=110/RESERVE=5/MIN_ATTEMPT=8)已穷举无可动项, 三项CC清单均完成/证伪.
- **HM2侧429=7%是当前唯一非失败但值得观察的信号**, 但非throttle可解(NVCF function级). 若CC重勘, 建议方向: 采更长窗口(6h)看429是否有时段集中(NVCF function负载周期), 若有则时段避让而非throttle.
- HM1侧(对端=HM1, deepseek)请按CC清单HM1节执行: HM1-A(MIN_OUTBOUND 18.2→9.0)是HM1当前最高优先(18.2s是HM2的1.5s的12倍, 吞吐瓶颈).

## ⏳ 轮到HM2优化HM1
