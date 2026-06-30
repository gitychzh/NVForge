# R372: HM1→HM2 — ⏸️ NOP · CC清单HM2-A/B/C三项全已做完或证伪 · 24h per-key 5key avg12.28-12.90ms(±2.3%)零离群证伪HM2-B · DIRECT vs SOCKS5 slow_pct 3.19-4.67%无差异 · 24h 24个≥95s慢成功证伪HM2-C降BUDGET · FASTBREAK=3被24h救援数据证伪最优(eq2=11+eq3=7牺牲18救回换260s净亏) · UPSTREAM_TIMEOUT=50被123个50-100s慢成功证伪 · 24h零429 · 容器env与live compose零漂移 · 源码FASTBREAK今日活跃(12:05-12:10多次触发) · 第21轮连续NOP · 铁律:只改HM2不改HM1

**轮次**: HM1 优化 HM2 (HM1=执行者, HM2=反对者)
**角色**: HM1=执行者, HM2=反对者
**日期**: 2026-06-30 16:08 UTC+08 (CST) / 08:08 UTC
**触发**: HM2端R371末尾标记 ⏳ 轮到HM1优化HM2 (commit 8060905, HM2→HM1方向NOP)
**作者**: opc_uname (HM1)
**铁律**: 只改HM2不改HM1 ✅ (本轮零配置变更)

---

## 📊 数据采集 (HM2实时窗口, host_machine='opc2sname', 100.109.57.26)

### 容器状态
- **hm40006**: Up 3 hours (healthy), docker inspect compose源=`/opt/cc-infra/docker-compose.yml`
- **health**: `{"status":"ok","proxy_role":"passthrough","hm_num_keys":5,"hm_default_model":"glm5.1_hm_nv","port":40006}`
- **后端模型**: glm5.1_hm_nv (NVCF pexec直连, 单tier无fallback)
- **路由**: k1=SOCKS5(7894), k2/k3=DIRECT(空), k4=DIRECT(空), k5=SOCKS5(7899) — 与env HM_NV_PROXY_URL1/5非空、2/3/4空一致

### DB时区陷阱核对 (R320#5严防)
- 远端 `date -u` = 08:05 UTC, 但 `hm_requests.ts` MAX = 16:05+00 → **ts列存储CST值标UTC, 比真UTC快8h**
- 本轮所有窗口查询一律用显式 ts-clock 时间戳 `'2026-06-30 15:35:00+00'`, **禁止 NOW()-interval**

### 30min窗口 (ts 15:35→16:05, host_machine='opc2sname')
| 指标 | 值 |
|------|-----|
| 总请求 | 98 |
| 成功 (200) | 94 |
| 失败 (非200) | 4 |
| 成功率 | 95.92% |
| avg延迟 | 14691ms |
| p50延迟 | 5677ms |
| p95延迟 | 66991ms |

**失败结构**: 4个失败全为 `all_tiers_exhausted` (502), avg 90446ms (max 90594ms)。0 429, 0 SSLEOF, 0 NVStream。

### 30min per-key (ts 15:35→16:05)
| key | 请求数 | fail | avg延迟 | p95 |
|-----|--------|------|---------|------|
| k0 (SOCKS5:7894) | 19 | 0 | 6974ms | 10772ms |
| k1 (SOCKS5:7894) | 20 | 0 | 15271ms | 59035ms |
| k2 (DIRECT) | 17 | 0 | 9215ms | 26641ms |
| k3 (DIRECT) | 17 | 0 | 9158ms | 26465ms |
| k4 (SOCKS5:7899) | 21 | 0 | 15602ms | 56912ms |
| (失败req无key) | 4 | 4 | 90446ms | - |

注: 30min窗口k1/k4看似偏慢, 但下方24h窗口已证伪为随机抖动非病态(与R371一致)。

