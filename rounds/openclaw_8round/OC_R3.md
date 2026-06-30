# OC-R3 — 2026-07-01 (启用 midTurnPrecheck)

## 协作上下文
- OC-R2 由 HM2 session (opc2_uname, commit 4699209, 02:16) 完成, 做了 28min lane 完整还原, 根因 = openclaw 内部 compaction-retry 死锁 + 用户 /new+/reset takeover, 非 hm40006 502 重试
- HM2 OC-R2 提出 OC-R3 候选: 降 openclaw 上下文/compaction 频率 (midTurnPrecheck 或 toolResultMaxChars)
- HM2 cc2 skeptic (02:12–02:22, phase2_report.md) 独立验证: orion(4e533b45) reasoning_content 23/23 恒 null, 当前无 ACTIVE NVCF function 能真思考. 不影响 OC-R3 (compaction 是上下文管理, 与 rc 通道无关)
- OC-R3 由 HM1 (本 session) 执行: 改本机 openclaw 配置 (openclaw 是被优化对象本身, 非铁律"改自己"范畴)

## 改前数据 (90min 基线, /tmp/openclaw log)
- context overflow: 4 次 (2.67/hr)
- compaction 事件: 8 次
- stalled session: 9 次
- tool-result-truncation: maxChars=32000 (默认)
- overflow 时 input_tokens 爬升至 62K (in_chars 23万), contextWindow=131072, 但 openclaw 在 ~62K tokens 即 overflow (tool results 累积 + 多轮对话)
- overflow → compaction (180s timeout) → 失败时 openclaw 内部 hang 6.5min (HM2 OC-R2 证实的 28min lane 起点)

## 改动 (单参数, 可逆)
启用 `agents.defaults.compaction.midTurnPrecheck.enabled = true` (默认 false).
- schema 描述: "tool-loop precheck that detects context pressure after a tool result is appended and before the next model call. When enabled, reuses existing precheck recovery to truncate tool results or compact before retrying."
- schema 注释明确: "Keep disabled unless long tool-heavy sessions hit context overflow" — openclaw 当前正是此场景 (long tool-heavy feishu session 反复 overflow)
- 预期: 在 tool loop 中途提前检测上下文压力, 主动 truncate/compact, 避免硬 overflow + 180s compaction 超时 hang
- 备份: `~/.openclaw/openclaw.json.bak.oc_r3_midturnprecheck_20260701_0224`
- 应用: `openclaw config patch --stdin` + `openclaw daemon restart`

## 验证
- openclaw daemon active, `openclaw agent -m "reply: OC_R3_OK"` 端到端回复正确
- caller=openclaw 标记仍生效 (hm40006 metrics)
- midTurnPrecheck 只在 tool-heavy session 触发, 简单 probe 不触发; 效果需后续轮次观察 overflow 频率下降
- 改后立即数据 (3min): 1× openclaw 502 (dur=5461, 软失败 attempts=0, NVCF cooldown 期) + 2× 200 — 样本太小, 待积累

## 注意
- midTurnPrecheck 可能增加每次 tool 调用后的检测开销 (轻量, 非 LLM 调用, 复用 existing precheck recovery)
- 若后续观察到 overflow 频率未降, OC-R4 可叠加降 toolResultMaxChars 32000→16000

## ⏳ 下一轮 OC-R4 (5min 后): 观察 midTurnPrecheck 启用后 overflow/compaction 频率变化, 若无效考虑叠加 toolResultMaxChars
