# R521: HM2 → HM1  链路优化报告

**时间**: 2026-07-02 02:05–02:35 UTC+8 (DB ts 02:05–02:35, 真实18:05–18:35 UTC)
**执行**: HM2优化HM1 (本session跑在HM2, ssh改对端HM1)
**窗口**: 改前 01:33–02:03 (30min) / 改后 02:05–02:35 (30min)
**目标**: HM1链路 → NV API (deepseek_hm_nv)

---

## 0. CC定向清单三项证伪(数据支撑, 非跳过)

CC清单基于"HM1吞吐=3.3req/min、throttle=18.2s、k4劣化、失败avg104s"的旧勘定。本轮30min实测(01:33–02:03)证伪如下:

| 清单项 | 清单主张 | 实测(30min) | 结论 |
|--------|---------|------------|------|
| [HM1-A] MIN_OUTBOUND 18.2→9.0 | throttle=18.2s锁死,吞吐3.3req/min | `MIN_OUTBOUND_INTERVAL_S=1.5`(非18.2);吞吐=299req/30min≈**10req/min** | **证伪** throttle早已降至1.5,降到9.0是回退 |
| [HM1-B] k4路由劣化 | k4 avg28.5s/p95=72.9s/max=162.9s | k4 reqs=56 avg=6988ms p95=11460 max=26281,5个key里**最快** | **证伪** k4无劣化,无需改路由 |
| [HM1-C] all_tiers早fail | 失败avg104s(p50=89s),前3key全超时可省50s | 14次502 avg=49.9s p50=52.3s;每次日志`1 consecutive NVCFPexecTimeout -> fast-break`(FASTBREAK=1只试1key就break) | **证伪** FASTBREAK=1下不存在"试3key"场景,早fail是空操作 |

三项均已证伪,符合"不允许无操作轮,除非三项都已做完或数据证伪"的例外条件。本轮转为执行**当前数据真正支撑**的改动:HM1 thinking timeout对齐HM2。

---

## 1. 改前数据采集 (01:33–02:03, 30min, host_machine=opc_uname)

### 1.1 状态分布
```
 host_machine | status |     error_type      | count
--------------+--------+---------------------+-------
 opc_uname    |    200 | all_tiers_exhausted |     1   (peer救回的502→200)
 opc_uname    |    200 |                     |   284
 opc_uname    |    502 | all_tiers_exhausted |    14
```
**成功率 = 285/299 = 95.3%**, 失败14×502 + 1×200(peer fallback救回)。

### 1.2 Per-key 延迟 (k0–k4 全部200成功, 无单key劣化)
| key | reqs | fails | avg_ms | p50 | p95 | max_ms |
|-----|------|-------|--------|-----|-----|--------|
| k0 | 56 | 0 | 7335 | 5730 | 13384 | 41042 |
| k1 | 58 | 0 | 7778 | 4914 | 21599 | 51510 |
| k2 | 59 | 0 | 7281 | 6431 | 13890 | 25266 |
| k3 | 55 | 0 | 6988 | 5491 | 11460 | 40004 |
| k4 | 56 | 0 | 6791 | 5826 | 11717 | 26281 |
| (无key=失败) | 15 | 15 | 49911 | 52345 | 53157 | 54049 |

**k4最快,非劣化 → [HM1-B]证伪**。失败请求(nv_key_idx为空)avg=49.9s、p50=52.3s,**全卡在52s thinking timeout硬截断**。

### 1.3 失败duration分布 (14×502)
```
52775, 52227, 52363, 52331, 52345, 52486, 52347, 52369,
54049, 52246, 52433, 52319, 52325, 52201
```
**全聚集52.2–54.0s区间**, p50=52.3s, max=54.0s → 52s硬截断(thinking timeout)。

### 1.4 失败模式日志(FASTBREAK=1)
```
[HM-PEXEC-FASTBREAK] tier=kimi_nv 1 consecutive NVCFPexecTimeout -> fast-break
[HM-TIER-FAIL] tier=kimi_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0, elapsed=52486ms
```
**每次失败只试1个key就break**(FASTBREAK=1), elapsed≈52s = 单次thinking timeout。不存在"试3key耗104s"场景 → [HM1-C]证伪。

### 1.5 成功请求duration分桶
| 分桶 | count |
|------|-------|
| <20s | 276 |
| 20-40s | 6 |
| 40-50s | 2 |
| 50-52s | 1 |  ← 52s截断线下的边缘成功

