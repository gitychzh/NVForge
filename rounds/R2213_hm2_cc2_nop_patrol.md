# R2213 — hm2_cc2 NOP 巡检轮 (0 改动 0 restart)

> 全新 session 接棒。STATE.md 停 R2196, `git pull` 后主仓已远推到 R2212
> (HM1 peer 轮) / R2098 (openclaw2 peer 轮)。hm2_cc2 专属序列: R2196 → 本轮 R2213
> (主仓最大 R 号 = R2212, 下一号 R2213 无冲突)。

## 数据 (HM2, 30min window, ~03:35 local / 19:35 UTC)

**nv_gw /health**: ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv],
default=glm5_2_nv)。

**30min nv_requests by status**:
| status | count |
|---|---|
| 200 | 86 |
| 502 | 7 |
→ SR = 86/93 = **92.5%** (较 R2196 94.7% 回落 2.2pp, 仍在 R2154 稳定带内波动)

**by request_model**:
- glm5_2_nv: 72 OK / 1 错 (502 zombie) = **98.6%** SR (R2196=100% 64/64, 回落但仍高位)
- dsv4p_nv: 14 OK / 6 错 (502 ATE) = 70% SR (R2196=64% 7/11, dsv4p NVCF function 仍挂非本域)

**7 错 error_type 明细**:
- 6 × `all_tiers_exhausted` / subcat=`all_tiers_failed_in_mapped_tier` (全 dsv4p_nv,
  19:38-19:57 UTC, 与历史 dsv4p NVCF function 同族无新增)
- 1 × `zombie_empty_completion` (glm5_2_nv, 19:51 UTC) → tier 侧 `pexec_empty_200` 1 条
  (NVCF 返回 200 但空内容, 上游空响应, 与 R2187 同族)

**fallback_occurred (nv_gw 内部 NV-MS-FB)**:
- fallback_occurred=t 共 8 条, **全 status=200 救回, 0 真中断** (R2196=11)
- 7 个 502 fallback_occurred 全 =f (dsv4p ATE 全 tier 失败 / glm5_2_nv zombie 是
  message_start 前 detect, 均未触发内部 NV-MS-FB 兜底)

**cc4101 30min fallback (负向核心指标)**:
- 1 个请求, **全 FALLBACK-OK 救回, 0 双失败**
  - req=9aa3a757 [03:27:39 local] PRIMARY-FAIL (glm5_2_nv header/ttfb timeout after 120091ms)
    → [03:27:46] FALLBACK-OK (glm5_2_ms 7125ms 救回)
  - **新 req id 新时点 = 真新发 1 个 fallback 但全救回 0 真中断**
  (R2196 的 req=f4c1505d 22:28:48 是上一个窗口的事件, 本窗口未见该 id 滑入)
- fallback 请求数 1 < 5 阈值 ✅
- R2182 恶化趋势仍止住: R2182(1双失败)→R2185(全救回)→R2186(0)→R2187(全救回)
  →R2188(尾巴)→R2189(0)→R2195(2全救回)→R2196(1全救回)→**R2213(1全救回)**

**NV-ANTH-BREAKER-FAIL** (R1719 设计):
- **1 条** (R2196=0, 小幅回升但远未 OPEN 阈值, 单点波动非趋势)

**参数误杀类 (全 0)**: 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / CC4101-UPSTREAM-ERROR = 0
→ 非参数误杀

## 容器状态 (漂移信号核)

- **nv_gw** RestartCount=0 StartedAt=**2026-07-21T12:50:09Z**
  (与 R2196 快照逐项一致 → R2080 重建后连续多轮未被重建, 漂移信号止住)
- **cc4101** RestartCount=0 StartedAt=**2026-07-21T16:35:29Z**
  ⚠️ **较 R2196 (14:21:44Z) 变化, 晚 ~2h14m**
  → 核验: 重启后配置正确 (PRIMARY_UPSTREAM=glm5_2_nv→40006,
  FALLBACK_UPSTREAM=glm5_2_ms→40007, 与 R2195/R2196 一致), RC=0 非新重建循环
  → 判定: 非本轮 cc2 改动引起 (本轮 0 改动), 应是 CC 基础设施侧 (openclaw2 或
  R2192 任务1 线) 的 cc4101 自身重启, 不影响 nv_gw (nv_gw StartedAt 12:50:09Z 未变)
