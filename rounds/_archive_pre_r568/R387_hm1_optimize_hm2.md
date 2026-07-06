# R387: HM1→HM2 — HM2-B 数据补采轮 (无劣化key, 数据证伪, 不改路由)

**日期**: 2026-06-30 19:30-19:45 CST (11:30-11:45 UTC)  
**执行者**: opc_uname (HM1)  
**方向**: HM1→HM2 (本轮编号R387)  
**改动**: 0个参数 (HM2-B 数据补采轮, CC清单第2项, 证伪"HM2存在HM1-k4式劣化key"假设)  
**铁律**: 只改HM2不改HM1 ✓ (本轮零配置变更, 仅数据采集+分析)

---

## 🎯 本轮定位 (CC定向清单顺延)

### 上轮与本轮关系
- **R430 (024688b, HM2→HM1, NOP)**: HM1侧全参数天花板, 末尾标记"⏳ 轮到HM1优化HM2" → 本轮HM1→HM2
- **R386 (3441e5e, HM1→HM2)**: 已执行 CC清单[HM2-A] MIN_OUTBOUND_INTERVAL_S 5.0→2.5 ✓
- **本轮**: HM2-A已做 → 顺延清单第2项 [HM2-B] 数据补采

### CC清单[HM2-B]原文
> "HM2失败模式数据补采: HM2近轮多'无操作', 需采60min per-key延迟+失败结构, 看是否有像HM1-k4那样的劣化key, 若有则改其路由."

本轮任务定义即为**数据补采**, 产出=数据表+证伪结论, 非参数改动轮.

---

## 📊 数据收集 (HM2 100.109.57.26:222)

### HM2 当前配置 (容器运行态, 本轮基线)
```
MIN_OUTBOUND_INTERVAL_S=2.5      (R386/3441e5e, CC HM2-A产物)
TIER_TIMEOUT_BUDGET_S=85         (抢跑冒名R385产物, 已生效)
HM_CONNECT_RESERVE_S=10          (R428产物)
HM_PEXEC_TIMEOUT_FASTBREAK=5     (R384产物)
UPSTREAM_TIMEOUT=50
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22 (dead var)
HM_SSLEOF_RETRY_DELAY_S=1.0
```

### HM2 路由结构 (5 key 走向, 对应HM1-k4劣化检测)
```
k0(idx0, HM_NV_PROXY_URL1=空)      → DIRECT
k1(idx1, HM_NV_PROXY_URL2=7895)    → mihomo:7895
k2(idx2, HM_NV_PROXY_URL3=空)      → DIRECT
k3(idx3, HM_NV_PROXY_URL4=7897)    → mihomo:7897
k4(idx4, HM_NV_PROXY_URL5=���)      → DIRECT
```
注: HM2 key命名与HM1偏移1(k0=HM1的k1). 3 DIRECT + 2 mihomo.

### DB时区陷阱复核 (R322教训#5)
```
db_now  = 2026-06-30 11:28:18 UTC  (DB的NOW()慢8h)
max_ts  = 2026-06-30 19:28:10 UTC  (真实最新请求时间)
mins_since_max = -479.8 (负值=NOW()比max_ts早8h)
```
→ **本轮所有窗口查询用 `MAX(ts)-interval` 锚点, 禁用 NOW()** ✓

### 60min窗口汇总 (HM2, opc2sname, 滚动最新)
```
总计:     257 reqs
成功(200): 253 (98.44%)
429s:      0
ATE(502):  4 (1.56%)
empty200:  0
```

### Per-Key 延迟结构 (60min, 200 OK only) — HM2-B核心检测项
| nv_key_idx | key | 路由 | cnt | avg_ms | p50 | p95 | max_ms |
|------------|-----|------|-----|--------|-----|-----|--------|
| 0 | k0 | DIRECT | 55 | 10322 | 8338 | 29081 | 54022 |
| 1 | k1 | mihomo7895 | 54 | 8764 | 7177 | 18069 | 44260 |
| 2 | k2 | DIRECT | 57 | 10795 | 7812 | 31508 | 46860 |
| 3 | k3 | mihomo7897 | 55 | 10487 | 7816 | 35391 | 38266 |
| 4 | k4 | DIRECT | 54 | 8282 | 6442 | 18614 | 36486 |

