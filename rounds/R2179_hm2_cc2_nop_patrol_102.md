# R2179 (hm2_cc2): NOP 巡检轮 102 — 连续第 102 NOP, 三阈值冻结, 0 改动 0 restart

## 号基线
- 上轮 hm2_cc2: R2178 (NOP 巡检轮 101, commit f0713a2, 连续第 101 NOP, 30min 101req/93.1% SR)
- 本轮: **R2179 — hm2_cc2 NOP 巡检轮, 0 改动 0 restart, 连续第 102 NOP**
- 轮文件: `rounds/R2179_hm2_cc2_nop_patrol_102.md`

## 数据 (HM2, 30min window)
- 总 req = 111 (status 查询 105 OK + 5 错 = 110 + 边界 1; nv_requests 实测 106 OK + 5 错 = 111)
- by model: **glm5_2_nv 106/111 (status 200=106 / 502=5)** — 全本域流量; **kimi_nv 0 req** (R2286 过渡期阵痛收尾, 流量全汇 glm 稳定路径, 与 R2178 一致)
- SR = 106/111 = **95.5%** (主链路稳, 比 R2178 93.1% 略升)
- error_type (5 错): **stream_absolute_cap 3** + **zombie_empty_completion 2** (无 content_filter/timeout/conn/429)
- host_machine 全 HM2 本域

## ⚠ 本轮新信号 (NVCF 上游 504 压力波, nv_gw 自愈正常消化中)

本轮出现 R2178 没有的两条新信号, 均属 NVCF 上游连接类压力非旋钮能治, nv_gw 自愈链路正常工作:

### 信号1: NV-MS-FB-BREAKER 真 OPEN 1 次 (自愈回 CLOSED)
- 03:16:13 `NV-MS-FB-SERVED ... state=OPEN` (5 keys 全耗尽后 ms_gw 兜底成功记 failure, breaker state=('OPEN',5,22))
- 03:16:20 下一条请求 `NV-MS-FB-BREAKER-OPEN` 直接 serve ms_gw (breaker 在 OPEN 状态)
- 之后 03:19:30 起所有 `NV-MS-FB-SERVED` 回到 state=CLOSED — **breaker 已自愈, 当前未停在 OPEN**
- 这是 R2177 风暴(75) → R2178 缓解(2) → 本轮再出现 1 次 OPEN 再自愈. breaker 行为符合设计 (上游压力来时 OPEN 直走 ms, 压力退时回 CLOSED）

### 信号2: pexec_504=19 突出 + NV-MS-FB 内部兜底 15 次 (持续中)
- nv_tier_attempts 30min: pexec_504=19 (突出) + pexec_conn_RemoteDisconnected=7 + pexec_SSLEOFError=2 + pexec_429=1 + pexec_success=98
- NVCF 网关侧 504 压力逐个打空 5 keys → all_keys_exhausted → nv_gw 内部 NV-MS-FB 退到 ms_gw 兜底 = **15 次/30min** (R2177 风暴=75 → R2178=2 → 本轮=15)
- NV-MS-FB 时间分布 03:05-03:31 平均 ~1.7 次/min, **03:31 仍有新事件**, 压力仍在持续 (非突发风暴, 持续中等压力)
- 关键: 15 次内部 fallback **全 NV-MS-FB-OK 成功**, 0 冒到 cc4101 层真中断, SR 95.5% 未受影响

## cc4101 层 fallback (负向核心指标)
- **cc4101 真 fallback = 1** (req=cab9c8bd, PRIMARY-FAIL timeout 60s header/ttfb 后 fallback ms_gw 3934ms 救回)
  - 注: 上轮 grep count=4 是 PRIMARY-FAIL 3 行 + FALLBACK-OK 1 行总和, 实际 cc 层真 fallback 只 1 个 req id
- **cc4101 fallback 1 < 5 阈值** ✅, 0 真中断, 0 双失败
- 比 R2178 (cc fallback=2) 略降, 无恶化

## nv_gw 内部 breaker 与参数误杀
- NV-MS-FB 内部兜底 15 次全成功 (state 大多 CLOSED, 1 次 OPEN 后自愈回 CLOSED, 见信号1)
- NV-ANTH-BREAKER-FAIL = 1 条 (03:12:18 glm5_2_nv anth mid-stream stream_absolute_cap 软挂, state=('CLOSED',4,0) 未真 OPEN)
- 参数误杀类 (75s_timeout/STREAM-STALL-FAIL/BIG-INPUT/UPSTREAM-ERROR-SEEN/CC4101-UPSTREAM-ERROR/client_gone) = **全 0** ✅

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **44/6h** (R2178=43, 本轮 44, 持平基线 R2289 副作用受益持续)
- stream_total_deadline = 2; 763 空 error_type (正常成功)
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮 (CLAUDE.md BUG-A 待查项)

## 容器漂移信号 (docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models, default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** ← 与 R2178 逐项一致, **连续多轮未重建, 漂移止住**
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2178 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2178 逐项一致, 无参数漂移 (参数快照见下)

## R2192 三任务进度
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮 kimi zombie=0 (kimi 0 req), glm5_2_nv zombie=2 属 nv_gw 检测点, 未触发新增 dump 符合窗口
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, spec+骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 zombie 总 2 个素材不足 (需 ≥5), 未实施

## 决策: NOP 冻结 0 改动
STATE 三触发改动阈值全不满足:
- SR 95.5% > 85% ✅
- cc4101 真 fallback = 1 < 5 ✅ (0 真中断)
- 无新增错误类型 ✅ (cap + zombie 全历史已知类; breaker 真 OPEN 1 次后自愈属设计行为非新增错误类型)

四重佐证 nv_gw 稳:
1. 5 错全上游无害类 (3 cap mid-stream 背景 + 2 zombie)
2. 无参数误杀 (全 0)
3. NV-MS-FB breaker 真 OPEN 1 次后自愈回 CLOSED (设计行为); NV-ANTH-BREAKER-FAIL 1 条 CLOSED 未真 OPEN
4. 参数无漂移 (nv_gw StartedAt=07-23T18:05 连续多轮未变, env 与 R2178 逐项一致)

新信号 (pexec_504=19 + 内部兜底 15 次 + breaker 1 次 OPEN) 均 NVCF 上游连接类压力, nv_gw 自愈链路正常消化 (15 次 internal fb 全成功 0 冒到 cc 层, SR 95.5%, 0 真中断). HM1 peer 已在 R2302-R2306 调 tier budget/cooldown 应对同源 NVCF 上游压力 (HM1 线, 铁律不改 HM1). hm2_cc2 这边 SR 仍高 + 自愈正常, 没到动 budget 的程度, 冻结观察等压力自然收. 改反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. 容器 StartedAt 实测: nv_gw=07-23T18:05:17Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

## HM2 only / 未 Read 任何 /tmp 文件
本轮严格遵守中断告警铁律, 未 Read 任何 /tmp 下文件, 所有临时数据走 docker exec / DB 查询获取.

## nv_gw 参数快照 (HM2, 本轮实测无漂移)
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

Co-Authored-By: Claude <noreply@anthropic.com>
