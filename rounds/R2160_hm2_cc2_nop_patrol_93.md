# R2160 — hm2_cc2 NOP 巡检轮 93

连续第 **93** NOP, 三阈值冻结, 0 改动 0 restart, HM2 only.

## 数据 (HM2, 30min window)

- 94 req / 89 OK(200) / 5 错(502) → **SR = 94.7%** (主链路稳, 与上轮 R2159 95.3% 基本持平)
- by model:
  - **glm5_2_nv 65/66 = 98.5%** (本域主链路极稳; 1 错 stream_absolute_cap mid-stream 背景波吸收)
  - **kimi_nv 24/28 = 85.7%** (R2286/R2292 新默认模型过渡期阵痛收尾中; 4 错 = 3 ATE + 1 zombie)
- error_type: 4 all_tiers_exhausted(kimi, NVCF function ATE 上游已知良性) + 1 zombie_empty_completion(kimi)
- 无 content_filter / timeout / conn / 429
- host_machine 全 HM2 本域 (opc2sname)

## ⚠ kimi_nv 过渡期 zombie 跟踪信号

- 30min kimi_nv **1 zombie** (R2159=0 → 本轮=1, 单点回升打破连续 2 轮归零)
- 但 ATE 持平 3, zombie 仅单点回升, **非趋势性恶化**, 仍属过渡期阵痛收尾的小波动
- 1 个 zombie 不构成"素材充分窗口", 不足以推进 R2192 任务3 实施

## cc4101 30min fallback (负向核心指标)

- **fallback = 0** ✅ 零数据空洞, 连续多轮最佳, 0 真中断, 0 双失败
- 与 R2159 (fallback=0) 持平, 无恶化

## nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)

- 30min nv_gw 日志 grep BREAKER/ANTH-BREAKER = **1 条** (比 R2159=0 多 1, 远未到 OPEN 阈值)
- nv_tier_attempts 30min 错误: pexec_success 57 / NVCFPexecRemoteDisconnected 4 / pexec_empty_200 4 / empty_200 2 / pexec_SSLEOFError 1 — 全 NVCF 上游连接类, 非旋钮能治
- breaker 远未到 OPEN 阈值. 注意 fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback. 本轮 cc4101 fallback=0.

## 参数误杀类 (全 0) ✅

- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)

- client_gone_mid_stream = **29 / 6h** (与 R2159=31 基本持平, R2289 副作用受益持续)
- timeout=164/6h(cc4101 自身非本域); server_5xx=6; stream_total_deadline=1
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)

- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2159 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2159 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2159 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)

- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮窗口 kimi 1 zombie 但属 nv_gw 检测点, 未触发新增 dump (符合单点波动)
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 kimi zombie=1 素材不足窗口(需 ≥5 才值得推进), 未实施. 是下一推进点.

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
- SR 94.7% > 85% ✅
- cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞 0 真中断)
- 无新增错误类型 ✅ (glm5_2_nv 1 cap 历史多轮已现中流背景波; kimi 1 zombie + 3 ATE 是 R2286 过渡期已知非旋钮可治上游类, 单点非持续上升)

四重佐证 nv_gw 稳:
1. 5 错全上游无害类 (glm5_2_nv 1 cap mid-stream 背景 + kimi 1 zombie + 3 ATE 过渡期阵痛收尾小波动)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (30min 1 条, 远未 OPEN 阈值)
4. 参数无漂移 (容器未重建 env 与 R2159 逐项一致)

改了反而破坏稳定带.

## 验证

0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. 容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.
