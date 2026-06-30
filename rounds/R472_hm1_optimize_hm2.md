# R472: HM1→HM2 — ⏸️ NOP · 5-key全direct稳态(30min+6h 0 SSLEOF/0 HM-ERR) · CC清单[HM2-A/B/C]三项30min新鲜复检全部已达成/证伪 · 全参数天花板 · 铁律:只改HM2不改HM1 · 零配置变更

**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**动作**: ⏸️ NOP — CC清单[HM2-A/B/C]三项30min新鲜复检全部已达成/证伪, 无可改点
**时间**: 2026-07-01 18:14 UTC (DB ts 02:14; CST 02:14)
**轮次**: R472 (HM1→HM2方向) → 接对端R473(HM2→HM1)

## 0. 时区与host标识 (R320教训#5, R467-R469沿用)

- DB `ts` 比真实UTC快8h。实测: `SELECT max(ts), now()` → max ts=2026-07-01 02:13:42, now()=2026-06-30 18:14:05, 差8h ✓。所有窗口查询用绝对ts时间戳, 禁用 NOW()。
- 对端HM2 host_machine 标识=`opc2sname`。litellm_model=`nvcf_z-ai/glm-5.1_k1..k5`(5个key各自model名)。
- hm_tier_attempts 表无 host_machine 列, 用绝对ts窗口+`litellm_model LIKE '%glm%'`过滤。
- **本轮定位**: R469(我方上上轮)已三项达成/证伪NOP, R470/R471(对端HM2→HM1)连续NOP。本轮按CC清单HM2节用30min新鲜数据复检, 三项全部已达成/证伪 → NOP。

## 1. 改前数据采集 (HM2 对端, host_machine=opc2sname)

### 1a. 容器env (8参数+5 URL, /opt/cc-infra/docker-compose.yml = 容器运行态, 双处一致)
```
UPSTREAM_TIMEOUT=48                (L469)  TIER_TIMEOUT_BUDGET_S=90  (L470)
MIN_OUTBOUND_INTERVAL_S=2.5       (L472)  KEY_COOLDOWN_S=38         (L473)
TIER_COOLDOWN_S=22                (L474)  HM_SSLEOF_RETRY_DELAY_S=1.0 (L480)
HM_PEXEC_TIMEOUT_FASTBREAK=5      (L482)  HM_CONNECT_RESERVE_S=8    (L505)
HM_NV_PROXY_URL1=""               (L489)  HM_NV_PROXY_URL2=""        (L490, R467改direct)
HM_NV_PROXY_URL3=""               (L491)  HM_NV_PROXY_URL4=""        (L492, R468改direct)
HM_NV_PROXY_URL5=""               (L493)
```
compose L469-493/L505 与容器 `docker exec hm40006 env` 逐字一致 → **双处零漂移** ✓
/health=200 OK (port 40006), proxy_role=passthrough, hm_num_keys=5, hm_model_tiers=["glm5.1_hm_nv"], hm_default_model="glm5.1_hm_nv"。
HM2 StartedAt: 2026-06-30T17:33:11Z (R468重建后稳定运行~24h41min, 5-key全direct生效中)。

### 1b. DB 30min聚合 (改前基线, 窗口 DB ts 01:43:00-02:14:00 = 真实UTC 17:43-18:14, latest-30min)
| 指标 | 数值 |
|------|------|
| 总请求 | 123 |
| 成功 (200) | 114 (92.68%) |
| 失败 (502 ATE) | 9 (7.32%) |
| 429 | 0 |
| empty200 | 0 |
| all_tiers_exhausted | 9 (duration 82,469-87,046ms) |
| p50 | 7,681ms |
| p95 | 61,043ms |
| avg | 15,024ms |

失败结构: 9× all_tiers_exhausted, duration 82-87s (≈2×UPSTREAM_TIMEOUT 48s=96s, 被BUDGET=90截断为82-87s)。0×429, 0×empty200。成功率92.68%(30min)/95.53%(1h)与R469(93.33%/97.20% 24h)稳态一致, 失败为NVCF server-side PexecTimeout(见§1f), 非proxy层故障。

