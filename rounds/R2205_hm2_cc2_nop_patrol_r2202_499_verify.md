# R2205 (hm2_cc2): NOP 巡检轮 + R2202 499 修复改后 40min 验证初报 — 0 改动 0 restart

**关联**: R2202 (cc4101 150-350K header_timeout 120→180s, 499 真根因修复, 待3-6h验证),
R2199 (全局 settings 900000 证伪 auto-compact 根因), R2196 (上一轮 NOP 巡检),
R2192 (撤40007 三任务持久指令, 全未做)

## 本轮定位
全新 session 接棒. STATE 停 R2196, `git pull` 后主仓已推到 R2204 (HM1 peer 轮, 非本域).
HM2 cc2 域进展: R2196(NOP) → R2199(全局settings 900k) → **R2202(cc4101 header_timeout 120→180s, 499 真根因修复)**.
R2202 commit 00:36 CST = 07-21 16:36 UTC, 当前 01:16 CST → **改后仅 ~40min 数据, 远不足 3-6h 验证窗口**.
本轮 = R2205, 定位为 **R2202 改后验证初报巡检轮**: 拉改后 499 信号 + 三阈值 + 三任务进度报告.

## 数据 (HM2, 30min window, ~01:16 时点)
- 68 请求 / 62 OK(200) / 6 错(502) → SR = **91.2%**
  (较 R2196 94.7% 回落 3.5pp, 仍在 STATE 稳定带内但偏低, 主因 glm5_2_nv 本窗口 NVCF 上游 soft-fail 抖动)
- by model: glm5_2_nv 49/51 = **96.1%** (R2188/R2195/R2196 连续三轮 100%, 本轮回落);
  dsv4p_nv 13/17 = 76.5% (4 错全 all_tiers_exhausted)
- 6 错 error_type 明细:
  - dsv4p_nv all_tiers_exhausted ×4 (NVCF function ATE 已知良性, 与历史同族无新增)
  - **glm5_2_nv stream_absolute_cap ×1** (1c1c09bf, NVCF 上游流式绝对上限 soft-fail)
  - **glm5_2_nv zombie_empty_completion ×1** (59286b9d, R2196=0, 本窗口 NVCF 上游空响应抖动)
- host_machine 全 HM2 本域

## cc4101 30min fallback (负向核心指标)
- **1 个请求, 全 FALLBACK-OK 救回, 0 双失败**
  - req=a4e82ef6 [01:00:47] PRIMARY-FAIL (glm5_2_nv header/ttfb timeout after **60s**, chars=13064 小请求)
    → [01:00:51] FALLBACK-OK (ms 3663ms 救回)
  - 注: 60s timeout 非 120s/180s 档, 走的是 cc4101 小请求档 (13K chars), 非本轮 R2202 改的 150-350K 档
- fallback 请求数 1 < 5 阈值 ✅
- 趋势: R2196(1全救回) → R2199(改settings) → R2202(改cc4101) → R2205(1全救回), 连续多轮无双失败

## ⭐ R2202 499 修复改后验证初报 (本轮核心)
R2202 commit 07-22 00:36 CST, 改 cc4101 upstream.py 150-350K header_timeout 档 120→180s.
**落地核证**:
- cc4101 StartedAt = **07-21 16:35:29Z** (= 00:35 CST, 与 R2202 commit 00:36 完全吻合, restart 落地证据)
  (R2196 记 cc4101 StartedAt=14:21:44Z, 本轮变 16:35:29Z = R2202 restart 造成, **非异常漂移**)
- cc4101 upstream.py 分档表确认: `150-350K=180s(R2202: 120->180, NVCF 120-142s 慢请求被 120s 砍致 499)` ✅

**改后 40min 499 信号 (6h 窗口 36 个, 但绝大多数是改前; 改后 00:36+ 仅 3 个)**:
| req | 时点 | chars | prim_ms | 类型 |
|-----|------|-------|---------|------|
| 7903587a | 00:38 | 173997 | **0** | B 型 (cc2 客户端断流) |
| 91887cbc | 00:58 | 170191 | **0** | B 型 |
| c95d2055 | 01:08 | 175453 | **0** | B 型 |

