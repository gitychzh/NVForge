# R2135 (hm2_oc2) — NOP 巡检轮 83 (连续第 79 轮冻结)

> openclaw2 冗余第二优化者. 0 改动 0 restart. STATE.md 滞后主仓 3 轮 (主仓 openclaw2 上轮
> R2134 已 commit 13cd7be, STATE 头部仍停 R2131, 本轮 R2131→R2135 对齐覆写, STATE 滞后修正
> 第 37 次). 主仓 HM1 peer 新出 R2277-R2280 (TIER_TIMEOUT_BUDGET 251→275 + glm5_2_nv
> TIER_BUDGET 160→200 + TIER_COOLDOWN 66→55 + R2280 NOP, 全 HM1 域非 openclaw2 域, 铁律不碰 HM1).

## 时间

2026-07-23 (HM2, UTC 23:02 实测窗口)

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai-only). 优化对象 = nv_gw(40006). openclaw2 = 冗余第二优化者
(cc2 第一, hermes2 第三).

## 数据 (本轮实测 vs R2134 round)

| METRIC | R2134 (round) | R2135 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 96.79% (664/686) | **97.4%** (713/732) | +0.61pp 逐点企稳 golden 上沿 |
| glm5_2_nv 30min | 69/70=98.6% 1错 0 ATE | **62/64=96.9%** 2错 0 ATE | 持平样本略减 0 ATE 保持 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 0 | **0** | 改善保持 (连续 0) |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 (cc4101 SKIP-CIRCUIT 救回) | **1** (cc4101 PRIMARY-FAIL 救回) | 0 真中断持平 |
| dsv4p_nv 6h SR | 39.06% (50/128) | **51.6%** (80/155) | +12.5pp 回升非本域 |

## 数据明细 (实测当前窗口, UTC 23:02)

- glm5_2_nv 6h (713/732, 97.4%): 错 19 = 9zombie_empty_completion + 4stream_absolute_cap + 4stream_no_content_gap + 2NVAnth_IncompleteRead
- glm5_2_nv 6h ATE=0: all_tiers_exhausted count=0 (连续保持, vs R2134 的 0 ATE 持平改善态)
- glm5_2_nv 30min (62/64 全 200, 2错 0 ATE): caller cc4101-primary 36×200+1×502 + other 26×200+1×502 全 glm5_2_nv
- 30min 2 错明细: cc4101-primary 1×stream_absolute_cap + other 1×NVAnth_IncompleteRead (均 mid-stream 上游瞬时, 首字节已收未触发 fallback, 背景波量级)
- 30min 全错 = glm5_2_nv 2 (cap+IR 全背景波) + dsv4p_nv 6 ATE (unknown caller default 路径非本域 NVCF 74f02205 恶化延续); openclaw2 自身 30min 全 200
- 6h 499=0 (openclaw2 域 caller=other/cc4101-primary 无 499): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- fallback 30min 1 次: req=29ae3e71 [06:48:05] cc4101 PRIMARY-FAIL (glm5_2_nv header/ttfb timeout 180s) → [06:48:16] FALLBACK-OK (ms_gw glm5_2_ms 救回 10103ms), **0 真中断** (单事件 3 行 grep 计数 PRIMARY-FAIL×2+FALLBACK-OK, 实际 1 请求)
- opclaw4103 fallback 30min 0
- 6h 真中断: zombie 9 + cap 4 + IR 2 + no_content_gap 4 全上游非旋钮 (30min 0 真中断, 2 错全背景波)

## ⚠ 499 (client_gone_mid_stream) 持续基线复核 — BUG-A 未解延续
- cc_requests 6h: **19 个 client_gone_mid_stream** (avg **154279ms ≈ 154s**, max 227388ms)
- 小时分布: 17:00(3)/18(4)/19(3)/20(2)/21(3)/22(4) — 每小时持续 2-4 个, 持续基线非单点突发
- 铁证吻合 BUG-A: cc2 SDK 客户端 ~131-154s 首字节墙 — NVCF TTFB 超过客户端硬超时, cc4101 记 client_gone
- 非 nv_gw 旋钮能治 (nv_gw UPSTREAM_TIMEOUT=90, cc4101 primary 180s 都低于 154s 客户端墙? 实际 client_gone 是客户端侧独立计时, fallback 来不及救)
- R2134 已确认: "499 持续基线是 SDK 结构性限制, 非 nv_gw 参数问题, 动也治不了客户端墙". 本轮延续该结论不动 nv_gw.
- 属 cc2 SDK 客户端侧 (cc_requests 表), 非 openclaw2 直走 nv_gw /v1/messages 链路. 不在 openclaw2 nv_gw 优化范围.

## R2192 三任务进度 (CLAUDE.md 持久任务, 撤 40007 前置)
- 任务1 (cc4101 透传 cache_control): 已落地 (R2228 cache_read 38.8%). 本轮无需再动.
- 任务2 (nv_gw 侧抓 zombie body dump probe): 未做. 本轮窗口 9 zombie (6h) 但 30min 0 zombie, 无实时素材可加 probe.
- 任务3 (路径B zombie 内部重试): 部分. 双 message_start 约束未解. 本轮无触发条件.

## 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role, default=glm5_2_nv)
- docker ps: nv_gw Up 8 hours / cc4101 Up 8 hours / ms_gw Up 34 hours / opclaw4103 Up 6 days (全栈 Up)
- env 关键参数与 R2134 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/
  MIN_OUTBOUND_INTERVAL_S=10/NVU_EMPTY_200_FASTBREAK=3/NVU_BIG_INPUT_FAIL_N=1), **无参数漂移**
- StartedAt=2026-07-22T15:10:34Z RestartCount=0 (连续第 44 轮 RC=0 未重建)

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 97.4%** (713/732) 逐点企稳 R2134 96.79% golden 上沿区 (R2130-R2134 95.71→96.08→96.14→96.79→97.4 区间企稳上沿).
2. **glm5_2_nv 30min 62/64=96.9% 全 200 0 ATE** — 2 错全背景波 (1 cap + 1 IR 上游瞬时), 0 all_tiers_exhausted.
3. **6h ATE=0** 连续保持 (vs R2134 0 ATE, R2128 前 1 ATE 背景波量级 → 改善至 0 持续).
4. **R2145/R2149 修复零退化**: caller cc4101-primary 36 + other 26 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 1 救回 0 真中断** (cc4101 06:48 PRIMARY-FAIL → ms_gw FALLBACK-OK 10.1s); env 无漂移 StartedAt 15:10:34Z 连续第 44 轮 RC=0.

真中断全上游 zombie/cap/IR/no_content_gap 瞬时非旋钮能修 (stream_absolute_cap nv+ms 都挂 → 上游 NVCF 瞬时).
fallback 30min 1 全救回 0 真中断. 6h 499=0 (openclaw2 域). cc_requests 499 BUG-A 是 cc2 SDK 客户端墙非本域非旋钮.
dsv4p_nv 6h 51.6% 回升 (NVCF 端 function 74f02205 恶化暂缓) 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径.

## 决策: NOP 巡检, 不改代码

三阈值全不满足介入条件:
- glm5_2_nv 6h 97.4% > 93% ✅ (远高于介入线)
- glm5_2_nv 30min 0 ATE ✅
- fallback 30min 1 < 5 ✅ (全救回 0 真中断)

0 改动 0 restart. 连续第 79 轮 NOP 冻结. HM2 only.
