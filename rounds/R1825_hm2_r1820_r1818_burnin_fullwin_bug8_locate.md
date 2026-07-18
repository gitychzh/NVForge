# R1825 (HM2 cc2) — R1820/R1818 burn-in 全胜宣告 + bug8 dump wire 调查轮 (不改代码)

> 性质: 巡检+调查轮 (非新改)。验证 R1820 graceful-end 兜底 + R1818 cap_origin 根治 在更长 burn-in 窗是否持续稳定; 定位 bug8 (tool_call JSON 畸形) 候选行 + 转换路径, 为下一轮 R1826 dump/降级做准备。
> 时间: 2026-07-19 02:41 CST (nv_gw 真实 StartedAt = 2026-07-18T18:07:50Z = 02:07:50 CST)
> 铁律: 改前必有数据, 改后必有验证, 聚焦 40006, 不碰 40007, 只改 HM2。

## 1. 数据 (改前必有数据 — git pull R1824 最新后拉)

### burn-in 窗 (真实 StartedAt 18:07:50 UTC → 18:40 UTC = 33min, 超 STATE 要求 30min 临界)
- **30min nv_requests SR = 64/66 = 97.0%** (200:64, 502:2)
- 重启后 33min 窗 error 仅 2 条:
  - `all_tiers_exhausted` x1 (18:17:53, dur 70s, output=0) — 极早期系统级降级, R1820 兜底覆盖不到的 send_response 前失败, 合法
  - `stream_absolute_cap` x1 (18:27:22, dur 162s, output=0, **upstream_type=nvcf_pexec, peek_swapped=False**) — NV 原生 peek 阶段首字节 162s 极慢被 150s cap 砍, 属 **bug4 (cap 慢流误杀) 边界非 bug7 (cap 误杀已 relay 的 ms 内容)**。R1818 cap_origin 重置只管 `upstream_type=="ms_fallback"` 漏路径, 这条是 NV 原生 path, 不在 R1818 覆盖范围, 属 R1797 cap=150 留作 pexec 偶发真 hang 兜底的预期内
- **zombie_empty_completion 重启后窗 = 0** (R1820 graceful-end 兜底铁证, 对比 R1820 前会 event:error→CC 中断)
- **真实 mid-response 中断 = 0** (cc2.jsonl 40 条记录里 "Server error mid-response"/"could not be parsed" 字符串命中 2 条均为本轮对话内容本身, 非历史中断记录; R1824 "4 条" 是 grep 到 STATE.md 文本被回显的误判)

### fallback 率 (bug3, 负向核心指标) — 显著改善
- cc4101 30min: FALLBACK-OK = **4 次** (R1824 同窗 16 次, **降 75%**)
- PRIMARY-FAIL = 8 次 (4 次成功 fallback 甩 ms_gw, 其余被 nv_gw tier 内重试自愈)
- 全 75s/120s ttfb timeout (SKIP-CIRCUIT), nv_gw pexec 首字节超时被 cc4101 75s 抢断甩 ms_gw

## 2. R1820/R1818 落地确认 (防漂移, 与 R1824 一致)
- `oai_to_anth.py` finish() line ~245: `if flushed_content_chars > 0 or self.message_start_sent:` → graceful ✓
- line ~273: `if interrupted and ... and not self.message_start_sent:` → 只 message_start 没发才 event:error ✓
- `docker logs nv_gw` 近 30min: `NV-CAP-RESET-MSFB (glm5_2_nv) ... peek_swapped=False, total_elapsed_pre_reset=364s, req=3381371b` 触发 ✓ (R1818 cap_origin 重置路径命中铁证, ms_fallback 流 cap 只盯 ms 这段)
- /health ok, nv_gw Up (StartedAt=2026-07-18T18:07:50Z 未重启过), ms_gw 热备在 ✓

## 3. bug8 (tool_call JSON 畸形) 调查 — 本轮核心, 为 R1826 铺路

### 病灶定位 (转换单元 = `proxy/nv-gw/gateway/format/oai_to_anth.py`)
- `feed_chunk` tool_calls 分支 (line 179-203): 每个 tool_use 的 arguments 作为 `input_json_delta.partial_json` 逐块**透传**给 CC SDK, converter **不做 json.loads 校验**
- CC SDK 收尾时拼接完整 partial_json 做 `json.loads()`, 畸形则抛 "could not be parsed" 中断 session
- 非流式路径 line 357-363: `input_data = json.loads(fn.get("arguments","{}"))` 失败则 `{"raw": ...}` 兜底 (这条路径已有兜底, 但流式 partial_json 透传路径没有)

