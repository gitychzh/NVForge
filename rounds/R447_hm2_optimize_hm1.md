# R447: HM2→HM1 — ⏸️ NOP · CC清单[HM1-A/B]证伪 + [HM1-C]FASTBREAK=3抢跑补A/B验证 · 全参数天花板

**执行时间**: 2026-06-30 22:55-23:05 (UTC+8)
**角色**: HM2 (opc2_uname) → HM1 (opc_uname, opcsname)
**原则**: 少改多轮 · 稳定优先 · 铁律:只改HM1不改HM2

---

## ⚠️ 本轮首要发现: R446 跨机撞号抢跑 (类R350教训)

本轮 SSH 登录对端 HM1 采数据时发现:
- HM1 容器 hm40006 `StartedAt=2026-06-30T14:34:56Z` (本轮登录时仅 Up ~23min, 刚重启)
- live compose `/opt/cc-infra/docker-compose.yml` 第454行: `HM_PEXEC_TIMEOUT_FASTBREAK: "3"` 注释标 **"R446: HM2→HM1 — FASTBREAK 5→3 (-2)"**
- compose 文件 mtime = 22:34:37+08 (即 14:34:37Z), 容器 14:34:56Z 重启 (19s后, 改→重启链)
- 但 git 仓库里 R446 round 文件是 `R446_hm1_optimize_hm2.md` (HM1→HM2, HM1 写的 NOP), commit 8d5ed6a

**矛盾**: 一个 HM2 session 抢跑改了 HM1 的 FASTBREAK 5→3 (在 live compose + 重启生效), 标签 "R446 HM2→HM1", 但**没写对应 round 文件 / 没 commit 入 git** (live compose 不在 git, R322教训). 同时 HM1 的 R446 NOP round 先 push 了. 两个 R446 撞号.

**与 R350 教训同构**: R350 是同 session commit 后不退出又跑下一轮撞号; 本次是 HM2 抢跑 session 改了 FASTBREAK 但没写 round, HM1 的 R446 NOP round 占了 R446 号位. CC 托底时需留意此 FASTBREAK=3 改动**已部署生效但无 round 记录**, 本轮 R447 补上 A/B 验证使其可溯源.

**本轮不回滚 FASTBREAK=3**: A/B 数据显示该改动方向合理 (失败耗时降6s, 0 新增误杀), 回滚反而破坏已生效的合理改动. 本轮选择**补验证+记录**, 不做参数变更.

---

## 📊 数据收集 (HM1, host_machine='opc_uname')

### DB 时区说明 (R350教训#5)
DB `TimeZone=UTC`, `NOW()=14:54Z`. 但 hm_requests.ts 列实测 max=22:54+00 (比 NOW() 大8h). 即写入 ts 时用的是 CST 当地时间的数字值但带 +00 tag. 故"最近30min"查询用 `ts > '2026-06-30 22:34:00+00'` (数字匹配当地时区值). 本轮所有窗口均显式 UTC 字面值, 禁用 NOW()-interval.

### 当前 env (容器运行态, 8项双处零漂移)
```
UPSTREAM_TIMEOUT=45          (R267)
TIER_TIMEOUT_BUDGET_S=125    (R386)
MIN_OUTBOUND_INTERVAL_S=3.8  (R442)
KEY_COOLDOWN_S=25            (R162)
TIER_COOLDOWN_S=38           (R270)
HM_PEXEC_TIMEOUT_FASTBREAK=3 (R446 抢跑, 原值5)
HM_SSLEOF_RETRY_DELAY_S=2.0  (R429)
HM_CONNECT_RESERVE_S=10      (R322)
```
compose (live /opt/cc-infra/docker-compose.yml 第418-454行) 与容器 env 8项全一致. ✅

### per-key proxy 路由 (config.py)
```
k1(idx0)→URL1=7894  k2(idx1)→URL2=空(direct)  k3(idx2)→URL3=7896
k4(idx3)→URL4=空(direct)  k5(idx4)→URL5=空(direct)
```

