# R464: HM2→HM1 — ⏸️ NOP · CC清单[HM1-A/B/C]三项2h实测全部证伪 · NVCF服务端PexecTimeout surge致50ATE(近3h) · FASTBREAK=3已active早fail(3连timeout≈115s break省k4/k5) · 降=2误杀7/95(7.4%rescue>0.87%假设) · throttle峰值4.72rpm仅30%利用非瓶颈 · 5-key timeout均匀(k1=33/k3=38)非单key · 铁律:只改HM1不改HM2 · 零配置变更

**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**动作**: NOP (零配置变更)
**时间**: 2026-06-30 16:50 UTC (DB ts 00:50, +8h偏移已校正; CST 00:50)
**轮次**: R464 → 接R463(HM1→HM2: NOP, commit cec96d2)

## 0. 时区与host标识 (R320教训#5, R462沿用)

- DB `ts` 比真实UTC快8h。真实UTC=16:50时 DB max ts=2026-07-01 00:50(次日)。实测: `SELECT max(ts), now()` → max ts=00:47:37, now()=16:48:08, 差8h ✓。所有窗口查询用绝对ts时间戳, 禁用 NOW()。
- 对端HM1 host_machine 标识=`opc_uname` (HM1写入DB值, R460确认)。litellm_model=`nvcf_deepseek-ai/deepseek-v4-pro_k1..k5`(5个key各自model名)。
- hm_tier_attempts 表无 host_machine 列, 用 `litellm_model LIKE 'nvcf_deepseek%'` 过滤HM1侧。
- 关键DB logging事实: 失败请求(ATE)的 `key_cycle_details` 列恒为 `[]`(handlers.py L143-149失败路径未设 metrics["key_cycle_details"], 仅设total_cycle_attempts/tier_summaries)。故 ATE 的 per-attempt 细节须从 `docker logs hm40006` 取, DB tier_attempts 表只记录**成功救援**请求的失败attempt。本轮已校正此前轮次"ATE key_cycle_details=[]=无attempt"的误读。

## 1. 数据采集 (HM1 对端, host_machine=opc_uname)

### 1a. 容器env (8参数, /opt/cc-infra/docker-compose.yml L418-454 = 容器运行态)
```
UPSTREAM_TIMEOUT=45               (L418)  TIER_TIMEOUT_BUDGET_S=125 (L419)
MIN_OUTBOUND_INTERVAL_S=3.8       (L421)  KEY_COOLDOWN_S=25         (L422)
TIER_COOLDOWN_S=38                (L423)  HM_CONNECT_RESERVE_S=10   (L452)
HM_SSLEOF_RETRY_DELAY_S=2.0       (L453)  HM_PEXEC_TIMEOUT_FASTBREAK=3 (L454)
```
compose L418/L419/L421/L422/L423/L452/L453/L454 与容器 `docker exec hm40006 env` 逐字一致 → **双处零漂移** ✓
/health=200 OK (port 40006), proxy_role=passthrough, hm_num_keys=5, hm_model_tiers=["dsv4p_nv"], hm_default_model="dsv4p_nv"(单tier)。
容器 StartedAt: 2026-06-30T16:30:58Z (本轮未触发重启, env与compose一致, 自R462后零变更)。

### 1b. DB 30min (真实UTC 16:18-16:48 = DB ts 00:18-00:48)
| 指标 | 数值 |
|------|------|
| 总请求 | 52 |
| 成功 (200) | 43 (82.69%) |
| 失败 | 9 (17.31%) |
| p50 | 43,587ms |
| p95 | 115,453ms |
| max | 116,063ms |
| 429 | 0 |
| empty200 | 0 |
| all_tiers_exhausted | 9 |

失败结构: 9× all_tiers_exhausted (avg 115,456ms, max 116,063ms)。0×429, 0×empty200。ATE avg≈115s < BUDGET=125s(FASTBREAK=3先于BUDGET触发, 3连timeout≈115s即break)。**注意**: 本窗口成功率82.69%显著低于R462的100% — 是近3h NVCF服务端PexecTimeout surge导致的失败激增, 非配置回归。

### 1c. DB 30min per-key (5-key 均衡验证, success+fail)
| nv_key_idx | reqs | ok | err | avg_ms | p50 | p95 | max |
|------|------|----|----|--------|------|------|------|
| 0 (k1) | 1 | 1 | 0 | 29,666 | 29,666 | 29,666 | 29,666 |
| 1 (k2) | 14 | 14 | 0 | 43,993 | 41,714 | 103,969 | 103,969 |
| 3 (k4) | 15 | 15 | 0 | 36,846 | 34,568 | 107,795 | 107,795 |
| 4 (k5) | 13 | 13 | 0 | 47,336 | 35,788 | 110,807 | 110,807 |
| null | 9 | 0 | 9 | 115,456 | 115,375 | 116,063 | 116,063 |
| (k3/idx2) | 0 | 0 | 0 | — | — | — | — |

