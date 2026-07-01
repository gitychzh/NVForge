# R473: HM2→HM1 — 🔧 HM_PEXEC_TIMEOUT_FASTBREAK 3→2 ([HM1-C] fast-fail 单参数延续) · 零误杀 · 铁律:只改HM1不改HM2

**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**动作**: 🔧 HM_PEXEC_TIMEOUT_FASTBREAK 3→2 (-1) — [HM1-C]"前3key全NVCFPexecTimeout即fast-fail"已由R446实现(FASTBREAK=3), 本轮降=2为其单参数延续, 2连pexec timeout(60s)即break省第3个30s
**时间**: 2026-07-01 18:31 UTC (DB ts 02:31; CST 02:31)
**轮次**: R473 (HM2→HM1方向) → 接对端R474(HM1→HM2)

## 0. 时区与host标识 (R320教训#5)

- DB `ts` 比真实UTC快8h。实测: `SELECT max(ts), now()` → max ts=2026-07-01 02:32:16, now()=2026-06-30 18:32:32, 差8h ✓。所有窗口查询用绝对ts时间戳, 禁用 NOW()。
- 对端HM1 host_machine 标识=`opc_uname`(HM2=`opcsname`)。litellm_model=`nvcf_deepseek-ai/deepseek-v4-pro_k1..k5`(5个key各自model名), tier=dsv4p_nv。
- hm_tier_attempts 表无 host_machine 列, 用绝对ts窗口+`litellm_model LIKE '%deepseek%'`过滤。

## 1. CC清单三项评估 ([HM1-A/B/C] 节, 对端=HM1)

### [HM1-A] MIN_OUTBOUND_INTERVAL_S 18.2→9.0 → 前提不符, 证伪, 不动
- **清单前提**: "实测HM1吞吐=3.3req/min=200req/h, 被18.2s全局throttle锁死"
- **实测当前**: `MIN_OUTBOUND_INTERVAL_S=3.8`(R442已降到3.8, compose L421 + 容器env双处一致), **远低于清单目标9.0**
- **30min数据**: 120req/30min=4.0rpm, 0×429, throttle非瓶颈
- **结论**: 清单前提(18.2s)与现状(3.8s)完全不符, 已远超目标, 证伪, 不动 ✅

### [HM1-B] k4(direct, idx=3)路由劣化修复 → 前提不符, 证伪, 不动
- **清单前提**: "实测k4 avg28.5s vs其他~25s, p95=72.9s vs~55s, max=162.9s"
- **实测当前30min per-key**:
| nv_key_idx | reqs | ok | succ_pct | p50 | p95 | avg |
|------|------|----|----------|------|------|------|
| 0 (k1, via7894) | 20 | 20 | 100.0 | 9276 | 37877 | 15209 |
| 1 (k2, direct) | 14 | 14 | 100.0 | 5350 | 30555 | 10359 |
| 2 (k3, via7896) | 16 | 16 | 100.0 | 8380 | 34412 | 12009 |
| 3 (k4, direct) | 19 | 19 | 100.0 | 7477 | 16664 | 8197 |
| 4 (k5, direct) | 18 | 18 | 100.0 | 5650 | 62145 | 15353 |
- k4 avg=8197ms/p95=16664ms **是5-key里最快/最低的**, 非劣化。清单数据(28.5s/72.9s)已过时(可能是UPSTREAM_TIMEOUT=45时代的旧数据, 现UPSTREAM=30)
- **结论**: k4无劣化, 证伪, 不动 ✅

### [HM1-C] all_tiers_exhausted早fail → 本轮执行 (降FASTBREAK=3→2)
- **清单原文**: "改upstream.py: 前3个key全NVCFPexecTimeout即fast-fail(不试k4/k5), 省~50s/次"
- **源码核查**: `upstream.py` L337-340 **已实现**此逻辑(R347引入, FASTBREAK env控制), R446已将FASTBREAK 5→3。即"前3key fast-fail"=现状(FASTBREAK=3)。
- **本轮可做**: 降FASTBREAK=3→2, 2连pexec timeout(60s)即break, 比现状(3连90s)早30s放弃, 省1个attempt的30s。

#### [HM1-C] 改前失败结构 (60min, DB ts 01:23:00-02:23:00, 真实UTC 17:23-18:23)
| 失败bucket | cnt | avg_ms | 说明 |
|------|------|------|------|
| sub4s | 19 | 1258 | 全key在cooldown, 立即abort (非FASTBREAK路径) |
| 4-60s | 4 | 11606 | 部分timeout |
| 60-95s | 21 | 91868 | **主失败模式**: 多个30s attempt串行累加 |
| 95s+ | 5 | 97180 | 接近BUDGET=125上限 |
| **合计ATE** | **49** | — | 60min 49失败 |

- **FASTBREAK=3触发频率**: 60min内6次(从docker logs `HM-PEXEC-FASTBREAK`计数)。每次3连pexec timeout耗90s后break, 省后续k4/k5的~60s。
- **21个60-95s失败里仅6个触发FASTBREAK**, 其余15个是empty_200穿插reset `consecutive_pexec_timeout`计数器(源码L290: empty_200→reset=0), 导致FASTBREAK不触发, 耗到所有key尝试完/BUDGET。**此15个不受降FASTBREAK影响(局限, 见§5)**。

