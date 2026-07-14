---
name: r854-disable-thinking-injection
description: "R854 真正根因修复 — nv_gw config.py 对 glm5_2_nv 强制注入 enable_thinking=True, 致 GLM5.2 把答案写进 reasoning_content 不产出 text content, CC 报 empty/filtered completion. 禁注入走普通模式 content 正常."
metadata:
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

R854 (2026-07-14, nv_gw config.py): 真正消除 "upstream returned empty/filtered completion" 的根因修复. R852/R852c 只是让 cc4101 emit api_error 触发 CC 重试, 但每次重试都再次命中 thinking-only-empty, CC 重试几次放弃仍报错给用户. R854 才是从源头不让 GLM5.2 进 thinking 模式.

## 真根因
nv_gw `config.py:106` NVCF_PEXEC_MODELS["glm5_2_nv"]["inject"] = `{"chat_template_kwargs": {"enable_thinking": True}}` (R827 开启). 每个真实 CC 请求都被强制注入 enable_thinking. GLM5.2 thinking 模式系统性把答案写进 `reasoning_content` (实测 3920-4245c) 但 `content` (text answer) 0c, 且 reasoning 涨满 max_tokens 返 finish_reason=length. CC 收"只有 thinking 没 text"报 empty/filtered completion. R827 注释"content 正常健康"已 stale (当时没测大 input / 现在模型行为变了).

## 修复
config.py:106 改 `"inject": {}` (空, 不注入任何思考参数). glm5_2_nv 走普通模式. strip_params 仍含 "thinking" 会 strip 掉 CC 自带的 thinking 字段. is_thinking_req=False → 走默认 25s timeout (普通模式秒回, 不需 150s extended).

## 验证 (软件本身测试)
- 探针 claude-opus-4-8 真实 model 名连发 8 次: 8/8 OK, 0 empty/filtered, text 89-147c, thinking=0c (普通模式不产 reasoning, content 正常).
- 6 次短请求: 6/6 OK.
- 真实 CC 流量 (nv_gw 重启后 21:52-21:53): 一连串 REQ, **0 个 ZOMBIE/empty/filtered/中断**.
- nv_gw 日志: 无 NV-INJECT-THINKING, 无 NV-THINKING-TIMEOUT — 注入确实停了.

## 残留 (非本错)
偶发 SSLEOFError: UNEXPECTED_EOF_WHILE_READING (integrate 通道 socks5 经 mihomo 网络层断). nv_gw 有 mode-advance + key-cycle 重试兜底, 不是用户报的 empty/filtered. 那是网络问题不是 thinking 问题.

## 关联
- R852/R852b/R852c (zombie 检测只看 content) 是兜底防线, 仍保留 — 万一 NVCF 恢复 thinking 或别的模型走 thinking, 仍能抓空响应让 CC 重试. 但日常不再触发 (普通模式 content 正常).
- [[r852-empty-content-zombie-fix]] [[r850-thinking-silence-miskill-fix]] [[r853-read-timeout-root-cause]]
- 备份: config.py.bak.r854 (含 R827 原 inject). NVCF 恢复 thinking 后可改回, 但需先实测 content 非空.
