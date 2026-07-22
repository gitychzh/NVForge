# R2140_hm2_cc2 — ATE 风暴过境轮 / 背景波已恢复 0 改动

> 轮号: R2140 (hm2_cc2 线, 接 R2137; R2138 被 hm1 peer 占用, R2139 被 storm_watch 占用, 跳过到 R2140)
> 日期: 2026-07-23 07:49 CST (DB now=23:49 UTC)
> 类型: 观测轮 (背景波过境已恢复, 非稳态退化)
> HM2 only. 铁律: 只改 HM2 不改 HM1, 不碰 ms_gw 源码.

## 数据 (HM2, 30min window, 07:49 CST 时点, DB now=23:49 UTC)

### nv_gw 30min 总览
- 89 请求 / 62 OK(200) / 27 错(502) → SR = **69.7%** (较 R2137 90.1% 大幅回落 20.4pp)
- by model:
  - glm5_2_nv 35/54 = **64.8%** (主链路大幅衰退; 上轮 94% → 砍到 64.8%)
  - dsv4p_nv 27/35 = 77.1% (8 ATE 上游已知良性)
- error_type (502): **all_tiers_exhausted 24** + stream_first_byte_timeout 2 + zombie_empty_completion 1
- by model x error:
  - glm5_2_nv: 16 ATE + 1 stream_first_byte_timeout + 1 zombie
  - dsv4p_nv: 8 ATE

### ⚠ 关键发现: ATE 风暴是 NVCF glm5.2 上游瞬时背景波, 已恢复

**时间线铁证 (glm5_2_nv ATE 按分钟分布)**:
- 23:27(2) → 23:30(1) → 23:32(1) → 23:33(2) → 23:36(2) → 23:37(2) → 23:38(2) → 23:39(1) → 23:40(2) → 23:41(1) = 共 16 ATE
- **集中 23:2723:41 这 15min 窗口**
- **23:42 之后全 200**, 近 5min (23:4423:49) = 25/26 = **96.2% SR 已恢复**

**主备双失败铁证 (证明是 NVCF glm5.2 整体不可用, 非 nv_gw 旋钮问题)**:
- cc4101 fallback 30min = **15 个 fallback 记录**, 多个 FALLBACK-FAIL:
  - req=4400fa4c [07:35] PRIMARY-FAIL (nv 60s) → [07:36] FALLBACK-FAIL (ms 60s timeout) → 双失败没救回, CC retry
  - req=3590073a [07:37] PRIMARY-FAIL (nv 60s) → [07:38] FALLBACK-FAIL (ms 60s) → 双失败
  - req=f232b51c [07:39] PRIMARY-FAIL (nv 60s) → [07:40] FALLBACK-FAIL (ms 60s) → 双失败
  - req=2850e4a1 [07:39] PRIMARY-FAIL (nv 160s > budget) → [07:41] FALLBACK-OK (ms 109s 救回) — 尾部已恢复
- **ms_gw (glm5_2_ms) 也 60s/120s header timeout** = NVCF glm5.2 主备上游整体慢, 这是上游端问题, nv_gw 旋钮 (timeout/cooldown) 治不了根因
- 这是连续多轮首次出现 **PRIMARY+FALLBACK 双失败没救回** 的真中断 (req=4400fa4c/3590073a/f232b51c), 但根因是上游背景波非 nv_gw 异常

### NV-MS-FB-BREAKER 真 OPEN (R1719 设计正常吸收, 已恢复)
- 30min 出现多条 NV-MS-FB-BREAKER-OPEN (state=('OPEN', 5, 27)):
  - @07:18 req=7fa03c43 (state OPEN 5,27)
  - @07:36 req=f69d3183, @07:37 req=23fc030e/c405ff96, @07:38 req=f69d3183, @07:40 req=b8695d50
- 多条 NV-MS-FB-BREAKER-OPEN-MSFAIL: breaker OPEN 但 ms_gw 也失败 → fall through nv chain (HALF_OPEN probe)
- 这是 R1719 `nv_breaker` (mid-stream 软挂累积 → OPEN 直走 ms) 设计正常行为: NVCF glm5.2 上游整体不可用时, breaker OPEN 试图甩 ms, 但 ms 也挂 (上游整体慢), 于是 fall through 回 nv HALF_OPEN probe 探活, 23:42 后 probe 成功 → CLOSED
- 最后一条 NV-ANTH-BREAKER-FAIL @07:41 state=('CLOSED', 3, 0) → 已恢复 CLOSED, 未持续 OPEN

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0
- client_gone 在 nv_gw 侧不记 (cc4101 侧记, 见下)

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = 49 / 6h (同 R2137 50/6h 量级, 持续基线)
- timeout = 7 / 6h; stream_total_deadline = 4 / 6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 属 CLAUDE.md BUG-A 待查项

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2137 一致无漂移)
- env 关键参数与 R2137 逐项一致, 无参数漂移:
  - MIN_OUTBOUND_INTERVAL_S=10 / KEY_COOLDOWN_S=60 / UPSTREAM_TIMEOUT=90
  - TIER_TIMEOUT_BUDGET_S=180 / TIER_COOLDOWN_S=180
  - NVU_TIER_BUDGET_GLM5_2_NV=120 / NV_INTEGRATE_KEY_COOLDOWN_S=90

## 决策: 观测轮, 0 改动 0 restart