### 24h per-key (ts 06-29 16:05→06-30 16:05, 关键证伪数据)
| key | 请求数 | fail | avg延迟 | p50 | p95 | ok_avg |
|-----|--------|------|---------|------|------|--------|
| k0 (SOCKS5:7894) | 690 | 1 | 12633ms | 7816ms | 39590ms | 12633ms |
| k1 (SOCKS5:7894) | 793 | 0 | 12898ms | 7465ms | 48492ms | 12898ms |
| k2 (DIRECT) | 736 | 1 | 12277ms | 6727ms | 47151ms | 12277ms |
| k3 (DIRECT) | 734 | 0 | 12499ms | 6649ms | 46869ms | 12499ms |
| k4 (SOCKS5:7899) | 712 | 0 | 12530ms | 7619ms | 44616ms | 12530ms |

**Per-key 24h完美均衡**: 5个key的avg仅 12.28-12.90ms区间(±2.3%), p95 39.6-48.5s区间, 每key失败0-1个。**无任何离群key** → 30min中k1/k4偏高纯属随机抖动, 复核24h即回归中游。证伪HM2-B(劣化key)。

### 24h DIRECT vs SOCKS5 慢请求占比 (HM2-B路由修复预案的直接检验)
| 路由组 | key | 24h成功数 | slow(>50s)数 | slow_pct |
|--------|-----|-----------|-------------|----------|
| SOCKS5 | k0(7894) | 689 | 22 | 3.19% |
| SOCKS5 | k1(7894) | 793 | 37 | 4.67% |
| DIRECT | k2 | 735 | 30 | 4.08% |
| DIRECT | k3 | 734 | 27 | 3.68% |
| SOCKS5 | k4(7899) | 712 | 26 | 3.65% |

**DIRECT(k2/k3)与SOCKS5(k0/k1/k4)无系统性差异**: slow_pct 3.19%-4.67%区间, max-min仅1.48pp, DIRECT组的k3(3.68%)甚至比SOCKS5组的k1(4.67%)还低。R371反对者预案唯一未触动方向(把DIRECT k2/k3改SOCKS5)无数据支撑, 本轮直接用slow_pct对比证伪。

### 24h失败结构
| error_type | count | avg_ms | max_ms |
|-------------|-------|--------|--------|
| (成功,空) | 3663 | 12572 | 122572 |
| all_tiers_exhausted | 109 | 114819 | 128337 |
| NVStream_IncompleteRead | 2 | 12303 | 15678 |
| (429) | **0** | - | - |

**零429** (24h) → MIN_OUTBOUND=2.5保护充分, 降throttle不增限流已验证(R327结论坐实)。

### 24h成功延迟分桶 (HM2-C降BUDGET + UPSTREAM_TIMEOUT证伪数据)
| 区间 | <50s | 50-80s | 80-90s | 90-95s | 95-100s | ≥100s |
|------|------|--------|--------|--------|---------|-------|
| 数量 | 3521 | 103 | 13 | 2 | 5 | 19 |

- **95-100s + ≥100s = 24个成功** → 降 TIER_TIMEOUT_BUDGET_S<100 会误杀这24个慢成功。100已是天花板。
- **50-80s + 80-90s + 90-95s = 123个成功** (即50-95s区间) → 加上95-100s的5个共128个落在50-100s区间。降 UPSTREAM_TIMEOUT<50 会误杀这123-128个慢成功。50已是天花板。

### 24h NVCFPexecTimeout attempt分布 (hm_tier_attempts JOIN hm_requests)
- 107个request出现NVCFPexecTimeout (24h, 与rescued_with_timeout=107一致)
- 每-request attempt计数: **eq1=89, eq2=11, eq3=7** (ge4=0)

---

## 🔬 CC清单HM2节三项 + 衍生旋钮证伪

### [HM2-A] MIN_OUTBOUND_INTERVAL_S 2.5 → 更低?
- **状态**: R327已做 4.5→2.5
- **24h数据**: 0 429, throttle保护充分
- **结论**: 已完成, 不重做(铁律"已完成项不重做")。再降需新数据支撑且违反"少改多轮"积累原则, 当前2.5无429风险点。

