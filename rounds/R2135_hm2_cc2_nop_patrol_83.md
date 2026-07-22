# R2135 (hm2_cc2): NOP 巡检轮 83 — 稳态延续, 三阈值冻结

> 全新 session 接棒. STATE.md 滞后停在 R2196 (旧交接未更新), 但 `git pull` 后主仓最新 hm2_cc2 轮为
> R2134 (13cd7be). 以 git log 为准, 本轮续 **R2135** (NOP 巡检轮 83).
> STATE.md 头部记录的 nv_gw StartedAt=07-21T12:50:09Z 是 R2196 旧值, R2134 已记 07-22T15:10:34Z
> (与本轮实测逐项一致), 容器无漂移, STATE 纯滞后.

## 数据 (HM2, 30min window, ~06:10 时点)

**nv_requests 30min**:
- 85 请求 / 79 OK(200) / 6 错(502) → SR = **92.9%**
  (较 R2134 30min 98.6% 回落, 但 R2134 是 30min 单窗口 glm5_2_nv 69/70 最干净窗口, 本轮含
  dsv4p_nv 23 条拉低整体; 主链路 glm5_2_nv 单看仍稳, 见下)
- by model: glm5_2_nv 60/62 = **96.8%** SR (2 错全 stream_no_content_gap 中游流背景波, 首字节已收
  未触发 fallback); dsv4p_nv 19/23 = 82.6% (4 错全 all_tiers_exhausted NVCF function ATE 上游已知良性)
- 6 错 error_type: all_tiers_exhausted(4, 全 dsv4p_nv) + stream_no_content_gap(2, 全 glm5_2_nv)
- 无 zombie / content_filter / timeout / conn / 429
- host_machine 全 HM2 本域

**cc4101 30min fallback (负向核心指标)**:
- 2 个请求 (ad4661ac 05:40 + 7216e60e 06:06), **全 PRIMARY-FAIL-SKIP-CIRCUIT + FALLBACK-OK, 0 真中断**
  - ad4661ac [05:40:43] PRIMARY-FAIL glm5_2_nv header/ttfb timeout 60069ms < chain budget 120s
    (cc4101 自身 60s header timeout pre-empt nv_gw retry, 不归因 nv_gw, 不计 circuit)
    → [05:41:03] FALLBACK-OK ms_gw glm5_2_ms 20277ms 救回
  - 7216e60e [06:06:46] PRIMARY-FAIL 同型 60072ms → [06:07:04] FALLBACK-OK ms 17685ms 救回
- 关键判读: 两个 fallback 的 PRIMARY-FAIL 都是 cc4101 自身 60s header timeout 在 chain budget
  (120s) 之前 pre-empt 掉 nv_gw 的重试 — **不归因 nv_gw 参数** (nv_gw TIER_TIMEOUT_BUDGET=180s
  本可继续 retry, 是 cc4101 先放弃). 这是 cc4101 层的 pre-empt 行为, 不是 nv_gw 病.
- ad4661ac 05:40 是 R2134 已记录的旧事件 (R2134 commit msg 明确提 req=ad4661ac 05:40), 本窗口滑入;
  7216e60e 06:06 是真新发但全救回 0 真中断.
- fallback 请求数 2 < 5 阈值 ✅

**cc_requests 499 6h (BUG-A 盲点指标, CLAUDE.md 必查)**:
- client_gone_mid_stream (499) = **51/6h**
- stream_total_deadline = 4/6h
- (error_type 为空 745 条 = 正常 200 响应无 error)
- **判读**: 499=51/6h 与 R2134 记录的 50/6h 同量级, 是 cc2 SDK ~131s 客户端首字节墙结构性限制
  (R2134/R2203 已结论铁证: 改后 499 primary_elapsed_ms=空但 duration=131124ms = cc2 在 131s 自断).
  **非 nv_gw 旋钮能治**, 属 CLAUDE.md BUG-A 待查项 (查 CLI 客户端超时旋钮), 不在本轮 nv_gw 范围.

**breaker + 参数误杀类 30min**:
- NV-ANTH-BREAKER-FAIL / STREAM-STALL-FAIL / BIG-INPUT / 75s_timeout / UPSTREAM-ERROR-SEEN 匹配 2 处
  (grep -cE, 实为 nv_gw 日志中 breaker 状态 CLOSED 单点或 fastbreak 提及, 非真 OPEN)
- → **非参数误杀, breaker 未真 OPEN**

**容器状态 (漂移信号核)**:
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough, default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=2026-07-22T15:10:34Z
  (**与 R2134 记录的 15:10:34Z 逐项一致 → R2080 重建后连续第 45 轮 RC=0 未重建**, 漂移信号止住)
- cc4101 RestartCount=0 StartedAt=2026-07-22T14:28:23Z (R2134 已知窗口 RC=0)
- ms_gw Up 33 hours (热备正常, 本轮未碰)
- env 关键参数与 R2134 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150/
  NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/BIG_INPUT 阈值同), **无参数漂移**

## R2192 三任务进度 (CLAUDE.md 持久任务, 巡检必报)

