---
name: glm52-thinking-toggle-truth
description: GLM-5.2思考是toggle非effort分档; opencode自带nvidia provider对glm5.2思考开不起来(源码铁证); reasoning_effort无效唯chat_template_kwargs.enable_thinking有效
metadata: 
  node_type: memory
  type: reference
  originSessionId: 25380329-22e9-46a9-be9b-8af44f0d1a9b
---

# GLM-5.2 思考模式真相(2026-07-10 会诊, 4模型专家+源码+实测)

**核心结论: opencode 自带 nvidia provider 跑 GLM-5.2, 思考本就开不起来 — "关闭思考"对用户是伪命题。**

## 源码铁证 (opencode v1.17.13, github anomalyco/opencode)

1. **nvidia provider 极简** (provider.ts:475): 只设 HTTP headers, 无思考参数注入, model 列表 autoload 自 models.dev。
2. **models.dev 数据** (api.json nvidia): `z-ai/glm-5.2`, `reasoning:true`, `reasoning_options:[{"type":"toggle"}]` ← **思考是开关型不是分档**, `interleaved:{field:reasoning_content}`, npm=`@ai-sdk/openai-compatible`, 免费(cost:0)。
3. **opencode variants() glm5.2 分支** (transform.ts:691): nvidia 走 `@ai-sdk/openai-compatible` → 返回 `{high:{reasoningEffort:"high"}, max:{reasoningEffort:"max"}}` 两档变体。
4. **AI SDK b4 函数**(二进制): reasoningEffort → `body.reasoning_effort`。但 **"max" 不在 OpenAI 标准 effort 集(low/medium/high/xhigh/none/minimal)** → isReasoningEffort("max")=false → 被拒; 即使 "high" 发出去, nvidia GLM-5.2 不认。
5. **思考注入分支** (transform.ts:1115-1156): 只对 `providerID==="opencode"`(glm-4.6) 或 `providerID.includes("zai"/"zhipuai")` 注入 `chat_template_args.enable_thinking` / `thinking.type=enabled`。**providerID==="nvidia" 不在任何分支 → 不注入任何能触发思考的参数**。

## NVCF 实测铁证 (NVU_KEY1 + 美国代理7894, 同题"What is 17*24")

| 参数 | 耗时 | content | reasoning | 思考? |
|---|---|---|---|---|
| `reasoning_effort:high`(opencode 发的) | 14.9s | 434 | 0 | ❌ |
| `chat_template_kwargs.enable_thinking:true` | 24.7s | 0 | 604 | ✅ |
| 裸请求 | 15.0s | 441 | 0 | ❌ |

**唯一有效触发思考 = `chat_template_kwargs.enable_thinking:true`(glm 原生)。reasoning_effort 对 glm5.2 完全无效。opencode 对 nvidia provider 不注入这个。**

## 本地生产 metrics (glm5_2_nv, 7天1076条 status=200)
- thinking_type/reasoning_effort **全为 None** → 生产链路本就无思考
- duration p50=14.5s p95=124.7s max=226s — **慢是 NVCF 后端 ttfb 波动, 非思考**

## 4专家共识 (glm5.2/dsv4p/kimi 完整, minimax 后端慢跳过)
- **条件关**: opencode+nvidia key 链路无需操作(本就无思考); 自建 nv_gw 链路才可选
- GLM-5.2 思考是中等深度 CoT(604字), 非质变; 关掉不跨档降级
- 自建 nv_gw 注入 enable_thinking 代价 ~10s/次(24.7 vs 15.0s)
- kimi(reasoning_effort=high, 829字 rc) 思考更易用; GLM-5.2 思考不可替代性弱, 优势仅免费+1M上下文
- p95 慢是后端问题, 关思考治标不治本

## 用户决策落地
用户当前架构(opencode→nv_gw→glm5_2_nv): **无需关闭, 本就无思考**。nv_gw config 里 glm5_2_nv `inject:{}` 空, openclaw 发的 reasoning_effort 被 strip, 不补 enable_thinking。
若想真正用 glm5.2 思考: 自建 nv_gw 把 `inject` 改 `{"chat_template_kwargs":{"enable_thinking":true}}` (config.py), 但接受 +10s/次 和 60-135s 偶发慢风险。
真要深度推理用 kimi_nv(reasoning_effort=high 已注入)。

关联:  [[nvcf-pexec-field-semantics]] [[nvcf-testing-methodology]]

## ⚠️ 重要纠偏(2026-07-11, R841b)
本 memory 的"无需操作/本就无思考"结论**仅适用 opencode→nv_gw 链路**。
**openclaw 链路不同**: R827 已把 nv_gw config.py glm5_2_nv tier 的 `inject` 改回 `{"chat_template_kwargs":{"enable_thinking":true}}`, 思考**是开着的**。opclaw4103 SUPPLEMENT-CONTENT 日志确认 reasoning_content 存在(61-533字)。详见 [[r841b-openclaw-deep-fix]]。
openclaw 链路思考开启的代价: 88k+ context(主agent固有)下 GLM-5.2 返回空僵尸(content极少+fr=stop), 占48%请求。R840 检测将其转 error+retry。
