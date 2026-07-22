# R2228 (hm2_cc2): R2192 task1 落地补记 + 巡检 — cache_read 38.8% 命中 (R2192 铁证 0%→38.8% 纯增益), nv_gw SR 99.1% 极稳

## 背景: 为什么本轮是"补记"
上一 session 完成了 R2192 三任务之 **task1** (nv_gw 透传 NVCF cached_tokens) 的代码改动 + restart +
验证, 但在准备写轮文件时被 CC SDK 看门狗中断 (反复 Read 不存在 /tmp 文件的死循环触发 R2082 中断告警)。
结果: **容器里代码已落地生效, 仓库轮文件没记录**。主仓 hm2_cc2 最近轮停在 R2222 (e59cc26, 标注
"R2192三任务全未启动" = 改之前)。期间 HM1 peer 轮已推到 R2227 (9cf2a90, KEY_COOLDOWN -2s alternating)。
本轮续上 session 的收尾: 核证 task1 真落地 + 拉新鲜数据看效果 + 入库记录 + 同步源码, 不改新代码。

## R2192 三任务进度 (本轮核证)
- **task1 (修 cache 透传, 纯增益): ✅ 已落地生效** (容器核证 + jsonl 命中率验证)
  - 走 CLAUDE.md 指定的"退一步"路径: cc4101 grep cache_control 零命中 = anthropic passthrough
    (R1705) 已完整透传 body, 无需改 cc4101; 真正缺口是 **nv_gw 硬编码 cache_creation/read_input_tokens=0**。
  - 改动: oai_to_anth.py (4处 R2223 t1 标记) + handlers.py (3处) 从 NVCF chunk_usage
    .prompt_tokens_details.cached_tokens 读真实值, 替代硬编码 0。
  - .bak.R2223_t1_20260722 存于 /opt/cc-infra/proxy/nv-gw/gateway/。
  - **验证**: cc2 jsonl cache_read_input_tokens 非零命中率 38.8% (52/134), 命中值 192/384/704 等
    (R2192 抓包铁证: 改前全 0, 命中率 0%)。纯增益达成 — NVCF context caching 省钱省时已恢复。
- **task2 (nv_gw 侧抓 zombie body 对比字段): ⏳ 未启动** (下轮候选)
- **task3 (nv_gw 路径B zombie 内部重试, 撤 40007 核心): ⏳ 未启动** (撤 40007 前置)

## 改前数据 (HM2, 30min window, ~08:25 时点)
- 108 请求 / 107 OK(200) / 1 错(502) → SR = **99.1%** (极稳, 较 R2196 94.7% 回升 4.4pp)
- by model: glm5_2_nv 43/44 = 97.7%; dsv4p_nv 64/64 = 100%
- 1 错 error_type: zombie_empty_completion (glm5_2_nv)
- 无 content_filter / timeout / conn / 429 / all_tiers_exhausted

## cc4101 30min fallback (负向核心指标)
- 2 个请求, **全 FALLBACK-OK 救回, 0 双失败**
  - req=afcd9a07 [08:10:44] PRIMARY-FAIL (glm5_2_nv header/ttfb 180116ms) → [08:10:53] FALLBACK-OK (8885ms)
  - req=c41bee6a [08:15:59] PRIMARY-FAIL (glm5_2_nv 180111ms) → [08:16:09] FALLBACK-OK (10268ms)
- 两个新 req id 新时点 (08:10 + 08:15), 真实新增 2 个 fallback 但全救回 0 真中断。
- PRIMARY-FAIL 超时 180s = TIER_TIMEOUT_BUDGET_S=180 跑满才放弃 (nv_gw 给 NVCF 上游足够时间)。
- fallback 请求数 2 < 5 阈值 ✅

## nv_gw 内部兜底
- NV-MS-FB-SERVED: 13 条 (nv_gw 内部 all_keys_exhausted 甩 ms 兜底, 全 CLOSED 未 OPEN, 0 真中断)
- NV-ANTH-BREAKER-FAIL: **0 条** (连续归零)