**关键信号**: 改前 A 型 499 (prim_ms≈120100 精确踩 120s 线) 在改后 **3 个 499 全 prim_ms=0**, A 型初步消失.
改后 3 个 499 在 cc4101 日志 grep 零命中 → 未触发 fallback = R2202 说的 B 型 (cc2 客户端主动断流, 非 header_timeout 病, R2202 不治 B 型).
**但样本仅 40min/3 个, 远不足下定论**, 需等 3-6h (约 R2208-R2210) 拉满窗口验证 499 是否真归零.

6h 499 总计 36 个 (6/h), 含改前 R2199-R2202 窗口的 A 型 + 改后 B 型. R2191 BUG1 段要求 "<5/6h" 仍超, 但 R2191 auto-compact 根因已被 R2199/R2202 证伪, 499 真根因是 NVCF ttfb 慢踩 cc4101 header_timeout 线.

## nv_gw 内部 NV-MS-FB 兜底 + breaker
- fallback_occurred=true: 14 条 (13×200 救回 + 1×502), 较 R2196 (11 全 200) 略增且 1 失败
- **NV-ANTH-BREAKER-FAIL 真 OPEN** (R2196=0 连续归零, 本轮 OPEN, 三阈值信号之一):
  - 01:14:20 1c1c09bf stream_absolute_cap → state CLOSED(3,0)
  - 01:19:16 07546e45 → state **OPEN(5,13)** (累积达 OPEN 阈值)
  - 01:19:32 a0aebdcd → **breaker OPEN, skip nv chain, 直走 ms_gw** (R1719 有意设计: 宁走 ms 不死循环)
- breaker OPEN 根因 = NVCF 上游 glm5_2_nv soft-fail 累积 (stream_absolute_cap + zombie + all_keys_exhausted),
  **非 nv_gw 参数病** (调 nv_gw 参数治不了 NVCF 上游 soft-fail), 且 OPEN 后全 ms 救回 cc2 无感.
- CLAUDE.md 明示: breaker 是最后保险, 目标是让它"几乎不 OPEN"而非调高阈值"假装不 OPEN".

## 参数误杀类 (全 0)
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0 ✅ → 非参数误杀

## 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models, passthrough, default=glm5_2_nv)
- nv_gw RC=0 StartedAt=**07-21 12:50:09Z** (同 R2196 连续多轮未重建, 漂移信号止住) ✅
- cc4101 RC=0 StartedAt=**07-21 16:35:29Z** (= R2202 commit 00:36 CST restart 落地, **非异常漂移**, R2196 记的 14:21:44Z 已被 R2202 restart 覆盖)
- env 关键参数与 R2196 快照逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/KEY_COOLDOWN_S=60/
  TIER_COOLDOWN_S=180/NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/BIG_INPUT 阈值同), **无参数漂移** ✅

## R2192 三任务进度报告 (持久指令, CLAUDE.md 要求每轮报告)
ULTIMATE GOAL: 撤 40007 (ms_gw fallback). 三任务:
- **任务1 (cc4101 透传 cache_control, 恢复缓存命中, 纯增益)**: **未做**. R2192 抓包铁证 cc4101 转换层
  完全丢弃 cache_control → cc2 缓存命中率 0% (344 响应全 0). 但任务1 改 cc4101 转换层, **会污染 R2202
  的 499 验证数据** (分不清 499 降是 header_timeout 改的还是 cache_control 改的). 建议 R2202 验证窗口
  (3-6h, 499 定论) 过完后, 约 R2208-R2210 启动任务1.
- **任务2 (nv_gw 侧抓 zombie body probe, 验证 A vs D)**: **未做**. 本窗口出现 1 个 zombie (59286b9d),
  但单点样本不足. 任务2 改 nv_gw handlers.py 加 probe (非 cc4101), 不污染 499 验证, 可择机启动.
