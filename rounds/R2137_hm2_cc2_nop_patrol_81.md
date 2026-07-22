# R2137 (hm2_cc2): NOP 巡检轮 80 — 稳态延续 三阈值冻结 (主链路 2 zombie 跟踪信号)

**日期**: 2026-07-23 07:13 CST
**主机**: HM2 (本域 only, 铁律不改 HM1)
**前序**: R2136 (6226aed, hm2_cc2) 连续第 80 NOP; git log HEAD = 0633de3 (R2135 hm2_oc2 @07:06)
**本轮**: R2137 hm2_cc2 NOP 巡检轮, **0 改动 0 restart**, 连续第 81 NOP

## STATE.md 滞后修正 (第 38 次)

STATE.md 头部停在 `1bbc20e R2196` (07-21 旧 session 交接), 与主仓 git log 实际最新 HEAD `0633de3 R2135 hm2_oc2` (07-23 07:06) 严重脱节。
STATE.md 里的参数快照 (nv_gw StartedAt=07-21T12:50:09Z) 实为 **ms_gw** 的 StartedAt (串错容器, R2135/R2136 已发现)。
本轮实测修正: **真实 nv_gw StartedAt=07-22T15:10:34Z** (RC=0 连续多轮未重建), ms_gw=07-21T12:50:09Z, cc4101=07-22T14:28:23Z。

> 轮号体系说明: 本仓有两条轮号线 —
> - **R21XX (hm2_cc2 / hm2_oc2)**: HM2 本域 nv_gw 自优化巡检, 我 (cc2) 跟这条线, 改 HM2 的 nv_gw/cc4101 源码。
> - **R22XX (hm2_optimize_hm1)**: HM2->HM1 跨域优化, **只改 HM1 peer**, 我不参与 (铁律只改 HM2)。
> git log 里另有一条 07-21 的旧 "R2136/R2137/R2139 hm2_cc2" commit (已被 07-22/23 的对齐序列覆盖命名空间), 当前真实基线 = HEAD = R2135 hm2_oc2, 本轮 hm2_cc2 续 R2137。
> 本轮清理了上一个 session 07:00 时点写的孤儿文件 `R2137_hm2_cc2_nop_patrol_85.md` (轮号 85 与连续第 81 NOP 不衔接, 未 commit, 内容是 07:00 时点过时数据)。

## 数据 (HM2, 30min window, 07:12 CST 时点)

**nv_gw 30min SR**:
- 91 请求 / 82 OK(200) / 9 错(502) → SR = **90.1%**
- by model:
  - **glm5_2_nv 63/67 = 94.0%** SR (主链路; 4错 = 2 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap, 全 mid-stream 上游背景波类)
  - dsv4p_nv 19/24 = 79% (5 错全 all_tiers_exhausted = NVCF function ATE 上游已知良性, 与历史同族无新增)
- error_type: 5 all_tiers_exhausted(dsv4p) + 2 zombie_empty_completion(glm5_2_nv) + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap
- 无 content_filter / timeout / conn / 429
- host_machine 全 HM2 本域

**⚠ 主链路 zombie 跟踪信号**:
- glm5_2_nv 30min 出现 **2 个 zombie_empty_completion** (R2139 曾有 1 zombie 单点, 本轮 2 个)。
- 对应 BREAKER 记录: zombie@07:00:05 (req=a36a7cdb, state CLOSED) + zombie@07:05:06 (req=31de5687, state CLOSED)。
- 另 2 条 BREAKER = cap@06:45:51 (req=570f739e) + IR@06:53:55 (req=0b2f008a)。
- 4 个 glm5_2_nv 软失败全 CLOSED 未 OPEN, 远未到 breaker 阈值。**非新增错误类型 (zombie 历史多轮已现)**, 但主链路 zombie 量较前几轮 (R2136=0) 抬升, 纳入下轮跟踪。

**cc4101 30min fallback (负向核心指标)**:
- 3 个请求, **全 FALLBACK-OK 救回, 0 双失败 / 0 真中断**
  - req=29ae3e71 [06:48:05] PRIMARY-FAIL (glm5_2_nv 180s header/ttfb timeout, cc4101 自身 header timeout 非 nv_gw chain budget 120s) → [06:48:16] FALLBACK-OK (ms 10103ms 救回) — **旧事件滑入** (R2136/R2137 孤儿文件都记过, 非本窗口新发)
  - req=24649f8c [07:02:09] PRIMARY-FAIL (60s timeout < chain budget 120s, **SKIP-CIRCUIT 不归因 nv_gw 不计 circuit**, cc4101 自身 60s header timeout pre-empt) → [07:02:13] FALLBACK-OK (ms 3663ms 救回) — 真新发
  - req=13355d43 [07:07:11] PRIMARY-FAIL (60s timeout < chain budget 120s, **SKIP-CIRCUIT**) → [07:07:13] FALLBACK-OK (ms 2429ms 救回) — 真新发
