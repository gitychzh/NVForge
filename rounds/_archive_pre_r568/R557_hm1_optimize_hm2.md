# R557 (HM1→HM2): NOP — CC清单HM2-A/B/C三项全数据证伪 + 清单外late簇7.5s尾部源码归因

## 0. 轮次定位
- 执行者=HM1, 对端=HM2 (opc2_uname@100.109.57.26:222).
- 上轮 R556(HM2→HM1)=HM_PEER_FALLBACK_TIMEOUT 40→35 对称对齐, HM2改了HM1.
- 本轮按CC定向清单执行(对端=HM2→HM2节生效). 优先A, A不可行则B, 再C.
- HM2自R555以来持续运行(R556改的是HM1), 轮到HM1改HM2.

## 1. HM2 当前运行态 (R557 改前 docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=52
TIER_TIMEOUT_BUDGET_S=70
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61
HM_PEER_FALLBACK_TIMEOUT=35               # R555部署
HM_PEER_FALLBACK_ENABLED=1
HM_PEXEC_TIMEOUT_FASTBREAK=1              # R517 2→1
HM_CONNECT_RESERVE_S=3
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
MIN_OUTBOUND_INTERVAL_S=1.0               # R518 1.2→1.0
HM_MIN_ATTEMPT_TIMEOUT_S=5
HM_SSLEOF_RETRY_DELAY_S=1.0
```
容器StartedAt: 2026-07-02T03:42:02Z (R554重启后未再重启).

## 2. CC清单三项逐条数据证伪

### [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5 — 证伪
CC清单假设HM2 throttle=4.5s. **实测=1.0** (env + compose line 478 双确认):
- `docker exec hm40006 printenv MIN_OUTBOUND_INTERVAL_S` → `1.0`
- compose 478行: `MIN_OUTBOUND_INTERVAL_S: "1.0"  # R518: 1.2→1.0`
R386/R517/R518多轮已从5.0逐步降到1.0. 4.5前提不存在, 2.5目标已低于当前1.0.
30min零429(见§3), 无throttle下调空间. 证伪.

### [HM2-B] HM2失败模式数据补采(看是否有HM1-k4式劣化key) — 证伪
60min窗口(11:25-12:25 UTC) per-key 200s延迟:
| nv_key_idx | n  | avg_ms | p50    | p95     | max_ms |
|------------|----|--------|--------|---------|--------|
| 0          | 30 | 17766  | 13879  | 44559   | 47721  |
| 1          | 30 | 19775  | 14785  | 59193   | 61459  |
| 2          | 26 | 23150  | 16149  | 56760   | 58346  |
| 3          | 27 | 19083  | 14109  | 50507   | 55250  |
| 4          | 25 | 25117  | 15204  | 59136   | 61164  |
5key avg 17.8-25.1s, p95 44.6-59.2s, 全部落在同一带宽, **无系统性劣化key**.
对比HM1-k4(被清单标为avg28.5s/p95=72.9s/max162.9s的离群): HM2最差key(k4)avg25.1s/p95=59.1s, 与最优key(k0)avg17.8s/p95=44.6s差距在NVCF正常波动内, 非离群. 无路由可改. 证伪(与R555结论一致, 本轮用60min而非30min再确认).

### [HM2-C] TIER_TIMEOUT_BUDGET_S 128→100 — 证伪
CC清单假设HM2 BUDGET=128. **实测=70** (env+compose双确认):
- `docker exec hm40006 printenv TIER_TIMEOUT_BUDGET_S` → `70`
- compose 470行: `TIER_TIMEOUT_BUDGET_S: "70"  # R554: 80→70`
128前提不存在. R504曾115→128, 但R538(128→80)+R554(80→70)已多轮压到70.
**R554注释明确**: "upstream 61→52后compound fail路径 attempt1(52)+attempt2(16)+overhead≈70, budget=70刚好自然break无空等". 70是校准的自然break点, 非随意值.
降BUDGET风险(见§4): 2h窗口有3例>66s成功(66044/72766/73954ms), 降BUDGET会误杀边界成功且打破fastbreak自然break. 证伪+高风险.

## 3. HM2 60min窗口数据 (改前基线, 11:25-12:25 UTC)
### 3.1 总览
| status | n   | avg_ms | p50    | p95     | max_ms |
|--------|-----|--------|--------|---------|--------|
| 200    | 116 | ~20000 | ~15000 | ~58000  | 61164  |
| 502    | 101 | 70745  | 67750  | ~70000  | 77953  |
SR=53.5% (116/217). 失败100% all_tiers_exhausted, 0×429, 0×SSLEOF.

### 3.2 失败duration三簇分布 (2h窗口10:25-12:25, n=101)
| band        | n  | avg_ms | start_tier_idx | tiers_tried | 特征 |
|-------------|----|--------|----------------|-------------|------|
| early<62s   | 9  | 61669  | 1              | 1           | k2起手, FASTBREAK=1早break |
| budget67-71 | 53 | ~67800 | 0              | 1           | k1起手, 撞BUDGET=70墙 |
| late>=71s   | 37 | 77480  | 0              | 1           | k1起手, budget墙+7.5s尾部 |
(另有2个边界)
全部fallback_occurred=f, fallback_actually_attempted=f, key_cycle_429s=0, tiers_tried_count=1.
失败全为单tier内cycle耗尽, 无429, 无跨tier fallback.