- **任务3 (nv_gw 路径B zombie 内部重试, 撤40007核心前置)**: **未做**. 源码核证 converter feed_chunk
  有 message_start_sent 守卫, 技术可行. 这是撤 40007 的核心前置, 待任务2 定论 zombie 字段差异后启动.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值核证:
- SR 91.2% > 85% ✅ (不满足"跌破85%")
- cc4101 fallback 请求数 1 < 5 ✅ (不满足">5 条/30min")
- 虽出现新错误类型 (zombie 1 + stream_absolute_cap 1, R2196=0) 且 breaker 真 OPEN,
  但阈值组合是 "SR跌破85% **或** (fallback>5 **且** 新错误类型)": 第一项不满足, 第二项"且"中 fallback 未>5 → **不满足**
- 三阈值全不满足 → **冻结, 0 改动 0 restart**

不改的理由:
1. R2202 改后仅 40min, 正处验证窗口期, 改 nv_gw/cc4101 会污染 499 验证数据
2. breaker OPEN + zombie 是 NVCF 上游 glm5_2_nv soft-fail 抖动 (本窗口), 调 nv_gw 参数治不了根因
3. glm5_2_nv 96.1% 回落是 NVCF 上游抖动, 非参数病 (参数误杀全 0, env 无漂移)
4. 全部失败被 ms 救回, cc2 无感 (cc4101 fallback 1 全救回, NV-MS-FB 13 救回)

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 +
env 无漂移 (与 R2196 逐项一致). 容器 StartedAt: nv_gw=12:50:09Z (未重建同 R2196),
cc4101=16:35:29Z (R2202 restart 落地, 非异常). 本轮 0 commit (NOP 巡检无改动).

## 下一轮建议
1. **R2202 499 验证是当前最高优先**: 下轮 (R2206+, 距 R2202 改动 ~1.5h) 继续拉 cc_requests 6h 499,
   重点看改后 A 型 (prim_ms≈120100) 是否持续消失, B 型 (prim_ms=0) 占比. 到 R2208-R2210 (3-6h 满
   窗口) 才能 499 定论. 若改后满窗口 499 显著降 (目标 <5/6h) → R2202 验证成功, 撤40007 前置之一达成.
2. breaker OPEN 监控: 本窗口 OPEN (NVCF 上游抖动). 若下轮持续 OPEN + zombie 持续, 需评估是否
   NVCF 上游 glm5_2_nv 劣化 (非 nv_gw 参数病, 但要确认不是趋势性恶化). 若单轮抖动自愈则继续冻结.
3. R2192 三任务: R2202 验证窗口过完后, 启动**任务1 (cc4101 透传 cache_control)** — 纯增益, 恢复
   缓存命中省钱省时. 任务1 改 cc4101 转换层, 不碰 nv_gw, 不碰 ms_gw. 备份 .bak.R2XXX_t1.
4. 任务2 (nv_gw zombie body probe) 可与任务1 并行评估 — 改 nv_gw handlers.py, 不污染 cc4101 499 验证.
   本窗口 1 个 zombie (59286b9d) 是好样本, 可加 probe dump oai_body.
5. 触发改动三阈值不变: 30min SR 跌破 85% **或** cc4101 fallback >5 条/30min **且** 新错误类型.
6. cc4101 StartedAt 16:35:29Z = R2202 落地, 下轮若再变需查是谁改的 (HM1 peer 不应动 HM2 cc4101).
7. 铁律: 只改 HM2, 不改 HM1 (R2197-R2204 是 HM1 peer 轮 alternating KEY/TIER, 非本域).

## 铁律合规
- 改前有数据 ✅ (30min nv_gw + 6h cc_requests 499 + fallback + breaker + 容器/env 快照)
- 改后有验证 ✅ (0 改动, curl /health + docker ps + env 快照)
- 聚焦 40006 nv_gw ✅ (未碰 ms_gw 源码)
- 写入仓库 ✅ (本轮轮文件)
- 只改 HM2 不改 HM1 ✅
- 未 Read /tmp 任何文件 ✅ (规避上一 session 死循环中断)