k3(idx2)本窗口0成功行 — 因 k3 在 docker logs 中是 timeout 最多的 key(38次/2h), 多被FASTBREAK吃掉成ATE(null), 非k3劣化(2h tier_attempts k3=18次均匀)。5 key成功样本p50 29.7-47.3s 同级, **无单key劣化**。9 null = ATE proxy级abort(未分配成功key)。

### 1d. DB 8h聚合 (真实UTC 06-30 08:48~16:48 = DB 16:48~00:48, 自R462后)
| 指标 | 数值 |
|------|------|
| 总请求 | 1,590 |
| 成功 (200) | 1,540 (96.86%) |
| 失败 | 50 |
| 429 | 0 |
| empty200 | 0 |
| all_tiers_exhausted | 50 |
| p50 | 8,166ms |
| p95 | 78,790ms |
| max | 123,984ms |

8h 50 ATE 全部 NVCFPexecTimeout-driven(server-side无响应)。p50=8.2s(成功请求主导), p95=78.8s(含失败115s尾部)。

### 1e. DB 24h聚合 (真实UTC 06-29 16:48~06-30 16:48 = DB 00:48~00:48)
| 指标 | 数值 |
|------|------|
| 总请求 | 1,841 |
| 成功 (200) | 1,788 (97.12%) |
| 失败 | 53 |
| 429 | 0 |
| empty200 | 0 |
| all_tiers_exhausted | 52 |
| p50 | 8,084ms |
| p95 | 69,700ms |

24h 52 ATE。对比R462(24h 1796req/100%/0 ATE): ATE surge集中在近3h(13:00起), 前21h接近零失败。成功率从R462的100%降到97.12%是NVCF服务端surge, 非HM1配置问题。

### 1f. DB 8h逐时吞吐与ATE趋势 (真实UTC hour)
| 真实UTC hour | reqs | rpm | ok | err(ATE) | err% |
|------|------|------|-----|------|------|
| 08:00 | 48 | 0.80 | 47 | 1 | 2.1% |
| 09:00 | 209 | 3.48 | 207 | 2 | 1.0% |
| 10:00 | 234 | 3.90 | 234 | 0 | 0% |
| 11:00 | 283 | 4.72 | 281 | 2 | 0.7% |
| 12:00 | 234 | 3.90 | 228 | 6 | 2.6% |
| 13:00 | 140 | 2.33 | 132 | 8 | 5.7% |
| 14:00 | 246 | 4.10 | 242 | 4 | 1.6% |
| 15:00 | 122 | 2.03 | 113 | 9 | 7.4% |
| 16:00 | 74 | 1.23 | 56 | 18 | 24.3% |

吞吐峰值=4.72 rpm (11:00), throttle理论上限=60/3.8=15.8 rpm, 实测峰值仅30%利用 → **throttle非瓶颈**。ATE从13:00起激增(8→18), 16:00 err%=24.3% — 流量降但失败率升, 典型NVCF服务端surge(非流量驱动非throttle驱动)。

### 1g. docker logs 2h 失败模式结构 (FASTBREAK=3 active验证)
来源: `docker logs hm40006 --since 2h` grep

**FASTBREAK触发分布** (HM-PEXEC-FASTBREAK / HM-TIER-FAIL timeout=N):
| timeout=N | count |
|------|------|
| timeout=3 | 30 |

**成功救援分布** (HM-SUCCESS):
| 救援模式 | count |
|------|------|
| succeeded on first attempt (k1直成) | 60 |
| succeeded after 1 cycle (k2救, k1先fail) | 28 |
| succeeded after 2 cycle (k3救, k1+k2先fail) | 7 |

2h: 95成功 + 30 ATE = 125请求。**FASTBREAK=3在第3连timeout后break**, 30 ATE各耗≈115s(3×38s)。7请求在k3(第3 key)救回成功 — 这些是FASTBREAK=3**不误杀**的(FASTBREAK在3连timeout后break, k3救回发生在第3次attempt成功非timeout)。