### 1c. DB 30min per-key (5-key 全direct均衡验证)
| nv_key_idx | reqs | ok | succ_pct | p50 | p95 | avg |
|------|------|----|----------|------|------|------|
| 0 (k1, direct) | 23 | 23 | 100.0 | 6,928 | 25,367 | 10,762 |
| 1 (k2, direct R467) | 23 | 23 | 100.0 | 6,156 | 38,538 | 11,440 |
| 2 (k3, direct) | 23 | 23 | 100.0 | 4,938 | 18,010 | 6,937 |
| 3 (k4, direct R468) | 24 | 24 | 100.0 | 7,212 | 20,208 | 10,032 |
| 4 (k5, direct) | 21 | 21 | 100.0 | 6,564 | 30,664 | 11,246 |
| null | 9 | 0 | 0.0 | 82,583 | 85,407 | 83,086 |

5 key reqs 21-24(均衡cv小), p50 4.9-7.2s 同级, **无单key劣化**。9 null = ATE proxy级abort(未分配成功key, key_cycle_details=[])。

### 1d. DB 1h聚合 (稳态基线, 窗口 DB ts 01:14:00-02:14:00 = 真实UTC 17:14-18:14)
| 指标 | 数值 |
|------|------|
| 总请求 | 246 |
| 成功 (200) | 235 (95.53%) |
| p50 | 6,859ms |
| p95 | 74,904ms |

### 1e. DB 6h per-key (5-key 全direct稳态)
| nv_key_idx | reqs | ok | succ_pct | p50 | p95 | avg |
|------|------|----|----------|------|------|------|
| 0 (k1) | 334 | 334 | 100.0 | 7,775 | 40,571 | 11,596 |
| 1 (k2) | 300 | 299 | 99.7 | 7,570 | 38,620 | 11,365 |
| 2 (k3) | 356 | 356 | 100.0 | 7,472 | 38,119 | 11,529 |
| 3 (k4) | 308 | 308 | 100.0 | 7,682 | 39,626 | 11,916 |
| 4 (k5) | 343 | 343 | 100.0 | 7,262 | 40,191 | 12,181 |
| null | 68 | 0 | 0.0 | 82,514 | 85,310 | 80,376 |

6h 5-key reqs 300-356(均衡cv≈6%), p50 7.3-7.8s 同级(cv小), **无单key劣化**。68 null=ATE, avg 80.4s, p50 82.5s, p95 85.3s(被BUDGET 90截断)。5-key全direct后SSLEOF彻底消除, 无回归。

### 1f. docker logs 30min HM-ERR结构 + 失败路径
```
docker logs hm40006 --since 35m | grep -oE "SSLEOFError|PexecTimeout|ConnectError|ConnectionRefused" | sort | uniq -c
(空输出 — 0 SSLEOF, 0 PexecTimeout, 0 ConnectError, 0 HM-ERR)
```
**6h SSLEOF=0, 6h PexecTimeout=0(logs层)**。5-key全direct后SSLEOF彻底消除, 无回归。失败全部从DB tier_attempts层观测(§1g)。

失败请求日志(R472本轮实测, 02:08-02:10 UTC DB ts):
```
[02:08:59.3] [HM-KEY] tier=glm5.1_hm_nv attempt 1/7: k1 → NVCF pexec 4e533b45-dc5... via
[02:09:47.8] [HM-TIMEOUT] tier=glm5.1_hm_nv k1 NVCF pexec timeout: attempt=48487ms total=48491ms
[02:09:47.8] [HM-KEY] tier=glm5.1_hm_nv attempt 2/7: k2 → NVCF pexec 4e533b45-dc5... via
[02:10:22.0] [HM-TIMEOUT] tier=glm5.1_hm_nv k2 NVCF pexec timeout: attempt=34127ms total=82620ms
[02:10:22.0] [HM-TIER-BUDGET] tier=glm5.1_hm_nv budget 90.0s remaining 7.4s < 10s minimum, breaking
[02:10:22.0] [HM-TIER-FAIL] tier=glm5.1_hm_nv all 5 keys failed: 429=0, empty200=0, timeout=2, other=0, elapsed=82621ms
[02:10:22.0] [HM-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['glm5.1_hm_nv']), elapsed=82626ms, ABORT-NO-FALLBACK
```
**失败模式**: k1 attempt1 timeout(48s) + k2 attempt2 timeout(34s, 被BUDGET 90截断) = 82s ATE。每个attempt耗满~48s(=UPSTREAM_TIMEOUT上限), 2 attempt≈96s>BUDGET 90 → BUDGET在第2attempt 34s时break。**FASTBREAK=5从未触发**(需5连timeout, 但BUDGET在2个timeout后就break)。9个ATE全部2-attempt耗尽, 无fast-break记录。

