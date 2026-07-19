# R1932: nv_gw oai_to_anth.py finish() 补读 saw_real_tool_call flag

**Commit**: 2cddb85 (already committed by cc2, this dir archives the before/after source)
**Host**: HM2 only
**Date**: 2026-07-19

## 根因

CC SDK "tool call could not be parsed (retry also failed)" session 中断 (3 次/2d) +
132 次 malformed retry 成功。

NVCF "半响应" — 声明 `finish_reason=tool_calls` 但实际未发任何带 id+args 的真
tool_call delta (`saw_real_tool_call=False`)。converter `oai_to_anth.py` finish()
里 `pending_stop_reason` 被 finish_reason chunk 设成 "tool_use" 但 CC SDK 看不到
tool_use block → "could not be parsed" → session 中断。

## 修复

finish() zombie + normal 两路径补:
```python
if self.pending_stop_reason == "tool_use" and not self.saw_real_tool_call:
    final_stop = "end_turn"
```

补的是 finish() 漏读的 `saw_real_tool_call` flag (line 74 init / 166 set=True,
只在 tool_call delta 带 id+非空 args 时置真)。与 R1839 `_detect_bad_tool_args`
互补: R1839 兜 "有 block 但 args 畸形", R1932 兜 "声明 tool_calls 但压根没发 block"。
正常 tool_call (id+args 齐全) saw_real_tool_call=True 不受影响。

## 文件

- `oai_to_anth.py.before_R1839` — R1839 版基线 (before R1932 fix)
- `oai_to_anth.py.after_R1932` — R1932 fix 后 (= 当前 live)

## 验证

R1933 restart (13:33:43Z) 之后, parse-fail signature
(`status=502 AND finish_reason=tool_calls AND error_type=zombie_empty_completion`)
2d hourly 趋势: R1933 前每小时 1-5 次, R1933 后 **0 次** (持续 1h+ 验证)。

关联: R1933 (半成品指数退避 NameError 紧急修复, R1932 restart 显形)。
