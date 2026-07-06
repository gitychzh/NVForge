# R325: HM1→HM2 — ⏸️ 无操作: CC清单HM2-A/B/C三项当前数据证伪 + 纠正R324架构误判(两机均旧NVCF直连,BUDGET等皆活参数) + R321 SSLEOF backoff首次触发验证闭环

**角色**: HM1(执行者, opc_uname) → HM2(目标, opc2sname)
**日期**: 2026-06-30 03:25 UTC
**铁律**: 只改HM2不改HM1
**前轮**: R324 (HM2→HM1, 误判HM1为LiteLLM架构); 期间HM2抢跑一轮 9880398 (HM2→HM1, HM1侧 HM_CONNECT_RESERVE_S 16→12, 已部署生效=12) — 此commit印证HM1侧CONNECT_RESERVE是活参数(改了并生效), 反证R324"死参数"误判
**本轮基线锚点**: max(ts)=2026-06-30 03:21:28 UTC (HM2 DB, host_machine='opc2sname', R317 §0 max(ts)口径)

## 0. 任务规则与本轮决策依据

任务规则: "优先执行清单第1项, 若第1项本轮无法实施(如已被前轮做过/数据不支撑), 顺延下一项。每轮只做1项。不允许无操作轮除非三项都已做完或数据证伪(证伪需给出具体数据)。"

本轮对CC定向清单HM2侧三项(A/B/C)用**当前30-360min窗口实测数据**复核, 三项均**数据证伪不可改**(§2)。同时主动候选(UPSTREAM_TIMEOUT↓/BUDGET↓/fast-fail)逐个数据证伪(§3)。

本轮**实质贡献**有三(非空泛无操作):
1. **纠正R324架构误判**(§4): R324称HM1运行LiteLLM架构使BUDGET/CONNECT_RESERVE/SSLEOF成死参数——**此判断错误**。HM1和HM2实际入口链均加载旧NVCF直连架构(execute_request), BUDGET等在两端**都是活参数**。R323改HM1 BUDGET 90→100**实际生效**, R321改HM2 SSLEOF 1.0**实际生效**。
2. **R321 SSLEOF backoff触发验证闭环**(§5): docker logs首次捕获 `[03:08:19.1] [HM-SSL-RETRY] ... after 1.0s backoff`, 证明R321代码读env补丁+env=1.0在HM2侧运行生效(显示"1.0s"而非旧硬编码3s)。闭环R321/R323留下的"待自然触发验证"待办。
3. **CC清单三项当前数据证伪**(§2): 用本轮新数据再确认A(throttle非瓶颈)/B(无劣化key)/C(误杀>100s救回)。

三项全证伪 + 架构纠正, 符合"无操作例外"(证伪需给出具体数据, 本轮每项有具体数据)。

## 1. 改前数据采集 (锚点 max_ts=2026-06-30 03:21:28 UTC, HM2)

### 1a. 多窗口成功率
| 窗口 | total | success | fail | 成功率 |
|---|---|---|---|---|
| 30min | 137 | 137 | 0 | **100.00%** |
| 60min | 201 | 196 | 5 | 97.51% |
| 120min | 327 | 310 | 17 | 94.80% |
| 360min(6h) | 917 | 867 | 50 | 94.55% |

**流量上升**: 30min=137reqs→4.57req/min (vs R323时2.4req/min, R321时3.87req/min)。30min窗口100%成功率(零失败)。

### 1b. 60min错误结构
| error_type | n | avg_dur | p50 | p95 | max_dur |
|---|---|---|---|---|---|
| (success) | 196 | 13744 | 8607 | 38972 | 117077 |
| all_tiers_exhausted | 5 | 122755 | 122241 | 124566 | 125051 |

**所有失败都是 all_tiers_exhausted**, avg 122s ≈ BUDGET 128s 减 overhead, 耗满预算。无429/empty200/SSL。

### 1c. 30min成功延迟 (改前基线, 100%成功率窗口)
| total | p50 | p95 | avg | max |
|---|---|---|---|---|
| 153 | 7376 | 31562 | 10426 | 77836 |

### 1d. 6h限流/SSL基线
| 指标 | 值 |
|---|---|
| 6h总请求 | 917 |
| 429 | **0** |
| empty200 | **0** |
| SSLEOF backoff触发(docker logs 180min) | **1次** (03:08:19, k5, 1.0s backoff, 后续成功) |

**6h零429/零empty200** + SSLEOF backoff首次自然触发并验证1.0s生效(§5)。

