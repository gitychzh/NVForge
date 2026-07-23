# R2170 — hm2_cc2 NOP 巡检轮 96 (连续第96 NOP, 三阈值冻结)

## 号基线
- 接棒: STATE 停 R2160 (commit 45ebd59). `git pull` 后 HEAD = c52cccb (R2162 hm2_cc2 连续第95 NOP).
- hm2_cc2 线: R2160 → R2161 → R2162. 本轮 hm2_cc2 续号, 选 **R2170** (R2163–R2169 已被 hm2_optimize_hm1 HM1 peer 线占用, 本线避让).
- commit (本轮): 待 push.

## 上一轮发生了什么 (= 本轮 R2170)
全新 session 接棒. STATE 落后 2 轮 (STATE 头 R2160, 主仓 HEAD R2162). 以 git log 为准续号.

### 数据 (HM2, 30min window, 19:33–20:03 CST)
- **101 req / 92 OK(200) / 9 错(502) → SR = 91.1%** (主链路稳, R2162 89.2% → 本轮 91.1%, 小幅回升)
- by model:
  - **glm5_2_nv 66 req / 64 OK / 2 错 = 97.0%** (本域主链路稳; 2 错 = 1 stream_absolute_cap + 1 zombie_empty_completion)
  - **kimi_nv 35 req / 28 OK / 7 错 = 80.0%** (R2286 过渡期阵痛延续; 7 错 = 5 all_tiers_exhausted + 2 zombie_empty_completion)
- error_type 分布 (全 9 错): stream_absolute_cap 1 / zombie_empty_completion 3 (glm1+kimi2) / all_tiers_exhausted 5 (kimi)
- 无 content_filter / 429 / conn 类
- host_machine 全 HM2 本域 (opc2sname)

### ⚠ 新现象 (本轮重点记录, 非新错误类型但是新行为)
**NV-MS-FB-BREAKER 在 30min 窗口内首次真 OPEN** (R1719 设计的 nv_gw 内部 NV-MS breaker):
- 19:33:41–19:37:51 共 **4 条 NV-MS-FB-BREAKER-OPEN** (state 递减 OPEN,5,29→21→16→16), glm5_2_nv 直走 ms_gw
- 触发根因 = NVCF 上游连接类累积 (nv_tier_attempts 30min: NVCFPexecRemoteDisconnected 4 + pexec_SSLEOFError 4 + pexec_empty_200 1, 共 9 上游连接错)
- **之后已自动 CLOSED 恢复**: 19:41–20:00 共 17 条 NV-MS-FB-SERVED (state=CLOSED), NV-MS-FB-OK 6 条 ms_gw fallback 成功
- 20:00 之后 glm5_2_nv 恢复正常 (20:03:55 NV-GLM52-KEY-FAULT 后 k2 恢复; 20:04:06 NV-SUCCESS + NV-PEEK-OK HEALTHY ttfb=34648ms)
- **这是过渡型上游波动, 非旋钮能治**, 且已自恢复. 注意: `NV-MS-FB` 是 nv_gw 内部 tier 兜底, ≠ cc4101 fallback (cc4101 fallback 仅 1 条, 见下).

**kimi_nv 过渡期跟踪**:
- R2162 kimi_nv 42.9% → 本轮 80.0% (回升), 但仍有 2 zombie + 5 ATE
- ATE 从 R2162 的 6 降到 5, zombie 从 2 持平 2 — 过渡期阵痛收尾中的小波动, 非趋势恶化
- kimi zombie = 2 仍不构成"素材充分窗口" (需 ≥5 才值得推进 R2192 任务3)

### cc4101 30min fallback (负向核心指标)
- **cc4101 fallback = 1 条** (req=8ce1b120, 19:37:16, glm5_2_nv primary 160s ttfb timeout → ms_gw 救回 19:37:35.9 FALLBACK-OK)
- 与 R2162 (fallback=1) 持平, 单点非系统性, 0 真中断
- ⚠ 区分: nv_gw 内部 NV-MS-FB-SERVED 多条 ≠ cc4101 fallback. cc4101 fallback 才是"撤 40007"负向核心指标, 本轮仅 1.

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / CC4101-UPSTREAM-ERROR = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **29 / 6h** (与 R2160=29 基线逐项一致, R2289 副作用受益持续)
- timeout = 164 / 6h (cc4101 自身非本域); server_5xx = 6
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model 仍是 glm5_2_nv — R2286 改默认模型但 nv_gw nv_default_model 未改, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2160/R2162 逐项一致, **无漂移**) ✅
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2162 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 STATE R2160 快照逐项一致, **无参数漂移**

