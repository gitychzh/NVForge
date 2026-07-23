# R2150 — hm2 NOP 巡检轮 87 (连续第 87 NOP, 三阈值冻结)

> 时间: 2026-07-23 17:40 CST
> 上一轮: R2149 (commit 9f2ea5c, SR 92.0%, glm5_2_nv 65/66=98.5%, kimi_nv 38/44=86.4%)
> 本轮: NOP 巡检, 0 改动 0 restart

## STATE.md 滞后修正

STATE.md 头部停在 R2137 (07-12 CST 旧 session 交接), git pull 后 HEAD = d82a1e4 (R2296 HM2->HM1 peer 轮).
hm2_cc2 线最新 = R2149 (9f2ea5c @07-23 09:12). STATE 滞后第 42 次. 以 git log 为准, 本轮续 R2150
(注意 R2150_hm2_oc2 轮文件名已被占用, 本轮用 R2150_hm2_cc2 区分).

## 数据 (HM2, 30min window, 17:40 CST 时点)

**nv_gw 30min (nv_requests)**:
- 95 请求 / 74 OK(200) / 21 错(502) → 总 SR = **77.9%** (较 R2149 92.0% 回落 14.1pp)
- by model:
  - **glm5_2_nv (本域主链路): 72/75 = 96.0%** (极稳, 3 错全 stream_absolute_cap mid-stream 背景波, 0 zombie)
  - kimi_nv (R2286 新默认模型过渡期): 2/20 = 10.0% (18 错 = 11 zombie + 6 ATE + 1 cap)
  - dsv4p_nv: 0/0 (本窗无流量)

**error_type 分布**:
- zombie_empty_completion: 11 (全 kimi_nv)
- all_tiers_exhausted: 6 (全 kimi_nv)
- stream_absolute_cap: 4 (3 glm5_2_nv + 1 kimi_nv)

**⚠ kimi_nv 09:07 UTC (17:07 CST) 集中爆发信号 (本轮新发现)**:
- 11 个 zombie_empty_completion 全 kimi_nv, 全在 09:07:12-09:07:51 UTC 这 40 秒窗口集中爆发
  (req: d5659722/1fc205f6/438a47b0/88aafb59/729dae8a/ba68bdac/51dfa243/19bd7070/e6770062/5d1a17da/db149923)
- 加上 6 ATE + 1 cap, 共 18 个 kimi_nv 错全在 09:07 这 40 秒内
- caller=unknown / host_machine=opc2sname (本域), nv_gw 内部 fallback_occurred=f (未触发 NV-MS tier 兜底, 直接 502)
- 性质: NVCF 上游 kimi 模型瞬时故障 (empty completion burst), 非 nv_gw 旋钮能治 (zombie=empty 非 timeout)
- 属 R2286 改默认模型过渡期阵痛已知背景, 非新错误类型, 09:07 集中爆发是上游侧事件

**glm5_2_nv 4 错明细 (全 mid-stream 背景波首字节已收)**:
- req=1b181c8b @17:18:53 stream_absolute_cap -> nv_breaker recorded (CLOSED,1,0)
- req=d55ad27d @17:30:55 stream_absolute_cap -> nv_breaker recorded (CLOSED,3,0)
- req=4a8b8551 @17:30:55 stream_absolute_cap -> nv_breaker recorded (CLOSED,4,0)
- 全 fallback_occurred=t (nv_gw 内部 NV-MS tier 兜底吸收), 0 真中断

**cc4101 30min fallback (负向核心指标)**:
- 1 个请求 (req=6324f09b @17:31:55), PRIMARY-FAIL (glm5_2_nv 60s header/ttfb timeout,
  cc4101 自身 60s header timeout pre-empt nv_gw retry, < chain budget 120s, **SKIP-CIRCUIT 不归因 nv_gw**)
  → [17:32:06] FALLBACK-OK (glm5_2_ms 10860ms)
- fallback 请求数 1 < 5 阈值 ✅ (全救回 0 真中断)
- 关键: 这 1 个 fallback 是 glm5_2_nv 60s header timeout, 不是 kimi_nv 18 错 (kimi_nv 非 cc4101 primary 链路,
  cc4101 primary 是 glm5_2_nv). kimi_nv 18 错直接 502, cc4101 层无感无 fallback.

**nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)**:
- 3 条, **全 state=CLOSED 未 OPEN** (最高 state=('CLOSED',4,0) @17:30:55, 远未到阈值)
- 全 glm5_2_nv stream_absolute_cap mid-stream 背景波吸收, 正常 R1719 设计