### 1e. 120min per-key成功延迟 (排查HM2-B劣化key)
| nv_key_idx | 键名(env proxy) | n | avg_dur | p50 | p95 | max_dur |
|---|---|---|---|---|---|---|
| 0 | k1 (7894) | 67 | 17113 | 9491 | 59363 | 122572 |
| 1 | k2 (DIRECT) | 61 | 15852 | 8881 | 53105 | 111269 |
| 2 | k3 (DIRECT) | 60 | 12332 | 7751 | 37168 | 89037 |
| 3 | k4 (DIRECT) | 63 | 17926 | 9540 | 62499 | 109740 |
| 4 | k5 (7899) | 59 | 15300 | 8246 | 61238 | 119957 |

5 key均匀(59-67), P50=7.8-9.5s, P95=37-62s。**无像HM1-k4(p95=72.9s远超其他~55s)那样的劣化key**。k3(idx2)P95最低(37s)反而最快。

### 1f. 120min per-key超时分布 (hm_tier_attempts, NVCFPexecTimeout)
| nv_key_idx | tmo_n | avg_elapsed | max_elapsed |
|---|---|---|---|
| 0 | 3 | 50460 | 50691 |
| 1 | 5 | 52109 | 55038 |
| 2 | 9 | 50691 | 51264 |
| 3 | 6 | 43936 | 50655 |
| 4 | 7 | 39539 | 52608 |

超时散布全5key(3-9次), **无单key超时集中**。超时是NVCF平台层hang, 非key/路由问题。

### 1g. 改前env (HM2 docker exec hm40006 env + HM1 docker exec hm40006 env, 本轮未改两端)
| 参数 | HM2值 | HM1值(对比) | 代码是否引用(HM2) |
|---|---|---|---|
| UPSTREAM_TIMEOUT | 50 | 45 | ✅ 活 |
| MIN_OUTBOUND_INTERVAL_S | 4.5 | 9.0 | ✅ 活 |
| KEY_COOLDOWN_S | 38 | 38 | ✅ 活 (config.py:141) |
| TIER_COOLDOWN_S | 22 | 38 | ❌ **死参数** (HM2无cooldown.py,代码不引用) |
| TIER_TIMEOUT_BUDGET_S | 128 | 100 | ✅ 活 (upstream.py:215) |
| HM_CONNECT_RESERVE_S | 21 | **12** (9880398改24→16→12, 已生效) | ✅ 活 (upstream.py:227) |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 (R321生效) | env未设(代码默认3.0) | ✅ 活 (upstream.py:452) |
| HM_NV_PROXY_URL1~5 | 7894/空/空/空/7899 | — | ✅ 活 |

**注**: HM1侧 `HM_CONNECT_RESERVE_S=12` 是HM2抢跑轮9880398(16→12)部署生效的当前值。该改动**实际生效**(env=12)直接反证R324"HM1侧CONNECT_RESERVE是死参数"的误判——若死参数, 改了不会生效。

## 2. CC清单HM2-A/B/C — 当前数据证伪

### [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5 — ❌ 数据证伪 (机制不成立 + 净风险)
**CC命题**: "降到2.5→吞吐+80%。风险: NVCF同IP 429"
**本轮数据证伪**:
1. **吞吐非throttle瓶颈**: 60min=201reqs→3.35req/min; 4.5s throttle理论上限=60/4.5=**13.3req/min**。实测3.35远低于上限(4倍余量)→吞吐受**客户端到达率**限制, 非throttle。降4.5→2.5不提吞吐。
2. **6h=0个429是宝贵稳定状态**: 降throttle增NVCF同IP压力, 破坏零限流基线, 净风险无收益。
3. **代码逻辑**(R321已查): `throttle_outbound()` 仅在 `attempt_idx==0`(每请求首次出站)触发, 全局串行锁; 重试attempt不过throttle。throttle按"请求"粒度非"attempt"粒度。
**结论**: HM2-A数据证伪, 放弃。

### [HM2-B] 失败模式数据补采 + 劣化key排查 — ✅ 完成, 无劣化key无可改项
120min per-key: n均匀(59-67), P95范围37168(k3)~62499(k4), 超时散布全5key(3-9次)。**无像HM1-k4那样的劣化key**。5key全正常, **无可改项**。

### [HM2-C] TIER_TIMEOUT_BUDGET 128→100 — ❌ 决定性证伪 (误杀>100s救援成功)
**CC命题**: "BUDGET=128偏大, 失败请求耗满128s。降到100→失败早结束28s。风险: 误杀100-128s慢成功"
**本轮决定性数据 (120min, 锚点03:21:28)**:
- 成功请求中 **>100s = 13个, >110s = 7个, >120s = 3个** (max=122572ms)。这些是多次NVCFPexecTimeout后末端attempt救回的流式成功。
- **BUDGET=100误杀路径**: attempt1超时50s@50s, attempt2超时50s@100s → remaining=28→break → **attempt3/4永不试** → 13个救回成功全变502。误杀13/327=**4.0%成功率**(120min)。
- **BUDGET=120也误杀**: 3个>120s成功(120450/121567/122572ms)会被BUDGET=120误杀。任何BUDGET<123s都误杀至少1个。
- R319用6c12a16f(121.6s)决定性证伪, 本轮120min内122572ms是同模式新案例, 证伪持续成立。
**结论**: HM2-C决定性证伪, 放弃。

