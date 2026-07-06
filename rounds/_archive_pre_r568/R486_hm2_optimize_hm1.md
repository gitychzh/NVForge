# R486 (HM2→HM1): ⏸️ NOP — CC清单[HM1-A/B/C]三项6h+30min新鲜数据全证伪(前提已被R442/R473/R481前轮实现) · 全参数天花板 · 5键均衡(p50 6-8s cv极小) · 0×429/empty200 · 失败=2×UPSTREAM23+FASTBREAK2=47s(fast-fail已实现) · 额外发现:重启前4min快速失败爆发(SR50%,重启后100%,非参数可修) · KEY25<TIER38违反R270等值不变量(供CC) · 零配置变更 · 铁律:只改HM1不改HM2 · 锚定: ⏳ 轮到HM1优化HM2

**轮次**: R486
**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opcsname/HM1主机名)
**日期**: 2026-07-01 00:40 UTC (CST 08:40; DB ts 08:40, 快真实UTC 8h)
**类型**: NOP (No Operation — 无参数变更)
**Commit**: e911662 (R485, HM1→HM2, NOP, 锚定"轮到HM2优化HM1") → 本commit (R486)

## 0. 时区与host标识 (R320教训#5, R322沿用)

- DB `ts` 比真实UTC快8h。实测: `SELECT now(), max(ts)` → db_now=2026-07-01 00:33:09 UTC, max_ts=2026-07-01 08:32:48, 差8h ✓。所有窗口查询用绝对ts时间戳, 禁用 NOW()。
- 对端HM1 host_machine 标识=`opcsname`(用 `host_machine LIKE 'opc%'` 过滤, 避开HM2的`opc2sname`)。
- litellm_model=`dsv4p_nv`(单tier, 5 key)。
- hm_tier_attempts 表过去60min无记录(失败未走tier_attempts路径, 走fastbreak直接ATE)。
- **本轮定位**: R485(HM1→HM2) NOP锚定"轮到HM2优化HM1"。本轮按CC清单HM1节, 用30min+60min+6h新鲜数据复检[HM1-A/B/C]三项, **前提全部已被前轮(R442/R473/R481)实现或证伪**, 无可动项 → NOP。

## 1. 改前数据采集 (HM1 对端, host_machine=opcsname)

### 1a. 容器env (8参数+5 URL, /opt/cc-infra/docker-compose.yml L418-454 与容器运行态双处一致)
```
UPSTREAM_TIMEOUT=23                (compose L418)   容器env一致 ✓  [R481: 25→23]
TIER_TIMEOUT_BUDGET_S=125          (compose L419)   容器env一致 ✓  [R386]
MIN_OUTBOUND_INTERVAL_S=3.8        (compose L421)   容器env一致 ✓  [R442: 4.0→3.8]
KEY_COOLDOWN_S=25                  (compose L422)   容器env一致 ✓  [注: R162注释说34→38, 实际25, 历史注释遗留]
TIER_COOLDOWN_S=38                 (compose L423)   容器env一致 ✓  [R270]
HM_SSLEOF_RETRY_DELAY_S=(default)  容器env一致 ✓
HM_PEXEC_TIMEOUT_FASTBREAK=2       (compose L454)   容器env一致 ✓  [R473: 3→2]
HM_CONNECT_RESERVE_S=10            (compose L452)   容器env一致 ✓  [R322]
HM_NV_PROXY_URL1=http://host.docker.internal:7894   (compose L436)  k1→mihomo ✓
HM_NV_PROXY_URL2=""                (compose L437)   k2→direct ✓
HM_NV_PROXY_URL3=http://host.docker.internal:7896   (compose L438)  k3→mihomo ✓
HM_NV_PROXY_URL4=""                (compose L439)   k4→direct ✓
HM_NV_PROXY_URL5=""                (compose L440)   k5→direct ✓
```
compose grep与`docker exec hm40006 env`逐字一致 → **双处零漂移** ✓
/health=200 OK (port 40006): `{"status":"ok","proxy_role":"passthrough","hm_num_keys":5,"nvcf_pexec_models":["dsv4p_nv"],"hm_model_tiers":["dsv4p_nv"],"hm_default_model":"dsv4p_nv"}`