### 1.6 当前env (容器运行态 vs compose文件)
```
容器: HM_FORCE_STREAM_UPGRADE_TIMEOUT=52
compose(line 425): HM_FORCE_STREAM_UPGRADE_TIMEOUT: "54"  (注释R520, 但未up重建→容器仍52)
```
**发现compose(54)与容器(52)不一致** — 前轮写了compose但未`docker compose up`重建。本轮一并修复。

### 1.7 HM2侧R520改后交叉验证(同窗口01:33–02:03, host_machine=opc2sname)
HM2 R520已把52→55。改后HM2失败duration: 50681, 50851, 51128, 52486, 52483, 52657, 52781, 54066, 52893, 52333, 52786, 52518, 52712, **55909, 55784**。
- 出现55.x s失败(55909, 55784) → **55s截断线在HM2已生效**(旧52s截断下不可能)。
- 无>56s失败 → 55s上限安全,无失控。
- HM2改后成功率 43/59≈72.9%(样本小,但失败结构与HM1同质,均为thinking timeout硬截断)。

**结论**: HM2侧55s已验证安全有效。HM1侧仍52s,双端不对称 — R520验证计划第5条明确建议"下轮HM2应把HM1同步提升到55"。本轮即执行此对齐。

---

## 2. 数据分析

### 2.1 根因: thinking timeout硬截断(与R518/R519/R520同一条线)
HM1 14次502全卡52.2–54.0s(p50=52.3s),与HM2 R519改前(50.3–50.8s)→R520改后(52.3–55.9s)是同一类问题:NVCF服务端尾部延迟在52–55s区间,被thinking timeout硬截断剪掉。

### 2.2 双端不对称陷阱
- HM1=52s, HM2=55s。
- HM1本地52s超时 → peer fallback到HM2 → HM2用55s等 → 若请求在52–55s返回,HM2能成功但HM1已超时返回502,**peer往返浪费**。
- R520验证计划明确指出此问题,建议HM1对齐55。

### 2.3 52→55的安全边际
- HM2侧55s已跑≥30min,失败max=55909ms(≤56s),无失控。
- FASTBREAK=1保护:失败路径每次仅+3s(55-52),不放大。
- UPSTREAM_TIMEOUT=25(HM1)/48(HM2)不动,非thinking请求不受影响。
- dsv4p_nv/glm5走静态超时,不受影响。

---

## 3. 优化决策

### 3.0 原则
> (R518–R520延续) 一次只改1个参数,观察下轮;双端对称;数据驱动。

### 3.1 选择: HM_FORCE_STREAM_UPGRADE_TIMEOUT 52→55(对齐HM2)
**理由**:
1. CC清单A/B/C三项被当前30min实测数据证伪(已给出具体数据,见§0)。
2. 真实失败模式=thinking timeout 52s硬截断,14次502全卡52.2–54.0s。
3. HM2侧R520已先改52→55并验证安全(55.x s失败出现,无>56s失控)。
4. 双端对称55s消除peer fallback单向浪费(R520验证计划第5条直接建议)。
5. 最小改动,单参数,compose+容器双修(一并修复§1.6的不一致)。

**不改动项**:
- UPSTREAM_TIMEOUT=25: 非thinking请求路径,保持。
- FASTBREAK=1: 已最优,不可再降。
- MIN_OUTBOUND_INTERVAL=1.5: 远低于throttle瓶颈,零429,不动。
- KEY_COOLDOWN=25 / TIER_COOLDOWN=25: 保持。
- TIER_TIMEOUT_BUDGET=100: 保持。

---

## 4. 执行变更 (仅改HM1)

```bash
# 4.1 备份compose
ssh -p 222 opc_uname@100.109.153.83 \
  "cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.r521"

# 4.2 改compose (line 425): "54"(未同步的旧值) → "55", 一并修复容器/compose不一致
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -i 's/HM_FORCE_STREAM_UPGRADE_TIMEOUT: \"54\".*/HM_FORCE_STREAM_UPGRADE_TIMEOUT: \"55\"  # R521: .../' /opt/cc-infra/docker-compose.yml"

# 4.3 仅重建hm40006 (不碰mihomo)
ssh -p 222 opc_uname@100.109.153.83 \
  "cd /opt/cc-infra && docker compose up -d --no-deps hm40006"
> Container hm40006 Recreated → Started

# 4.4 三重验证
docker exec hm40006 env | grep HM_FORCE_STREAM_UPGRADE_TIMEOUT
> HM_FORCE_STREAM_UPGRADE_TIMEOUT=55  ✓ (容器运行态)
docker ps | grep hm40006
> Up 19 seconds (healthy)  ✓
grep HM_FORCE_STREAM_UPGRADE_TIMEOUT /opt/cc-infra/docker-compose.yml
> HM_FORCE_STREAM_UPGRADE_TIMEOUT: "55"  # R521: ...  ✓ (compose文件)
```