### R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮窗口 zombie 3 个 (glm1+kimi2) 属 nv_gw 检测点, 未触发新增 dump (单点波动)
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 kimi zombie=2 素材不足(需 ≥5), 未实施. 是下一推进点.

### 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
- SR 91.1% > 85% ✅ (未跌破)
- cc4101 fallback 请求数 1 < 5 ✅ (单点 160s ttfb timeout, ms_gw 救回 0 真中断)
- 无新增错误类型 ✅ (glm cap+zombie 历史多轮已现; kimi ATE+zombie 过渡期已知; NV-MS-FB-BREAKER OPEN 是已有 R1719 breaker 正常工作非新错误类型)

四重佐证 nv_gw 稳:
1. 9 错全上游无害类 (glm cap/zombie 背景波 + kimi ATE/zombie 过渡期阵痛 + NV-MS-FB breaker 正常工作)
2. 无参数误杀 (全 0)
3. NV-MS-FB breaker 真 OPEN 过但已自恢复 (19:33 OPEN → 20:00 全 CLOSED), NV-ANTH-BREAKER 2 条全 CLOSED 未 OPEN
4. 参数无漂移 (容器未重建 env 与 R2160 逐项一致)

改了反而破坏稳定带. 本轮额外盯 NV-MS-FB-BREAKER 真 OPEN 事件给下轮跟踪.

### 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

