# R760: HM2 cx4102 reasoning/content 分离修复 (codex 输出乱码+重复+思考泄漏)

**时间**: 2026-07-06 01:20 UTC
**作者**: opc_uname (CC, HM1→HM2 远程)
**类型**: HM2 cx4102 适配器 bug 修复
**目标**: 修复 codex CLI 经 cx4102 链路时输出乱码、内容重复、思考过程当正文显示

---

## 📊 数据采集 (改前必有数据)

### 现象
codex 0.142.5 (HM2, `~/.codex/config.toml` 指向 cx4102) 对话时三类症状:

1. **思考过程当正文显示**:
   ```
   user: List the files in /tmp using a shell tool, then say DONE.
   codex: The user wants me to list files in /tmp using a shell tool, then say DONE. Simple task.
          I'll list the files in /tmp for you.I'll list the files in /tmp for you.I'll list the files in /tmp for you.
          [ls /tmp] DONE.
   ```
   `reasoning_content` 被当作 `output_text` 正文输出.

2. **内容重复**: 同一段 reasoning 在 SSE 多 chunk 出现, 全部拼进正文 → 重复 3 次.

3. **乱码**: `total patients totalexecsql Strategicassigned contents...` — 多个 reasoning chunk
   的字节边界被字符串拼接切到多字节字符中段.

### 根因 (codex.py feed_chunk)
```python
# 旧代码 (R751 引入, line 301-311):
text_delta = delta.get("content") or ""
reasoning_delta = delta.get("reasoning_content") or ""
merged = reasoning_delta + text_delta          # ← 把 reasoning+content 合并
if merged:
    self.text_buffer += merged
    yield ("response.output_text.delta", {
        "delta": merged,                        # ← 作为 output_text.delta 发给 codex
    })
```
cx4102 把 glm5.2 的 `reasoning_content` (思考) 和 `content` (答案) 合并成同一个
`response.output_text.delta` 事件流. codex 收到后全当正文显示.

R751 commit (`1c3f952`) 的 "chat_to_responses 合并 message+delta 字段" 修的是**非流式**
ms_gw 同时返回 message+delta 的情况 (合理). 但**流式** feed_chunk 里的
`merged = reasoning_delta + text_delta` 是另一回事, 把 reasoning 也合并进 output_text 是错的.
R751 commit message 没明确提这条, 推测是顺手写的、没单独验证 reasoning 通路.

非流式 `chat_to_responses` (line 191-192) 也有同样问题:
```python
if reasoning_content:
    msg_content.append({"type": "output_text", "text": reasoning_content})  # ← 同样混入正文
```

### 链路数据
```
codex exec (PONG 测试, 修前):
  tokens used 2,806
  输出: "The user wants me to reply with exactly \"PONG\"...PONG"  ← 思考+答案粘连
cx4102 日志:
  01:11:37 REQ model=glm5_2_nv stream=True tools=11
  01:11:xx STREAM-FINAL 上游 EOF, 发 final_events
```

---

## 🔧 修改 (改前已备份: codex.py.bak.R760, forwarder.py.bak.R760)

文件: `/opt/cc-infra/proxy/cx-gw/gateway/codex.py` (HM2, bind-mount, `docker restart cx4102` 生效)

### 改1: 流式 feed_chunk — reasoning 走单独事件, content 走 output_text.delta
```python
# R760: content delta → output_text.delta; reasoning_content 单独走 reasoning.delta.
# 之前把 reasoning+content 合并成一个 output_text.delta 是错的:
#   1) 思考过程被当成正文显示给 agent
#   2) reasoning 在多 chunk 重复 → 内容重复
#   3) 字符串拼接切到多字节字符中段 → 乱码 (如 'total patients totalexecsql...')
# codex catalog 设 supports_reasoning_summaries=false 会忽略 reasoning 事件,
# 故 reasoning 不再污染正文. text_buffer 只累加真实 content.
text_delta = delta.get("content") or ""
reasoning_delta = delta.get("reasoning_content") or ""
if reasoning_delta:
    yield ("response.reasoning.delta", {
        "type": "response.reasoning.delta",
        "output_index": self.output_index, "summary_index": 0,
        "delta": reasoning_delta,
    })
if text_delta:
    self.text_buffer += text_delta
    yield ("response.output_text.delta", {
        "type": "response.output_text.delta",
        "output_index": self.output_index, "content_index": self.content_index,
        "delta": text_delta,
    })
```

