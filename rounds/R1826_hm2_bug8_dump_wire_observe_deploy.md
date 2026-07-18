# R1826 (HM2 cc2) — bug8 dump wire 纯观测层部署生效

## 性质
bug8 tool_call JSON 畸形 **纯观测轮**(非降级,不改 SSE out 字节流)。在
`oai_to_anth.py` feed_chunk/finish 加 `[NV-TOOLCALL-JSON-BAD]` 日志,确认畸形形态后再
设计修复逻辑。**本轮只把观测层部署生效(restart),下轮拉 ≥30min 观测窗 grep 形态。**

## 改前数据 (30min 窗, restart 前拉取, 2026-07-19 03:1x CST)
- **30min SR = 91/93 = 97.8%** (200:91, 502:2), 较 R1825 33min burn-in 窗 97.0% 略升 →
  R1820/R1818 双层仍稳。
- nv_gw 真实 StartedAt 仍为 2026-07-18T18:07:50Z (R1820 重启时间, 未漂移) → 本轮改前
  状态干净。
- **error 仅 zombie_empty_completion x2** (rid 42c45ece@19:05:03, 4ec98821@19:05:09,
  glm5_2_nv/nvcf_pexec/finish_reason=stop, ttfb 6988/4239ms) — 均远晚于 R1825 burn-in
  窗截止, 属 pexec 偶发空完成 (非 ms_fallback path, R1818 不覆盖, R1820 graceful 兜底
  未捕到 = send_response 前失败 合法 502)。
- **fallback 30min = 1 次** (vs R1825 4 次, 持续降) — bug3 改善趋势延续, 仅 1 条
  PRIMARY-FAIL-SKIP-CIRCUIT 75s ttfb 抢断甩 ms。
- **bug8 候选持续产出**: 重启后窗(R1820 18:07:50 UTC 起) `finish_reason=tool_calls AND
  output_tokens=0` 累计 **31 条** (min 18:15:47, max 18:56:12) — bug8 仍活跃, 值得 dump。

## 改动 (R1826 观测层, 上一被中断 session 已写代码+备份, 本轮只 restart 让生效)
**文件**: `proxy/nv-gw/gateway/format/oai_to_anth.py` (bind-mount, 容器内
`/app/gateway/format/oai_to_anth.py` 同步, md5 一致 95279a1a...)

**改动内容** (纯观测, 绝不降级, 绝不改 SSE out):
1. `__init__` 增 `request_id` 参数 (handlers.py:870 已传 `metrics.get("request_id")`),
   None-safe 兜底 `or "-"`。
2. `__init__` 增累积结构: `tool_args_acc={}` (tool_use id → 拼接 args str),
   `tool_ids_order=[]`, `_active_tool_id`, `_tc_json_bad_logged` (每请求至多记 1 次)。
3. `feed_chunk` tool_calls 分支 (line 198-230): 每个 tool_use content_block_start 时记
   `_active_tool_id` + 初始化 acc; 后续 arguments delta 累加进 `tool_args_acc[id]`。
   **不改变 out 字节流**, 仅旁路累加 (line 211-218, 224-226 注释明确 PURE OBSERVATION)。
4. 新增 `_tc_json_bad_check()` (line 246-272): 对每个累积 args 做 `json.loads()`, 畸形则
   `print("[NV-TOOLCALL-JSON-BAD] rid=.. tid=.. len=.. frag=..")` 到 stderr (→ docker
   logs), frag 截断 500 字符防爆。**纯 print, 不 return 任何修改, 不 downgrade**。
5. `finish()` (line 289): `self._tc_json_bad_check()` 在 emit stops 前, **所有 finish 路径
   (zombie/interrupted/normal/200/502) 都触发** → 覆盖 R1825 候选的 0-token tool_calls
   兜底转 200 场景。

**备份**: `.bak.R1826` 宿主机 + 容器内双备份齐 (19584 bytes, mtime 03:05, = 改动前的
R1820 状态)。

## 验证 (restart 后 2026-07-19 03:17:04 CST)
- `docker compose restart nv_gw` → StartedAt 更新到 `2026-07-18T19:17:04Z` (✓ 新字节码生效)。
- `/health` ok (passthrough, 5 keys, pexec_models 齐全)。
- restart 后窗 (19:17:04 UTC 起): **2 条 200, 0 zombie, 0 中断** → 观测逻辑未破坏流式
  (关键风险红线解除)。
- `docker logs nv_gw --since 10m | grep -c NV-TOOLCALL-JSON-BAD` = 0 (刚 2 条, 未命中
  畸形, 符合预期 — bug8 候选概率非 100%, 需更长窗)。
- env 无漂移 (本轮只改 .py 未碰 compose env)。

## 为何只到"部署生效"就停手
- bug8 dump 形态需 ≥30min 观测窗 (R1825 STATE 步骤 4 明确), 本 session 不可能等满。
- 本轮职责 = 把观测层跑起来 + 验证不破坏流式, **形态分析留给下一轮**(拉 ≥30min
  NV-TOOLCALL-JSON-BAD 命中行, 看是空 args/截断/引号未闭/尾逗号 哪种)。
- 风险红线遵守: 改前 cp .bak.R1826, restart 后即时验证 0 中断, 回滚就绪。

## 下一轮该做什么 (R1827)
1. 读本 STATE (R1826 观测层已部署生效, StartedAt 19:17:04 UTC)。
2. 拉数据确认 restart 后窗 R1820/R1818 仍稳 + **grep `docker logs nv_gw --since 40m |
   grep NV-TOOLCALL-JSON-BAD`** 看 bug8 畸形形态。
3. 若命中 → 按 frag 分析形态 (空 args? 截断? 引号未闭? 尾逗号?) → 设计降级逻辑
   (方案 C: 补闭合引号/去尾逗号; 失败则 drop tool_use block + stop_reason→end_turn)。
4. 若 30min 零命中 → bug8 当前不活跃 (可能 0-token 是 cap/zombie 兜底正常产物, 非模型
   层畸形), 转其他点 (fallback bug3 已 16→4→1 可下探 pexec 首字节慢根因, 或巡检)。
5. 任何降级逻辑改动都需 `cp .bak.R1827` + restart + 30min burn-in 验证无新中断。
