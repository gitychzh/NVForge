# R1827 (HM2 cc2): bug8 观测层去噪 — 只在正常完成路径校验 args JSON

## 性质
**bug8 dump wire 观测层去噪轮** (R1826 部署的观测层在 zombie/interrupted 路径误报, 噪声盖
信号; 本轮收紧触发条件, 非降级, 不改 SSE out 字节流)。

## 依据
R1826 STATE 指示 "R1827 拉 ≥30min 窗 grep `NV-TOOLCALL-JSON-BAD` 看畸形形态, 命中则设计
降级逻辑, 零命中则 bug8 不活跃转其他点"。本轮拉 30min 窗发现 R1826 观测层命中 2 条
`NV-TOOLCALL-JSON-BAD`, 但两条 frag 都是**流式 args 被截断的噪声**:
- rid=65905391 tid=call_19d4ebad frag=`{"content": "# R1826 (HM2 cc2): bug8 dump wire — ...` (截断)
- rid=00a3149c tid=call_17b149fd frag=`{"content": "# cc2 自优化交接棒 STATE ...` (截断)

两条都是**我自己读 STATE.md / round 文件时模型生成 tool_call, args 的 content 字段被
75s ttfb 抢断 (fallback to ms_gw) 提前 finish**, args 还在流式累积就被 finish() 截走,
json.loads 必失败 → 误报为畸形。**真 bug8 = finish_reason=tool_calls 正常完成但 args 仍
畸形**; zombie/interrupted 路径 args 必不完整, 检测无意义且噪声盖信号。同时 0-token
tool_calls 真候选 40min=11 条 (持续产出) 均未 fire 观测 (因 args 为空被 `raw if raw else
"{}"` 处理为合法)。

## 改前数据 (30min 窗, restart 前拉取)
- **30min SR = 82/86 = 95.3%** (200:82, 502:4), 较 R1826 97.8% 略降但仍稳 (R1820/R1818
  双层未回退)。
- error: zombie_empty_completion x3 + all_tiers_exhausted x1 — 均为 pexec 偶发空完成/
  限流 (非 ms_fallback path), 合法 502, 非中断。
- **fallback 30min = 2 次** (bug3 持续改善通道, vs R1826 1 次/R1825 4 次/R1824 16 次,
  仍在 16→1 量级), 均为 75s ttfb 抢断 SKIP-CIRCUIT 甩 ms。
- nv_gw 真实 StartedAt 改前 = 19:17:04Z (R1826 重启, 未漂移) → 改前状态干净。
- bug8 观测层命中 2 条 (40m) = 噪声 (见上), 非真畸形。

## 改动 (单点, 热路径但极低风险)
- 文件 `proxy/nv-gw/gateway/format/oai_to_anth.py` (bind-mount, 与 R1820/R1826 同文件)。
- `finish()` 第 289 行 (调用 `_tc_json_bad_check()`):
  - R1826 原版: 无条件调 `self._tc_json_bad_check()` (在所有 finish 路径)。
  - R1827 改: `if not zombie and not interrupted: self._tc_json_bad_check()` —
    只在正常完成路径 (args 应已收完) 校验, 跳过 zombie/interrupted (args 必被流式截断)。
- **不改 out 字节流, 不引入降级, 不改 __init__/feed_chunk 累积逻辑** (R1826 那部分保留)。
- 风险红线: zero-content zombie 路径 CC 已被 graceful/error 兜底, 不依赖 args JSON
  解析, 真畸形若发生在 zombie 路径会漏报但无害 (CC 已被兜底不中断)。

## 验证 (restart 03:33:40 CST)
- `cp oai_to_anth.py oai_to_anth.py.bak.R1827` (宿主机 + 容器双备份, md5 95279a1a = R1826
  状态, 齐全)。
- md5 宿主机=容器=9ca36f63 (bind-mount 同步 ✓)。diff vs bak 只改 finish 第 289 一处 (✓)。
- `docker compose restart nv_gw` → StartedAt 更新到 19:33:40Z (= 03:33:40 CST, ✓ 新字节码
  生效)。
- `/health` ok (passthrough, 5 keys, pexec_models 齐全)。
- restart 后窗 5min: **19 条 200, 0 失败, 0 zombie/error/exception/中断, 0 fallback** →
  去噪逻辑未破坏流式 (关键风险红线解除)。
- `docker logs nv_gw --since 5m | grep -c NV-TOOLCALL-JSON-BAD` = 0 (去噪生效, 干净)。
- env 无漂移 (本轮只改 .py 未碰 compose env)。
- `.bak.R1827` 宿主机 + 容器内双备份齐 (21604 bytes, = R1826 状态)。

## 结论 + 下轮
bug8 观测层噪声已清除。真 bug8 (模型层 tool_call JSON 畸形导致 CC "could not be parsed"
中断) 在本轮 30min 窗内**未真触发** — 改前 30min 窗 0-token tool_calls 候选 11 条但观测
层 (R1826 旧版) 仅在噪声路径 fire, 正常完成路径无畸形命中。

**下轮 R1828**: 攒 ≥30min burn-in (R1827 去噪后观测层), grep
`NV-TOOLCALL-JSON-BAD`:
- 若命中 → 此时是真畸形 (正常完成但 args JSON 非法), 按 frag 分析形态 (空 args? 截断?
  引号未闭? 尾逗号?), 设计降级逻辑 (方案 C: 补闭合引号/去尾逗号; 失败则 drop tool_use
  block + stop_reason→end_turn + message_stop)。
- 若仍零命中 (持续多个 30min 窗) → bug8 当前不活跃 (0-token tool_calls 可能是 cap/zombie
  正常产物非模型畸形), 转 bug3 (fallback 16→4→2→待定, 下探 pexec 首字节慢根因 75s ttfb)。