## 下一轮该做什么
1. **继续巡检**. 本轮新现象 NV-MS-FB-BREAKER 真 OPEN 已自恢复. 下轮盯: 若 NV-MS-FB-BREAKER-OPEN 再次出现且持续 OPEN ≥2 轮不恢复 → 评估是否上游 NVCF 持续恶化 (根因 NVCF 上游连接类, 非旋钮能治, 不轻易改). 若单轮出现又自恢复 (如本轮) → 过渡型波动, 冻结.
2. **kimi_nv 过渡期跟踪**: R2162 42.9% → 本轮 80.0% 回升, 但 2 zombie 持平. 若下轮 kimi zombie/ATE 继续收尾 (≤3) → 过渡期收尾确认; 若回升 ≥5/30min 且连续 2-3 轮 → 评估过渡期延长.
3. **cc4101 fallback**: 本轮 1 条 (160s ttfb timeout 大请求). 若下轮见新 req id + 新时点 → 真新发需评估; 若同 req 滑入 → 非新发. fallback <5 保持.
4. **盯 NV-ANTH-BREAKER-FAIL state**: 本轮 2 条全 CLOSED (state CLOSED,1,0 / CLOSED,4,0), 远未 OPEN. 若逼近 OPEN 阈值再评估.
5. **触发改动的三阈值** (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback 请求数 >5 条/30min **且** 出现新错误类型 (zombie 比例持续上升 / NV-ANTH-BREAKER-FAIL 真 OPEN).
6. **R2192 任务3 (路径B zombie 内部重试) 是撤 40007 前置核心**. 当前双 message_start 约束未解, 需读 `~/cc_ps/cc2_repair_self/specs/R2192_task3_zombie_internal_keyretry_spec.md` + task3_skeleton_to_anth.py + task3_skeleton_passthrough.py 设计实施. 三阈值满足冻结时不实施; 若出现 zombie 素材充分窗口 (连续多轮 ≥5 zombie) 可主动推进任务3 spec 复核 + 实施 (grep -n 核实行号, 落盘前必须核实).
7. **轮号体系**: hm2_cc2 与 hm2_optimize_hm1 共用 R 号空间, HM1 peer 已占 R2163–R2169. 本轮 hm2_cc2 选 R2170 避让. 下轮 hm2_cc2 续号须先 `ls rounds/R21*.md` 确认无冲突. hm2_cc2 与 hm2_oc2 各自续号 (本轮 hm2_cc2=R2170).
8. 主仓 R22XX (hm2_optimize_hm1) 是 HM1 peer 轮 (only HM1), HM2 不参与, 保持 HM2 稳态. 铁律: 只改 HM2 不改 HM1.
9. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**.
10. **数据库列名**: nv_requests 列是 `request_model` (不是 model), `status` 是 integer (200/502). 别再用错列名.

## 最近 5 轮摘要
1. **R2170** (本轮) hm2_cc2 NOP 巡检: 连续第96 NOP. 30min 101req/91.1% SR (glm5_2_nv 64/66=97.0% 2错=1cap+1zombie; kimi_nv 28/35=80.0% R2286过渡期回升 7错=5ATE+2zombie). **⚠NV-MS-FB-BREAKER 真 OPEN 事件(19:33-19:37 4条 state OPEN)首次30min窗口记录, 之后已自恢复(20:00全CLOSED) 过渡型上游波动非旋钮能治**. cc4101 fallback 30min=1(160s ttfb timeout 大请求 ms_gw救回 0真中断). NV-ANTH-BREAKER-FAIL 2条全CLOSED未OPEN. 参数误杀全0. 499=29/6h同基线R2289副作用持续. **容器无漂移**(nv_gw StartedAt=07-22T15:10:34Z docker inspect实测连续多轮RC=0未重建)+env无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie=2素材不足未实施. STATE三阈值全不满足→冻结. 0改动0restart. HM2 only.
2. **R2162** (hm2_cc2) NOP 巡检95: 连续第95 NOP. 30min 74req/89.2% SR (glm5_2_nv 60/60=100% nv_requests侧零错极稳; kimi_nv 6/14=42.9% R2286过渡期阵痛延续 8错=6ATE+2zombie). cc4101 fallback=1(打破连续多轮=0): 1条~150K大请求glm5_2_nv撞NVCF慢节点ttfb超160s墙→ms_gw救回0真中断(单点非系统性). NV-ANTH-BREAKER-FAIL 30min 0条比R2161更干净. 参数误杀全0. 499=29/6h. 容器无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie=2素材不足未实施. 三阈值全不满足→冻结. 0改动0restart. commit c52cccb.
3. **R2161** (hm2_cc2) NOP 巡检94: 连续第94 NOP. 30min 84req/89.3% SR (glm5_2_nv 62/63=98.4% 1错zombie; kimi_nv 13/20=65.0% R2286过渡期振荡 7错=6ATE+1zombie 非趋势 6h hourly 62-87%振荡型). cc4101 fallback=0 零数据空洞连续多轮最佳. NV-ANTH-BREAKER-FAIL 30min 1条远未OPEN. 参数误杀全0. 499=28/6h. 容器无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie素材不足未实施. 三阈值全不满足→冻结. 0改动0restart. commit 3bb9929.
4. **R2160** (hm2_cc2) NOP 巡检93: 连续第93 NOP. 30min 94req/94.7% SR (glm5_2_nv 65/66=98.5% 1错stream_absolute_cap mid-stream背景波吸收; kimi_nv 24/28=85.7% R2286过渡期阵痛收尾中 4错=3ATE+1zombie). cc4101 fallback=0 零数据空洞连续多轮最佳0真中断. NV-ANTH-BREAKER-FAIL 30min 1条远未OPEN. 参数误杀全0. 499=29/6h. 容器无漂移. R2192三任务: 任务1/2已落地 任务3部分. STATE三阈值全不满足→冻结. 0改动0restart. commit 45ebd59.
5. **R2159** (hm2_cc2) NOP 巡检92: 连续第92 NOP. 30min 85req/95.3% SR (glm5_2_nv 63/64=98.4% 1错stream_absolute_cap; kimi_nv 18/21=85.7% R2286过渡期阵痛收尾中 3错=3ATE). cc4101 fallback=0 零数据空洞连续多轮最佳0真中断. NV-ANTH-BREAKER-FAIL 30min 0条新触发未OPEN. 参数误杀全0. 499=31/6h. kimi过渡期zombie持续归零(连续2轮0)收尾趋近结束. env无漂移. R2192三任务: 任务1/2已落地 任务3部分. STATE三阈值全不满足→冻结. 0改动0restart. commit 3a063b5.

## nv_gw 参数快照 (HM2, 本轮确认无漂移, docker inspect 实测容器区分)
```
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_FORCE_STREAM_UPGRADE=0
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=90
```
容器 (docker inspect 实测, 非旧 STATE 串错值):
- nv_gw RestartCount=0 StartedAt=2026-07-22T15:10:34Z (连续多轮未重建, RC=0, env无漂移) ← 真实
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2162 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
