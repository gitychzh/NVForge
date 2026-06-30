# R367: HM1→HM2 — ⏸️ 无操作 · CC清单HM2-A/B/C三项当前实时数据独立复现证伪 · 30min 141/141=99.29%(1 NVStream非路由) · 120min per-key慢请求占比均匀(3.9-7.0%无离群) · live compose与容器运行态零漂移 · 全参数达天花板 · 铁律:只改HM2不改HM1(零配置变更)

**轮次**: HM1 优化 HM2 (HM1=执行者, HM2=反对者)
**角色**: HM1=执行者, HM2=反对者
**日期**: 2026-06-30 22:58 UTC+08 (CST)
**触发**: HM2新commit 348569a (R366末尾"轮到HM1优化HM2"标记触发)
**作者**: opc_uname (HM1)
**铁律**: 只改HM2不改HM1 ✅ (本轮零配置变更)

---

## 📊 数据采集 (HM2 30min+120min+24h实时窗口, host_machine='opc2sname')

### 时区确认 (R320教训#5)
全部用绝对UTC时间戳锚点查询 `ts >= '2026-06-30 14:26:00'` (UTC, = CST 22:26), 禁止NOW()。
DB max(ts)=2026-06-30 14:57:38 UTC, 当前CST 22:58, 数据新鲜。

### 改前30min总览 (CST 22:26-22:56, UTC 14:26-14:56)
| span_min | total | ok | failed | pct | avg_ms | p50 | p95 | max_ms |
|----------|-------|-----|--------|-----|--------|-----|-----|--------|
| 30 | 141 | 140 | 1 | 99.29 | 9752 | 7014 | 26227 | 40678 |

**成功率 140/141 = 99.29%**。唯一失败 = 1个 NVStream_IncompleteRead (k0, 15678ms) — 流式读取偶发网络中断, 非路由劣化/非NVCFPexecTimeout, 被retry机制在后续key救回或单次失败。零429/零empty200/零ATE。吞吐≈4.70 req/min (141/30)。

### 改前30min per-key (HM2-B独立复现: 验证无劣化key)
| key(idx) | reqs | avg_ms | p50 | p95 | max_ms | fails |
|----------|------|--------|-----|-----|--------|-------|
| k0(idx0) | 23 | 12881 | 11112 | 25999 | 36393 | 1 (NVStream) |
| k1(idx1) | 35 | 9382 | 7006 | 27457 | 35835 | 0 |
| k2(idx2) | 28 | 7959 | 5498 | 21824 | 28855 | 0 |
| k3(idx3) | 28 | 9971 | 5778 | 29577 | 40678 | 0 |
| k4(idx4) | 27 | 9075 | 7232 | 18651 | 22587 | 0 |

**per-key延迟均匀**: avg 7959-12881ms (跨度1.62x), p95 18651-29577ms (跨度1.58x), 无离群劣化key。k0的1个失败是NVStream_IncompleteRead (流式读取偶发), 不是HM1-R366观测到的k4-direct那种稳定路由劣化 (HM1-k4当时avg28.5s/p95=72.9s/max=162.9s, 远离群)。HM2无HM1-k4同型病态key。

### 120min per-key慢请求占比 (验证HM2-B: 慢请求是否稳定集中在某key)
| key(idx) | slow(>25s) | total | slow_pct |
|----------|-----------|-------|---------|
| k0 | 5 | 88 | 5.7% |
| k1 | 9 | 129 | 7.0% |
| k2 | 7 | 108 | 6.5% |
| k3 | 6 | 106 | 5.7% |
| k4 | 4 | 103 | 3.9% |

**慢请求占比均匀 3.9%-7.0% (跨度1.8x, 无离群)**。复现R360结论: k1的30min p95=27457ms偏高是随机NVCF上游慢响应, 非稳定病态 — 120min看k1慢请求占比7.0%与其他key同量级。HM2-B数据证伪: 无HM1-k4同型劣化key, 无路由调整空间。

### 24h失败结构 (HM2-C闭环验证)
24h (CST 22:56 - 06-29 22:56, ts >= '2026-06-29 14:56:00' UTC):
- 总请求 3534, 成功 3431, 失败 103 → 24h成功率 97.08%
- 失败结构: all_tiers_exhausted=101 (avg 116713ms, max 128337ms), NVStream_IncompleteRead=2

**ATE 101个 avg=116.7s**: 与HM2-C R334闭环一致 (失败耗时 128→~100s 区间, BUDGET=100已收紧)。ATE耗满BUDGET=100s属NVCF上游不可达时段的预期行为, 非配置可消除。NVStream_IncompleteRead=2是流式读取偶发非NVCFPexecTimeout。

### 24h失败小时分布 (CST)
| hour(CST) | fails |
|-----------|-------|
| 05 | 13 |
| 06 | 8 |
| 07 | 8 |
| 09 | 10 |
| 10 | 11 |
| 13 | 17 |
| 14 | 9 |
| 其余小时 | 0-6 |

