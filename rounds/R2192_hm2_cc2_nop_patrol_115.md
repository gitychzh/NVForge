# R2192 — hm2_cc2 NOP 巡检轮 115

> 全新 session 接棒. STATE.md 停 R2188 (滞后 3 轮). `git pull` 后 HEAD=4d40b85 (R2191,
> 连续第 114 NOP). STATE 滞后修正: 接棒停 R2188 实际 git 到 R2191, 以 git log + DB 重建.
> 本轮 hm2_cc2 续 R2192. 未 Read 任何 /tmp 文件.

## 数据 (HM2, 30min window)
- 101 req / 97 OK(200) / 4 错 → **SR = 96.0%**
- by model: **glm5_2_nv 96/100 = 96.0%** (主力, 全本域流量, 4 错全 stream_absolute_cap
  mid-stream 背景波)
- kimi_nv 0 req (过渡期收尾, 流量全汇 glm, 连续多轮同模式)
- error_type (nv_requests 层): stream_absolute_cap × 4
- 无 content_filter / timeout / conn / 429 / all_tiers_exhausted (nv_requests 层)
- host_machine 全 HM2 本域

## nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)
- pexec_success 53 / pexec_429 22 / pexec_empty_200 5 / pexec_conn_RemoteDisconnected 2 / pexec_500 1
- pexec_429=22 (R2191=21 略升, 仍 NVCF 账户级配额非旋钮能治; KEY_COOLDOWN=60/MIN_OUTBOUND=10
  已保守, 历史已证改大反触发更多 primary timeout 恶化, 不动)

## cc4101 30min fallback (负向核心指标)
- **真 fallback = 2** (req 7ff204ee 13:43 + req db6c76ce 13:47, both 180s full budget timeout,
  both FALLBACK-OK 救回 6639ms / 6015ms)
- **0 真中断** (2 条全救回, 与 R2186/R2187/R2188/R2189/R2190/R2191 同模式窗口边缘单例)
- 2 < 5 阈值, 不触发改动

## nv_gw 内部 NV-MS-FB-BREAKER (R1719 设计)
- NV-MS-FB-BREAKER-OPEN **26 事件** (13:48-13:52 集中, state ('OPEN',5,27/25/21/17/16) 衰减)
- 全自愈: 13:52 ATTEMPT breaker=HALF_OPEN→OPEN→CLOSED, internal ms_fb 兜底全 OK
  (NV-MS-FB-SERVED after 6639ms~6015ms, state 衰减后 CLOSED)
- 0 冒 cc 层 (cc4101 fallback=2 全救回, nv_requests 96.0% SR 不受直接影响)
- **NV-ANTH-BREAKER-FAIL 30min = 0 条** (健康)
- R2179-R2191 同模式设计行为 (NVCF 上游 pexec_429/empty_200/conn 级联 → breaker OPEN →
  internal ms_fb 兜底 → 自愈 CLOSED)

## 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR /
  client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **48 / 6h** (R2191=48 同基线, R2289 副作用 SDK 131s 客户端首字节墙
  结构性基线区间波动 42-52)
- stream_total_deadline = 2/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮,
  属 CLAUDE.md BUG-A 待查项 (SDK 客户端首字节超时是否可调 — API_FORCE_IDLE_TIMEOUT? 硬编码?)

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv],
  **default=glm5_2_nv** ← R2286 改默认模型但 nv_gw nv_default_model 仍 glm5_2_nv, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 无漂移)
  ← 与 R2184-R2191 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- docker ps: nv_gw Up 12h / cc4101 Up 22h / ms_gw Up 2d / logs_db Up 7d
- env 关键参数与 R2188 快照逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (累计 47 sample, hypothesis A 强证伪).
  本轮窗口 0 zombie, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk
  守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 0 zombie
  素材严重不足窗口 (需 ≥5 连续多轮才值得推进), 未实施. 是下一推进点.

## 决策
NOP 巡检不改代码. STATE 三触发改动阈值全不满足:
1. SR 96.0% > 85% ✅
2. cc4101 fallback 请求数 2 < 5 ✅ (且全救回, 0 真中断)
3. 无新增错误类型 ✅ (NV-MS-FB-BREAKER OPEN 26 是 R2179-R2191 连续多轮已知设计行为,
   self-healed 0 冒 cc 层)

四重佐证 nv_gw 稳:
1. nv_requests 96.0% SR (4 错全 stream_absolute_cap mid-stream 背景波, tier 错误全 NVCF
   上游连接类无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (26 OPEN 事件 13:48-13:52 集中后自愈回 CLOSED,
   NV-ANTH-BREAKER-FAIL=0)
4. 参数无漂移 (容器未重建 env 与 R2188 快照逐项一致, nv_gw StartedAt 连续多轮稳定 07-23T18:05)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-23T18:05:17Z (连续多轮未重建) /
cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

HM2 only. 未碰 proxy/ms-gw/. 未 Read 任何 /tmp 文件.