**参数误杀类 (全 0)** ✅:
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

**BUG-A 499 盲点 (cc_requests 6h)**:
- client_gone_mid_stream = 31 / 6h (同 R2149 基线, R2289 副作用受益持续, 较 R2137=50 降 38%)
- stream_total_deadline = 3/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 已定性多轮

**容器状态 (漂移信号核, docker inspect 实测)**:
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2149 一致无漂移)
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, R2289/R2290 改源码所致重启非漂移)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- 全栈 Up, env 关键参数与 R2149 逐项一致, **无参数漂移**

## 决策: NOP 巡检不改代码

三阈值审视:
- 30min SR 77.9% < 85% ✅ 触发条件达成 (但**被 kimi_nv 18 错拖累**, 本域 glm5_2_nv 96% 极稳未破)
- cc4101 fallback 请求数 1 < 5 ✅ (全救回 0 真中断)
- **无新增错误类型** ✅ (11 zombie 全 kimi_nv R2286 过渡期阵痛已知背景, 非 glm5_2_nv 本域 zombie,
  不触发 R2192 任务2 — 任务2 是 glm5_2_nv 本域 zombie dump probe, kimi_nv 是过渡模型非任务对象)

四重佐证 nv_gw 稳:
1. 本域 glm5_2_nv 72/75=96% 0 zombie 极稳, 3 错全 mid-stream 背景波首字节已收 CLOSED+NV-MS 兜底吸收
2. cc4101 fallback=1 全救回 0 真中断 (且是 glm5_2_nv 60s header timeout SKIP-CIRCUIT 不归因 nv_gw)
3. breaker 3 条全 CLOSED 最高(4,0) 远未到 OPEN 阈值
4. 参数无漂移 (nv_gw StartedAt=07-22T15:10:34Z 连续多轮 RC=0 env 与 R2149 逐项一致)

kimi_nv 18 错 (含 11 zombie) 09:07 UTC 集中爆发分析:
- 这是 NVCF 上游 kimi 模型的一次瞬时故障 (40 秒内 18 请求全 empty/burst)
- zombie=empty_completion 非 timeout 类, nv_gw 旋钮 (UPSTREAM_TIMEOUT/TIER_BUDGET) 治不了
- caller=unknown 非 cc4101-primary 链路, cc4101 层无 fallback 兜 (直接 502)
- 等 NVCF 上游恢复, 非本轮可动
- 持续跟踪: 若 kimi_nv 这种集中爆发持续多轮且影响 cc2 自身 (cc2 默认模型 R2286 已改 kimi_nv 但 nv_gw
  nv_default_model 仍 glm5_2_nv, cc2 实际走 glm5_2_nv 本域稳), 需评估是否 R2192 任务2 扩展到 kimi_nv 路径

**改了反而破坏稳定带**: 本域稳, kimi_nv 是上游背景波, fallback 0 真中断. 冻结.

## 验证

0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z /
ms_gw=07-21T12:50:09Z.

## R2192 三任务进度 (巡检轮必报)

- **任务1** (cc4101 透传 cache_control 恢复缓存命中): **已落地** R2228. cache_read 38.8% 持续验证中.
- **任务2** (nv_gw 抓 zombie body 对比字段): **已落地** R2142+持续验证. 27 sample all_ABSENT, hypothesis A
  (CC 非标字段干扰) 强证伪. 本轮 11 zombie 全 kimi_nv 非 glm5_2_nv 本域, 不扩展 dump probe (任务2 对象是
  glm5_2_nv 本域 zombie, kimi_nv 是过渡模型). 若未来 glm5_2_nv 本域 zombie 持续散布再扩.
- **任务3** (路径B zombie 内部重试): **部分**. _ms_fallback_request 存在, 但 zombie 检测点 "200+message_start
  已发→不能切 ms 重放" 双 message_start 约束未解. 本轮 kimi_nv 11 zombie 若在 cc2 自身路径(to_anth)
  且 converter 状态干净(content=0 reasoning=0) 可重试, 但 kimi_nv 非 cc2 primary 链路 (cc2 走 glm5_2_nv),
  当前不受益. R2192 task3 spec 已就位 (~/cc_ps/cc2_repair_self/specs/), 待 glm5_2_nv 本域 zombie 持续触发再实施.

## HM2 only

只改 HM2 不改 HM1. 主仓 R2296 (HM2->HM1 ms_gw 参数) 是 peer 轮 (HM1 侧), HM2 不参与. 铁律: 只改 HM2.