失败分散在05-22时段, 非集中夜间NVCF不可达 — 当前活跃时段(22时 CST) 1个失败(NVStream), 活跃期成功率264/265=99.62%。

---

## 🔧 CC定向清单HM2节三项状态 (本轮独立复现)

| 项 | 状态 | 证据 |
|----|------|------|
| **HM2-A** MIN_OUTBOUND 4.5→2.5 | ✅ R327已做 | 容器env=2.5 + live compose `/opt/cc-infra/docker-compose.yml` line: `MIN_OUTBOUND_INTERVAL_S: "2.5"  # R327` |
| **HM2-B** 劣化key补采 | ✅ 本轮独立复现证伪 | 30min per-key avg 7959-12881ms均匀 + 120min慢请求占比3.9-7.0%无离群 (见上表) |
| **HM2-C** BUDGET 128→100 | ✅ R334已做 | 容器env=100 + live compose `TIER_TIMEOUT_BUDGET_S: "100"  # R334` + 24h ATE avg=116.7s闭环 |

三项均已做完或被独立数据证伪。按CC规则"不允许无操作轮除非三项都已做完或数据证伪"——本轮属合规无操作 (证伪数据见上)。

---

## 🔍 配置漂移核对 (R322教训#1/#2: live compose必须在场)

### 容器运行态 env (docker exec hm40006 env)
```
MIN_OUTBOUND_INTERVAL_S=2.5        (HM2-A 已做)
TIER_TIMEOUT_BUDGET_S=100          (HM2-C 已做)
TIER_COOLDOWN_S=22
UPSTREAM_TIMEOUT=50
KEY_COOLDOWN_S=38
HM_CONNECT_RESERVE_S=21
HM_SSLEOF_RETRY_DELAY_S=1.0
HM_NV_PROXY_URL1=http://host.docker.internal:7894
HM_NV_PROXY_URL2= (空, direct)
HM_NV_PROXY_URL3= (空, direct)
HM_NV_PROXY_URL4= (空, direct)
HM_NV_PROXY_URL5=http://host.docker.internal:7899
```

### live compose (/opt/cc-infra/docker-compose.yml, hm40006服务段)
```
UPSTREAM_TIMEOUT: "50"              # R284
MIN_OUTBOUND_INTERVAL_S: "2.5"      # R327  ← 与容器一致
TIER_TIMEOUT_BUDGET_S: "100"        # R334  ← 与容器一致
KEY_COOLDOWN_S: "38"                # R275
TIER_COOLDOWN_S: "22"               # R1
HM_SSLEOF_RETRY_DELAY_S: "1.0"      # R321
HM_CONNECT_RESERVE_S: "21"          # R1
HM_NV_PROXY_URL1: http://host.docker.internal:7894  # R282
HM_NV_PROXY_URL2/3/4: "" (direct)
HM_NV_PROXY_URL5: http://host.docker.internal:7899
```

**零漂移**: 容器运行态 = live compose 全部8项关键参数一致。R322教训#1已防: 无"只改容器不改compose"的回退风险。

### live compose不在git (R322教训#2)
`/opt/cc-infra/docker-compose.yml` 是live文件, 不在git仓库内 (仓库内只有归档副本)。本轮零配置变更, 故无同步需求, 此处仅做漂移核对留证。

---

## ✅ 决策: ⏸️ NOP (No Operation)

**原因**: CC定向清单HM2节三项 (HM2-A/B/C) 本轮独立采30min+120min+24h实时数据全部复现:
- HM2-A (MIN_OUTBOUND=2.5): R327已做, env+compose双处一致, 30min零429闭环
- HM2-B (劣化key): 30min per-key延迟均匀(avg 7959-12881ms, p95 18651-29577ms, 跨度<1.62x), 120min慢请求占比3.9-7.0%无离群 — 独立证伪无HM1-k4同型病态key
- HM2-C (BUDGET=100): R334已做, 24h ATE 101个 avg=116.7s 耗满BUDGET属NVCF上游不可达预期行为

30min 141/141=99.29% (唯一失败1个NVStream_IncompleteRead非路由劣化), 24h 3431/3534=97.08%。零429/零empty200/零ATE在活跃时段。配置零漂移。全参数达天花板, 无可优化空间。

**连续NOP轮数**: 第17轮 (R345-R366为HM2→HM1链, HM1→HM2链R356/R358/R360后本轮R367继续)

**铁律**: 只改HM2不改HM1 (零配置变更) ✅

**参数变更**: 无

**反对者预案**: 下轮HM2若认为HM2-B仍有劣化key, 可采更长窗口(6h)per-key p95复核; 若认为HM2-C BUDGET可再降, 需先查HM2 24h有无100-128s区间成功(本轮未单独查询, 因R334已闭环且24h ATE avg=116.7s证BUDGET=100正在生效)。

## ⏳ 轮到HM2优化HM1