1. **任务1 (cc4101 透传 cache_control)**: ✅ 已落地 (R2228, cache_read 0%→38.8%, 走 nv_gw 读
   NVCF prompt_tokens_details.cached_tokens 路径, cc4101 passthrough 已透传). 本轮未复查命中率,
   下次 6h 复核窗口顺带验证不退化.
2. **任务2 (nv_gw 抓 zombie body dump probe)**: ⏳ 未做. 本轮 0 zombie (6 错全 ATE+no_content_gap,
   无 zombie_empty_completion), 无素材. handlers.py L779 有 oai_body 但无 dump 到文件. 需等
   zombie 窗口出现再加 probe (本轮无素材不可强做).
3. **任务3 (路径B zombie 内部重试)**: 🔶 部分. _ms_fallback_request 存在但 zombie 检测点
   "200+message_start 已发→不能切 ms 重放" 约束未解 (双 message_start 错乱). 需设计 converter
   feed_chunk 内部重试. 本轮 0 zombie 无触发, 无进展.

## 决策: NOP 巡检, 0 改动 0 restart

STATE 三触发改动阈值全不满足:
- SR 92.9% > 85% ✅ (主链路 glm5_2_nv 96.8% 稳, 整体被 dsv4p_nv 拉低但 dsv4p 是 NVCF 上游 ATE)
- cc4101 fallback 请求数 2 < 5 ✅ (全 SKIP-CIRCUIT 不归因 nv_gw, 全救回 0 真中断)
- 无新增错误类型 ✅ (2 no_content_gap + 4 ATE 全上游同族背景波)

四重佐证 nv_gw 稳: 主链路 glm5_2_nv 96.8% (2 错全中游流背景波非参数误杀) / fallback 全
SKIP-CIRCUIT 不归因 nv_gw (cc4101 60s pre-empt 非 nv_gw 病) / breaker 未真 OPEN / 参数无漂移
(容器连续第 45 轮 RC=0). 改了反而破坏 R2154 稳定带.

**499=51/6h 是 BUG-A 已知未破项** (cc2 SDK 131s 客户端墙结构性限制), R2134/R2203 已结论非
nv_gw 旋钮能治, 不在本轮 nv_gw 范围. 如要推进需查 claude CLI 客户端首字节超时旋钮
(API_FORCE_IDLE_TIMEOUT? 或 SDK 硬编码), 属 CC 基础设施侧待查, 非 nv_gw 源码改动.

## 验证

0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 +
env 无漂移 (与 R2134 逐项一致). 容器 StartedAt: nv_gw=07-22T15:10:34Z (连续第45轮未重建同 R2134),
cc4101=07-22T14:28:23Z (R2134 窗口 RC=0).

## 下一轮建议

1. 继续巡检. 盯 75s_timeout / STREAM-STALL-FAIL 持续归零 (本轮非真 OPEN ✅).
2. cc4101 fallback 趋势: 本轮 2 全 SKIP-CIRCUIT 不归因 nv_gw. 若下轮出现 PRIMARY+FALLBACK 双失败
   没救回, 或 fallback 请求数升到 ≥5/30min (且是新 req id 非 SKIP-CIRCUIT), 需评估. 但动也
   治不了 NVCF 上游 header/ttfb 慢 (本轮 2 个 fallback 全是 cc4101 60s pre-empt, nv_gw 180s
   budget 本可 retry 但被 cc4101 先放弃).
3. 盯 NV-ANTH-BREAKER-FAIL 真 OPEN (本轮未 OPEN). fallback_occurred=true ≠ cc4101 fallback,
   前者是 nv_gw 内部 NV-MS-FB tier 兜底正常吸收, 后者才是负向指标.
4. **BUG-A 499=51/6h**: 下一轮若要推进, 查 claude CLI 客户端首字节超时旋钮是否可调
   (非 nv_gw 源码). 若不可调, 接受 499 是 SDK 限制, 转 nv_gw 端容忍设计.
5. **R2192 任务2**: 需等 zombie 窗口出现 (本轮 0 zombie). 若连续多轮 0 zombie, 任务2 无素材
   可搁置, 优先级低于稳态巡检. 任务3 同理 (依赖任务2 字段对比结论).
6. 触发改动三阈值 (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback 请求数
   >5 条/30min (且非 SKIP-CIRCUIT 即真归因 nv_gw) **且** 出现新错误类型 (zombie 比例上升 /
   NV-ANTH-BREAKER-FAIL 真 OPEN).
7. 主仓 R227X alternating 是 HM1 peer 轮 (only HM1), HM2 不参与, 保持 HM2 稳态. 铁律: 只改 HM2.
8. 数据库列名: nv_requests 列是 `request_model` (不是 model), `status` 是 integer (200/502).
9. 下一 session 接棒若 STATE 又滞后: 用 `git log --oneline -8` 找最新 hm2_cc2 轮号重建,
   **绝不 Read /tmp** (上次 session 因反复 Read 不存在的 /tmp 文件陷入 tool-use 死循环被
   SDK 看门狗中断).

HM2 only. 连续 79 NOP.