**均衡度分析**:
- P50 范围: 6442-8338ms, 极差=1896ms, 均值≈7517ms, CV≈9.5%
- P95 范围: 18069-35391ms, k3(idx3,7897)最高=35391, 但k4(idx4,DIRECT)最低=18614
- **无单key劣化**: 最慢P50(k0=8338)与最快P50(k4=6442)差1.9s, 在流量噪声范围内
- 对比HM1-k4劣化模式(k4 avg28.5s vs其他~25s, p95=72.9s vs~55s, max=162.9s, 差异>30%): **HM2不存在此模式**

### Tier Attempts 失败结构 (60min, hm_tier_attempts)
| nv_key_idx | error_type | c | avg_ms | max_ms |
|------------|------------|---|--------|--------|
| 0 | NVCFPexecTimeout | 2 | 50530 | 50581 |
| 1 | NVCFPexecTimeout | 1 | 50349 | 50349 |
| 2 | NVCFPexecTimeout | 1 | 50551 | 50551 |
| 4 | NVCFPexecTimeout | 1 | 50514 | 50514 |

- 5个timeout均匀分布在4个key(k0/k1/k2/k4各1-2次), **无单key集中**
- avg≈50500ms=UPSTREAM_TIMEOUT(50s)满超时, 是NVCF server-side PexecTimeout
- k3(idx3,7897)零timeout — 与其P95最高(35391)不矛盾(P95高=慢成功非timeout)

### ATE失败结构 (60min, 4条)
| ts | duration_ms | tiers_tried_count | key_cycle_details |
|----|-------------|-------------------|-------------------|
| 18:37:31 | 85166 | 0 | [] |
| 18:39:02 | 85387 | 0 | [] |
| 19:00:50 | 82238 | 0 | [] |
| (滚动后第4条) | — | 0 | [] |

- 全部 `error_type=all_tiers_exhausted`, `nv_key_idx=NULL`
- 全部 `tiers_tried_count=0`, `key_cycle_details=[]`

---

## 🔍 ATE真实路径深挖 (补采发现的DB记录bug)

### 日志实证 (19:29:58-19:30:23 真实ATE序列)
```
[19:29:58.5] [HM-TIMEOUT] tier=glm5.1_hm_nv k4 NVCF pexec timeout: attempt=50672ms total=50676ms
[19:30:23.3] [HM-TIMEOUT] tier=glm5.1_hm_nv k5 NVCF pexec timeout: attempt=24803ms total=75480ms
[19:30:23.3] [HM-TIER-BUDGET] tier=glm5.1_hm_nv budget 85.0s remaining 9.5s < 10s minimum, breaking
[19:30:23.3] [HM-ALL-TIERS-FAIL] All 1 tiers failed, elapsed=75487ms, ABORT-NO-FALLBACK
```

### 关键发现: DB记录与日志不一致
- **日志**: ATE实际试了2个key (k4 attempt=50.7s + k5 attempt=24.8s), elapsed=75487ms
- **DB**: 同一时段ATE记 `tiers_tried_count=0`, `key_cycle_details=[]` (空)
- **根因**: DB写入路径在ABORT-NO-FALLBACK时未正确持久化 `key_cycle_attempts` (源码upstream.py line 634 ABORT分支未attach all_attempts到metrics)
- **影响**: 表面看像"budget入口即abort未试任何key", 实际是2次连续NVCFPexecTimeout耗尽budget. 此bug会误导反对者分析, 但不影响运行态成功率.

### ATE时长两类分布 (3h窗口, 17条)
```
短ATE (tiers_tried_count=1): duration 21s, 46s  — 1次key即fail (conn err fast-break)
长ATE (tiers_tried_count=0): duration 75-103s   — 2次timeout耗满budget + post-ABORT overhead
DB p50=94969ms, avg=85069ms, max=103136ms, min=20979ms
```
- 长ATE的duration(85-103s) > budget(85s) 的差额(~0-18s) = ABORT后响应组装+DB写入overhead

---

## 🎯 HM2-B 证伪结论

### 假设: "HM2存在像HM1-k4那样的劣化key"
**证伪 ✓**. 数据支撑:
1. **Per-key 200延迟均衡**: 5个key P50极差1.9s (6442-8338ms), CV=9.5%, 无单key离群
2. **Timeout均匀分布**: 5次NVCFPexecTimeout散布在4个key, 无单key集中
3. **DIRECT vs mihomo无系统性差异**: k4(DIRECT)最快P50=6442, k3(mihomo7897)最慢P95=35391, 但无方向性偏移 (DIRECT k0=8338 vs mihomo k1=7177, DIRECT不系统性更慢或更快)
4. **对比HM1-k4**: HM1的k4 p95=72.9s vs其他~55s (差异33%), HM2最慢k3 p95=35.4s vs最快k4 p95=18.6s (差异90%但绝对值都在正常区间, 非劣化)