**为何不改 (SR 破阈值但根因不可治 + 已恢复)**:
1. **30min SR 69.7% 破 85% 阈值, 但尖峰已过**: 23:4249 全 200, 近 5min 96.2% 恢复. 这不是稳态退化, 是上游瞬时背景波过境.
2. **根因是 NVCF glm5.2 上游整体不可用, 非 nv_gw 旋钮能治**: 主备双失败铁证 (连 ms_gw glm5_2_ms 也 60s/120s header timeout) = 上游端 glm5.2 整体慢, nv_gw 的 timeout/cooldown/key 轮换都救不了"上游整体不响应".
3. **breaker NV-MS-FB 真 OPEN 是 R1719 设计正常吸收**: 上游不可用时 OPEN 试图甩 ms, ms 也挂则 fall through HALF_OPEN probe, 恢复后 CLOSED. 这是设计意图, 不是 nv_gw 故障. 改高 breaker 阈值会"假装不 OPEN"把死循环请回来 (CLAUDE.md 明确警告).
4. **容器无漂移**: env 一致, StartedAt 07-22T15:10:34Z 未变, RC=0. 没有参数被改.
5. 改 nv_gw 旋钮 (如 UPSTREAM_TIMEOUT 90→更高) 反而: 上游背景波时让请求挂更久才失败, 增大 cc2 SDK 131s 客户端墙触发 499 的概率. 无益有害.

**与 R2137 的区别**: R2137 是稳态冻结 (无背景波, 三阈值全不满足), 本轮是**背景波过境已恢复** (SR 破阈值但根因不可治且已恢复). 两者都判 0 改动, 但触发条件不同, 需 STATE 明确标注防下轮误读.

## R2192 三任务进度 (巡检轮必报)
- **任务1** (cc4101 透传 cache_control): ✅ 已落地 R2228, cache_read 0%→38.8%. 本轮未验证命中率 (背景波窗口不宜测), 下轮稳定窗口复核.
- **任务2** (nv_gw 抓 zombie body dump probe): **未做**. 本轮 30min 1 zombie (req=23fc030e, 也是 breaker OPEN 后 fall through 的那个). 单点不足以触发 dump probe (需 ≥3 持续). 但本轮有真实 zombie req id, 若下轮 zombie 持续 ≥3/30min 则优先做任务2.
- **任务3** (路径B zombie 内部重试): **部分**. _ms_fallback_request 存在, 但 zombie 检测点"200+message_start 已发→不能切 ms 重放"约束未解 (双 message_start 错乱). 需设计 converter feed_chunk 内部重试.

## 验证
0 改动 0 restart 无需验证改动. 容器状态确认:
- curl /health ok + docker ps 全栈 Up (nv_gw/cc4101/ms_gw/logs_db)
- nv_gw StartedAt=07-22T15:10:34Z (docker inspect 实测连续多轮 RC=0 未重建)
- env 无漂移 (逐项核对 R2137 一致)
- 近 5min SR 96.2% 恢复确认背景波过境

## 下一轮该做什么
1. **先拉数据判背景波是否再起**: 若 30min SR 恢复 ≥95% 且无新 ATE 风暴 → 回到稳态冻结节奏 (R2137 模式). 若 ATE 风暴再起 (glm5_2_nv ATE 集中某 15min 窗口) → 仍判上游背景波, 0 改动, 但记录风暴频次 (若 6h 内 ≥2 次风暴且每次主备双失败, 需评估是否上游持续不可用而非瞬态).
2. **主链路 zombie 跟踪**: 本轮 1 zombie (req=23fc030e) + 上轮 2 zombie (req a36a7cdb/31de5687) = 2 轮共 3 zombie. 若下轮再有 ≥1 zombie → 累计 3 轮 zombie 信号, **触发 R2192 任务2** (handlers.py zombie 检测点加 oai_body 落盘 dump probe, 对比成功请求字段差异, 验证四推测 A/B/C/D). 本轮有素材 (req=23fc030e) 但单轮单点不足.
3. **cc4101 fallback 趋势**: 本轮 15 fallback 含 3 双失败没救回 (req 4400fa4c/3590073a/f232b51c) 是 R2182 后首次双失败再现. 但根因是上游 ATE 风暴主备双挂, 非稳态. 若下轮 SR 恢复后仍见双失败 → 需评估. 若 SR 恢复后 fallback 归零或全救回 → 视为本轮双失败是背景波瞬时.
4. **触发改动阈值** (全满足才动): 30min SR<85% **且** 不是上游背景波 (即主备不双失败, 只是 nv_gw 单链路问题) **或** cc4101 fallback 请求数 >5/30min 且是新 req id 且非上游整体慢 **或** 出现新错误类型持续. 本轮虽 SR 破阈值但因上游背景波+主备双失败+已恢复, 不满足"非背景波"条件.
5. 主仓 R22XX (HM2->HM1) 是 HM1 peer 轮, HM2 不参与, 保持 HM2 稳态.
6. 下一 session 接棒若 STATE 被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**.
7. **轮号体系**: R21XX (hm2_cc2/hm2_oc2) 是 HM2 本域; R22XX 只改 HM1 不碰. R2138/R2139 已被 hm1/storm_watch 占用, 本轮用 R2140 hm2_cc2. 接棒以 HEAD 为准.
8. **容器漂移**: nv_gw StartedAt=07-22T15:10:34Z 连续多轮未变. 若下轮变 + 参数漂移, 需查是谁改的.
9. **R2192 三任务** (ULTIMATE GOAL 撤 40007): 任务1已落地持续验证; 任务2未做 (本轮有 1 zombie 素材, 下轮若 zombie 持续则优先做); 任务3部分 (双 message_start 约束未解).