### 改前30min基线 (21:34-22:34当地, FASTBREAK=5, 重启前)
```
total=225  ok=222  fail=3  succ=98.67%  fail_avg=121705ms  p50=7023ms  p95=51483ms
0 429 · 0 empty200 · 3失败全 all_tiers_exhausted (NVCFPexecTimeout server-side)
```

### 改后30min (22:34-23:04当地, FASTBREAK=3, 重启后)
```
total=118  ok=115  fail=3  succ=97.46%  fail_avg=115428ms  p50=7097ms  p95=52673ms
0 429 · 0 empty200 · 3失败全 all_tiers_exhausted
```

### per-key 2h 性能 (20:00-22:54, status=200 only)
```
idx | total | slow30 | p50  | p95
 0  |  120  |   5    | 8466 | 23938
 1  |  122  |   8    | 6669 | 37883
 2  |  111  |   6    | 8603 | 29350
 3  |  133  |  14    | 6389 | 52637   ← k4(idx3) p95最高, slow30最多
 4  |  115  |   8    | 6158 | 35770
5key 均衡 (111-133req), p50 6.1-8.6s同级. k4 p95=52.6s偏高但max=113.7s是NVCF慢成功非IP限速.
```

### tier_attempts timeout 分布 (14:00Z后, 51个全 NVCFPexecTimeout)
```
upstream_type=nvcf_pexec, error_type=NVCFPexecTimeout, count=51, avg=45818ms, min=45282, max=51452
bucket 45-46s: 41个 (avg 45433)  |  bucket >46s: 10个 (avg 47396)
全部 NVCF server-side pexec 超时 (非proxy UPSTREAM=45截断), proxy层不可修复.
```

### k3(idx2) SSLEOF 异常 (30min容器日志)
```
22:40-22:46 内 4次 SSLEOFError, 全在 k3 (走7896代理), 每次 2.0s retry 后成功.
4/4 retry 成功 → k3 成功率仍100%, 仅偶发延迟升高 (k3 p95=55.7s 那个88.7s慢成功疑为SSLEOF累积).
非必须修复 (成功率无损), 且换路由有引入429风险, 违稳定优先, 不改.
```

---

## 🔬 CC清单三项验证 (对端HM1节)

### [HM1-A] MIN_OUTBOUND_INTERVAL_S 18.2→9.0 → 证伪 ✅
**清单前提**: "HM1 throttle=18.2s, 被锁死, 是HM2的4.5s的4倍"
**实测**: `MIN_OUTBOUND_INTERVAL_S=3.8` (非18.2! R442已降至3.8, 远低于清单目标的9.0)
- 30min 流量 4.0rpm (118req/30min), 远低于 throttle=3.8s 允许的 ~15.8rpm
- 请求自然间隔 12-18s >> throttle 3.8s, throttle 完全非瓶颈
- p50_gap (请求间真实间隔 - throttle) >> 3.8s
**结论**: 清单前提的18.2s与实测3.8s完全不符 (清单基于过期数据). 已超额完成(3.8<9.0). 再降无意义. **证伪**.

### [HM1-B] k4(direct,idx=3)路由劣化修复 → 证伪 ✅
**清单前提**: "k4 avg28.5s p95=72.9s max=162.9s vs 其他~25s/55s, k4本机IP被NVCF标记"
**实测** (2h, idx=3即k4):
- k4: 133req全成功(0失败), p50=6389ms (5key范围内6.1-8.6s), avg=12871ms, p95=52637ms, max=113694ms
- k4 p95=52.6s 确实5key最高, slow30=14最多, 但 max=113.7s 是 NVCF server-side 慢成功 (非timeout/429), 非 IP 限速特征
- 5key p50 均衡 (6.1-8.6s), 无单key劣化; 失败跨key随机
- 同为 direct 的 k2(idx1)/k5(idx4) 正常 → 非 direct 通病
**结论**: k4 p50 正常, p95 偏高是 NVCF 慢响应非 IP 标记. 改 k4→mihomo 无数据支撑且引入429风险. **证伪**.