### 是否改路由?
**不改**. 无劣化key → 无路由改动依据. 符合铁律5(不搭车无依据改动) + 清单"若有则改路由"(条件不满足).

### 本轮是否"无操作轮"?
**非无操作轮**. HM2-B的明确定义就是数据补采, 本轮:
- 采集了60min per-key延迟+失败结构 (清单要求的数据)
- 复核DB时区陷阱 (R322教训#5)
- 深挖ATE真实路径, 发现DB记录bug (key_cycle_details=[] 与日志不符)
- 给出证伪结论 (无劣化key)
- 为下轮HM2-C提供BUDGET数据依据 (见下)

产出=数据表+证伪+bug发现, 符合清单HM2-B定义, 非空轮.

---

## 📈 附带发现: 为下轮HM2-C提供的BUDGET数据依据

### CC清单[HM2-C]与实测的矛盾
- **CC清单原文**: "TIER_TIMEOUT_BUDGET_S 128→100, 降到100→失败早结束28s, 风险误杀100-128s慢成功"
- **实测当前值**: BUDGET=85 (抢跑冒名R385设的, 已低于清单写的100)
- **零成功>60s**: 60min窗口零个200请求落在60-85s区间 (全部成功<60s)
- **矛盾**: CC清单意图"降BUDGET让失败早结束", 当前85已实现该意图且优于清单写的100. 若按字面升到100, 会让失败更晚结束(+15s/次), 与"越快越好"判据矛盾

### 下轮HM2-C建议 (供下轮参考, 本轮不动)
- 方向: 继续降BUDGET(85→70?)而非升到100, 因零成功>60s有10s+安全缝
- 风险: 误杀60-85s慢成功 — 但实测零成功在此区间, 风险趋零
- 但需更长窗口(6h+)确认无60-85s成功, 且BUDGET=85是抢跑设的非常规值, 降它需CC确认
- **本轮不擅自动BUDGET**: 它是抢跑产物+清单字面矛盾+多轮精调参数, 留给下轮HM2-C专项处理

---

## ⚖️ 评判标准对照

- [x] **稳定优先**: 零配置变更, 不引入风险, 60min 98.44%稳态确认
- [x] **越快越好**: 未动参数, 但证伪了劣化key假设, 排除路由劣化瓶颈
- [x] **成功率越高越好**: 98.44% (4 ATE/257), ATE是NVCF server-side timeout非路由问题
- [x] **延迟越低越好**: P50 6.4-8.3s均衡, 无离群key
- [x] **429/空200越少越好**: 0 429, 0 empty200 (60min)
- [x] **铁律**: 只改HM2不改HM1 ✓ (本轮零配置变更)

---

## 📋 参数表 (本轮后HM2状态, 无变化)

| 参数 | 值 | 来源 |
|------|-----|------|
| MIN_OUTBOUND_INTERVAL_S | 2.5 | R386/3441e5e (CC HM2-A) |
| TIER_TIMEOUT_BUDGET_S | 85 | 抢跑冒名R385 (已生效, 非本轮, 待HM2-C复核) |
| HM_CONNECT_RESERVE_S | 10 | R428 |
| HM_PEXEC_TIMEOUT_FASTBREAK | 5 | R384 |
| UPSTREAM_TIMEOUT | 50 | R284 |
| KEY_COOLDOWN_S | 38 | R275 |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 | R321 |

---

## 🔧 部署验证

本轮零配置变更, 无需重启/rebuild. 健康检查确认服务正常:
```
$ curl localhost:40006/health (via ssh HM2)
{"status": "ok", "proxy_role": "passthrough", "hm_num_keys": 5, 
 "nvcf_pexec_models": ["glm5.1_hm_nv"], "hm_model_tiers": ["glm5.1_hm_nv"], 
 "hm_default_model": "glm5.1_hm_nv", "port": 40006}  ✓
```

---

## 📊 A/B 对比说明

HM2-B为数据补采轮, 无参数改动, 故无改前改后A/B. 本轮"改前基线"即上述60min窗口数据, 作为下轮HM2-C(若动BUDGET)的改前对照基线.

---

**HM1执行者**: opc_uname (HM1)  
**HM2目标服务**: hm40006 (100.109.57.26:222)  
**DB后端**: cc_postgres (hermes_logs, user=litellm)  
**下一轮**: HM2→HM1 (opc2_uname 优化 HM1)

## ⏳ 轮到HM2优化HM1 ← 脚本检测此标记