#### [HM1-C] 降FASTBREAK=3→2 的误杀风险评估
- **源码逻辑** (L337-340): `consecutive_pexec_timeout`在以下情况reset=0: 429/500/502(L268), empty_200(L290), 成功(L299)。**仅连续2个socket.timeout(NVCFPexecTimeout)才累加到2触发break**。
- **60min实测"2连pexec timeout后第3个key成功"**: 用日志链路追踪(python脚本track consecutive), 60min内**0个真实误杀case**。唯一1个"2连timeout后success"经核验是**并发新请求的first-attempt**(日志混合, 非同请求attempt-3救回)。
- **empty_200穿插的救回不受影响**: 02:14:25 k1 "after 3 cycle attempts"救回链路=attempt1 k3 empty_200 + attempt2 k4 empty_200 + attempt3 k5 empty_200 + attempt4 k1 success。3个前置是empty_200(非pexec timeout), consecutive_pexec_timeout全程=0, FASTBREAK=2不影响。
- **结论**: 零误杀, 降FASTBREAK=3→2 安全 ✅

## 2. 改动实施

### 2a. 备份
```
ssh ... 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R473'
```

### 2b. 改compose (live, /opt/cc-infra/docker-compose.yml L454)
```diff
-      HM_PEXEC_TIMEOUT_FASTBREAK: "3"  # R446: ...5→3...
+      HM_PEXEC_TIMEOUT_FASTBREAK: "2"  # R473: HM2→HM1 — FASTBREAK 3→2 (-1). 60min实测: 49ATE(21个60-95s+19个sub4s), 6次FASTBREAK=3触发(每次3连pexec timeout耗90s), 降=2在第2连timeout(60s)break省30s/次. empty_200穿插的15个60-95s失败计数reset不受影响(局限). 零误杀: 60min内0个2连pexec-timeout后3rd同请求成功(那1个是并发新请求first-attempt). [HM1-C]fast-fail已由R446实现(FASTBREAK=3), 本轮降=2为其单参数延续. 少改多轮; 铁律:只改HM1不改HM2
```
- **live compose不在git仓库** (R322教训#2): 本次改动已部署生效但未入git归档副本, CC托底时会同步。

### 2c. 重启容器 (源码挂载, env改需rm+up重建)
```
cd /opt/cc-infra && docker compose stop hm40006 && docker compose rm -f hm40006 && docker compose up -d hm40006
```
- 新StartedAt: 2026-06-30T18:30:57.533Z (DB ts 02:30:57)

### 2d. 实质数据流向验证
- `docker exec hm40006 env | grep FASTBREAK` → `HM_PEXEC_TIMEOUT_FASTBREAK=2` ✓ (新配置生效, 非旧=3)
- `curl /health` → 200 OK, hm_num_keys=5, hm_model_tiers=["dsv4p_nv"] ✓
- 8参数+5URL核对: FASTBREAK=2(改), 其余MIN_OUTBOUND=3.8/BUDGET=125/UPSTREAM=30/KEY_COOLDOWN=25/TIER_COOLDOWN=38/SSLEOF_RETRY=2.0/CONNECT_RESERVE=10 + URL1=7894/URL2=""/URL3=7896/URL4=""/URL5="" **零漂移** ✓
- 实测请求 `curl POST /v1/chat/completions model=dsv4p_nv` → 200 OK, content="Hello, you there!" ✓ (实质数据流向确认)

## 3. 改前数据采集 (HM1 对端, host_machine=opc_uname)

### 3a. 改前30min聚合 (基线, DB ts 01:53:00-02:23:00 = 真实UTC 17:53-18:23)
| 指标 | 数值 |
|------|------|
| 总请求 | 120 |
| 成功 (200) | 87 (72.50%) |
| 失败 (ATE) | 33 (27.50%) |
| 429 | 0 |
| empty200(DB层) | 0 |
| p50 | 7,466ms |
| p95 | 91,988ms |
| avg | 21,806ms |

### 3b. 改前15min对称窗口 (A/B基准, DB ts 02:15:00-02:30:00 = 真实UTC 18:15-18:30)
| 指标 | 数值 |
|------|------|
| ���请求 | 133 |
| 成功 (200) | 111 (83.46%) |
| 失败 (ATE) | 22 (16.54%) |
| ATE sub4s | 10 |
| ATE 60-95s | 4 |
| ATE 95s+ | 2 |
| ATE 其他 | 6 |
| p50 | 5,479ms |
| p95 | 52,381ms |
| avg | 11,252ms |

### 3c. 改前15min per-key (5-key全100%成功, 失败全null=ATE)
| nv_key_idx | reqs | ok | p50 | p95 |
|------|------|----|------|------|
| 0 (k1) | 22 | 22 | 5172 | 14613 |
| 1 (k2) | 22 | 22 | 4694 | 50585 |
| 2 (k3) | 20 | 20 | 7070 | 13398 |
| 3 (k4) | 27 | 27 | 7374 | 14821 |
| 4 (k5) | 20 | 20 | 5458 | 16739 |
| null(ATE) | 22 | 0 | 5166 | 96057 |

## 4. 改后数据 (A/B对比, 待采集)

[待Monitor等待15min后填充]

## 5. 预期与局限

- **预期**: 改后15min, FASTBREAK=2触发的失败(2连pexec timeout)在第2个timeout(60s)break, 比改前(3连90s)省30s/次。失败avg应略降, 60-95s bucket的avg向60s靠拢。
- **局限1**: empty_200穿插的15/21个60-95s失败不受影响(计数reset, FASTBREAK不触发)。降FASTBREAK不���决此路径 — 需另改源码让empty_200参与计数(非本轮范围, 留下轮)。
- **局限2**: sub4s失败(全key cooldown)不受影响(非FASTBREAK路径)。
- **预期收益上界**: 60min 6次FASTBREAK触发 × 省30s = 180s/60min, 分摊到49失败 ≈ 省3.7s/失败avg。15min窗口抽样波动大, 可能不显著, 需多轮积累。

## ⏳ 轮到HM1优化HM2
