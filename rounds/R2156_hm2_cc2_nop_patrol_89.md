# R2156 (hm2_cc2): NOP 巡检轮 89 — 连续第 89 NOP 三阈值冻结

> HM2 only. 全新 session 接棒, STATE.md 头部停在 R2137 (07-23 07:xx 旧 session 交接),
> `git pull` 后 HEAD = 2f38313 (R2155 hm2_oc2). hm2_cc2 线最新 = d2b9f3d R2155 (连续第 88 NOP).
> 本轮 hm2_cc2 续 R2156. STATE 滞后修正第 48 次 (头停 R2137, hm2_cc2 线已 R2155, 本轮对齐).

## 数据 (HM2, 30min window, 18:20 CST 时点)
- 96 req / 87 OK(200) / 9 错(502) → **SR = 90.6%** (主链路稳, 错集中在 kimi_nv 过渡期)
- by model:
  - **glm5_2_nv 57/58 = 98.3%** (本域主链路极稳; 1 错 stream_absolute_cap mid-stream 背景波首字节已收 → breaker CLOSED(3,0) 吸收)
  - **kimi_nv 31/39 = 79.5%** (R2286/R2292 新默认模型过渡期阵痛; 8 错 = 5 zombie_empty_completion + 3 all_tiers_exhausted, 全 NVCF 上游连接类非旋钮能治)
- error_type: 5 zombie(kimi) + 3 all_tiers_exhausted(kimi, NVCF function ATE 上游已知良性) + 1 stream_absolute_cap(glm5_2_nv)
- 无 content_filter / timeout / conn / 429
- host_machine 全 HM2 本域

## kimi_nv zombie 明细 (4 个, 窗口滑动 18:20→18:22 最早 1 个滑出 30min)
- dbb6070c @09:53:05 / 65d81acd @10:00:01 / ad7a38c3 @10:01:17 / baaaa8f5 @10:11:07
- 全 kimi_nv 非 glm5_2_nv 本域主链路. R2286 改默认模型后的过渡期阵痛, 与 R2155 hm2_cc2 报告"kimi_nv 34/45=75.6% 11错全上游连接类"一致, 非新增错误类型, 非旋钮能治.

## cc4101 30min fallback (负向核心指标)
- **fallback = 0** ✅ 零数据空洞, 连续多轮最佳, 0 真中断, 0 双失败
- 比 R2155 hm2_cc2 (fallback=0) 持平, 无恶化

## nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 1 条: req=8de6558d @10:19:27 (glm5_2_nv stream_absolute_cap mid-stream) → state=('CLOSED', 3, 0) **未 OPEN**
- 注意: fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback. 本轮 cc4101 fallback=0.

## 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **31 / 6h** (同 R2149/R2150 基线, R2289 副作用受益持续)
- timeout = 164 / 6h (cc4101 自身 timeout, 非本域); server_5xx=6; stream_total_deadline=2
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮 (CLAUDE.md BUG-A 待查项)

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], **default=glm5_2_nv** ← R2286 改默认模型但 nv_gw nv_default_model 仍 glm5_2_nv, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移) ← 真实
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 较 R2155 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2155 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 持续验证)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段)
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, 待实施)

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
- SR 90.6% > 85% ✅
- cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞 0 真中断)
- 无新增错误类型 ✅ (kimi 5 zombie+3 ATE 是 R2286 过渡期已知非旋钮可治上游类; glm5_2_nv 1 cap 历史多轮已现)
四重佐证 nv_gw 稳: 9 错全上游无害类 (glm5_2_nv 1 cap mid-stream CLOSED 吸收 + kimi 8 错过渡期阵痛) / 无参数误杀 (全 0) / breaker 不真 OPEN (1 条 CLOSED(3,0) 远未到阈值) / 参数无漂移 (容器未重建 env 与 R2155 逐项一致). 改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

## 下一轮建议
1. 继续巡检. 盯 kimi_nv 过渡期 zombie/ATE 是否收尾 (R2286 改默认模型阵痛期). kimi zombie 若归零或仅单点 → 过渡期结束, 继续冻结.
2. cc4101 fallback 已连续多轮=0, 保持. 若再出现 PRIMARY+FALLBACK 双失败没救回, 或 fallback 请求数升到 ≥5/30min (且新 req id), 需评估.
3. 盯 NV-ANTH-BREAKER-FAIL state 计数 (本轮 1 条 CLOSED(3,0)). 若单轮 +5 或逼近 OPEN 阈值再评估.
4. 触发改动三阈值 (全满足才动): 30min SR 跌破 85% 或 cc4101 fallback >5 条/30min 且出现新错误类型.
5. R2192 任务3 (路径B zombie 内部重试) 是撤 40007 前置核心. 当前双 message_start 约束未解, 需读 specs/R2192_task3_zombie_internal_keyretry_spec.md 设计实施. 但本轮 kimi zombie 素材充分, 可作为任务3 实施后的验证数据源.
6. 铁律: 只改 HM2 不改 HM1. HM1 peer R2296 ms_gw 改动非本域.
7. 绝不 Read /tmp (上次 session 因反复 Read 不存在 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断).
