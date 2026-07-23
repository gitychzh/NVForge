# R2141 (hm2_cc2) — NOP 巡检轮 连续第 82 NOP

**时点**: 2026-07-23 12:50 CST (STATE 滞后修正: STATE 头部停 R2137 @07-12, 实际 git log HM2-cc2 线最新已 commit = R2140 8b7935e @风暴过境观测, 本轮续 R2141)
**commit 基线**: HEAD=c162c8d (R2284 HM1 peer, non-HM2). HM2-cc2 本域上一已知 = R2140 8b7935e.
**轮文件**: `rounds/R2141_hm2_cc2_nop_patrol_82.md`

## 数据 (HM2, 30min window, 12:50 CST 时点)

- **81 请求 / 71 OK(200) / 10 错(502) → SR = 87.7%** (> 85% 阈值 ✅, 边缘但满足)
- by model:
  - **glm5_2_nv 51/55 = 92.7%** (主链路; 4错 = 1 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap + 1 stream_first_byte_timeout, 全 mid-stream 上游背景波类)
  - dsv4p_nv 20/26 = 76.9% (6错 全 all_tiers_exhausted NVCF function ATE 上游已知良性)
- error_type: 6 all_tiers_exhausted(dsv4p) + 1 zombie + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap + 1 stream_first_byte_timeout
- 无 content_filter / timeout / conn / 429
- host_machine 全 HM2 本域

### 30min glm5_2_nv 主链路 4 错明细 (全 mid-stream 背景波, breaker CLOSED 吸收)
| UTC time | error_type | request_id | CST |
|---|---|---|---|
| 04:28:00 | stream_absolute_cap | 369d5f2b | 12:28 |
| 04:34:46 | zombie_empty_completion | 0d69ecba | 12:34 |
| 04:43:04 | stream_first_byte_timeout | 7a86ec7d | 12:43 |
| 04:48:46 | NVAnth_IncompleteRead | eb1dc03e | 12:48 |

## cc4101 30min fallback (负向核心指标)
- **1 个请求, 全 FALLBACK-OK 救回, 0 双失败 / 0 真中断** ✅ (< 5 阈值)
  - req=8ad0deb1 [12:28:00] PRIMARY-FAIL (glm5_2_nv 60s header/ttfb timeout, **60s < chain budget 120s, SKIP-CIRCUIT 不归因 nv_gw 不计 circuit**, cc4101 自身 60s header timeout pre-empt nv_gw retry) → [12:28:03] FALLBACK-OK (ms 2745ms)
- 该 fallback 与主链路 stream_absolute_cap req=369d5f2b @12:28 同一上游 NVCF glm5_2_nv header 阻塞慢事件 (cc4101 先 60s pre-empt 切 ms 救回, nv_gw 侧记 cap)
- **关键细节(下轮读懂)**: 该 fallback 是 cc4101 自身 60s header timeout pre-empt nv_gw retry (< chain budget 120s, SKIP-CIRCUIT 不归因 nv_gw), 是 NVCF 上游 glm5_2_nv header 阻塞慢, 不是 nv_gw 旋钮能治根因. 下轮拉数据若仍见 req=8ad0deb1 + 12:28 时点 → 判为旧事件滑入非新发.

## nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 2 条, **全 state=CLOSED 未 OPEN** (最高 state=('CLOSED', 2, 0), 远未到阈值)
  - [12:28:00] req=369d5f2b stream_absolute_cap → CLOSED,2,0
  - [12:48:46] req=eb1dc03e NVAnth_IncompleteRead → CLOSED,2,0
- fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback. 前者 R1719 设计正常吸收, 后者才是真正"数据空洞"负向指标 (本轮 cc4101 fallback=1 全救回).

## 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **37 / 6h** (vs STATE R2137 基线 50/6h, **下降 13**, 持续改善趋势)
- stream_total_deadline = 3/6h; server_5xx = 6; timeout = 164; 空 = 598 (非 nv_gw 链路)
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- **nv_gw RestartCount=0 StartedAt=2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2137/R2140 一致无漂移) — docker inspect 实测
- cc4101 RestartCount=0 StartedAt=2026-07-22T14:28:23Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- nv_gw Up 14h / cc4101 Up 14h / ms_gw Up 40h / logs_db Up 6d 全栈 Up
- env 关键参数与 R2137 快照逐项一致, **无参数漂移**

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

## R2192 三任务进度 (ULTIMATE GOAL 撤 40007)
- **任务1** (cc4101 透传 cache_control): ✅ 已落地 R2228 (cache_read 0%→38.8%, 走 nv_gw 读 NVCF prompt_tokens_details.cached_tokens 路径). 本轮未专查命中率, 下轮若做可扫 jsonl usage 验证不退.
- **任务2** (nv_gw 侧抓 zombie body dump probe): ⏳ 未做. 本轮 30min 有 1 zombie (req=0d69ecba @12:34), 1h 累积 2 zombie (与 R2137 同量级, 非持续扩散). handlers.py L779 有 oai_body 但无 dump 到文件. STATE 判定优先级: "若 zombie 持续 ≥3 个/30min 且连续 2-3 轮 → 触发任务2". 本轮 1h=2 不满足持续扩散阈值, 暂不动.
- **任务3** (路径B zombie 内部重试): ⏳ 部分. _ms_fallback_request 存在但 zombie 检测点"200+message_start 已发→不能切 ms 重放"约束未解 (双 message_start 错乱). 需设计 converter feed_chunk 内部重试.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
1. SR 87.7% > 85% ✅ (边缘但满足)
2. cc4101 fallback 请求数 1 < 5 ✅ (全救回 0 真中断)
3. 无新增错误类型 ✅ (zombie/IR/cap/first_byte_to 全 mid-stream 历��多轮已现非首现; 10错全上游类)

四重佐证 nv_gw 稳:
- 10错全上游无害类 (glm5_2_nv 4软失败全mid-stream背景波首字节已收CLOSED吸收 + dsv4p 6ATE已知良性)
- 无参数误杀 (全0)
- breaker不真OPEN (2条全CLOSED最高(2,0)远未到阈值)
- 参数无漂移 (容器未重建 env与R2137逐项一致)

改了反而破坏稳定带. SR 87.7% 较 R2137 90.1% 略降 2.4pp, 回落主因 = glm5_2_nv 4 软失败 (zombie+IR+cap+first_byte_to) 散布在 12:28-12:48 这 20min 窗口, 全 mid-stream 上游背景波类, 非nv_gw旋钮能治 (NVCF上游偶发 mid-stream empty/zombie/header 阻塞慢), breaker CLOSED 吸收 + 无 fallback 真中断.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. 容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-22T14:28:23Z / ms_gw=07-21T12:50:09Z. commit TBD.

## 铁律遵守
- 只改 HM2 不改 HM1 ✅ (本轮 0 改动)
- 不碰 ms_gw 源码/配置 ✅
- 改前有数据 ✅ / 改后有验证 (NOP 无需) ✅
- HM1 peer R2277-R2284 全 HM1 域非本域, 不参与

HM2 only. 连续第 82 NOP.