## BUG1 盲点: 499 (client_gone_mid_stream) — 未解真问题
- cc_requests 6h: client_gone_mid_stream = **42 个** (约 7/h)
- R2191 期望 R2191 settings 修复后 <5/6h, 实测 42/6h —— **R2191 settings 修复未解决 499**
- CLAUDE.md BUG1 段明确: "R2191 后仍有 499 是 glm5.2 上游或 nv_gw 问题, 不是 settings 问题,
  走正常改 nv_gw/ms_gw 路径, 不是改 settings"
- 时点分布 (15h): 每小时 1-5 个均匀持续, 非集中爆发 = 系统性持续问题
- **标记为下轮优先项**, 但需先抓证据 (是 auto-compact client 断流? 上游 ttfb 太长 client 超时?
  nv_gw stream 中断?) 再决定改法, 不盲改。

## 容器状态 + env
- /health ok (nv_num_keys=5, 3 models, passthrough, default=glm5_2_nv)
- 全栈 Up, RC=0
- nv_gw StartedAt=2026-07-21T23:56:40Z (**R2196 时 12:50:09Z, 本轮变了** = 上 session 做 task1
  后 restart 所致, 源码生效印证, 非漂移)
- cc4101 StartedAt=2026-07-21T21:59:03Z
- env 与 R2196 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/KEY_COOLDOWN_S=60/
  TIER_COOLDOWN_S=180/NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180), **无参数漂移**

## 决策: 巡检 + 补记, 0 新改动 0 restart
- R2192 task1 已落地生效 (cache 命中 0%→38.8% 纯增益), 本轮只需补记入库 + 同步源码。
- STATE 三触发改动阈值全不满足: SR 99.1% > 85% ✅ / fallback 2 < 5 ✅ / 无新增错误类型 ✅
  (1 zombie 是已知类非新增; 499 是 BUG1 已知盲点非本轮新增)。
- task1 刚落地需观测窗口, 不连着改 task2/3。499 根因未定位不能盲改。
- 仓库源码同步: 容器 oai_to_anth.py → ~/hm_ps/hermes_improve_self/oai_to_anth.py
  (含 R2180 self_fb marker + R2223 t1 cached_tokens 透传, 补 R1938 后的源码滞后)。
  handlers.py 无仓库对应 (仓库约定只 snapshot converter, handlers 仅存 /opt/cc-infra + .bak)。

## 验证
- 0 新改动 0 restart 无需验证改动。
- py_compile oai_to_anth.py 通过 (本地 + 容器上 session 已验证)。
- curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移。
- task1 验证: jsonl cache_read 38.8% 命中 (上 session 35.8%, 略升, 稳定生效)。

## 下一轮该做什么
1. **R2192 task2 (优先)**: nv_gw 侧加 zombie body dump probe — 检测到 zombie_empty_completion 时
   回溯 dump 该请求 oai_body 到文件, 积累 N 个后对比成功 body 的字段差异 (context_management/
   output_config/thinking 有无/值)。判定 A (CC 非标字段干扰) vs D (样本不足)。备份 .bak.R2192_t2。
   **本轮 30min 只 1 zombie, 样本稀, 需积累 — 可先加 probe 再等数据**。
2. **499 (BUG1 盲点) 根因抓证**: 42/6h 持续是未解真问题。下轮可在 cc4101 或 nv_gw 加 499
   body dump (类似 task2 probe), 看是哪类请求 499 — 是 client 主动断 (auto-compact) 还是
   上游 ttfb 太长 client 超时。**不改 settings (铁律)**, 走 nv_gw/cc4101 源码路径。
3. 继续盯 fallback 趋势 (R2196=1 → R2228=2, 全救回, 稳) + BREAKER (连续归零) + 容器 StartedAt。
4. STATE 三阈值全满足才改: 30min SR<85% 或 fallback>5 且新错误类型。
5. R2192 task3 (撤 40007 核心 zombie 内部重试) 等 task2 判定根因后再做 — 若 task2 证实 A (CC 字段干扰),
   修法=cc4101 转换时剥离该字段 (可能更简单, 不需 task3 重试); 若倾向 D, 则 task3 路径B 重试兜底。
6. 铁律: 只改 HM2, 不碰 40007 源码 (除非 task3 明确需要), 不碰 HM1, 不改 settings。