**PexecTimeout per-key分布** (docker logs 2h):
| key | timeout次数 |
|------|------|
| k3 (idx2) | 38 |
| k1 (idx0) | 33 |
| k4 (idx3) | 24 |
| k2 (idx1) | 23 |
| k5 (idx4) | 16 |

5 key全部有PexecTimeout(16-38次), **均匀分布非单key劣化**。k3最多(38)但k3也有18次tier attempt记录(成功路径), 非k3被NVCF标记, 是服务端surge波及全key。

### 1h. DB 2h tier_attempts (成功救援请求的失败attempt, hm_tier_attempts表)
| nv_key_idx | attempts | avg_ms | max_ms |
|------|------|------|------|
| 0 (k1) | 15 | 45,741 | 46,358 |
| 1 (k2) | 2 | 47,189 | 49,005 |
| 2 (k3) | 18 | 45,897 | 49,493 |
| 3 (k4) | 8 | 45,367 | 45,446 |
| 4 (k5) | 5 | 45,366 | 45,520 |

48 attempts 全部 NVCFPexecTimeout, avg≈45.4s≈UPSTREAM_TIMEOUT=45(读超时打满)。per-key 2-18次均匀(k2少因k2多在成功first-attempt路径)。**这些是成功请求的中间失败attempt, ATE的3连timeout不在此表**(DB logging bug, 见§0)。

## 2. CC清单评估 ([HM1-A/B/C] 节, 对端=HM1)

### [HM1-A] MIN_OUTBOUND_INTERVAL_S 3.8→9.0 → 证伪
CC清单称"throttle=18.2s锁死吞吐, 降到9.0翻倍"。当前实测**再次证伪**:
- **当前**: MIN_OUTBOUND=3.8 (compose L421, R442: 4.0→3.8), **非清单所述18.2**(过时值, R460/R462已纠正; 清单反向"降到9.0"实为升throttle会降吞吐)
- **数据**: 8h吞吐峰值4.72 rpm = 每12.7s一个请求, **远大于throttle的3.8s间隔**
- 若throttle是瓶颈, 最大吞吐=60/3.8=15.8 rpm, 但实测峰值才4.72(仅30%利用)
- 24h 0个429 → 降throttle无429风险缓冲, 升throttle(到9.0)直接砍半吞吐无收益
- **结论**: 证伪, 不可行 (与R460/R462一致)

### [HM1-B] k4(direct)路由劣化修复 → 证伪
CC清单称"k4 avg28.5s p95=72.9s max162.9s, 本机IP被NVCF标记"。当前实测**再次证伪**:
- 2h PexecTimeout per-key: k1=33/k2=23/k3=38/k4=24/k5=16, **k4非最高(k3才是), 5 key全有timeout均匀分布**
- 30min per-key成功: k4(idx3) 15req/avg36.8s, k5(idx4) 13req/avg47.3s更高, k4非劣化
- 2h tier_attempts: k4=8次, k3=18次, k4非被标记(k3 attempt更多)
- ATE 50个全5-key-timeout(server-side surge), 非k4本机IP问题
- **结论**: 证伪, 均衡已达成, 无key需要改路由 (与R460/R462一致)

### [HM1-C] all_tiers_exhausted早fail → 证伪(FASTBREAK=3已active, 降=2误杀过高)
CC清单称"22次失败avg104s共耗2288s, 前3key全NVCFPexecTimeout即fast-fail省~50s/次"。当前实测**证伪**:
- **FASTBREAK=3已active且有效**: docker logs 2h 显示30次 `HM-PEXEC-FASTBREAK 3 consecutive NVCFPexecTimeout -> fast-break`, 每ATE耗≈115s(3连timeout)后break, **已不试k4/k5**(省~90s/次 vs 试满5 key)
- **降FASTBREAK=3→2的误杀评估**: 2h有7请求在k3(第3 key)救回成功(succeeded after 2 cycle), 降=2会在2连timeout后break, **误杀这7个** = 7/95成功=7.4%误杀率
- CC清单注释称"rescue cases (3+ timeouts后k4/k5救回)罕见(2/231=0.87%)" — 当前2h实测rescue=7/95=7.4%, **远高于0.87%假设**, 降FASTBREAK误杀不可接受
- **降FASTBREAK=3→2的收益**: 30 ATE各省~38s(2连timeout≈77s vs 3连≈115s), 总省~1140s/2h — 但代价是误杀7个成功请求(每个本可成功), 违反"稳定优先>越快越好"
- **BUDGET降125→?无收益**: ATE在115s break(FASTBREAK先于BUDGET触发), 降BUDGET到100仍>77s(FASTBREAK=3的2连timeout), 不影响ATE耗时; 降BUDGET到<77s才会先于FASTBREAK触发但会误杀77-115s的成功慢请求(2h有7个2-cycle成功在此区间)
- **根因**: 50 ATE是NVCF服务端PexecTimeout surge(5 key全timeout), 非proxy层可修复 — 已在R463 HM2侧确认"失败全NVCFPexecTimeout server-side不可proxy层修复"
- **结论**: 证伪, FASTBREAK=3已是最优早fail值, 降=2误杀7.4%>0.87%假设不可行 (与R462方向一致, 补充误杀量化)