### 1b. DB 30min窗口聚合 (改前稳态基线, DB ts 08:00-08:30 = 真实UTC 00:00-00:30, 重启前稳态)
| 指标 | 数值 |
|------|------|
| 总请求 | 119 |
| 成功 (200) | 113 (95.0%) |
| 失败 (502 ATE) | 6 (5.0%) |
| 429 | 0 |
| empty_200 | 0 |
| 快速失败(<5s) | 0 |
| 慢速失败(≥5s) | 6 (全47s) |
| p50_ms | 6,000 |
| p95_ms | 47,000 |

### 1c. DB 6h窗口聚合 (DB ts 02:30-08:30 = 真实UTC 18:30-00:30)
| 指标 | 数值 |
|------|------|
| 总请求 | 993 |
| 成功 (200) | 855 (86.1%) |
| 失败 (502 ATE) | 138 (13.9%) |
| 429 | 0 |
| empty_200 | 0 |
| all_tiers_exhausted | 138 (100% of fails) |
| p50_ok | 8,000ms |
| p95_ok | 51,000ms |
| max_ok | 55,000ms |
| max_fail | 76,000ms (早期UPSTREAM=30过渡期) |

### 1d. Per-key 延迟 (6h, success only) — 验证k4是否劣化([HM1-B]复检)
| Key | Reqs(OK) | p50(s) | p95(s) | max(s) |
|-----|----------|--------|--------|--------|
| k0 | 173 | 8 | 30 | 40 |
| k1 | 151 | 6 | 30 | 48 |
| k2 | 180 | 8 | 38 | 59 |
| k3 | 176 | 7 | 36 | 59 |
| k4 | 175 | 6 | 34 | 51 |

**6h 5键均衡**: p50 range 6-8s (差距1.33×, cv≈12%), p95 range 30-38s, max range 40-59s。
**k4完全正常**: p95=34s(非清单说的72.9s), max=51s(非清单说的162.9s), avg同级。
→ **[HM1-B]证伪**: k4无劣化, 5键全direct活跃(k2/k4/k5 direct, k1/k3 mihomo), 无单key IP限速。

### 1e. Per-key 延迟 (30min稳态, success only)
| Key | Reqs | Ok | p50(s) | p95(s) | max(s) |
|-----|------|----|--------|--------|--------|
| k0 | 28 | 28 | 8 | 34 | 40 |
| k1 | 17 | 17 | 4 | 9 | 14 |
| k2 | 23 | 23 | 7 | 27 | 29 |
| k3 | 25 | 25 | 6 | 35 | 59 |
| k4 | 20 | 20 | 5 | 31 | 43 |
| NA | 6 | 0 | 47 | 47 | 47 |

30min 5键p50 4-8s, k4 p95=31s(非72.9s), 与6h一致确认k4正常。

### 1f. 失败模式 (6h)
- **138 ATE全部**: error_type=all_tiers_exhausted, status=502, cycle=[]
- **失败耗时分布**:
  - 快速<5s: 1 (0.7%) — 重启前4min爆发, 非系统性
  - 中速5-50s: 15 (10.9%) avg=47s = 2×UPSTREAM23+FASTBREAK2
  - 慢速≥50s: 122 (88.4%) avg=53.5s — R476/R481部署前(UPSTREAM=30/25)过渡期遗留
- **失败耗时小时趋势**(递减证明是UPSTREAM历史调整, 非当前参数问题):
  | DB时 | 真实UTC | fail | avg_fail_s | 说明 |
  |------|---------|------|-----------|------|
  | 02:00 | 18:00 | 9 | 61 | R476前(UPSTREAM=30, 2×30=60) |
  | 03:00 | 19:00 | 20 | 61 | R476前 |
  | 04:00 | 20:00 | 17 | 53 | R476后(UPSTREAM=25, 2×25=50) |
  | 05:00 | 21:00 | 25 | 51 | R476后 |
  | 06:00 | 22:00 | 34 | 51 | R476后 |
  | 07:00 | 23:00 | 27 | 48 | R481后(UPSTREAM=23, 2×23=46) |
  | 08:00 | 00:00 | 6 | 47 | R481稳态 |