### [HM2-B] 劣化key路由修复?
- **24h per-key数据**: 5 key avg 12.28-12.90ms(±2.3%), p95 39.6-48.5s, fail 0-1/key
- **DIRECT vs SOCKS5 slow_pct**: 3.19%-4.67%无系统差异, DIRECT(k3=3.68%)甚至优于SOCKS5(k1=4.67%)
- **结论**: **证伪**。无任何离群key, 30min中k1/k4偏高在24h窗口回归中游, 纯随机抖动。DIRECT与SOCKS5无路由劣化差异, 无可改路由。

### [HM2-C] TIER_TIMEOUT_BUDGET_S 100 → 更低?
- **状态**: R334已做 128→100
- **24h成功延迟分桶**: <50s=3521, 50-80s=103, 80-90s=13, 90-95s=2, **95-100s=5, ≥100s=19**
- **结论**: **证伪**。24h有24个成功请求落在95-100s+≥100s区间。降BUDGET<100会误杀这24个慢成功。100已是天花板。

### 衍生[HM2-D] HM_PEXEC_TIMEOUT_FASTBREAK 3 → 2? (严防R350撞号仅分析不改)
- **源码**: upstream.py:214 `PEXEC_TIMEOUT_FASTBREAK = int(os.environ.get('HM_PEXEC_TIMEOUT_FASTBREAK', '3'))`, env未设默认3; line 431/432消费逻辑活跃
- **今日日志实证**: hm_proxy.2026-06-30.log 12:05:33/12:07:04/12:08:36/12:10:07 多次 `[HM-PEXEC-FASTBREAK] 3 consecutive NVCFPexecTimeout -> fast-break` → 逻辑活跃且今日实际生效, 非死参
- **24h含NVCFPexecTimeout的成功请求(=被救回)分布**:
  - 含1次timeout的200: 89个
  - 含2次timeout的200: **11个** ← FASTBREAK=2会在第2次timeout时fast-break, 牺牲这11个救回
  - 含3次timeout的200: **7个** ← FASTBREAK=2会牺牲这7个救回
- **FASTBREAK=2代价**: 24h牺牲18个救回成功(11+7), 即~0.5%成功率损失
- **FASTBREAK=2收益**: 7个eq3失败请求省第3次attempt(avg~37s) = ~260s/24h 花在注定失败请求上
- **评判**: 评判标准"稳定>越快>吞吐>成功率>延迟>429少" → 牺牲18个成功换260s失败耗时 = **净亏**(成功率损失>速度收益)
- **FASTBREAK=3最优性**: 24h含≥4次timeout的200=0个 → 升到4+无效。**3是唯一最优值**。
- **结论**: **证伪**。FASTBREAK=3已达天花板, 降=净亏, 升=无效。

### 衍生[HM2-E] UPSTREAM_TIMEOUT 50 → 更低?
- **24h成功延迟分桶**: 50-80s=103, 80-90s=13, 90-95s=2, 95-100s=5 → 50-100s区间共123个成功
- **结论**: **证伪**。24h有123个成功落在50-100s区间。降UPSTREAM_TIMEOUT<50会误杀这123个慢成功。50已是天花板。

---

## 📊 Live compose vs 容器运行态漂移核对 (R320#4/R322#1严防)

容器env (docker exec hm40006 env) 与 live compose hm40006服务块 (/opt/cc-infra/docker-compose.yml, python精确解析hm40006 service block) 对比:

| 参数 | 容器env | live compose (hm40006块) | 漂移 |
|------|---------|--------------------------|------|
| UPSTREAM_TIMEOUT | 50 | "50" (line 469) | ✅零 |
| TIER_TIMEOUT_BUDGET_S | 100 | "100" (line 470) | ✅零 |
| MIN_OUTBOUND_INTERVAL_S | 2.5 | "2.5" (line 472) | ✅零 |
| KEY_COOLDOWN_S | 38 | "38" (line 473) | ✅零 |
| TIER_COOLDOWN_S | 22 | "22" (line 474) | ✅零 |
| HM_CONNECT_RESERVE_S | 21 | "21" (line 504) | ✅零 |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 | "1.0" (line 480) | ✅零 |
| HM_SSLEOF_RETRY_ENABLED | true | "true" (line 479) | ✅零 |
| HM_NV_PROXY_URL1 | http://host.docker.internal:7894 | http://host.docker.internal:7894 (line 488) | ✅零 |
| HM_NV_PROXY_URL2 | (空=DIRECT) | "" (line 489) | ✅零 |
| HM_NV_PROXY_URL3 | (空=DIRECT) | "" (line 490) | ✅零 |
| HM_NV_PROXY_URL4 | (空=DIRECT) | "" (line 491) | ✅零 |
| HM_NV_PROXY_URL5 | http://host.docker.internal:7899 | http://host.docker.internal:7899 (line 492) | ✅零 |
| HM_PEXEC_TIMEOUT_FASTBREAK | (未设→默认3) | (未设→默认3) | ✅零 |

**零漂移**: 容器运行态 = live compose 全部14项关键参数(含5个PROXY_URL)一致。无回退风险。源码FASTBREAK逻辑(line 214/431/432)经grep确认活跃, 今日日志12:05-12:10多次触发实证生效。

注: live compose文件(/opt/cc-infra/docker-compose.yml)不在git仓库(R322#2教训), 本轮零配置变更故无需入git。

---

## ✅ 决策: ⏸️ NOP (No Operation)

**原因**: CC清单HM2节三项(A/B/C)全已做完(R327/R334)或证伪(本轮24h per-key零离群+DIRECT vs SOCKS5 slow_pct无差异+BUDGET误杀24慢成功), 衍生两项旋钮FASTBREAK=3与UPSTREAM_TIMEOUT=50均被24h救援数据与成功延迟分桶证伪为天花板:
- FASTBREAK=3→2会牺牲24h内18个救回成功(含2次timeout的200有11个+含3次timeout的200有7个)换260s失败耗时, 按评判标准成功率>速度为净亏; 今日日志实证FASTBREAK=3在12:05-12:10多次触发且逻辑活跃非死参
- UPSTREAM_TIMEOUT=50→更低会误杀24h内123个50-100s慢成功
- 24h per-key 5 key avg仅±2.3%无离群, DIRECT vs SOCKS5 slow_pct 3.19-4.67%无路由差异, 无可改路由
- 24h零429, MIN_OUTBOUND=2.5保护充分
- 容器env与live compose双处零漂移(14项含PROXY_URL), 源码FASTBREAK逻辑活跃

**连续NOP轮数**: 第21轮 (HM1→HM2方向; HM2→HM1方向R346-R371连续20轮NOP)

**铁律**: 只改HM2不改HM1 (零配置变更) ✅

**参数变更**: 无

**反对者预案**: HM2若认为仍有优化空间, 须给出具体数据指向新旋钮。本轮已穷尽CC清单+FASTBREAK+UPSTREAM_TIMEOUT+per-key路由(含DIRECT vs SOCKS5直接对比)四条线, 均有24h具体数据证伪。HM2节所有env类参数(MIN_OUTBOUND=2.5/UPSTREAM_TIMEOUT=50/TIER_TIMEOUT_BUDGET=100/KEY_COOLDOWN=38/TIER_COOLDOWN=22/CONNECT_RESERVE=21/SSLEOF_RETRY_DELAY=1.0/PROXY_URL1-5)均已坐实最优点或被前轮做过。唯一理论未触是HM_NV_PROXY_URL2/3/4(空=DIRECT)改SOCKS5, 但本轮24h DIRECT(k2/k3)与SOCKS5(k0/k1/k4)的slow_pct 4.08%/3.68% vs 3.19%/4.67%/3.65%无系统差异, 改动无数据支撑且违反铁律5少改。若HM2发现某子窗口DIRECT劣化, 须先采该key 60min+数据证明(非随机抖动, 本轮30min k1偏慢被24h证伪)。

---

## ⏳ 轮到HM2优化HM1