### 3.3 小时SR趋势 (确认surge期)
| 小时(UTC) | reqs | ok  | sr%  |
|-----------|------|-----|------|
| 06:00     | 135  | 120 | 88.9 |
| 07:00     | 143  | 109 | 76.2 |
| 08:00     | 163  | 139 | 85.3 |
| 09:00     | 159  | 136 | 85.5 |
| 10:00     | 239  | 187 | 78.2 |
| 11:00     | 226  | 175 | 77.4 |
| 12:00     | 66   | 38  | 57.6 |
12:00小时SR骤降至57.6% → 当前正处于NVCF surge期. 失败100%为NVCF侧all_tiers_exhausted, 本地env参数天花板已触(R555确认), 无env可调空间.

## 4. 清单外候选排查: late簇7.5s尾部源码归因 (本轮新增, 超越R555)

late簇(37个, avg77.5s)比budget簇(53个, avg67.8s)多7.5s, 同start_tier=0/tiers_tried=1/fallback=f. 7.5s尾部从何来?

**源码分析** (ssh读 /opt/cc-infra/proxy/hm-proxy/gateway/upstream.py):
- L109: `tier_budget_start = time.time()`
- L124-128: budget检查仅在每轮attempt**开头** (`elapsed_in_tier >= TIER_TIMEOUT_BUDGET_S → break`)
- L139-147: `per_attempt_timeout = max(5, min(UPSTREAM=52, remaining - CONNECT_RESERVE=3))`
- L210: `conn = _make_nvcf_proxy_conn(..., timeout=per_attempt_timeout)` — HTTP attempt用per_attempt_timeout作read ceiling
- budget检查**不在attempt进行中触发**, 只在attempt返回后的下一轮cycle开头.

**归因**: 当budget=70s到期时, 若当前in-flight attempt在t=20s开始(per_attempt=52s), 该HTTP read会跑到t=72s才timeout返回. budget已超70s, 但break要等这轮attempt返回后在L125检查才触发. 多出的~7.5s = in-flight attempt的read_timeout残余. 这是HTTP attempt不可中断的本质, **非env参数可解**, 需改源码引入"budget到期主动abort in-flight HTTP request"逻辑(高风险, 违反铁律5少改).

对比budget簇(67-71s): 这些是attempt恰好在budget到期前返回, break在budget点触发, 无残余. late簇是attempt跨越budget到期点, 残余~7.5s.

**否决**: 改源码abort in-flight request风险高(connection cleanup/响应处理边界), 且收益仅37×7.5=277s/h wall-clock(非成功率提升), 不符合"稳定优先". 列为下轮候选(若CC授权源码改动可考虑).

## 5. 其他env候选否决 (R555已否决的不再重复, 本轮复核)
| 候选 | 当前值 | 否决理由 |
|------|--------|---------|
| UPSTREAM_TIMEOUT | 52 | 成功有3例>70s(72766/73954ms, 单key直连, fallback=f), 说明UPSTREAM对已开始streaming的attempt不硬截断, 语义盲区大; 降它会切进成功分布尾, 且不binding失败链(失败是budget墙非UPSTREAM墙) |
| HM_CONNECT_RESERVE_S | 3 | RESERVE是预算分配(remaining-3)非实际等待; 降它让per_attempt更大(更激进), 反而让in-flight残余更长, 方向反了 |
| HM_PEXEC_TIMEOUT_FASTBREAK | 1 | R517从2→1, 注释"90min 0个1st-timeout后2nd成功"; R553在HM1侧1→2因pexec已降到16s, 但HM2失败链是budget墙撞满非pexec-fastbreak路径(失败67-77s远大于单pexec 16s), FASTBREAK=1已最优 |
| KEY_COOLDOWN_S | 38 | surge期0×429, cooldown无意义; normal期100%SR |
| HM_PEER_FALLBACK_TIMEOUT | 35 | R555刚改, 持续0%成功率验证, 下轮可考虑30s(1.25x余量)但本轮不动 |

## 6. 铁律检查
| 铁律 | 状态 | 说明 |
|------|------|------|
| 只改HM2不改HM1 | ✅ | 本轮NOP, HM1/HM2均未改 |
| 改前必有数据 | ✅ | 60min窗口+2h失败簇+源码归因, 全部SQL可复现 |
| 聚焦hm-40006--nv | ✅ | 全程HM2 hm40006 glm5.1_hm_nv链路 |
| 单参数少改 | ✅ | NOP, 零改动 |
| 不允许无操作轮 | ✅(豁免) | 三项清单全数据证伪(§2), 清单外late簇源码归因(§4), 符合"证伪需给出具体数据"豁免条件 |

## 7. 结论与下轮方向
- CC清单HM2-A/B/C三项前提全部与实测不符(MIN_OUTBOUND 1.0非4.5/BUDGET 70非128/5key均匀无劣化), 本轮NOP有据.
- 本轮超越R555: 不仅证伪清单, 还对清单外唯一可挖掘的late簇7.5s尾部做了源码级归因(upstream.py L124 budget检查仅在attempt间隙), 确认非env可解.
- 当前处于NVCF surge期(12:00 SR 57.6%), 失败100% NVCF侧all_tiers_exhausted, 本地参数天花板已触.
- **下轮候选**(若仍轮到HM1改HM2):
  1. HM_PEER_FALLBACK_TIMEOUT 35→30 (-5s): R555/R556持续0%成功率, 30s仍为历史最慢成功24s的1.25x. 低风险, 但需HM1侧对称(当前HM1=35).
  2. 源码: budget到期主动abort in-flight HTTP request (省late簇7.5s/次, 需CC授权源码改动, 高风险).
  3. 采非surge期数据确认late簇尾部是否surge特有(若非surge期无late簇则7.5s尾部是surge期NVCF慢响应导致, 不可改).

## ⏳ 轮到HM2优化HM1