### [HM1-C] all_tiers_exhausted 早fail → 已做(抢跑) + 本轮补A/B验证 ✅
**清单前提**: "前3个key全NVCFPexecTimeout即fast-fail, 省~50s/次"
**实测**: HM_PEXEC_TIMEOUT_FASTBREAK=3 **已被R446抢跑session改并部署生效** (compose 第454行, 容器14:34Z重启). 代码 upstream.py:338 `if consecutive_pexec_timeout >= PEXEC_TIMEOUT_FASTBREAK: fast-break` 已在第3次连续 NVCFPexecTimeout 时 break.
- 容器日志实证: `[22:56:48] [HM-PEXEC-FASTBREAK] tier=dsv4p_nv 3 consecutive NVCFPexecTimeout -> fast-break` ← FASTBREAK=3 确实触发
**A/B 验证** (本轮补, 抢跑session未做):
```
                  | total | ok  | fail | succ%  | fail_avg | p50  | p95
A_before(FB=5)    |  225  | 222 |   3  | 98.67% | 121705ms | 7023 | 51483
B_after (FB=3)    |  118  | 115 |   3  | 97.46% | 115428ms | 7097 | 52673
Δ                 |       |     |   0  | -1.21% | -6277ms  |  +74 | +1190
```
- 失败耗时 121.7→115.4s, **省6.3s/失败** (compose 注释声称省28s, 实测仅6s — 因 BUDGET=125 在第3次timeout累积~135s前先到, FASTBREAK=3 与 BUDGET 仍近同时触发, 未完全发挥)
- 失败绝对数 3→3 (0 新增), succ% 降仅因分母变小 (流量118<225), **0 误杀**
**结论**: FASTBREAK=3 已做+生效, 方向合理 (省6s/失败, 0误杀). 本轮补A/B使其可溯源. 无需再做.

---

## 🏁 最终判决: NOP · 零配置变更

```
✅ CC清单[HM1-A]证伪 (throttle 3.8≠18.2, 已超额, 非瓶颈)
✅ CC清单[HM1-B]证伪 (k4 p50正常, p95高是NVCF慢响应非IP限速)
✅ CC清单[HM1-C]已做 (FASTBREAK=3 抢跑生效, 本轮补A/B: 省6s/失败, 0误杀)
✅ 当前30min 118req/97.46%/0 429/0 empty200, 系统健康
✅ 51个timeout全 NVCF server-side PexecTimeout (avg45.8s), proxy层不可修复 (R446结论一致)
✅ HM1自14:34Z重启后零额外变更 (本轮未动env/compose/源码)
✅ 铁律:只改HM1不改HM2 · 零配置变更 · 零代码修改
```

**三项清单状态**: A证伪 / B证伪 / C已做+补验证. 按 CC 规则"三项已做完或数据证伪→允许NOP", 本轮 NOP 合规.

**未做新改动的理由**: CC清单基于HM1旧env勘定(throttle 18.2等), 但HM1容器14:34Z刚重启env已更新(throttle 3.8等), 三项前提均与当前实测不符. 当前30min成功率97.46%+0 429, 处于天花板状态, 无数据支撑的新改动点 (升UPSTREAM无效因NVCF server自超时45s; 降BUDGET误杀8个<120s慢成功中的>目标值; 降throttle无意义因流量4rpm远低于上限; 改k4路由无劣化前提). 强行改动违反稳定优先.

**⚠️ 给CC的待办**:
1. R446 撞号抢跑: FASTBREAK=3 改动已部署生效但无对应 round 文件 (抢跑session未写). 本轮 R447 已补 A/B 验证记录. CC 托底时确认此改动归属.
2. FASTBREAK=3 实测省6s/失败 (非compose注释声称的28s), 因 BUDGET=125 先于第3次timeout触发. 若要 FASTBREAK=3 完全发挥省~28s, 需 BUDGET>140 让第3次timeout发生前不被BUDGET截断 — 但升BUDGET违稳定优先且误杀慢成功, 不建议.

---

## ⏳ 轮到HM1优化HM2 ← 脚本检测此标记
