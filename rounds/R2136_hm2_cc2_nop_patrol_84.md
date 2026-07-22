# R2136 (hm2_cc2): NOP 巡检轮 84 — 稳态延续 三阈值冻结

**日期**: 2026-07-23 06:21 CST (22:21 UTC)
**主机**: HM2 (本域 only, 铁律不改 HM1)
**前序**: R2135 (86fef6c) 连续第 79 NOP
**本轮**: R2136 hm2_cc2 NOP 巡检轮, **0 改动 0 restart**, 连续第 80 NOP

## STATE.md 滞后修正

STATE.md 头部停在 `1bbc20e R2196`, 与主仓 git log 实际最新 `86fef6c R2135` 严重脱节。
git log R2135 commit message 已明记 "STATE.md滞后停R2196, 以git log为准本轮R2135对齐"。
STATE.md 里的参数快照 (nv_gw StartedAt=07-21T12:50:09Z) 实为 **ms_gw** 的 StartedAt (串错了容器),
env 旧值也过气。本轮全部以实测为准重写, 旧 STATE 值作废。

> 轮号体系说明 (避免下一个 session 困惑): 本仓有两条轮号线:
> - **R21XX (hm2_cc2 / hm2_oc2)**: HM2 本域 nv_gw 自优化巡检, 我 (cc2) 跟这条线。改 HM2 的 nv_gw/cc4101 源码。
> - **R22XX (hm2_optimize_hm1)**: HM2->HM1 跨域优化, **只改 HM1 peer**, 我不参与 (铁律只改 HM2)。
> 接棒时若 STATE 头部轮号 ≠ git log 最新, **以 git log 为准**, STATE 可能被并发 lag。

## 数据 (HM2, 30min window, 06:21 CST 时点)

**nv_gw 30min SR**:
- 110 请求 / 107 OK(200) / 3 错(502) → SR = **97.3%**
- by model: **glm5_2_nv 72/73 = 98.6%** (主链路稳态延续 R2135 的 96.8% 持平略升);
  dsv4p_nv 35/38 = 92% (3 错全 all_tiers_exhausted)
- 错误分类: glm5_2_nv 1 × stream_no_content_gap (中游流背景波, 首字节已收未触发 fallback);
  dsv4p_nv 3 × all_tiers_exhausted (NVCF function ATE 已知良性, 与历史同族无新增)
- **无 zombie / content_filter / timeout / conn / 429 on glm5_2_nv**
- host_machine 全 HM2 本域

**cc4101 30min fallback (负向核心指标)**:
- 2 个请求, **全 FALLBACK-OK 救回, 0 双失败 / 0 真中断**
  - req=7216e60e [06:06:46] PRIMARY-FAIL (glm5_2_nv header/ttfb timeout after 60072ms, **< chain budget 120s, cc4101 自身 60s header timeout pre-empt nv_gw retry, SKIP-CIRCUIT 不归因 nv_gw 不计 circuit**) → [06:07:04] FALLBACK-OK (ms 17685ms 救回)
  - req=8e10357a [06:15:02] PRIMARY-FAIL (glm5_2_nv header/ttfb timeout after 160105ms, **160s > chain budget 120s**, 会计 circuit) → [06:15:08] FALLBACK-OK (ms 5488ms 救回)
- req=8e10357a 是新 id 新时点 (06:15:02, 非 R2135 记录的 ad4661ac/7216e60e) = **真实新增 1 个 160s timeout fallback 但全救回 0 真中断**. 下轮拉数据若仍见 req=8e10357a + 06:15:02 → 判为旧事件滑入非新发.
- fallback 请求数 2 < 5 阈值 ✅
- R2182 恶化趋势仍止住: R2182(1双失败) → R2185(全救回) → R2186(0) → R2187(全救回) → R2188(尾巴) → R2189(0) → R2195(2全救回) → R2196(1全救回) → R2134(1全救回) → R2135(2全救回) → R2136(2全救回)

**nv_gw 内部 tier 吸收 (nv_tier_attempts 30min)**:
- pexec_success 67 / pexec_429 23 / NVCFPexecRemoteDisconnected 5 / pexec_SSLEOFError 2 / pexec_conn_RemoteDisconnected 1
- 31 失败 vs 67 成功 = tier 内部多 key 重试在吸收 NVCF 上游 429/disconnect 抖动, 未上浮到请求层

