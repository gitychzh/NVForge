---
name: r852-empty-content-zombie-fix
description: "R852/R852b — zombie 检测改只看 content_chars 不加 reasoning_chars; GLM5.2 thinking 产出 3920c reasoning 但 0c content 时 CC 报 empty/filtered completion, 旧检测漏判"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

R852 (2026-07-14, cc4101 stream.py + nv_gw handlers.py R852b): 修 "upstream returned empty/filtered completion, please retry" 错误.

**真根因**: GLM5.2 thinking 模式(`enable_thinking=True`)实测产出大量 reasoning_content (probe 实测 3920c/4174c) 但 **text content 为 0c** — 模型把答案写进思考里没给正式回答. cc4101 把 reasoning 转 thinking block 正常返回, CC 收到一个"只有 thinking 没 text content"的 message → 判定 empty/filtered completion 报错.

**旧 bug**: cc4101 stream.py 三处 zombie 检测 + nv_gw 一处, 都用 `(content_chars + reasoning_chars) < 50`. 当 reasoning=3182c 时 sum≥50 → 条件 False → 不判 zombie → 干净 message_stop → CC 收空. 三个站点: stream.py:107(_emit_graceful_end 守卫), :257(clean-EOF zombie), :446(finish_reason=stop zombie); nv_gw handlers.py:791.

**修复**: 全改 `stream_content_chars < 50` (只看 text answer, 不加 reasoning). CC 真正需要的是 text content, thinking 是辅助 — 思考完没产出文本答案就是空壳, 该让 CC 重试.

**验证**: 21:05:45 真实 CC 会话 input=197038c finish_reason=tool_calls content=0c → `[ZOMBIE-EMPTY-STREAM] ... emitting api_error so CC retries (req=f75003a6)` — R852 抓到, CC 重试. (注意: probe 小 input <5000c 不触发, 因 zombie 要求 total_input_chars>=5000 只兜大 context; 小 input 模型正常产出 text, 如 "2+2等于几" → thinking 304c + text "2+2等于4。" 正常.)

**R852c (finish_reason=length 扩展, 同会话补)**: probe 大 input(6455c) thinking 实测 reasoning 涨到 max_tokens=2048 时 content 仍 0c, 上游返 **finish_reason=length** + 0c content. 旧 zombie 只抓 `finish_reason in (stop,tool_calls)`, length 漏网 → cc4101 发干净 message_stop(max_tokens) → CC 收空回答报 empty/filtered. 修: zombie 条件加 `_is_thinking_only_length = (finish_reason=="length" and content<50 and reasoning>50)`, 把 length 也判 zombie(需 reasoning>50 佐证是 thinking-only 截断, 非真 length-truncated 有文本). 验证 21:34-21:36 连续 4 req (a86bb4ee/1bd1c860/e7da1b1a/55effcf7) 全 `[ZOMBIE-EMPTY-STREAM] finish_reason=length content=0c reasoning=~4000c → api_error`; 累积到 5 触发 `[PRIMARY-BREAKER-OPEN] fast-fail (R851)`. probe 侧 `saw_error=True err_msg='upstream returned empty/filtered completion, please retry'`.

**边界**: zombie 阈值要 total_input_chars>=5000 才触发(避误杀短问答). 真实 CC 会话 input 动辄 100k+ 远超阈值, 必中. 小 input 即便 thinking-only-empty 也不兜(罕见, 小问题模型通常会给 text).

**注意 thinking 静默 vs thinking-only-empty 是两个不同故障**: thinking 静默=上游发完首块 reasoning 后长时间不发 chunk → 走 idle-stall 路径(200s)报 "stream interrupted"; thinking-only-empty=上游正常发完 finish_reason=stop 但 content 空 → 走 zombie 路径报 "empty/filtered". 两条路都 emit api_error 让 CC 重试. R853 修前者(让 stall-watcher 能跑), R852 修后者.

关联: [[r853-read-timeout-root-cause]] [[r850-thinking-silence-miskill-fix]] [[r840-openclaw-zombie-empty-stall-fix]]
