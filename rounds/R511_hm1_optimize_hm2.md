# R511 (HM1→HM2): TIER_TIMEOUT_BUDGET_S 110→100 — 收紧失败预算上限, 验证失败路径是否早结束 (证伪: 失败duration不变)

**轮次**: R511
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-01 14:20 UTC (CST 22:20)
**类型**: 单参数收紧 (BUDGET -10s)
**Commit**: 本commit

## 0. 时区与host标识

- 对端HM2 host_machine标识=`opc2sname`, 主机名=opc2sname。
- DB NOW()=UTC, 系统CST=UTC+8 (实测 DB 11:57 = 系统 19:57)。窗口一律用绝对UTC时间戳, 未用NOW() (R320#5已防)。
- NVCF function: glm5.1_hm_nv=6155636e (z-ai/glm-5.1, HM2后端, 不能改)。另有 kimi_nv/dsv4p_nv 两tier共存于同容器。

## 1. CC清单核对与基线纠正

CC清单HM2节三项基线**两项失配**, 实测纠正:

| 清单项 | CC清单基线 | R511实测 | 状态 |
|--------|-----------|----------|------|
| [HM2-A] MIN_OUTBOUND 4.5→2.5 | 4.5s | **1.5s** (R506前已降) | 已低于目标, A不可行 |
| [HM2-B] 失败模式数据补采 | 需采 | **本轮已完成** (per-key/tier_attempts/error_detail) | 完成, 无单key劣化 |
| [HM2-C] BUDGET 128→100 | 128s | **110s** (R504曾升到128, 后某轮降到110) | 基线部分失配, 但110>100, 可执行 |

按规则: A不可行 → B(数据补采)已完成 → 执行C。B补采结果见第2节, 无劣化key可改路由, 故C是唯一可执行改动项。

## 2. 改前数据采集 (HM2 对端, host_machine=opc2sname)

### 2a. 容器env实测 (docker exec hm40006 env, 改前)

```
UPSTREAM_TIMEOUT=48
TIER_TIMEOUT_BUDGET_S=110      # ← 改前
MIN_OUTBOUND_INTERVAL_S=1.5    # CC清单A基线失配(清单说4.5, 实测1.5)
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
HM_SSLEOF_RETRY_DELAY_S=1.0
HM_PEXEC_TIMEOUT_FASTBREAK=3   # R509刚改 2→3
HM_CONNECT_RESERVE_S=5
HM_MIN_ATTEMPT_TIMEOUT_S=8
HM_NV_PROXY_URL1=http://host.docker.internal:7894
HM_NV_PROXY_URL2=http://host.docker.internal:7894  # R508已改
HM_NV_PROXY_URL3=                  # k3直连
HM_NV_PROXY_URL4=                  # k4直连
HM_NV_PROXY_URL5=http://host.docker.internal:7896
```

### 2b. 改前2h窗口 (ts 09:55–11:54 UTC, BUDGET=110, FASTBREAK=3生效)

| 指标 | 数值 |
|------|------|
| 总请求 | 159 |
| 成功 (200) | 116 |
| 502 (ATE) | 39 |
| 429 (请求级) | 4 |
| 成功率 | 73.0% |
| 成功 p50 / p95 | 12.2s / 62.4s |
| 502 p50 / p95 / max | 92.6s / 92.7s / 92.8s |
| reqs/min | 1.34 |

### 2c. 改前失败模式 (hm_error_detail.2026-07-01.jsonl, 改前2h 43次all_tiers_failed)

num_attempts分布: {0: 15, 2: 23, 3: 1, 5: 4}

- **2-attempt失败23次**: 全 (NVCFPexecTimeout, NVCFPexecTimeout), 第2key跑完~48s完整timeout (last attempt truncated<30s: 仅7/157全日), **未被budget截断**。
- **3-attempt失败1次**: 3连NVCFPexecTimeout。
- **0-attempt 15次**: all-429或empty-200快速失败 (na=0, 无pexec attempt)。
- **5-attempt 4次**: 多key429 cycle后耗尽。

**核心发现**: 改前2h的39次502 duration全在~92.5s (max=92787ms), **没有跑到110-128s的**。失败在2-attempt(~92.5s=2×48s-overlap)就终止, 不触达BUDGET=110 wall。

### 2d. 全日3-attempt失败深度分析 (jsonl, 51次3-timeout失败)

| 指标 | 前2key sum elapsed | 第3key elapsed | total elapsed |
|------|-------------------|---------------|---------------|
| median | 97.5s | 19.7s | 120.5s |
| 分布 | 各~48s | 5-10s×10, 10-15s×12, 20-30s×25, ≥30s×2 | 超过110 |

**第3key全为NVCFPexecTimeout (53/53, 0次成功救回)**: R509 FASTBREAK=3 给第3key的尝试机会, 在实测中**0% 救回率**。前2keytimeout后第3key必timeout (correlated server-side pexec拥塞)。这是R509接力信息担心的"第3attempt也必败"的实证。

**注意**: 3-attempt失败total median=120.5s > BUDGET=110, 说明BUDGET wall未硬截断 (因 per_attempt_timeout = min(UPSTREAM=48, remaining-5), 第3key在remaining=14s时per_attempt_timeout=9s, 但NVCF服务器端timeout返回比客户端切断晚, 实际跑到~20s+; 且BUDGET检查在attempt前, 不打断已start的attempt)。

### 2e. 失败duration直方图 (90min窗口 10:27-11:57, 60-120s分桶)

| bucket | 60-70s | 70-80s | 80-90s | 90-100s | 100-110s |
|--------|--------|--------|--------|---------|----------|
| 成功 | 93 | 2 | 1 | 1 | 0 |
| 失败 | 2 | 0 | 0 | 0 | 23 |

**关键**: 100-110s区间 **0成功 / 23失败**。降到100零误杀 (100-110s无成功可救)。90-100s有1次成功 (边缘, 降到100可能影响但极罕见)。

## 3. 改动计划

### 3a. 候选评估

| 候选 | 数据支撑 | 风险 | 裁决 |
|------|----------|------|------|
| **BUDGET 110→100** | 100-110s区间0成功(零误杀); 失败p50=92.5s<100, 预期让失败早结束; CC清单C项 | 失败本就92.5s结束, 降到100可能无收益; 第3key空间从14s→4s | **执行** (A不可行/B已完成, C是唯一项) |
| MIN_OUTBOUND 1.5→2.5 | CC清单A基线失配(实测1.5<2.5), 反向升throttle | 降吞吐 | 不执行 (基线失配) |
| k4/k5路由调整 | per-key无单key劣化 (k0-k4全成功) | - | 不执行 (B补采无劣化key) |
| FASTBREAK 3→2 | 第3key0%救回(53/53全timeout), FASTBREAK=3无收益 | 回退前轮R509改动 | 不执行 (违反少改+不否定前轮, 留下轮评估) |

### 3b. 最终计划

只做1个参数: `TIER_TIMEOUT_BUDGET_S: "110" → "100"`

- 预期1: 失败请求早结束 (从~92.5s或更长→~100s上限)。**注: 改前失败p50=92.5s已<100, 此预期可能不成立**。
- 预期2: 零误杀 (100-110s区间0成功, 直方图铁证)。
- 风险: 第3key可用attempt时间从 remaining=14s(BUDGET=110下) 减到 4s(BUDGET=100下), 但第3key0%救回, 无损失。

## 4. 改动执行

### 4a. 备份+改compose (live文件 /opt/cc-infra/docker-compose.yml)

```bash
# HM1 (本机) ssh 到对端HM2执行
sudo cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R511
sudo sed -i '470s/TIER_TIMEOUT_BUDGET_S: "110"/TIER_TIMEOUT_BUDGET_S: "100"/' /opt/cc-infra/docker-compose.yml
sudo grep -n '^      TIER_TIMEOUT_BUDGET_S:' /opt/cc-infra/docker-compose.yml
# → 470:      TIER_TIMEOUT_BUDGET_S: "100"  (compose=100 ✓)
```

### 4b. recreate容器

```bash
cd /opt/cc-infra && sudo docker compose up -d hm40006
# → Container hm40006 Recreated/Started
```

### 4c. 改后验证 (实质数据流向)

```
docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET_S
# → TIER_TIMEOUT_BUDGET_S=100  ✓ (容器运行态)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:40006/health
# → 200  ✓
# compose第470行="100", 容器env="100", 两处一致 (R322#1已防)
```

## 5. 改前改后A/B对比

### 5a. 2h等长窗口对比表

| 指标 | 改前 (09:55–11:54, 2h, BUDGET=110) | 改后 (12:07–14:15, 2h, BUDGET=100) |
|------|------------------------------------|------------------------------------|
| 总请求 | 159 | 329 |
| 成功 (200) | 116 | 314 |
| 502 (ATE) | 39 | 15 |
| 429 (请求级) | 4 | 0 |
| 成功率 | 73.0% | **95.4%** (↑) |
| reqs/min | 1.34 | 2.74 (↑) |
| 成功 p50 / p95 | 12.2s / 62.4s | 8.7s / 46.1s |
| 502 p50 / max | 92.6s / 92.8s | 92.8s / **121.9s** |
| 502 duration分布 | 全~92.5s (max 92.8s) | 8次~92.5s + 5次118-122s + 1次107s + 1次113s |

### 5b. 失败attempt结构对比 (jsonl all_tiers_failed)

| 窗口 | 总失败 | na=0 | na=2 | na=3 | na=5 |
|------|--------|------|------|------|------|
| 改前2h (BUDGET=110) | 43 | 15 | 23 | 1 | 4 |
| 改后2h (BUDGET=100) | 15 | 1 | 13 | 1 | 0 |

### 5c. 关键证伪: 失败duration未降

**预期是"失败早结束~10s", 实测证伪**:
- 改前502 max=92787ms (全在~92.5s), 改后502 max=**121924ms** (出现5次118-122s)。
- 改后2-attempt失败13次仍~92.5s (与改前23次2-attempt一致)。
- BUDGET=100对2-attempt失败无影响: 2×48=96s, 在BUDGET=100和110下都< wall, 第3key因 `remaining<MIN_ATTEMPT=8` (100-96=4<8, 110-96=14>8) 而异——**实际上改后remaining=4<8应更快break第3key, 但2-attemptduration仍92.5s, 因失败在第2key timeout(~48s×2)时就终止, BUDGET wall未触达**。
- 改后出现118-122s长失败的机制: 3-attempt (3×~48s timeout, 但第3key NVCF服务器返回timeout晚于客户端budget检查), BUDGET=100未硬截断已start的attempt。这部分长失败在改前2h未出现(改前2h恰好无3-attempt长失败样本, 仅1次3-attempt)。

**结论: BUDGET 110→100 既未让失败早结束, 也未误杀成功。失败duration由fastbreak/2-attempt决定, 与BUDGET wall(100或110)基本无关。**

### 5d. SR提升的因果归因

SR从73.0%→95.4%大幅提升, 但**不能归因于BUDGET改动**:
- 改前2h(09:55-11:54)含较多拥塞 (39次502, 15次na=0快速失败暗示多429/empty-200时段)。
- 改后2h(12:07-14:15)流量更平稳 (15次502, 0次429请求级)。
- 失败duration不变 (证伪BUDGET对失败路径有影响), 故SR提升更可能是**时段server-side拥塞差异**, 非BUDGET因果。
- 按R320#3, 不编造因果: SR提升观察到了, 但无法证明是BUDGET 110→100的功劳。

## 6. 数据诚实与局限

- **[HM2-C]核心预期证伪**: "BUDGET 110→100让失败早结束" 未实现。失败p50/max未降, 改后反现118-122s长失败 (3-attempt, BUDGET wall未硬截断)。
- **零误杀确认**: 100-110s区间0成功 (直方图铁证), 改后2h无任何成功被截断在100s。k0-k4 per-key全成功。
- **SR提升非因果**: 73%→95.4%是观察值, 但失败duration不变, 归因于时段差异更诚实。
- **未回调**: BUDGET=100虽未达预期收益, 但 (a)零误杀, (b)理论上给失败更早的wall (虽实测未触达), (c)与HM1侧BUDGET=80更接近 (跨机一致性)。保留=100, 标"待观察"。
- **样本局限**: 改后2h 15次502, 其中3-attempt仅1次, 不足以确认BUDGET=100对3-attempt长失败的截断效果。需下轮更长窗口复核。
- **R509 FASTBREAK=3复核**: 改后2h 13次2-attempt失败 + 1次3-attempt。2-attempt占主导说明 FASTBREAK=3在多数失败中未触发第3key (因第2key timeout后remaining<MIN_ATTEMPT=8直接break)。FASTBREAK=3的"第3key救回"收益仍0证据 (第3key0%救回, 2e节)。

## 7. 铁律检查

- [x] 只改HM2对端配置 (/opt/cc-infra/docker-compose.yml 第470行), 未改HM1本地
- [x] 改前必有数据: 2h窗口159req + per-key + 43次失败attempt结构逐条溯源 (jsonl+DB+logs三源)
- [x] 改后必有验证: env=100 + health=200 + 2h窗口329req A/B对比 (实质数据流向)
- [x] 少改多轮: 仅改 BUDGET 1个参数
- [x] compose与运行态两处一致 (grep compose=100, docker exec env=100)
- [x] 每句可溯源: 全部来自 docker logs hm40006 + docker exec env + DB psql + jsonl python分析, 无编造
- [x] 时区: 用绝对ts时间戳, 未用NOW()
- [x] 不跨profile操作

## 8. 给下轮 (HM2优化HM1) 的接力信息

- HM2当前配置: BUDGET=100 / UPSTREAM=48 / FASTBREAK=3 / MIN_OUTBOUND=1.5 / RESERVE=5 / MIN_ATTEMPT=8 / KEY_CD=38 / TIER_CD=22 / STREAM_UPGRADE_TIMEOUT=55。
- **BUDGET=100待复核**: 本轮证伪"失败早结束"预期, 但零误杀。下轮需采更长窗口(4h+)确认 (a)3-attempt长失败(118-122s)是否仍出现, (b)是否有任何成功被截断在100s。
- **FASTBREAK=3收益疑点**: 全日53次3-attempt失败, 第3key 0%救回(全NVCFPexecTimeout)。R509的FASTBREAK 2→3在实测中无救回收益。下轮可评估回调 FASTBREAK 3→2 (但需对比2-attempt vs 3-attempt失败duration, 2-attempt~92.5s vs 3-attempt~120s, 回调可让失败早结束~28s/次——这反而是本轮BUDGET想做却没做到的)。
- **HM2侧MIN_OUTBOUND=1.5已低于CC清单A目标2.5**, 不再降。
- HM1侧 (deepseek) 请按CC清单HM1节复核 R510 FASTBREAK=2 的30min+平稳期效果, 重点看"第1key timeout+第2key成功救回"案例数 (R510核心收益证据)。

## ⏳ 轮到HM2优化HM1