**NV-ANTH-BREAKER-FAIL** (R1719 设计):
- **1 条** (req=369cd3a2 stream_no_content_gap, state=('CLOSED', 1, 0) 未 OPEN) — 对应 DB 里 glm5_2_nv 的那 1 个 stream_no_content_gap 错, breaker 正确吸收未真 OPEN, 未甩 ms. R2135=0, 本轮 1 单点 CLOSED (远未到 OPEN 阈值, 不评估).

**499 盲点 (cc_requests 6h, CLAUDE.md BUG-A 必查)**:
- client_gone_mid_stream = **51/6h** (R2134=50, R2135=51, 同量级基线, 非 nv_gw 旋钮能治 — BUG-A: cc2 SDK ~131s 客户端首字节墙结构性限制, 属 CC 基础设施侧待查项, 不在本轮 nv_gw 范围)
- stream_total_deadline = 4/6h (正常尾部超时, 量级同历史)
- R2191 (1M context) 后 499 未归零的原因 (R2203 巡查结论): cc2 SDK ~131s 客户端首字节墙未破, 非 settings 问题, 非 nv_gw 旋钮能治.

**参数误杀类 (全 0)**:
- BIG-INPUT / STALL-FAIL / 75s_timeout / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0
- → **非参数误杀**

**容器状态 (漂移信号核)**:
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role, default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (Up 7h, **与 R2133/R2135 逐项一致 → 连续第 45+ 轮未被重建**, 漂移信号止住; 旧 STATE 写的 07-21T12:50:09Z 实为 ms_gw 的 StartedAt, 串错容器)
- cc4101 RestartCount=0 StartedAt=2026-07-22T14:28:23Z (Up 8h, RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (Up 34h, 热备正常)
- env 关键参数实测与 R2135/STATE 快照逐项一致 (UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 /
  NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_TIER_BUDGET_DSV4P_NV=180 / BIG_INPUT 阈值 250000 同), **无参数漂移**

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
- SR 97.3% > 85% ✅ (glm5_2_nv 98.6% 主链路稳)
- cc4101 fallback 请求数 2 < 5 ✅ (低于阈值, 全救回; 1 真新发 160s timeout 但 0 真中断)
- 无新增错误类型 ✅ (glm5_2_nv 1 stream_no_content_gap + dsv4p_nv 3 ATE 全与历史同族)

四重佐证 nv_gw 稳:
1. 错误全上游无害类 (glm5_2_nv 主链路连续多轮 96.8%+, dsv4p NVCF function ATE 已知良性)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (本轮 1 单点 CLOSED, 远未到 OPEN 阈值)
4. 参数无漂移 (容器未重建, env 与 R2135 逐项一致)

改了反而破坏 R2154 稳定带。glm5_2_nv 本轮 98.6% SR, 证明 R2154 动态 header timeout 后主链路持续最稳。
根因 (cc4101 PRIMARY-FAIL 是 NVCF 上游 glm5_2_nv header/ttfb 60-160s 超时) 本窗口 2 次但全被 ms 救回 0 真中断 —
不是 nv_gw 参数能治根因 (NVCF 上游偶发 header 阻塞), NV-MS-FB + cc4101 fallback 已正确吸收。

## R2192 三任务进度 (CLAUDE.md 持久指令, 每轮必报)

1. **任务 1 (cc4101 透传 cache_control)**: ✅ **已落地** (R2228 走 nv_gw 读 NVCF prompt_tokens_details.cached_tokens 路径, cc4101 passthrough 透传). git log R2135 记 cache_read 38.8%. **本轮不动**, 持续验证命中率不退.
2. **任务 2 (nv_gw 侧 zombie body dump probe)**: ⏸ **未做, 本窗口 0 zombie 无素材**. handlers.py 有 oai_body 但无 dump 到文件. 待真 zombie 窗口推进.
3. **任务 3 (路径B zombie 内部重试)**: 🔶 **部分**. `_ms_fallback_request` 存在但 "200+message_start 已发→不能切 ms 重放" 的双 message_start 错乱约束未解. 本窗口 0 zombie 无验证机会.

## 验证

0 改动 0 restart 无需验证改动。
- curl /health ok
- docker ps 全栈 Up (nv_gw 7h / cc4101 8h / ms_gw 34h / logs_db 6d)
- 容器 RC=0
- env 无漂移 (与 R2135 逐项一致)
- 容器 StartedAt: nv_gw=15:10:34Z (未重建同 R2135), cc4101=14:28:23Z, ms_gw=07-21T12:50:09Z

## commit
本轮 0 改动, 轮文件归档记录. commit + push origin main.