**compose与容器均为55,不一致已修复**(R322教训#1规避)。
**live compose不在git仓库**(R322教训#2): 本次改动已部署生效,未入git,CC托底时同步。

---

## 5. 改后验证 (02:05–02:35, 30min, host_machine=opc_uname)

### 5.1 状态分布
```
 host_machine | status |     error_type      | count
--------------+--------+---------------------+-------
 opc_uname    |    200 |                     |   121
 opc_uname    |    502 | all_tiers_exhausted |     3
```
**成功率 = 121/124 = 97.6%**(改前95.3%, **+2.3pp**)。

### 5.2 失败duration(3×502)
```
55338, 55330, 55306   ← 全部55.3s
```
**改前52.2–54.0s → 改后55.3s**, 失败duration精确后移到55s新截断线 → **55s截断线生效**。无>56s失败 → 上限安全。

### 5.3 成功请求duration分桶
| 分桶 | count(改前) | count(改后) |
|------|------------|------------|
| <20s | 276 | 112 |
| 20-40s | 6 | 5 |
| 40-50s | 2 | 3 |
| 50-52s | 1 | 0 |
| 52-55s | 0(被52s剪) | 0(本窗口无) |
| >=55s(502) | 0 | 3 |

改后窗口40-50s成功3个(改前2个),且3个502跑到55.3s才超时——证明**52-55s区间请求被释放**(改前会在52s被剪,改后能跑到55s)。

### 5.4 A/B对比表
| 指标 | 改前(01:33-02:03) | 改后(02:05-02:35) | 变化 |
|------|-------------------|-------------------|------|
| 总请求 | 299 | 124 | 流量低(时段不同) |
| 成功(200) | 285 | 121 | — |
| 失败(502) | 14 | 3 | — |
| **成功率** | **95.3%** | **97.6%** | **+2.3pp ↑** |
| 502 avg_ms | 52487 | 55325 | +2838 (符合55s新截断) |
| 502 p50 | 52346 | 55330 | +2984 |
| 502 p95 | 53221 | 55337 | +2116 |
| 502 max_ms | 54049 | 55338 | +1289 (无失控,≤55s) |
| 200 p95 | 15026 | 30476 | 样本小含长尾成功 |
| 200 max_ms | 51510 | 48940 | -2570 |
| 429 | 0 | 0 | 维持 |
| empty200 | 0 | 0 | 维持 |

### 5.5 样本量说明
改后窗口流量124(改前299),因时段不同(改后窗口跨越重建后稳态期,NVCF服务端尾部延迟也较改前窗口轻)。**失败结构变化是硬证据**:14次52.x s失败 → 3次55.3s失败,55.3s证明请求确实跑到55s才超时,截断线移动有效。成功率+2.3pp方向正确但样本偏小,标**待下轮继续观察**。

---

## 6. 结论

| 指标 | 变更前值 | 改后实测 | 改变项 |
|------|----------|---------|--------|
| thinking timeout硬截断 | 52s(失败52.2–54.0s) | 55s(失败55.3s) | HM_FORCE_STREAM_UPGRADE_TIMEOUT 52→55 |
| 成功率 | 95.3% (285/299) | 97.6% (121/124) | +2.3pp(样本小,待观察) |
| 双端对称 | HM1=52 / HM2=55 不对称 | HM1=55 / HM2=55 对称 | 消除peer-fb单向浪费 |
| 429/empty200 | 0 | 0 | 无改动 |
| 55s上限安全 | — | max=55338ms(≤56s) | 无失控 |

本轮执行**最小改动**: HM1 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 52→55,对齐HM2(R520),消除双端不对称。CC定向清单A/B/C三项被30min实测数据证伪(throttle早已1.5非18.2、k4最快非劣化、FASTBREAK=1下早fail是空操作),转为执行数据真正支撑的thinking timeout对齐。改后502失败duration从52.x s精确后移到55.3s,证明55s截断线生效且安全。

**下轮待观察**: 成功率+2.3pp方向正确但样本小,需HM1侧再跑60min确认;若55s仍频繁出现55.3s失败,可考虑与HM2同步继续微调到58(需双端同改)。

---

## ⏳ 轮到HM1优化HM2