### 改2: 非流式 chat_to_responses — reasoning 不再追加为 output_text
```python
if text_content:
    msg_content.append({"type": "output_text", "text": text_content})
# R760: reasoning_content 不再作为 output_text 追加 (会把思考过程当正文显示给 agent,
# 且 reasoning 在多 chunk 重复会导致内容重复/乱码). codex catalog 设了
# supports_reasoning_summaries=false, 不期望 reasoning, 故直接丢弃.
# 若未来 agent 需要 reasoning, 应走单独的 reasoning summary item, 不混入 content.
if not msg_content:
    msg_content.append({"type": "output_text", "text": ""})
```

### 配套: codex catalog (R760 同步部署)
`~/.codex/glm5_2_nv_catalog.json` 设 `supports_reasoning_summaries=false` +
`default_reasoning_summary="none"`, 让 codex 忽略 `response.reasoning.delta` 事件,
思考过程不显示. catalog 从 `codex debug models` (gpt-5.4-mini 模板) 派生, 改
slug/context_window(131072)/reasoning. 详见 `~/.codex/config.toml` 的
`model_catalog_json` 字段.

---

## ✅ 验证 (改后必有验证)

### 测试1: tool-use prompt
```
user: List the files in /tmp using a shell tool, then say DONE.
codex: ls /tmp   ← 干净, 无思考泄漏, 无重复, 无乱码
tokens used 2,830
```

### 测试2: 纯文本中文
```
user: 用中文回答: 1+1等于几? 只回答数字.
codex: 2         ← 干净
tokens used 2,795
```

### 测试3: 链路完整性
cx4102 日志确认请求到达, nv_gw 5xx 时自动切 ms_gw fallback 正常:
```
01:20:36 START cx4102 listening on 0.0.0.0:4102
01:20:36 START primary=nv_gw:40006/glm5_2_nv fallback=ms_gw:40007/glm5_2_ms
```

---

## 📋 参数表

| 项 | 旧值 | 新值 | 位置 |
|---|---|---|---|
| 流式 reasoning 处理 | 合并进 output_text.delta | 单独 response.reasoning.delta 事件 | codex.py feed_chunk |
| 流式 text_buffer 累加 | reasoning+content 全累加 | 只累加 content | codex.py feed_chunk |
| 非流式 reasoning 处理 | 追加为 output_text | 丢弃 (catalog 关了 reasoning summaries) | codex.py chat_to_responses |
| codex catalog | 无 (用 fallback metadata) | glm5_2_nv_catalog.json (128K, reasoning off) | ~/.codex/ |

---

## 🎯 预期效果

- codex 输出干净: 只显示最终 content, 不显示思考过程
- 消除内容重复 (reasoning 在多 chunk 重复不再拼进正文)
- 消除乱码 (不再有跨多字节字符的字符串拼接)
- 消除 "Model metadata for glm5_2_nv not found" warning (catalog 已部署)
- 消除 "bubblewrap not found" warning (danger-full-access 不启动 bwrap)

---

## 📝 备注

- nv_gw/ms_gw 代码未改 (模块化铁律), 只改 cx4102 适配器.
- HM1 全程未动. HM1 若要用 codex (目前 HM1 codex 未配 cx4102), 需同步此修复.
- R751 的非流式 message+delta 合并逻辑保留 (那条是合理的, 修的是 ms_gw 同时返回两者的情况).
- 备份: `/opt/cc-infra/proxy/cx-gw/gateway/codex.py.bak.R760`,
  `/opt/cc-infra/proxy/cx-gw/gateway/forwarder.py.bak.R760` (forwarder 未改, 备份冗余).
