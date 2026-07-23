# R2142 (hm2_cc2) — NOP检轮 连续第 83 NOP 三阈值冻结

> 全新 session 接棒. STATE.md 头部停在 R2137 (07-12 CST 旧 session), 但 `git pull` 后
> HEAD = 938d283 (R2285 HM2→HM1 @07-23 更新), hm2_cc2 线最新 commit = **R2141 (b86e234)**.
> STATE 滞后修正第 39 次 (头部停 R2137, 实际 cc2 线最新已 commit R2141, 本轮续 R2142).
> 以 git log 为准, 本轮 hm2_cc2 续 R2142 (R2141=b86e234 已 commit, 本轮在其后).

## 数据 (HM2, 30min window, 07-23 ~12:50 CST 时点)
- 96 请求 / 89 OK(200) / 7 错(502) → SR = **92.7%**
- by model:
  - **glm5_2_nv 64/67 = 95.5%** (主链路; 3 错 = 1 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout, 全 mid-stream 上游背景波首字节相关类)
  - dsv4p_nv 25/29 = 86.2% (4 错全 all_tiers_exhausted, NVCF function ATE 上游已知良性)
- error_type: 4 all_tiers_exhausted(dsv4p) + 1 zombie(glm5_2_nv) + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- 无 content_filter / timeout / conn / 429
- host_machine 全 HM2 本域

## 与近几轮 SR 对比 (主链路 glm5_2_nv)
- R2142 本轮: 64/67 = 95.5% (3 错 1z+1IR+1fbyte)
- R2141 (b86e234): 51/55 = 92.7% (4 错 z+IR+cap+fbyte)
- R2137 (0553f7f): 63/67 = 94.0% (4 错 2z+IR+cap)
- R2136 (6226aed): 72/73 = 98.6% (1 错 stream_no_content_gap)
- 本轮主链路 95.5% 较 R2141 (92.7%) 回升 2.8pp, 较 R2137 (94.0%) 微升, 稳态正常波动.
- zombie 1 个 (req=eb1dc03e, 见 breaker 日志), 较 R2141 (1z) 持平, 较 R2137 (2z) 下降, 非持续扩散.

## cc4101 30min fallback (负向核心指标)
- fallback 请求数 = **0** (30min 全无 PRIMARY-FAIL/FALLBACK 事件, 0 真中断)
- 较 R2141 (1 全救回) 更干净, 较 R2137 (3 全救回) 大幅改善.
- 这是连续多轮 fallback 最低点之一, nv_gw 本身 + 上游 glm5_2_nv 头部响应稳.

## nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 1 条记录: req=eb1dc03e @12:48:46, state=('CLOSED', 2, 0), err=NVAnth_IncompleteRead
- **全 CLOSED 未 OPEN** (state 2 远未到阈值), 正常吸收
- 注意: fallback_occurred (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback (本轮 cc4101 fallback=0 最佳)

## 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **34 / 6h** (持续下降趋势: R2137=50 → R2141=37 → R2142=34)
- stream_total_deadline = 3/6h; timeout = 164 (含 cc4101 内部超时标记非 nv_gw 链路失败)
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项
- 499 持续下降是好信号 (可能背景波减弱或上游 TTFB 改善), 但根因结构性限制未破

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2141/R2137/R2136 完全一致无漂移) — docker inspect 实测
- cc4101 RestartCount=0 StartedAt=2026-07-22T14:28:23Z (RC=0, 同 R2141 窗口)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0) — 旧 STATE 曾错记成 nv_gw 的值, R2135 起已修正
- nv_gw Up 14h / cc4101 Up 15h / ms_gw Up 40h / logs_db Up 6d 全栈 Up
- env 关键参数与 R2141 逐项一致, **无参数漂移**

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
- SR 92.7% > 85% ✅
- cc4101 fallback 请求数 0 < 5 ✅ (最佳 0 真中断)
- 无新增错误类型 ✅ (zombie 1 个历史多轮已现非首现; 7 错全上游类)

四重佐证 nv_gw 稳:
1. 7 错全上游无害类 (glm5_2_nv 3 软失败全 mid-stream 背景波首字节已收 CLOSED 吸收 + dsv4p 4 ATE 已知良性)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (1 条全 CLOSED, state=2 远未到阈值)
4. 参数无漂移 (容器未重建 env 与 R2141 逐项一致)

改了反而破坏稳定带. fallback=0 是连续多轮最佳, 说明 nv_gw 当前配置正吸收上游波动.

## R2192 三任务进度 (ULTIMATE GOAL 撤 40007)
- **任务 1** (cc4101 透传 cache_control): **已落地** (R2228, cache_read 0%→38.8%, 走 nv_gw 读 NVCF prompt_tokens_details.cached_tokens 路径). 本轮未单独查 cache 命中率, 持续验证中, 无退化信号.
- **任务 2** (nv_gw 抓 zombie body dump probe): **未做**. 本轮 1 zombie (req=eb1dc03e) 单点非持续, 三阈值不满足冻结不动. 累计 R2137(2z)+R2141(1z)+R2142(1z)=4 zombie 跨 3 轮但散布无连续扩散, 未达触发条件 (连续 2-3 轮 ≥3 个/30min).
- **任务 3** (路径B zombie 内部重试): **部分**. _ms_fallback_request 存在但 zombie 检测点 "200+message_start 已发→不能切 ms 重放" 约束未解 (双 message_start 错乱). 需设计 converter feed_chunk 内部重试, 留后.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-22T14:28:23Z / ms_gw=07-21T12:50:09Z.

## 铁律
- 只改 HM2 不改 HM1 (HM1 peer R22XX 线不碰)
- 不碰 40007 (ms_gw 是重启窗口热备)
- 改前有数据 改后有验证 写轮文件 commit push

## 结论
连续第 83 NOP. nv_gw 稳态延续, fallback=0 连续多轮最佳, 499 持续下降 (50→37→34). 三阈值全不满足冻结, 0 改动 0 restart. HM2 only.