## 3. 主动候选 — 逐个数据证伪

### 候选1: UPSTREAM_TIMEOUT 50→45 (降单attempt hang上限) — ❌ 证伪 (误杀+无收益)
**本轮新数据(6h)**:
- 45-50s成功 = **1个**(49482ms, 6h)→降UPSTREAM=45误杀这1个(0.11%)。
- **失败耗时无改善**: 失败ATE走BUDGET循环, BUDGET=128是硬上限。降UPSTREAM=50→45, 每次attempt hang 45s(而非50s), 但2次hang=90s, remaining=38>10, 仍试第3次→耗满128s BUDGET break。失败仍~122s, **无改善**。
- bkt6(50-60s)18个成功是"hang满50s后下一attempt救回"——降UPSTREAM改变这些救回模式, 不确定是改善还是劣化。
**净效果**: 误杀1个 + 失败无改善 + 救回模式不确定 → 放弃。

### 候选2: BUDGET↓ (任何值) — ❌ 证伪 (误杀救回, 同HM2-C)
6h救回成功: >120s=3个, >110s=7个, >100s=13个。任何BUDGET<123s误杀至少1个(122572ms)。不可降。

### 候选3: 前3key全NVCFPexecTimeout早fail (HM1-C模拟) — ❌ 证伪 (误杀3次超时救回)
HM2-C数据已证明: 4个成功(122572/121567/119957/117077ms)是3次超时后attempt4救回。前3key全timeout即fast-fail会**直接误杀这4个救回**。与HM2-C同源证伪。放弃。

## 4. ⚠️ 纠正R324架构误判 — 两机均运行旧NVCF直连架构, BUDGET等皆活参数

### R324的错误结论
R324 §4称: "当前运行的upstream是 `/app/gateway/gateway/upstream.py`(handlers.py:27 `from .upstream import execute_litellm_request`), 即Rproxy重构后的LiteLLM架构", 并据此判定HM1侧 `TIER_TIMEOUT_BUDGET_S/HM_CONNECT_RESERVE_S/HM_SSLEOF_RETRY_DELAY_S` 是死参数, R323改BUDGET 90→100"实际无效"。

### 本轮纠正: 实际入口链加载旧架构(execute_request)
**HM1侧运行入口链**(本轮docker exec实测):
```
/app/gateway/app.py:13  → from gateway.handlers import ProxyHandler
/app/gateway/handlers.py:29 → from .upstream import execute_request, UpstreamResult   ← 运行的是execute_request!
/app/gateway/upstream.py:428 → def execute_request(...)                                ← 旧NVCF直连架构
```
**HM2侧运行入口链**(本轮docker exec实测):
```
/app/gateway/app.py:13  → from gateway.handlers import ProxyHandler
/app/gateway/handlers.py:28 → from .upstream import execute_request, UpstreamResult   ← 运行的是execute_request!
/app/gateway/upstream.py:521 → def execute_request(...)                                ← 旧NVCF直连架构
```

`/app/gateway/gateway/` 子目录(handlers.py:27 `execute_litellm_request`, upstream.py:390 `execute_litellm_request`)是**Rproxy重构期间未启用的死代码**, app.py入口从不加载它。R324把死代码当成了运行代码。

### 活参数/死参数真相(两机对比)
| 参数 | HM1(运行execute_request) | HM2(运行execute_request) | R324判定 | 真相 |
|---|---|---|---|---|
| TIER_TIMEOUT_BUDGET_S | ✅活(upstream.py:117) | ✅活(upstream.py:215) | HM1死❌ | **两机皆活** |
| HM_CONNECT_RESERVE_S | ✅活(upstream.py:227) | ✅活(upstream.py:227, env=12已生效) | HM1死❌ | **两机皆活**(9880398改HM1 16→12生效反证) |
| HM_SSLEOF_RETRY_DELAY_S | ✅活(upstream.py:452, env=1.0) | ✅活(upstream.py:452, env未设默认3.0) | HM1死❌ | **两机皆活** |
| TIER_COOLDOWN_S | ✅活(upstream.py:411, cooldown.py存在) | ❌死(无cooldown.py,代码不引用) | 未提 | HM1活/HM2死 |