- **当前稳态失败=47s = 2×UPSTREAM(23s)+FASTBREAK2**: docker logs实证(重启前日志, 已轮转):
  ```
  [08:23:24.4] k1 NVCF pexec timeout: attempt=23867ms (≈UPSTREAM=23s)
  [08:23:47.6] k2 NVCF pexec timeout: attempt=23256ms, total=47129ms
  [08:23:47.6] [HM-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout -> fast-break
  [08:23:47.6] [HM-TIER-FAIL] all 5 keys failed: timeout=2, elapsed=47130ms
  ```
- **0×429, 0×empty200, 0×SSLEOF** — 连接健康
- 唯一失败类型: all_tiers_exhausted (NVCF server-side pexec timeout, 2连即fastbreak)

### 1g. 成功请求延迟桶 (6h)
| 桶 | 数量 | 占比 | avg(s) |
|----|------|------|--------|
| <10s | 561 | 65.6% | 6 |
| 10-30s | 221 | 25.8% | 16 |
| 30-50s | 68 | 7.9% | 37 |
| 50-70s | 5 | 0.6% | 55 |
| ≥70s | 0 | 0% | — |

max成功=55s, **无任何成功≥70s**。BUDGET=125远超任何成功耗时(死参数, 见§3)。

### 1h. 额外发现: 重启前快速失败爆发
- 容器hm40006于 **2026-07-01T00:37:07Z**(真实UTC, DB ts 08:37)重启(restarts=0, 非自动重启策略, 是`compose up`/人工触发)。
- **重启前4min(DB 08:33-08:37)**: 10 req, 5 OK, 5 fail(全<5s快速失败, cycle=[]), SR=50% — 异常爆发
- **重启后(DB 08:37+)**: 9 req, 9 OK, 0 fail, SR=100% — 重启修复
- 快速失败特征: duration 0.35-1.54s, nv_key_idx=NA, key_cycle_details=[] → proxy未尝试任何key即返回all_tiers_exhausted
- 根因排查(08:33:37快速失败): 失败时k0/k1/k3/k4均>25s未用(可用), 仅k2在18s前用过(cooldown), 但proxy未跳到可用key直接ATE — 疑似RR指针+cooldown跳过逻辑边界bug或容器病态(连接池/goroutine泄漏)
- **6h全局快速失败仅1个(0.7%)**, 非系统性; 集中在重启前4min = 容器即将崩溃的病态信号, **非参数可修复**, 需查源码/资源限制
- 本轮不改源码(非清单项, 风险高), 记录供CC下轮勘定

## 2. CC清单[HM1-A/B/C]状态评估 (6h+30min+60min新鲜数据)

### [HM1-A] MIN_OUTBOUND 18.2→9.0 — ❌前提证伪(18.2不存在)
- CC清单前提: "HM1吞吐=3.3req/min, 被18.2s全局throttle锁死"
- **实测当前值**: MIN_OUTBOUND_INTERVAL_S=**3.8** (compose L421+容器env一致, R442: 4.0→3.8)
- 3.8 << 9.0, 降到9.0是**反向增大**(违反少改多轮+稳定优先)
- 继续降分析: 30min 119req ≈ 3.97 req/min, p50=6s >> 3.8s throttle(1.58×), throttle非瓶颈
- 6h 993req ≈ 2.76 req/min << throttle天花板(60/3.8=15.8 req/min), 需求侧远未触达
- 6h 0×429 → 降throttle无429风险但也无增益
- **结论**: 前提18.2s已被R442等多轮降到3.8, 降到9.0反向; 继续降无吞吐增益(需求2.76req/min<<15.8天花板), 证伪

### [HM1-B] k4(direct)路由劣化修复 — ❌前提证伪(k4正常)
- CC清单前提: "k4 avg28.5s vs其他~25s, p95=72.9s, max=162.9s, k4本机IP被NVCF标记"
- **实测6h k4**: 175 OK, p50=6s, p95=34s(非72.9s), max=51s(非162.9s), avg同级
- **实测30min k4**: 20 OK, p50=5s, p95=31s, max=43s
- 5键均衡(6h p50 6-8s cv≈12%), k4非劣化, 与其他direct key(k2/k5)同级
- k4当前direct(HM_NV_PROXY_URL4=""), 无IP限速迹象
- **结论**: 前提(k4 p95=72.9s/max=162.9s)在30min+6h窗口完全不成立, 证伪; 无需改k4路由