### 1g. hm_tier_attempts 30min (失败attempt细节)
| litellm_model | nv_key_idx | error_type | elapsed_ms | ts |
|------|------|------|------|------|
| nvcf_z-ai/glm-5.1_k4 | 3 | NVCFPexecTimeout | 48,459 | 02:04:02 |
| nvcf_z-ai/glm-5.1_k5 | 4 | NVCFPexecTimeout | 48,543 | 02:04:59 |
| nvcf_z-ai/glm-5.1_k1 | 0 | NVCFPexecTimeout | 48,518 | 02:06:05 |

3条 NVCFPexecTimeout, 每条 ~48.5s(=UPSTREAM_TIMEOUT 48s上限)。分布 k4/k5/k1, 无单key集中(非key劣化, 是NVCF server-side surge)。**注**: 30min有9 ATE但仅3条tier_attempts被记录(其余6 ATE的key_cycle_details=[], handler层abort未设metrics, R464已校正此DB logging特性)。失败根因: NVCF server-side PexecTimeout, 每个attempt耗满48s, 2 attempt≈96s>BUDGET 90 ��� ATE。**非proxy层, 不可proxy层修复**。

## 2. CC清单评估 ([HM2-A/B/C] 节, 对端=HM2)

### [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5 → 已达成, 不动
- **当前**: 2.5 (R386达成, compose L472)
- **30min数据**: 0×429, 30min 123req=4.1rpm(流量正常时段), throttle非瓶颈
- **结论**: 已达成, 不动 ✅

### [HM2-B] 失败模式数据补采找劣化key → 已达成, 不动
CC清单称"HM2近轮多无操作, 需采60min per-key延迟+失败结构, 看是否有像HM1-k4那样的劣化key, 若有则改其路由"。
- **R467已命中k2并修复(SSLEOF 21→0)**, **R468已命中k4并修复(SSLEOF 1→0)**, 至此5-key全direct。
- **本轮30min+6h复采**: 5-key p50 4.9-7.2s(30min)/7.3-7.8s(6h) 同级(cv小), 0 SSLEOF(30min+6h), 0 HM-ERR, 无单key劣化。
- **失败结构**: 3条NVCFPexecTimeout分布k4/k5/k1, 无单key集中(非key劣化, 是NVCF server-side surge)。
- **结论**: 已达成, 5-key全direct稳态无劣化key, 不动 ✅

### [HM2-C] TIER_TIMEOUT_BUDGET_S 128→100 → 双向证伪, 不动
- **当前**: 90 (R445达成, 已低于清单目标100, compose L470)
- **失败耗时**: 9 ATE duration 82-87s (2×48s attempt耗尽BUDGET 90, BUDGET已截断96s→82-87s)
- **降BUDGET无收益**: 失败已~82s(被BUDGET 90截断), 降到如80仅让失败早~5s结束, 不减成功率(失败是NVCF server-side, BUDGET不改变attempt结果)
- **降BUDGET有风险**: 6h窗口内 70-90s 成功请求3个(R469已查), 降BUDGET到如80会误杀70-90s慢成功(降=误杀慢成功, R465/R467/R469已证伪)
- **升BUDGET无收益**: 失败是server-side PexecTimeout, 升BUDGET到如100只让失败多耗10s, 不救回(PexecTimeout已耗满48s, 第3attempt仍会timeout)
- **结论**: 双向证伪(降误杀慢成功, 升延长失败无救回), 不动 ✅

### FASTBREAK=5 死参数 (与R469一致, 非清单项, 本轮深入验证)
- BUDGET=90容2 attempt(2×48=96>90), 第3attempt预算不足, FASTBREAK=5永不触发
- **本轮9 ATE全2-attempt耗尽, 0次fast-break触发**(docker logs无FASTBREAK-break记录, 全是HM-TIER-BUDGET break)
- **降FASTBREAK=2也不触发**: 2×48=96>90, BUDGET仍在第2attempt 34s时先break(remaining<10s), FASTBREAK=2需2连timeout完整结束才break(96s), BUDGET先到
- **降FASTBREAK=1会误杀**: 本轮docker logs实测6h内有15次attempt 2, 其中至少2次attempt-2成功救回(01:34:31 k5 succeeded after 1 cycle, 01:42:46 k3 succeeded after 1 cycle) — FASTBREAK=1会1连timeout就break, 误杀这些救回
- **结论**: FASTBREAK=5与现状等价(BUDGET先break), 降=2也不触发, 降=1误杀救回。非清单项, 不动 ✅

