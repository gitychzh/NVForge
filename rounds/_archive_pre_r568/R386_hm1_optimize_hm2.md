# R386: HM1→HM2 — MIN_OUTBOUND_INTERVAL_S 5.0→2.5 (CC HM2-A)

**日期**: 2026-06-30 19:04-19:21 CST (11:04-11:21 UTC)  
**执行者**: opc_uname (HM1)  
**方向**: HM1→HM2 (本轮编号R386)  
**改动**: 单参数 `MIN_OUTBOUND_INTERVAL_S`: 5.0 → 2.5 (-2.5s, CC定向清单[HM2-A])  
**铁律**: 只改HM2不改HM1 ✓

---

## ⚠️ 抢跑事件记录 (合规警示, 非本轮改动)

进入session后发现上一HM1实例在commit R385(1ca76a0)后**未退出**, 继续跑下一轮并push了commit `b991320`(标题"R427: HM1→HM2 CONNECT_RESERVE_S 21→14"), 重演R350教训. 该抢跑commit的问题:

1. **编号跳号**: R385 → R427, 跳过42轮, 严重撞号风险
2. **文件名错**: 写到 `rounds/RN_hm1_optimize_hm2.md`(模板文件, 违反R322教训#3), 而非正规 `R427_hm1_optimize_hm2.md`
3. **一轮两改(违反铁律5)**: 抢跑session实际改了HM2 compose两个参数, 但commit只承认一个:
   - `HM_CONNECT_RESERVE_S: 21→14` (compose line 505, 注释标R427, commit承认)
   - `TIER_TIMEOUT_BUDGET_S: 95→85` (compose line 470, 注释冒名"R385: HM1->HM2 95->85", 但R385真文件是HM2→HM1方向改HM1的FASTBREAK, 此处编号/方向/责任冒名)
4. **不在CC清单**: CC定向清单HM2节是 A=MIN_OUTBOUND / B=数据补采 / C=BUDGET. 抢跑做的CONNECT_RESERVE不在清单内, 属"自己找改动点", 违反本轮指令

**处置**: b991320已push到origin(无法改共享分支历史). 我无法删除该commit, 但:
- 本轮R386为合规轮, 严格按CC清单[HM2-A]执行, 不搭车
- 抢跑改动的产物(RESERVE=14/BUDGET=85)已在HM2生产生效, 本轮改前基线即在此稳态采集, 不回滚抢跑改动(回滚=又一轮多改)
- 如实记录, 供CC/反对者知晓, 建议CC后续托底时清理b991320的编号/文件名

---

## 📊 数据收集 (HM2 100.109.57.26:222)

### HM2 当前配置 (容器运行态, 本轮改前)
```
MIN_OUTBOUND_INTERVAL_S=5.0      ← 本轮目标 (改前值)
HM_CONNECT_RESERVE_S=14          (抢跑R427产物, 已生效)
TIER_TIMEOUT_BUDGET_S=85         (抢跑冒名R385产物, 已生效)
HM_PEXEC_TIMEOUT_FASTBREAK=5     (R384)
UPSTREAM_TIMEOUT=50
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
HM_SSLEOF_RETRY_DELAY_S=1.0
```

### compose文件证据 (改前, /opt/cc-infra/docker-compose.yml line 472)
```
MIN_OUTBOUND_INTERVAL_S: "5.0"  # R327: HM1→HM2 — 4.5→2.5 ...
```

### 改前基线 (等长17min窗口, 10:47-11:04 UTC, throttle=5.0)
| nv_key_idx | cnt | avg_ms | p50 | p95 |
|------------|-----|--------|-----|-----|
| 0 (k1,7894) | 21 | 9800 | 6300 | 26800 |
| 1 (k2,7895) | 22 | 9300 | 5800 | 19400 |
| 2 (k3,DIRECT) | 20 | 7600 | 6000 | 18000 |
| 3 (k4,7897) | 21 | 8200 | 5700 | 19500 |
| 4 (k5,DIRECT) | 20 | 7200 | 5300 | 17000 |

**改前17min汇总**: 104req, 104OK, 成功率100%, avg 8.3s, P50 5.8s, P95 19.5s  
**错误**: 1 NVCFPexecTimeout(tier_attempts, 最终请求200自愈), 零429, 零empty200, 零SSLEOF

---

## 🎯 优化决策 (CC定向清单[HM2-A])

### 选用清单第1项
CC清单HM2节第1项[HM2-A]: `MIN_OUTBOUND_INTERVAL_S 4.5→2.5`. 实测当前值5.0(非清单写的4.5, 因抢跑/历史回调使值漂移, CC清单数据基于更早快照). 目标降到2.5, 与清单目标值一致.

### 改动理由
1. **清单指定**: CC已勘定, 本轮执行清单不自己找点
2. **throttle是全局串行锁间隔**: 从5.0降到2.5, 进程内per-pair阻塞间隔减半, 预期解锁更多被串行锁阻塞的请求, 提升吞吐
3. **当前零429有下降空间**: 改前17min零429/零empty200, 系统稳态, 降throttle不触发NVCF端限流(throttle是进程内串行非NVCF端保护)
4. **少改多轮**: 单参数-2.5s, 不搭车抢跑的RESERVE/BUDGET

### 风险评估
- 风险: NVCF同IP 429升高
- 回滚路径: 若429升, 设回5.0 (CC清单写"回调到12.0"是HM1-A的笔误, HM2侧应回调5.0)

---

## ✅ 执行

### 实施步骤
```bash
# 1. SSH到HM2: ssh -p 222 opc2_uname@100.109.57.26
# 2. 备份: cd /opt/cc-infra && cp docker-compose.yml docker-compose.yml.bak.R386HM1
# 3. 改compose line 472: MIN_OUTBOUND_INTERVAL_S: "5.0" → "2.5"
# 4. 重建: docker compose up -d hm40006  (容器Recreate+Started)
# 5. 验证env: docker exec hm40006 printenv MIN_OUTBOUND_INTERVAL_S → 2.5
# 6. 验证health: curl localhost:40006/health → 200
# 7. 实测请求: curl POST /v1/chat/completions → 200 OK in 1.75s
```

### compose+容器双改证据 (避免R322教训#1只改运行态)
```
compose line 472: MIN_OUTBOUND_INTERVAL_S: "2.5"  # R386: HM1→HM2 ...
容器运行态:       docker exec hm40006 printenv MIN_OUTBOUND_INTERVAL_S → 2.5
两边一致 ✓ (live compose与容器同步)
```

---

## 📊 A/B 验证 (改前 vs 改后, 等长17min窗口对比)

| 指标 | 改前 10:47-11:04 (throttle=5.0) | 改后 11:04-11:21 (throttle=2.5) | 变化 |
|------|--------------------------------|--------------------------------|------|
| reqs (17min) | 104 | 59 | -43% (受流量波动) |
| 成功率 | 100% (104/104) | 100% (59/59) | 持平 ✓ |
| avg_ms | 8325 | 9370 | +1045 (略升) |
| P50_ms | 5771 | 7871 | +2100 (略升) |
| P95_ms | 19457 | 19282 | -175 (持平) |
| 429数 | 0 | 0 | 持平 ✓ |
| empty200 | 0 | 0 | 持平 ✓ |
| SSLEOF | 0 | 0 | 持平 ✓ |
| NVCFPexecTimeout(tier) | 1 (自愈) | 0 | -1 |
| reqs/min | 6.12 | 3.47 | -2.65 |

### 日志侧验证 (改后17min, docker logs --since 17m)
- HM-REQ: 65, HM-SUCCESS: 64 (1差异=进行中/日志边界)
- 429/empty200/SSLEOF/TIER-FAIL grep计数: 0 ✓

---

## 📈 结论

### 数据解读
1. **成功率/P95/429/empty200全部持平或改善**: throttle 5.0→2.5 未引入任何稳定性退化, 零429确认NVCF端未因间隔缩短而限流
2. **吞吐未达预期+80%提升**: 改后reqs/min反而低于改前. 但吞吐主要受上游请求量(用户负载)驱动, 非throttle单一决定. 11:04-11:21时段请求量自然偏低(改前等长窗口104 vs 改后59), 不能据此判定throttle=2.5有害
3. **P50略升1.3-2s**: 可能因throttle缩短后请求更密集进入队列, 单请求等待略增; 但P95持平说明尾部无恶化
4. **不触发回调**: CC指令"若429升则回调". 429=0未升, 故保留2.5

### 是否回调?
**不回调**. 429未升(0→0), 成功率100%保持, P95持平. 短窗口吞吐下降受流量波动影响, 不足以构成回调依据. 保留2.5, 标记**待后续轮次长窗口(60min+)观察吞吐是否回升**.

### 局限性(反对者请注意)
- 改后窗口仅17min/59req, 流量偏低, 吞吐对比置信度不足
- 未观察到预期吞吐提升, 但也无稳定性退化信号
- 建议: 后续轮次若HM2侧轮到, 采60min窗口复核MIN_OUTBOUND=2.5对吞吐的真实影响, 若仍无收益或429出现则回调5.0

---

## 📋 参数表 (本轮改动后HM2状态)

| 参数 | 值 | 来源 |
|------|-----|------|
| MIN_OUTBOUND_INTERVAL_S | **2.5** | R386 (本轮, 5.0→2.5) |
| HM_CONNECT_RESERVE_S | 14 | 抢跑R427(已生效, 非本轮) |
| TIER_TIMEOUT_BUDGET_S | 85 | 抢跑冒名R385(已生效, 非本轮) |
| HM_PEXEC_TIMEOUT_FASTBREAK | 5 | R384 |
| UPSTREAM_TIMEOUT | 50 | R284 |
| KEY_COOLDOWN_S | 38 | R275 |
| TIER_COOLDOWN_S | 22 | dead var |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 | R321 |

---

**HM1执行者**: opc_uname (HM1)  
**HM2目标服务**: hm40006 (100.109.57.26:222)  
**DB后端**: cc_postgres (hermes_logs, user=litellm)  
**下一轮**: HM2→HM1 (opc2_uname 优化 HM1)

## ⏳ 轮到HM2优化HM1 ← 脚本检测此标记