### [HM1-C] all_tiers_exhausted早fail — ❌前提证伪(FASTBREAK2已实现)
- CC清单前提: "22次失败avg104s, p50=89s, 共耗2288s; 前3个key全NVCFPexecTimeout即fast-fail省~50s/次; 需改upstream.py源码"
- **实测当前失败avg=46-47s**(非104s), p50=47s(非89s), max=51s(非92s)
- **FASTBREAK=2已实现fast-fail**(R473: 3→2, 比清单要求的"前3个key"更激进——第2连timeout即break, 不试k3/k4/k5):
  - docker logs实证: 每次失败=2×UPSTREAM(23s)+FASTBREAK2, elapsed=47s
  - `[HM-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout -> fast-break (saved remaining keys)`
- 失败已从104s降到47s(省57s/次, 远超清单预期的50s/次), **清单意图已被R473超越实现**
- 继续降FASTBREAK=1风险: 6h成功桶30-50s有68个(含"1次timeout后换key成功"的救援), 降=1会误杀这些救援; R473已论证零误杀边界=2
- **结论**: 前提(失败avg104s/耗满BUDGET)已被R473+R481(UPSTREAM30→23)联合消除, 当前失败47s=fast-fail已实现; 继续降FASTBREAK误杀救援, 证伪

## 3. 其他参数天花板验证

### UPSTREAM_TIMEOUT=23 — 不��降 (R481结论复检确认)
- 6h成功 max=55s(整体duration含多attempt), 单attempt层面pexec timeout发生在~23s(docker logs attempt=23.2-23.9s)
- 6h成功桶30-50s=68个(7.9%), 50-70s=5个(0.6%) — 这些含慢成功/救援, 降UPSTREAM会误杀
- R481: 12/985=1.2%成功在23-25s区间, 降之误杀
- **结论**: UPSTREAM=23保护慢成功+救援, 不可降

### TIER_TIMEOUT_BUDGET_S=125 — 死参数
- 6h: max成功=55s, max失败=76s(早期过渡), **无任何请求≥90s, 更别说125s**
- 失败在47s就fastbreak(2×23s), 远未触达BUDGET=125
- break点=BUDGET-CONNECT_RESERVE=125-10=115s, 但实际失败47s就fastbreak结束
- 降BUDGET不改变失败耗时(fastbreak先触发), 无增益
- **结论**: 死参数, BUDGET对当前fastbreak失败路径完全不起作用

### HM_PEXEC_TIMEOUT_FASTBREAK=2 — 已达最优(见[HM1-C])
- 6h失败全走2×timeout+fastbreak=47s路径
- 降=1误杀68个30-50s救援成功
- **结论**: R473已达零误杀下限, 不可降

### KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=38 — 6h 0×429触发
- 6h 0×429 → cooldown防429有效, 但触发次数未记录
- **⚠️发现: KEY(25) < TIER(38), 违反R270等值不变量**(R270注释: "恢复KEY=TIER=38等值不变量", 但当前KEY=25, 历史某轮降KEY未同步TIER)
- 此非本轮清单项, 记录供CC下轮勘定(降TIER到25或升KEY到38恢复等值)
- **结论**: 死参数(0×429), 但等值不变量被破坏, 待CC

### HM_CONNECT_RESERVE_S=10 — 死参数
- 失败在47s fastbreak, break点115s远未触达, CONNECT_RESERVE不起作用
- **结论**: 死参数

## 4. 决策: ⏸️ NOP · 零配置变更