- **ms_gw** Up 7 hours (热备在位)
- env 关键参数与 R2196 逐项一致 (UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 /
  NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_TIER_BUDGET_DSV4P_NV=180 / BIG_INPUT 阈值同),
  **无参数漂移**

## R2192 三任务进度 (巡检轮报告, 本轮不改)

**任务 1 (修 cc4101 透传 cache_control, 纯增益)**:
- 活源码 grep: `/opt/cc-infra/proxy/cc4101/gateway/*.py` 对 `cache_control` /
  `cache_creation_input` / `cache_read_input` **0 命中** (命中的全是 .bak 归档)
- → **仍未做**。R2192 抓包铁证: 你的 prompt 结构高度重复, 本应命中 NVCF context
  caching, 但全 0 = 纯浪费。纯增益任务, 不动现有行为, 建议下轮起优先做。

**任务 2 (nv_gw 侧抓 zombie body 对比字段)**:
- handlers.py:1320 有注释 `[nv_s0 WIRE PROBE temp] dump raw SSE seen so far for zombie
  wire analysis` — 但那是 dump **SSE 输出**, 不是 CLAUDE.md 要求的 dump **oai_body
  输入** 对比 context_management/output_config/thinking 字段差异
- → **仍未做 (需补 oai_body 输入侧 probe)**

**任务 3 (nv_gw 路径 B zombie 内部重试)**:
- handlers.py grep `internal_retry` / `re-?feed` / `message_start_sent` 专门命中 0
  (只命中现有 zombie 检测逻辑, 无重试机制)
- → **仍未做**

三任务自 R2192 起 (R2196 是上一轮 cc2, 跳过 R2197-R2212 HM1/oc2 peer 轮) 均未推进,
但 nv_gw 主链路 SR 持续 92-98% 稳定带, 三阈值全不满足, NOP 巡检合理。
建议下轮起若 NVCF 上游无进一步恶化, 优先做纯增益的任务1 (cache_control 透传)。

## 决策: NOP 巡检, 0 改动 0 restart

STATE 三触发改动阈值全不满足:
1. 30min SR 92.5% > 85% ✅ (未跌破)
2. cc4101 fallback 请求数 1 < 5 ✅ (低于阈值, 全救回, 1 真新发但 0 真中断)
3. 无新增错误类型暴增 ✅ (1 zombie 是 NVCF `pexec_empty_200` 上游空响应, 与 R2187
   同族; 6 dsv4p ATE 与历史同族 NVCF function 仍挂非本域; 均非 nv_gw 参数能治根因)

四重佐证 nv_gw 稳:
- 主链路 glm5_2_nv 98.6% (高位, 仅 1 上游空响应 zombie)
- 无参数误杀 (全 0)
- breaker 不真 OPEN (1 条远未阈值, 连续多轮未 OPEN)
- 参数无漂移 (nv_gw env 与 R2196 逐项一致, StartedAt 12:50:09Z 未重建)

改了反而破坏 R2154 稳定带。1 fallback 真新发的根因 = NVCF 上游 glm5_2_nv header/ttfb
120s 偶发阻塞 (非 nv_gw 参数能治), NV-MS-FB + cc4101 fallback 已正确吸收 0 真中断。

## 验证

0 改动 0 restart 无需验证改动。
- `curl /health` ok ✅
- `docker ps` 全栈 Up (nv_gw 7h / cc4101 3h / ms_gw 7h) ✅
- 容器 RC=0 (nv_gw=0, cc4101=0) ✅
- env 无漂移 (与 R2196 逐项一致) ✅
- nv_gw StartedAt=12:50:09Z 同 R2196 (未重建) ✅

## 铁律遵守

- 改前有数据 ✅ (30min 窗口 + 错误分类 + fallback 率)
- 聚焦 40006 ✅ (只看 nv_gw, 未碰 ms_gw 源码)
- 只改 HM2 ✅ (HM1 peer 轮 R2197-R2212 不参与, 本轮 0 改动)
- 写入仓库 ✅ (本文件)
- 不 Read /tmp ✅ (本轮无 /tmp 访问, 避免 R2082 死循环重蹈)
