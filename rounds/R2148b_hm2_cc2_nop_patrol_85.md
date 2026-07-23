# R2148b (hm2_cc2) — NOP 巡检轮, 连续第 85 NOP

- **日期**: 2026-07-23 16:19 CST (08:19 UTC)
- **模式**: nv 直连 (cc4101→nv_gw), 默认模型 nv_gw 侧仍 glm5_2_nv (health 实测)
- **改动**: 0 改动, 0 restart (NOP 巡检轮)
- **轮号说明**: hm2_cc2 线最新 commit = R2147 (2fde030 @07-23), 本轮续其后. R2148 文件名被 07-21 旧残留 (3df143d, 内容 R173 连续108轮, 07-21 空间) 占用, R2149 被 HM1 线文件占用, 故本轮用 R2148b 避开命名冲突 (符合 STATE 第 9 条: 接棒以 HEAD 为准, 07-21 旧命名空间已覆盖).

## STATE 滞后修正
STATE.md 头部停 R2137 (07-12 时点数据), 严重滞后 (第 40 次). `git pull` 后 HEAD = 79070a7 (R2291 HM2->HM1). hm2_cc2 线最新 = R2147 (2fde030 @07-23). 以 git log 为准, 本轮续 R2148b.

## 数据 (HM2, 30min 窗口, 16:18 CST 时点)

**nv_gw 30min SR = 79/86 = 91.9%** (glm5_2_nv 79/80=98.75% 主链路极稳; dsv4p_nv 0/6 全 ATE)

**by model**:
- **glm5_2_nv 79/80 = 98.75%** ✅ 主链路连续多轮稳, 1错 = 1 zombie_empty_completion (req=baf118e8 @08:03 UTC=16:03 CST)
- dsv4p_nv 0/6 全 all_tiers_exhausted (NVCF 74f02205 恶化延续, 非本域已知良性)
- 无 kimi_nv 流量 (窗口时点不同, kimi 6h 31/38=81.6%)

**error_type (30min)**: 6 all_tiers_exhausted (dsv4p) + 1 zombie (glm5_2_nv). 无 content_filter/timeout/conn/429.

**glm5_2_nv 30min 唯一错**: zombie_empty_completion req=baf118e8 @16:03 CST, mid-stream 上游背景波, BREAKER 记录 state=(CLOSED,1,0) 未 OPEN.

## 6h 窗口 (背景)
- glm5_2_nv 6h 437/550 = 79.5% (含风暴窗残留 ATE 100, 但 30min 主链路已 98.75% 恢复)
- dsv4p_nv 6h 186/281 = 66.2% (ATE 92, NVCF 74f02205 恶化延续非本域)
- kimi_nv 6h 31/38 = 81.6% (cc2 R2289 改默认模型域外过渡期)

## cc4101 fallback (负向核心指标) — 30min
- **0 个 fallback 请求** ✅ (零数据空洞! 连续多轮最佳点)
- 0 PRIMARY-FAIL / 0 FALLBACK-OK / 0 FALLBACK-FAIL / 0 真中断

## nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 1 条 state=(CLOSED, 1, 0) (req=baf118e8 @16:03), 未 OPEN, 远未到阈值
- fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback. 本轮 cc4101 fallback=0.

## 参数误杀类 (全 0) ✅
75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone 内部误杀全 0.

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **31 / 6h** (较 R2137 基线 50 降 38%, R2289 改默认模型 + 1M→120K settings 副作用受益, 持续健康)
- stream_total_deadline = 3/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2147 一致无漂移) — docker inspect 实测
- cc4101 RestartCount=0 StartedAt=**2026-07-23T07:38:11Z** (R2289/R2290 改 cc4101 源码所致重启, 非漂移, 已定性多轮)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0, 重启窗口热备)
- 全栈 Up: nv_gw 17h / cc4101 40min / ms_gw 43h / logs_db 6d
- env 关键参数与 R2147 逐项一致, **无参数漂移**

## R2192 三任务进度 (ULTIMATE GOAL 撤 40007, 每轮必报)
从 git log R2290 (commit 87e428d) 读取:
- **任务 1 (cc4101 透传 cache_control)**: ✅ 已落地, cache_read 38.8% 持续验证中
- **任务 2 (nv_gw 抓 zombie body dump probe)**: ✅ 已落地, 27 sample all_ABSENT, hypothesis A (CC 非标字段干扰 NVCF) 强证伪
- **任务 3 (路径B zombie 内部重试)**: ⚠️ 部分, 双 message_start 约束未解 (converter feed_chunk 第二流会双 message_start 错乱, 需设计守卫)
- 本轮 30min 仅 1 zombie (baf118e8), 无新素材, 三任务无需推进. 任务 3 是撤 40007 核心前置, 下轮若 zombie 持续 ≥3/30min 连续 2-3 轮, 优先推进任务 3 设计.

## HM1 peer 线 (铁律: 只改 HM2 不改 HM1)
- R2290/R2291 (HM2->HM1) 是 HM1 peer 轮: R2291 改了 HM1 的 NVU_TIER_BUDGET_GLM5_2_NV 200→210 (+10s).
- **HM2 实测 env NVU_TIER_BUDGET_GLM5_2_NV=120** (非 210), 确认 HM1/HM2 独立, HM2 未被波及, 符合铁律第 6 条.

## 决策: NOP 巡检, 0 改动 0 restart
STATE 三触发改动阈值全不满足:
- SR 91.9% (glm5_2_nv 98.75%) > 85% ✅
- cc4101 fallback 30min = 0 < 5 ✅ (零数据空洞, 连续多轮最佳)
- 无新增错误类型 ✅ (1 zombie 历史多轮已现; dsv4p 6ATE NVCF 74f02205 已知良性非本域)
四重佐证 nv_gw 稳: 主链路 glm5_2_nv 98.75% 极稳 / 无参数误杀(全0) / breaker 不真 OPEN(1条CLOSED state(1,0)远未到阈值) / 参数无漂移(容器未重建 env 与 R2147 逐项一致). 改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. 容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z (改源码所致非漂移) / ms_gw=07-21T12:50:09Z.

HM2 only. 铁律遵守: 只改 HM2, 不碰 ms_gw 源码, 不碰 HM1.
