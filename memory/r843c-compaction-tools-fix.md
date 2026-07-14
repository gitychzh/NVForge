---
name: r843c-compaction-tools-fix
description: "R843C方案C执行-openclaw compaction估算漏算tools修复+contextWindow 65536→48000,让main agent到95k chars自动compact离开88-102k死亡窗口"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

R843C 方案C 执行(2026-07-11 HM2),治 main agent 落 88-102k chars 死亡窗口根因。

**真根因(颠覆 R842 结论)**:openclaw `estimateLlmBoundaryTokenPressure`(attempt.tool-run-context-BdvQvDEH.js:147)只算 history+system+prompt,**完全漏算 tools**(tools 作为 API `tools:` 参数单独传,不进 messages/system)。main agent tools 42k chars 漏算约 14000 tokens(×1.2=16800)。且 contextWindow 配 65536 → 触发阈值 57536 tokens,远大于死亡窗口 25-29k NVCF tokens(88-102k chars)。compaction 永远不在死亡窗口前触发。

**两处必须协同修复(C1+C2,缺一不可)**:
- C1: 修 `estimateLlmBoundaryTokenPressure` 加 `toolsTokens = Array.isArray(params.tools) ? estimateJsonPayloadTokenPressure(params.tools) : 0` 累加(JSON_PAYLOAD_CHARS_PER_TOKEN=3,比 ESTIMATED_CHARS_PER_TOKEN=4 准,因 tools 是 JSON schema)
- C2: openclaw.json glm5_2_nv `contextWindow 65536 → 48000`(触发阈值降到 40000 tokens)
- **协同必要性**:88k chars 时,不修 C1 估算 27500 远低于 40000 不触发;修 C1 后估算 36000(仍<40000,刚不到);95k 时估算 40000 触发 ✓;102k 时 43500 触发 ✓。C1 让估算准,C2 降阈值,两者配合在 95k chars(死亡窗口中部)触发 compact。

**patch 三处**:
1. attempt.tool-run-context-BdvQvDEH.js:151 加 toolsTokens 行
2. selection-CVIPXpKT.js:13556 调用 `estimateLlmBoundaryTokenPressure` 加 `tools: effectiveTools`(effectiveTools 在 runEmbeddedAttempt 同作用域 11485 定义)
3. openclaw.json glm5_2_nv contextWindow 65536→48000

**验证**:
- node 单元测:25 tools×1700c(42591c payload)→ withTools=41080 withoutTools=24044 diff=17036 = 14197×1.2=17037 ✓ 精确匹配
- node --check 两文件语法 OK
- opclaw4103 restart 后短请求正常响应(opclaw-gw-token auth),reasoning_content 正常
- 正常短请求估算 28242 < 40000 不触发过度 compact ✓

**未碰的次要路径**:`shouldPreemptivelyCompactBeforePrompt` 内部 175 行 unwindowed 分支 + 7100 midTurnPrecheck 调用点仍漏算 tools。主路径 13561 通过 llmBoundaryTokenPressure(已含 tools)间接覆盖。midTurn 是辅助检查,漏算 14000 tokens 误差可接受(14k/48k≈29%,且 mid-turn history 已含大量 tool results 占主导)。未碰是为降风险。

**备份**:openclaw.json.bak.preR843C + attempt.tool-run-context-BdvQvDEH.js.bak.preR843C + selection-CVIPXpKT.js.bak.preR843C(全在 HM2 对应路径 .bak.preR843C)

**待观察**:生产 zombie 率是否下降(长期指标)。若 RR 优先+方案C 后 zombie 基本消失则方案5 D(换 dsv4p)不��做。fallback(R842c content_filter 切 ms_gw)仍兜底。

**HM1 待同步**(按铁律:改 HM2 不动 HM1 本地即可,但此 patch 是 openclaw 源码层,HM1 若同源需同步;实际 HM1/HM2 openclaw 可能不同源,需时再查)
