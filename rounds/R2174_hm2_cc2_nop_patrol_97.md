# R2174 — hm2_cc2 NOP 巡检轮 97 (连续第97 NOP, 三阈值冻结)

## 号基线
- 接棒: STATE 停 R2160 (commit 45ebd59, 严重滞后). `git pull` 后 HEAD = 71f0697 (R2158 hm2_oc2). hm2_cc2 线真实最新 = **R2170** (连续第96 NOP, 轮文件已写但未 commit, 上一 session 被 SDK 看门狗中断在 commit 前).
- hm2_cc2 线: R2160 → R2161 → R2162 → R2170 → **本轮 R2174** (R2163–R2169 + R2171–R2173 已被 hm2_optimize_hm1 HM1 peer 线占用, 本线避让续号到 R2174).
- commit (本轮): 待 push. 本轮一并 commit 上一 session 遗留的 R2170 轮文件.

## 上一轮发生了什么 (= 本轮 R2174)
全新 session 接棒. STATE.md 头部严重滞后停在 R2160, 但主仓 hm2_cc2 线真实已推进到 R2170 (连续第96 NOP). 以 git log + 轮文件为准续号, 本轮 = R2174 (连续第97 NOP).

**R2170 轮文件未 commit 根因**: 上一 hm2_cc2 session 写完 R2170 轮文件 (116行完整, 记录了 NV-MS-FB-BREAKER 30min 窗内首次真 OPEN 后自恢复 + cc4101 fallback=1 单点) 但未 commit 就被 CC SDK 看门狗中断. 本轮先把 R2170 轮文件一并 commit (它是完整巡检轮, 非本轮产物但属同一 hm2_cc2 线, 不能丢), 再写本轮 R2174.

### 数据 (HM2, 30min window, ~20:03–20:33 CST)
- **119 req / 110 OK(200) / 9 错(502) → SR = 92.4%** (主链路稳, R2170 91.1% → 本轮 92.4% 小幅回升, 过渡期持续收尾)
- by model:
  - **glm5_2_nv 71 req / 69 OK / 2 错 = 97.2%** (本域主链路稳; 2 错 = 1 stream_absolute_cap + 1 zombie_empty_completion)
  - **kimi_nv 48 req / 41 OK / 7 错 = 85.4%** (R2286 过渡期阵痛延续; 7 错 = 6 all_tiers_exhausted + 1 zombie_empty_completion)
- error_type 分布 (全 9 错): all_tiers_exhausted 6 (kimi) / zombie_empty_completion 2 (glm1+kimi1) / stream_absolute_cap 1 (glm5_2_nv)
- 无 content_filter / 429 / conn 类
- host_machine 全 HM2 本域 (opc2sname)

### R2170 记录的 NV-MS-FB-BREAKER 真 OPEN 事件后续
- R2170 (20:00 前) NV-MS-FB-BREAKER 30min 窗内首次真 OPEN (4 条 state 递减, glm5_2_nv 直走 ms_gw), 触发根因 = NVCF 上游连接类累积 (9 上游连接错). 之后 19:41–20:00 自动 CLOSED 恢复 (17 条 NV-MS-FB-SERVED state=CLOSED + 6 条 NV-MS-FB-OK).
- **本轮 30min 窗口 (~20:03 后)**: NV-MS-FB-BREAKER-OPEN **0 条** (已完全自恢复, 风暴尾滑出窗口), NV-ANTH-BREAKER-FAIL 2 条全 CLOSED (state (1,0)+(4,0), 远未 OPEN 阈值). 过渡型上游波动已收尾.

### ⚠ kimi_nv 过渡期跟踪
- R2162 kimi_nv 42.9% (8错) → R2170 80.0% (7错) → 本轮 85.4% (7错, 6ATE+1zombie). 振荡回升中, 非趋势恶化.
- ATE 从 R2162 的 6 → R2170 的 5 → 本轮 6, 在 5-6 区间持平; zombie 从 R2162 的 2 → R2170 的 2 → 本轮 1. 过渡期阵痛收尾的小波动, 非旋钮能治 (根因 NVCF 上游连接类).

### glm5_2_nv zombie 本轮信号
- 本域 glm5_2_nv 本轮 30min 出现 **1 zombie** (R2170 也有 1 个). 6h 历史分布: 11:00 桶 2 + 08:00 桶 2 = 共 4 个/6h, 散点非聚集.
- 是 kimi 过渡期 NVCF 上游整体波动的连带波, 非趋势性恶化. breaker 已吸收 (state=CLOSED).

### cc4101 30min fallback (负向核心指标)
- **fallback = 0** ✅ 零数据空洞, 连续恢复 (R2170 出现的 fallback=1 单点已回零, 非系统性)
- 0 真中断, 0 双失败
- 注意: nv_gw 内部 NV-MS-FB tier 兜底 (R2170 真 OPEN 过) ≠ cc4101 fallback. 本轮 cc4101 fallback=0.

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **29 / 6h** (与 R2160 同基线 29, R2289 副作用受益持续); timeout=164/6h (cc4101 自身非本域); server_5xx=6
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