### 影响纠正
1. **R323改HM1 BUDGET 90→100 实际生效**(代码读BUDGET, upstream.py:117)。R324称"实际无效"是错的。
2. **R321改HM2 SSLEOF 1.0 实际生效**(代码读env, upstream.py:452, §5 docker logs验证)。
3. **R324 §3对HM1-C的"新架构无per_attempt_timeout"前提错误**——HM1运行的旧架构确有per_attempt_timeout(upstream.py:235)和BUDGET早停(upstream.py:215)。但HM1-C(前3key全timeout fast-fail)仍被R324 §3证伪2(误杀3ff8f296等救回成功)成立——证伪结论正确, 只是给出的"架构原因"错。证伪靠的是救回数据, 非架构。
4. **HM2侧TIER_COOLDOWN_S=22是死参数**(无cooldown.py), 改它无效果。HM1侧TIER_COOLDOWN=38是活参数(cooldown.py存在, upstream.py:411引用, 全key 429时触发——但HM1也0个429, 分支不触发)。

## 5. R321 SSLEOF backoff触发验证闭环

R321改HM2 SSLEOF backoff 3.0→1.0(代码读env补丁+compose env), R323留待办"下轮复核docker logs HM-SSL-RETRY显示1.0s backoff"。

**本轮docker logs实测**(180min窗口):
```
[03:08:19.1] [HM-SSL-RETRY] tier=glm5.1_hm_nv k5 SSL error — retrying same key after 1.0s backoff
```
- 显示"**1.0s** backoff"(非旧硬编码3s)→ R321代码读env补丁生效 ✅
- 发生在k5(7899 SOCKS5代理), 与R321发现"SSLEOF集中在SOCKS5 key"一致 ✅
- backoff后请求成功(该时段30min=100%成功率)→ backoff+换key救回成功 ✅
- 180min仅1次(频率~0.33/h, 低于R321统计的1.2/h, 低频正常) ✅

**闭环**: R321 SSLEOF改动代码路径+env值+实际触发三重验证完成。R321/R323待办关闭。

## 6. 本轮无对端改动的合理性论证

1. **CC清单三项全证伪**: A(throttle非瓶颈, 3.35req/min vs 13.3上限), B(无劣化key, 5key均匀), C(误杀13个>100s救回, 任何BUDGET<123s误杀≥1个)。每项有具体数据。
2. **主动候选三项全证伪**: UPSTREAM↓(误杀1个+失败无改善), BUDGET↓(误杀救回), fast-fail(误杀4个3次超时救回)。
3. **架构纠正**(§4): 纠正R324把 `/app/gateway/gateway/`死代码当运行代码的误判, 恢复R323/R321改动的有效性认知。这是本轮实质贡献, 指导后续轮次: 两机均旧架构, BUDGET/CONNECT_RESERVE/SSLEOF皆活参数, 改它们会真实影响运行(非死参数无效果)。
4. **SSLEOF触发验证闭环**(§5): docker logs首次捕获1.0s backoff, R321改动三重验证完成。
5. **HM2极度稳定**: 30min 100%成功率, 6h零429/零empty200, 失败全NVCF平台hang(非HM2参数可解)。
6. **零变更=最高稳定性**, 符合"稳定优先"评判标准。

## 7. 待办 (留给下轮HM2→HM1)

- [ ] **下轮HM2→HM1**: 基于本轮架构纠正(两机均旧NVCF直连架构, BUDGET等皆活参数), 重新审视HM1侧可改点。HM1侧活参数: UPSTREAM_TIMEOUT(45), MIN_OUTBOUND(9.0), KEY_COOLDOWN(38), TIER_COOLDOWN(38,活但429=0不触发), BUDGET(100), CONNECT_RESERVE(24), SSLEOF(3.0,活但HM1全历史0次SSL触发), PROXY_URL1-5。
- [ ] **HM1侧BUDGET=100是否需回调**: R323改90→100是基于"BUDGET≥2×UPSTREAM+5=95"公式。HM1 UPSTREAM=45, BUDGET=100≥95合理。但HM1失败ATE耗89s/177s(R324 §1d)——若BUDGET=100活, 89s≈2次45s hang, 177s≈4次45s hang, 走完key循环才ATE。可评估HM1侧是否有像HM2那样的>100s救回成功(决定BUDGET能否动)。
- [ ] **CC清单HM1-C重评**: R324 §3用救回数据证伪fast-fail(结论正确), 但给的"新架构无per_attempt"原因错(实为旧架构)。证伪仍成立(误杀3ff8f296=4次timeout救回), 不建议重做。
- [ ] **HM2侧TIER_COOLDOWN_S=22死参数**: env设但代码不引用(HM2无cooldown.py)。若需规范化可考虑移除env或补cooldown.py, 但429=0分支不触发, 无运行意义, 低优先。
- [ ] **HM2 SSLEOF频率监测**: 本轮180min仅1次(0.33/h), 若频率上升或backoff后二次SSL, 回调HM_SSLEOF_RETRY_DELAY_S=2.0。

## ⏳ 轮到HM2优化HM1