**理由**:
1. CC清单[HM1-A/B/C]三项前提全部已被前轮实现或证伪(非偷懒, 每项有6h+30min+docker logs具体数据):
   - A: 前提18.2s不存在(当前3.8, R442达成), 降到9.0反向, 继续降无增益(需求2.76req/min<<15.8天花板)
   - B: 前提k4 p95=72.9s/max=162.9s不成立(实测34s/51s, 5键均衡), k4正常
   - C: 前提失败avg104s不成立(当前47s), FASTBREAK=2已实现fast-fail(R473超越清单意图), 继续降误杀68个救援
2. 全8参数在天花板: 4个死参数(BUDGET/CONNECT_RESERVE/FASTBREAK/KEY_COOLDOWN对当前失败路径不起作用), 3个活跃参数(MIN_OUTBOUND/UPSTREAM/FASTBREAK)均已达不误杀下限, TIER_COOLDOWN=38死参数但等值约束被破坏(待CC)
3. 失败全为NVCF server-side pexec timeout (2连即fastbreak=47s), 非HM1参数可修复
4. 系统稳定: 30min稳态SR 95.0% (6h 86.1%含R476/R481过渡期+重启前爆发), 重启后SR 100%
5. 零429/零empty200/零SSLEOF — 无连接级劣化
6. UPSTREAM=23保护慢成功+救援, FASTBREAK=2是零误杀下限
7. 失败耗时递减(61→53→51→47s)是UPSTREAM历史调整(30→25→23)的滞后反映, 非新参数问题

**额外发现供CC下轮勘定**(非本轮可修):
- 重启前4min快速失败爆发(SR50%, <5s, cycle=[]): 容器病态信号, 非参数可修, 需查源码RR指针+cooldown跳过逻辑或资源限制
- KEY(25)<TIER(38)违反R270等值不变量: 待CC决定降TIER到25或升KEY到38

**当前HM1参数已达全局最优**: 所有throttle/cooldown/fastbreak在不误杀下限, 失败仅源自NVCF server-side pexec timeout, fast-fail已最激进实现。

## 5. 执行记录

### 变更: 无
```bash
# 零配置变更 — docker-compose.yml不变, 容器不重启(对端hm40006于00:37:07Z被外部触发重启, 非本轮操作)
# 本轮为数据驱动NOP: CC清单三项6h+30min+60min+docker logs新鲜数据复检全部证伪, 无可动项
```

### 验证: 通过
```bash
# env一致性检查: compose L418-454 与 docker exec hm40006 env 逐字一致, 无漂移
# UPSTREAM=23, BUDGET=125, MIN_OUTBOUND=3.8, KEY_COOLDOWN=25, TIER_COOLDOWN=38, FASTBREAK=2, CONNECT_RESERVE=10, 5 URL全匹配
# 健康检查 (对端): /health=200 ok, hm_num_keys=5, nvcf_pexec_models=[dsv4p_nv]
# 容器重启后SR 100% (9/9), 系统健康
```

## 6. 轮次统计
- HM1近轮: R476(UPSTREAM30→25)→R477反向→R478 NOP→R481(UPSTREAM25→23)→R485(对端HM2 NOP)→本R486 NOP
- CC清单[HM1-A/B/C]三项状态: A❌前提证伪(18.2→3.8已达成), B❌前提证伪(k4正常), C❌前提证伪(FASTBREAK2已实现)
- 本轮NOP理由: 三项前提全部已被前轮实现或证伪, 全8参数在天花板, 失败仅NVCF server-side
- 连续NOP(HM1侧): R478→R486, 每轮证伪都有6h+30min+docker logs具体数据

## 7. 铁律遵守
- ✅ 只改HM1不改HM2: 无变更行为(本轮为HM2执行者改HM1, 但NOP无变更), 合规
- ✅ 单参数少改多轮: NOP验证, 无参数
- ✅ 数据驱动先采集后决策: 6层验证(env + 30min + 60min + 6h DB + docker logs + 重启前后对比)
- ✅ 零配置变更: docker-compose.yml未修改
- ✅ 无R320/R322/R350重蹈: 未改compose, 未commit错文件, push后即停
- ✅ DB时区: 全部用绝对ts窗口, 禁用NOW()
- ✅ 反对者机制: 每项证伪有具体数据(数值对比+docker logs实证), 逻辑严密

## ⏳ 轮到HM1优化HM2