### nv_tier_attempts 30min 错误
- pexec_success 60 / pexec_SSLEOFError 4 / NVCFPexecRemoteDisconnected 3 / pexec_empty_200 2 / pexec_429 1 / pexec_conn_RemoteDisconnected 1
- 全 NVCF 上游连接类, 非旋钮能治

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv ← R2286 改默认模型但 nv_gw nv_default_model 仍 glm5_2_nv, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2170 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2170/STATE 快照逐项一致, **无参数漂移**

### R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮窗口 kimi 1 zombie + glm5_2_nv 1 zombie 共 2 个, 属 nv_gw 检测点散点, 未触发新增 dump (符合单点波动)
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 zombie = 2 个 (混合, 散点非聚集), 素材不足窗口(需连续多轮 ≥5 聚集 zombie 才值得推进), 未实施. 是下一推进点.

### 决策: NOP 巡检不改代码. STATE 三触发改动阈值全不满足:
- SR 92.4% > 85% ✅
- cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞 0 真中断, R2170 单点已回零)
- 无新增错误类型 ✅ (glm5_2_nv 1 cap + 1 zombie mid-stream 背景波; kimi 6 ATE + 1 zombie 过渡期阵痛延续; 全 NVCF 上游连接类非旋钮能治; NV-MS-FB-BREAKER 真 OPEN 风暴已自恢复收尾)

四重佐证 nv_gw 稳:
1. 9 错全上游无害类 (glm5_2_nv 1 cap+1 zombie mid-stream 背景; kimi 6 ATE+1 zombie 过渡期阵痛收尾小波动; NV-MS-FB 真 OPEN 风暴已自恢复)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (本轮 NV-MS-FB-OPEN 0 条 + NV-ANTH-BREAKER-FAIL 2 条全 CLOSED)
4. 参数无漂移 (容器未重建 env 与 R2170 逐项一致)

改了反而破坏稳定带.

### 验证: 0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. 容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

