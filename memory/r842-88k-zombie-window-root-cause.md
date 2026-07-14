---
name: r842-88k-zombie-window-root-cause
description: "glm5_2_nv 在 88k-100k chars 窗口 80% 空僵尸的真根因,非���纯context太大"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

# R842: 88k 空僵尸真根因 = model × context 窗口,非单纯 context 太大

**日期**: 2026-07-11
**对象**: HM2 远程 openclaw main agent(glm5_2_nv)

## 决定性数据(model × input_chars bucket, 07-11 全天精确统计)

用 `error_type=zombie_empty_completion`(R840 标记)精确判据:

| model | input_chars | n | zombie | rate |
|---|---|---|---|---|
| **glm5_2_nv** | **88k-100k** | **60** | **48** | **80.0%** ← 唯一问题区 |
| glm5_2_nv | <50k | 40 | 0 | 0% |
| glm5_2_nv | 50-80k | 2 | 0 | 0% |
| glm5_2_nv | 80-88k | 2 | 0 | 0% |
| glm5_2_nv | 100k+ | 31 | 0 | 0% ← 100k+ 反而全成功 |
| dsv4p_nv | 任何区间 | ~1233 | 0 | 0% ← 全稳 |

## 颠覆性结论

1. **不是单纯 context 太大**:100k+ chars(glm5_2_nv)0% zombie,88k-100k 反而 80%
2. **是 glm5.2 特定窗口 bug**:NVCF 后端对 glm5.2 在 88k-100k chars 区间返回空僵尸,边界外全 OK
3. **dsv4p_nv 全区间 0% zombie**:dsv4p context 支持更稳健
4. **main agent 当前请求 98759 chars**:正好落在 glm5_2_nv 的死亡窗口(88-100k)→ 每次 ping 都触发 zombie → R840 retry 3 次 → LLM request failed

## main agent 请求构成(R842 临时 dump 实测, 98759 chars)

```
grand=98759 chars (~38k tokens, 但 NVCF tokenizer 可能算到 100k+ tokens 触上限)
├── system prompt: 37896 (system message)
├── tools 定义: 42429 (25 tools: cron 12525, message 7798, skill_workshop 2444...)
├── messages 历史: 41395 (70条, 但其中 system 37896 重复, 实际对话仅 ~3500 chars)
└── 死重(system+tools) = 80325 chars = 总量 81%
```

## C+D 方案落地结果(openclaw.json, 已应用)

- **C**: `contextWindow: 131072 → 65536`(先试 32768 但 overflow,静态 system+tools ~31k tokens > 24768 budget → `context_overflow precheck`;改 65536 后 budget=57536 不 overflow)
- **C**: `agents.defaults.compaction.reserveTokens: 8000`(注意路径!非顶层 `agents.defaults.reserveTokens`,zod schema 拒绝 "Unrecognized key")
- **D**: `agents.defaults.heartbeat.every: "30m" → "2h"`(减累积频率)
- 备份: `openclaw.json.bak.preR842`

## compaction 估算的致命盲区

`estimateLlmBoundaryTokenPressure`(attempt.tool-run-context-BdvQvDEH.js:175):
- 只估算 `historyTokens + systemTokens + promptTokens`
- **tools 定义(~16k tokens)不参与估算**(tools 在 provider 层注入,不进 messages 数组)
- 所以 estimatedPromptTokens(~14.5k)远小于 promptBudgetBeforeReserve(57536) → compaction 永不触发
- **结论:contextWindow 调小无法在"对的时机"触发 compaction,因为估算漏算 tools**
- compaction 只有在历史本身大到 >57k tokens 才触发,但那时实际请求(含 tools)已达 ~73k+ tokens

## 当前状态

- C+D 已应用,服务干净启动无 config error
- 但 main agent 仍在 88-100k 死亡窗口(98759 chars)→ 仍 zombie
- **真正解法不是 compaction,是让 main agent 请求避开 88-100k 窗口**
  - 要么把死重(system 38k + tools 42k = 80k)砍下来 → 请求降到 <88k
  - 要么用 dsv4p_nv(全区间 0% zombie)
  - 要么让 main agent 不带 25 个 tools(砍 tools 42k 死重最大)

## 待深挖方向

1. main agent 的 25 个 tools 谁最大?能否瘦身(cron 12525c, message 7798c)
2. system prompt 37896c 里 project 16219 + nonProject 21730,各自能砍多少
3. 100k+ 区间 glm5_2_nv 0% zombie 但 88-100k 80% —— 是 NVCF prompt cache 边界?tokenizer 边界?需抓包确认
4. contextWindow=65536 配合历史自然累积能否触发 compaction(需 main agent 跑长对话验证)

## main agent 88k context 构成(临时 dump 实测)
```
grand=98759 chars (~38k tokens, NVCF tokenizer 可能算到 100k+ 触上限)
├── system: 37896 (45%) = nonProject 21730(openclaw内置不可改) + project 16219(AGENTS.md 8478 + MEMORY.md 4370 + SOUL/TOOLS 等)
├── tools: 42429 (49%) = 25 工具 schema (cron 12525 最大! message 7798, skill_workshop 2444)
├── messages 历史: ~3500 chars (会话本身极短)
└── 死重(system+tools) = 80325 chars = 总量 81%
```
fresh session msgs=2 仍 88k → **不是会话累积, 是启动时固有肥胖**. system+tools 占 94%, 会话只占 6%.

## heartbeat 累积规律性空僵尸
openclaw main agent `heartbeat.every` 默认 30m, 用同一 session 累积 context 永不 compact → 每 30min 累到 105k → 必然空僵尸 → 飞书可能收到 HEARTBEAT_OK 空回复. 这是设计问题. R842 已改 heartbeat 30m→2h 缓解.

## 系统性方案(治本到治标)
- A: 精简 tools(降~22k 效果最大, 去 cron/skill_workshop 等不常用大工具)
- B: 精简 system(降~8-10k, AGENTS.md/MEMORY.md 删冗余)
- C: openclaw compaction 修复(见 [[r843c-compaction-tools-fix]] 估算漏算 tools 是根因)
- D: heartbeat 独立短 session 或专用精简 agent
- E: R840 兜底(已做, 空僵尸→content_filter→retry, 见 [[r840-openclaw-zombie-empty-stall-fix]])
用户选 C 优先(R843c), 不稳再考虑 D 换 dsv4p.

## 关键阈值(可指导配置)
- 80k chars(≈20k tokens)是 NVCF/GLM-5.2 空僵尸激增阈值
- 40-80k 几乎 0% 空僵尸(4天49请求只1个)
- NVCF 标称 131072 context, 实际 80k+ 就崩 → 后端真实可用远小于标称

关联: [[r841b-openclaw-deep-fix]] [[r840-openclaw-zombie-empty-stall-fix]] [[r843c-compaction-tools-fix]]