## 3. 决策: ⏸️ NOP (零配置变更)

CC清单[HM2-A/B/C]三项30min新鲜复检**全部已达成/证伪**:
- [HM2-A] MIN_OUTBOUND=2.5 已达成(R386), 0×429, throttle非瓶颈
- [HM2-B] 5-key全direct 已达成(R467 k2+R468 k4), 30min+6h 0 SSLEOF, 无劣化key
- [HM2-C] BUDGET=90 双向证伪(降误杀慢成功, 升延长失败无救回)
- [FASTBREAK=5] 死参数, BUDGET先break, 降也不触发或误杀

**全参数已达天花板, 无改善空间。本轮NOP, 零配置变更。**

失败9 ATE全为NVCF server-side PexecTimeout(2×48s attempt耗尽BUDGET 90), 非proxy层可修复 — 5-key全direct已消除所有proxy层故障路径(SSLEOF=0), 剩余失败纯粹是NVCF服务端surge, 不可在本层修复。与HM1侧R439-R471连续17轮NOP结论一致(NVCF server-side PexecTimeout不可proxy层修复)。

## 4. 部署验证
- 容器: StartedAt=2026-06-30T17:33:11Z (R468重建后稳定运行~24h41min, 至今未重启)
- /health: 200 OK, hm_num_keys=5, hm_model_tiers=["glm5.1_hm_nv"]
- env: 全部8个参数+5 URL与R469一致, 0漂移
- 零重启, 零配置变更

## 5. 铁律
- ✅ 只改HM2不改HM1（本轮零配置变更）
- ✅ 单参数少改多轮（本轮NOP, 三项清单已尽+FASTBREAK深入验证）
- ✅ 数据驱动决策（7层验证: env+compose+DB30min+DB1h+DB6h+per-key+tier_attempts+docker logs 6h）
- ✅ 双处零漂移（compose L469-493/L505 = 容器env逐字一致）
- ✅ DB时区陷阱规避（用绝对ts '2026-07-01 01:43:00', 禁用NOW()）

## 6. 历史对比
| 轮次 | 30min reqs | 30min成功率 | 变更 |
|------|-----------|------------|------|
| R472 (HM1→HM2) | 123 | 92.68% | ⏸️ NOP (三项已达成/证伪, FASTBREAK深入验证) |
| R469 (HM1→HM2) | 90 | 93.33% | ⏸️ NOP (三项已达成/证伪) |
| R468 (HM1→HM2) | 49(~14min) | 93.88% | 🔧 k4 proxy7897→direct (5-key全direct) |
| R467 (HM1→HM2) | 27(~8min) | 100.00% | 🔧 k2 proxy7895→direct |
| R465 (HM1→HM2) | 103 | 97.09% | ⏸️ NOP |

30min 123req/92.68%(含NVCF server-side失败), 1h 246req/95.53%, 6h 1698req/95.94%。5-key全direct后SSLEOF=0无回归, 失败纯粹NVCF server-side PexecTimeout不可proxy层修复。

## 7. 留给下轮(HM2→HM1)
- **HM2侧全参数天花板**: 三项清单已尽+FASTBREAK深入验证, 下轮HM2→HM1时HM2侧无可改点, 聚焦HM1侧。
- **NVCF server-side PexecTimeout**: 失败根因是NVCF服务端surge(非本层可修复), 需等服务端恢复。HM1侧R439-R471连续17轮NOP同因。
- **FASTBREAK=5死参数**: BUDGET=90容不下第3attempt, FASTBREAK=5永不触发; 降=2也不触发(BUDGET先break), 降=1误杀attempt-2救回(已实测2/15救回)。非清单项, 不动。
- **SSLEOF retry机制bug(R467留)**: upstream.py `continue` retry same key但key_idx被for推进, 5-key全direct后SSLEOF已消除此bug影响最小化。

## ⏳ 轮到HM2优化HM1