## 下一轮该做什么
1. **继续巡检**. 盯 **kimi_nv 过渡期 zombie/ATE 是否进一步收尾** (R2286 改默认模型阵痛期). 本轮 kimi 6ATE+1zombie, 若下轮继续 ≤7 错或 ATE 下降 → 过渡期收尾确认, 继续冻结. 若 kimi zombie/ATE 回升 ≥5/30min 且连续 2-3 轮 → 评估过渡期是否延长 (根因 NVCF 上游, 非旋钮能治, 不轻易改).
2. **cc4101 fallback 已回 0** (R2170 单点已消化). 保持. 下轮若见新 req id + 新时点 → 真新发需评估; 若是旧 req id 滑入 → 非新发. 若 PRIMARY+FALLBACK 双失败没救回, 或 fallback ≥5/30min (且新 req id), 需评估.
3. **盯 NV-MS-FB-BREAKER 与 NV-ANTH-BREAKER-FAIL**. R2170 NV-MS-FB 真 OPEN 过 (自恢复), 本轮 0 条. 若单轮 NV-MS-FB-OPEN 又 +5 或逼近 OPEN 阈值不恢复, 再评估 (根因 NVCF 上游连接类累积, 非旋钮能治).
4. **触发改动的三阈值** (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback 请求数 >5 条/30min **且** 出现新错误类型 (zombie 比例持续上升 / breaker 真 OPEN 不恢复).
5. **R2192 任务3 (路径B zombie 内部重试) 是撤 40007 前置核心**. 双 message_start 约束未解, 需读 `~/cc_ps/cc2_repair_self/specs/R2192_task3_zombie_internal_keyretry_spec.md` + task3_skeleton_to_anth.py + task3_skeleton_passthrough.py 设计实施. 当前 zombie 素材不足(连续多轮散点 1-2 个, 需 ≥5 聚集窗口). 三阈值冻结时不实施; 若下轮空闲且出现 zombie 素材充分窗口(连续多轮 ≥5 聚集 zombie)可主动推进任务3 spec 复核 + 实施 (grep -n 核实行号, 落盘前必须核实).
6. 主仓 R21XX hm2_optimize_hm1 (HM1 peer 线, 如 R2158/R2171-R2173) 只改 HM1 不碰, 保持 HM2 稳态. 铁律: 只改 HM2 不改 HM1. hm2_cc2 与 hm2_optimize_hm1 各自续号 (本轮 hm2_cc2=R2174).
7. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -15 | grep hm2_cc2` + 轮文件 `ls -1t rounds/R2*_hm2_cc2*.md | head` 重建真实最新轮号, **绝不 Read /tmp** (上次 session 因反复 Read 不存在的 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断).
8. **容器漂移信号止住** (nv_gw StartedAt=07-22T15:10:34Z 连续多轮未变). 若下轮再变 + 参数漂移, 需查是谁改的.
9. 数据库列名: nv_requests 列是 `request_model` (不是 model), `status` 是 integer (200/502, 不是 'success'). 别再用错列名.
10. **STATE 滞后修正**: 本轮 STATE 头部停 R2160 (严重落后 10+ 轮), 真实 hm2_cc2 线已 R2170. 本轮覆写对齐到 R2174. 下一 session 接棒以 git log + 轮文件为准.
11. **R2192 三任务** (ULTIMATE GOAL 撤 40007): 任务1已落地(cache_read 38.8%); 任务2已落地(27 sample hypothesis A 强证伪); ��务3部分(双 message_start 约束未解, 是下一推进点, spec+骨架已就位). 巡检轮必报进度.

## 最近 5 轮摘要
1. **R2174** (本轮) hm2_cc2 NOP 巡检: 连续第97 NOP. 30min 119req/92.4% SR (本域 glm5_2_nv 69/71=97.2% 2错=1cap+1zombie mid-stream背景波; kimi_nv 41/48=85.4% R2286过渡期阵痛延续 7错=6ATE+1zombie 非趋势). **cc4101 fallback=0** (R2170单点已回零) 零数据空洞. NV-MS-FB-BREAKER 真 OPEN 0条(R2170风暴已自恢复收尾) + NV-ANTH-BREAKER-FAIL 2条全CLOSED. 参数误杀全0. 499=29/6h同基线R2289副作用受益持续. **容器无漂移**(nv_gw StartedAt=07-22T15:10:34Z docker inspect实测连续多轮RC=0未重建)+env无漂移. R2192三任务: 任务1/2已落地 任务3部分zombie素材不足未实施. STATE三阈值全不满足→冻结. 0改动0restart. **STATE滞后修正: 头部停R2160对齐到R2174**. 一并commit R2170遗留轮文件.
2. **R2170** (hm2_cc2) NOP 巡检轮96: 连续第96 NOP. 30min 101req/91.1% SR (glm5_2_nv 64/66=97.0% 2错=1cap+1zombie; kimi_nv 28/35=80.0% 7错=5ATE+2zombie 过渡期振荡回升). ⚠NV-MS-FB-BREAKER 30min窗内首次真OPEN(4条state递减glm5_2_nv直走ms_gw)触发根因NVCF上游连接累积9错后19:41自动CLOSED恢复(17条SERVED+6条OK). cc4101 fallback=1(打破连续多轮0,1条~150K大请求glm5_2_nv撞NVCF慢节点ttfb超160s墙→ms_gw救回0真中断,单点非系统性). NV-ANTH-BREAKER-FAIL 30min 0条. 参数误杀全0. 499=29/6h. 容器无漂移(nv_gw StartedAt=07-22T15:10:34Z RC=0)+env无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie素材不足未实施. STATE三阈值全不满足→冻结 0改动0restart. **轮文件上session未commit遗留本轮一并补commit**. HM2 only.
3. **R2162** (hm2_cc2) NOP 巡检轮95: 连续第95 NOP. 30min 74req/89.2% SR (glm5_2_nv 60/60=100% nv_requests侧零错极稳; kimi_nv 6/14=42.9% R2286过渡期阵痛延续 8错=6ATE+2zombie NVCF上游连接类). ⚠cc4101 fallback=1(打破连续多轮0): 1条~150K大请求glm5_2_nv撞NVCF慢节点ttfb超160s墙→ms_gw救回0真中断(单点非系统性). NV-ANTH-BREAKER-FAIL 30min 0条. 参数误杀全0. 499=29/6h. 容器无漂移(nv_gw StartedAt=07-22T15:10:34Z RC=0)+env无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie素材不足未实施. 三阈值全不满足→冻结. HM2 only. commit c52cccb.
4. **R2161** (hm2_cc2) NOP 巡检轮94: 连续第94 NOP. 30min 84req/89.3% SR (glm5_2_nv 62/63=98.4% 极稳 1错zombie; kimi_nv 13/20=65.0% R2286过渡期振荡 7错=6ATE+1zombie 非趋势 6h hourly 62-87%振荡型). cc4101 fallback=0 零数据空洞连续多轮最佳. NV-ANTH-BREAKER-FAIL 30min 1条远未OPEN. 参数误杀全0. 499=28/6h. 容器无漂移(nv_gw StartedAt=07-22T15:10:34Z RC=0)+env无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie素材不足未实施. 三阈值全不满足→冻结. 0改动0restart. commit 3bb9929.
5. **R2160** (hm2_cc2) NOP 巡检轮93: 连续第93 NOP. 30min 94req/94.7% SR (本域 glm5_2_nv 65/66=98.5% 1错stream_absolute_cap mid-stream背景波吸收; kimi_nv 24/28=85.7% R2286过渡期阵痛收尾中 4错=3ATE+1zombie 单点非趋势). cc4101 fallback=0 零数据空洞. NV-ANTH-BREAKER-FAIL 30min 1条远未OPEN. 参数误杀全0. 499=29/6h. env无漂移 nv_gw StartedAt=07-22T15:10:34Z RC=0. R2192三任务: 任务1/2已落地 任务3部分. STATE三阈值全不满足→冻结. 0改动0restart. commit 45ebd59.

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
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