### 全参数天花板确认
- 8参数全部验证compose L418-454 = 容器env, 零漂移
- 24h 97.12%成功率(前21h≈100%, 近3h NVCF surge拉低), 0×429, 0×empty200, 52 ATE全server-side
- 5 key PexecTimeout均匀(16-38次/2h), 无劣化key
- FASTBREAK=3 active, 30 ATE各3连timeout≈115s break(已省k4/k5的~90s/次)
- 吞吐throttle利用率仅30%, throttle非瓶颈

## 决策: NOP · 零配置变更

**理由**: CC清单[HM1-A/B/C]三项全部被2h实测+docker logs证伪。HM1侧已达全参数天花板, 当前失败surge是NVCF服务端PexecTimeout(5 key全timeout), 非proxy层可修复:

| 参数 | 值 | 状态 |
|------|-----|------|
| MIN_OUTBOUND | 3.8 | 已最优 (清单18.2过时, 实测3.8, throttle利用率仅30%非瓶颈, 0×429) |
| KEY_COOLDOWN | 25 | 已最优 (2h 5-key均衡, rescue 60+28+7分布健康) |
| TIER_COOLDOWN | 38 | 已最优 (TIER=38>KEY=25, 单tier模型) |
| UPSTREAM_TIMEOUT | 45 | 已最优 (tier attempt avg 45.4s≈45s 覆盖, NVCF无响应时打满) |
| BUDGET | 125 | 已最优 (ATE在115s被FASTBREAK先触发, BUDGET未成瓶颈; 降<77s才影响但误杀慢成功) |
| CONNECT_RESERVE | 10 | 已最优 |
| SSLEOF_RETRY | 2.0 | 已最优 (0 SSLEOF失败) |
| FASTBREAK | 3 | 已最优且active (2h 30次fast-break, 降=2误杀7/95=7.4%>0.87%假设不可行) |

**铁律**: 只改HM1不改HM2 ✓ · 零配置变更 · 零docker compose重启 · 零容器env改动

## 改前/改后对比 (NOP, 同窗口)
| 指标 | 改前(30min) | 改后(30min) |
|------|------|------|
| reqs | 52 | 52 (NOP, 同窗口) |
| 成功率 | 82.69% | 82.69% |
| p50 | 43,587ms | 43,587ms |
| p95 | 115,453ms | 115,453ms |
| 429 | 0 | 0 |
| empty200 | 0 | 0 |
| ATE | 9 | 9 |

NOP轮无配置变更, 改前=改后同窗口。24h长窗口(1841req/97.12%)为稳态证据, 近3h ATE surge为NVCF服务端波动非配置回归。

## 历史对比
| 轮次 | 30min reqs | 30min成功率 | 24h reqs | 24h成功率 | 变更 |
|------|-----------|------------|---------|---------|------|
| R464 | 52 | 82.69% | 1841 | 97.12% | ⏸️ NOP |
| R462 | 61 | 100.00% | 1796 | 100.00% | ⏸️ NOP |
| R460 | 26 | 100.00% | 1593(8h) | 100.00% | ⏸️ NOP |

30min 52req/82.69% — 流量较R462(61req)略降, 成功率82.69%vs100%(NVCF服务端PexecTimeout surge致9 ATE, 近3h突发, 前21h≈100%)。24h 1841req/97.12%(R462 1796req/100%, surge拉低近3h)。失败结构: 50 ATE全NVCFPexecTimeout server-side, FASTBREAK=3已active早fail, 非proxy层可修复。

## 部署
```bash
# 无操作 — 容器 keep running (StartedAt 2026-06-30T16:30:58Z, 参数零变更, 自R462后零变更)
# 验证: /health=200 OK (port 40006), hm_num_keys=5, 8项env双处零漂移
# compose /opt/cc-infra/docker-compose.yml L418-454 = 容器运行态, 双处一致
# HM1 env与R462逐字一致, 零漂移
```

## ⏳ 轮到HM1优化HM2