- fallback 请求数 3 < 5 阈值 ✅ (全救回 0 真中断)
- 2 真新发 fallback 全是 cc4101 自身 60s header timeout pre-empt nv_gw retry (<chain budget 120s, SKIP-CIRCUIT 不归因 nv_gw), 是 NVCF 上游 glm5_2_nv header 阻塞慢, 不是 nv_gw 旋钮能治根因

**nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)**:
- 4 条, **全 state=CLOSED 未 OPEN** (state=('CLOSED',4,0)@06:45 + ('CLOSED',2,0)@06:53 + ('CLOSED',2,0)@07:00 + ('CLOSED',3,0)@07:05)
- breaker 记录失败但未到 OPEN 阈值, 远未到, 同族良性 (cap/IR/zombie 全 mid-stream 上游背景波)
- **注意**: fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback。前者是 R1719 设计正常吸收, 后者才是真正"数据空洞"负向指标 (本轮 cc4101 fallback=3 全救回)。

**参数误杀类 (全 0)** ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0
- → **非参数误杀**

**BUG-A 499 盲点 (cc_requests 6h)**:
- client_gone_mid_stream = **50 / 6h** (同 R2134/R2135 量级, 持续基线)
- stream_total_deadline = 4 / 6h (小量级, 上游慢)
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制 (NVCF TTFB>131s 时 cc2 客户端自断 broken pipe, cc4101 记 499), 非nv_gw 旋钮能治, 已定性多轮, 不在本轮 nv_gw 范围, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核)
- nv_gw /health ok (passthrough role, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2136 一致无漂移) — docker inspect 实测确认 (非 STATE 旧值的 ms_gw 串错)
- cc4101 RestartCount=0 StartedAt=2026-07-22T14:28:23Z (RC=0, R2136=同窗口)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0) — **这就是旧 STATE 错记成 nv_gw 的值**
- nv_gw Up 8h / cc4101 Up 9h / ms_gw Up 34h / logs_db Up 6d 全栈 Up
- env 关键参数与 R2136 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/KEY_COOLDOWN_S=60/
  TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150/NVU_TIER_BUDGET_GLM5_2_NV=120/
  NVU_TIER_BUDGET_DSV4P_NV=180/BIG_INPUT 阈值同), **无参数漂移**

## R2192 三任务进度 (巡检必报, ULTIMATE GOAL 撤 40007)
- 任务1 (cc4101 透传 cache_control): **已落地** (R2228 cache_read 38.8%, 走 nv_gw 读 NVCF prompt_tokens_details.cached_tokens 路径, cc4101 passthrough 已透传, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): **未做** — **本轮有素材了** (2 个 zombie req=a36a7cdb/31de5687), 但本轮三阈值不满足冻结不动, 留下轮评估时优先做 (handlers.py zombie 检测点加 oai_body 落盘 probe, 对比成功请求字段差异, 验证 R2192 四推测 A/B/C/D)
- 任务3 (路径B zombie 内部重试): **部分** (双 message_start 约束未解, converter feed_chunk 内部重试设计待做; 本轮 2 zombie 是验证场景, 但本轮不动)

## 决策: NOP 巡检 0 改动 0 restart

STATE 三触发改动阈值全不满足:
1. SR 90.1% > 85% ✅ (glm5_2_nv 94% 主链路稳, dsv4p 79% 为上游 ATE 拖累非本域)
2. cc4101 fallback 请求数 3 < 5 ✅ (全救回 0 真中断, 2 真新发全 60s SKIP-CIRCUIT 不归因 nv_gw)
3. 无新增错误类型 ✅ (2 zombie 历史多轮已现非首现; 4 错全上游类 cap/IR/zombie 同族 + dsv4p ATE 已知良性)

四重佐证 nv_gw 稳:
- 9错全上游无害类 (glm5_2_nv 4 软失败全 mid-stream 背景波首字节已收 CLOSED吸收 + dsv4p 5 ATE NVCF function 已知良性)
- 无参数误杀 (全0)
- breaker 不真 OPEN (4 条全 CLOSED state 最高 (3,0) 远未到阈值)
- 参数无漂移 (容器未重建 env 与 R2136 逐项一致, nv_gw StartedAt=07-22T15:10:34Z 连续多轮不变)

主链路 2 zombie 信号分析: 94.0% vs R2136 98.6% 回落 4.6pp, 回落主因 = glm5_2_nv 4 软失败 (2z+1IR+1cap) 集中在 06:45-07:05 这 20min 窗口。非 nv_gw 旋钮能治 (NVCF 上游偶发 mid-stream empty/zombie), breaker CLOSED 吸收 + 无 fallback 真中断。改了反而破坏稳定带。

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 +
env 无漂移 (与 R2136 逐项一致). 容器 StartedAt (docker inspect 实测, 非旧 STATE 串错值):
nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-22T14:28:23Z (R2136 窗口 RC=0) / ms_gw=07-21T12:50:09Z.

HM2 only. 铁律: 只改 HM2 不改 HM1.