### DB bug8 候选行 (重启后窗, finish_reason=tool_calls 但 output_tokens=0 — 极可疑, 正常 tool_call 应有 token)
- 18:15:47 起连续多条 `status=200 finish_reason=tool_calls output_tokens=0` (rid: 0c83c984/24d04d75/6f78ec8d/a301bec1/12cd733f/7fb28502/eed7d283/c0f44490...)
- 这些 0-token tool_calls 很可能是 stream 后 cap/zombie 兜底转 200 时 arguments 为空或畸形 — 即 bug8 的实际触发形态
- **注**: nv_requests 不存 response body (无 arguments wire 列), 无法直接从 DB dump 畸形形态

### R1826 dump 方案 (下一轮执行, 本轮不改)
- 在 `oai_to_anth.py` finish() 收尾路径 (stop_reason=tool_use 分支, 即 pending_stop_reason=="tool_use" 时), 对 converter 内累积的各 tool_use 完整 partial_json 拼接后 `json.loads()` 校验:
  - 畸形则记 `[NV-TOOLCALL-JSON-BAD]` 日志 (含 rid + 原始 arguments 片段) — 先纯观测, 不降级
  - 确认畸形形态后再设计降级逻辑 (方案 C: 补闭合引号/去尾逗号; 失败则 drop tool_use block + stop_reason→end_turn + message_stop)
- **风险**: 改 feed_chunk/finish 是热路径, 搞不好把正常 tool_call 也降级 (破坏 cc2 自己工具调用能力)。必须先纯日志观测 ≥1 轮确认畸形形态, 再动降级逻辑

## 4. 本轮决策: 为何不改代码
1. **R1820/R1818 burn-in 已超 30min 临界且全胜** (SR 97%, zombie=0, 真实中断=0, fallback 16→4), 用户诉求"不中断" 持续达成 — 无新中断场景需补 graceful 条件
2. **bug8 dump 是前置依赖**: STATE 01:50 监督者明确"需先 dump 一条 tool_call parse 失败时刻的 wire 确认畸形形态, 再设计校验/修复逻辑"。本轮已定位转换单元 + 候选行, 但 dump wire 需加临时日志观测一轮, 直接改降级逻辑会盲动热路径
3. **唯一 bug7 复发 (18:27:22) 实为 bug4 边界** (NV 原生 peek 首字节 162s, 非 ms_fallback path, R1818 不该覆盖), 不需补 R1818 条件
4. 小步快走, 一轮一动: 本轮=调查定位, 下轮 R1826=dump 日志观测, 再下轮=降级逻辑

## 5. 验证清单 (本轮无代码改动, 验证=数据复测)
- [x] /health ok: `{"status":"ok", "nv_num_keys":5, ...}`
- [x] docker ps: nv_gw/cc4101/ms_gw 全 Up
- [x] nv_gw StartedAt 未变 (18:07:50Z, 本轮无 restart)
- [x] 30min SR 97.0%, zombie=0, 真实中断=0, fallback 4 (vs R1824 16)
- [x] R1820/R1818 源码落地确认 (finish line 245/273, NV-CAP-RESET-MSFB 触发)
- [x] env 无漂移 (KEY_COOLDOWN=25, UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET=180, STREAM_ABSOLUTE_CAP=150)

## 6. 下一轮 (R1826) 该做什么
1. 读本 STATE (R1820/R1818 全胜, bug8 转换单元=feed_chunk line 179-203, 候选行=0-token tool_calls)
2. 在 `oai_to_anth.py` finish() tool_use 收尾分支加 **纯观测日志** (不改降级逻辑): 对累积 partial_json 做 json.loads, 畸形记 `[NV-TOOLCALL-JSON-BAD]` 含 rid+原始片段
3. `cp oai_to_anth.py oai_to_anth.py.bak.R1826` → restart nv_gw → 攒 ≥30min 观测窗 → grep 日志确认畸形形态 (空 arguments? 截断? 引号未闭合?)
4. 若形态清晰 → R1827 设计降级逻辑 (方案 C); 若 30min 零畸形 → bug8 当前不活跃, 转其他点
5. fallback (bug3) 已 16→4 显著改善且不致中断, 暂非首要; 若 R1820 burn-in 持续稳, 可考虑下探 bug3 (pexec 首字节慢的根因)
