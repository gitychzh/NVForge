# OC-R6 — 2026-07-01 (零改动轮 + overflow触发机制勘定, cc2选Q)

## 协作上下文
- OC-R5 (commit 8601597): cc2选N零改动 + OC-R4勘定纠误.
- OC-R6 由 HM1 (本 session) 执行. cc2反对者 (bb7mkpl6b session) 审视.

## cc2批判 (bb7mkpl6b) — 机制层面, 关键
1. **P/R 是类别错误 (category error), 非数据不足**:
   - OC-R5 已勘定: overflow 触发源 = NVCF `assistantError` 回推 (服务端错误), 非客户端计 token.
   - P (降 toolResultMaxChars) / R (升 contextTokens) 都是**客户端侧**截断/配额参数, 不在 overflow 触发链路上. 给满样本也不会生效, 因为动错对象.
2. **P 的"数据支撑"是假的**:
   - 最近60min 0 overflow = 事件缺席, 非"P能预防overflow"的证据.
   - 今天2次 tool-result-truncation 都在 overflow recovery 期间触发 → truncation 是 overflow 的**症状/伴随**, 不是因. 降 maxChars=16000 只让截断更频繁, 不阻止 overflow. 逻辑反了.
   - HM1独立佐证: log显示 `oversized=0` (50条被截断的tool result里0条超32000) → 截断是 aggregateBudget 主动修剪, 非单条超限. 降 toolResultMaxChars 收紧的是 aggregate budget, 不是单条大小.
3. **R 比 P 更差**: 升 contextTokens→160000 同样不在触发链路, 还多一层"真撞NVCF硬限"风险. P至少无效, R无效+有害.
4. **拒绝 L (降xhigh→medium)**: max桶n=11(现18)统计薄; 且OC-R4证medium→body high不产reasoning_content, 降xhigh=丢全部reasoning, 高成本决策11样本撑不起.
5. **选Q (NOP+继续累计)**: "8轮过5轮没动参数总得动一次"是沉没成本+锚定压力, 违反铁律(无数据就NOP). R1-R5没动参数是因为每轮都没拿到支撑数据, 不是偷懒. 坚持到底才是纪律.

## overflow 触发机制勘定 (本轮HM1深化)
- **触发源**: openclaw log `[context-overflow-diag] source=assistantError` — NVCF返回错误暗示上下文过大, openclaw回推触发overflow处理.
- **触发链**: NVCF assistantError → openclaw overflow detected → auto-compaction (60s timeout) → 成功则retry, 失败则 tool-result-truncation fallback → 仍失败则 hang.
- **客户端参数不在主触发链**: toolResultMaxChars/contextTokens 只影响 compaction/truncation 的处理行为, 不影响 NVCF 是否返 assistantError. → cc2 "类别错误" 成立.
- **唯一能从客户端侧减 overflow 频率的**: 降上下文体积 (减 messages 数或单条体积), 但 max input_tokens 才 64K << 131072, 体积压力不在线性区. 真正的 overflow 是 NVCF 侧硬限 (可能远低于 131072), 客户端无法预知.

## K 累计快照 (本轮, 累计至 07:55)
| effort | n | ok | 502 | p50 dur |
|---|---|---|---|---|
| max (=xhigh) | 18 | 18 (100%) | 0 | 7642ms |
| high | 2 | 2 (100%) | 0 | 3975ms |
| `<None/legacy>` | 943 | 785 (83.2%) | 158 | 8460ms |

- max桶 18/18 = 100%, 跨 NVCF 故障-恢复周期 (02:00段78.5% → 02:40段93.3% → 07:55 max桶100%).
- 样本继续累计中. 接受跨轮累计, 不主动发探针 (探针不真实).

## 本轮改动
**无参数改动.** 仅 overflow 触发机制勘定 + K累计. 符合 cc2 选Q 与铁律"改前必有数据".

## 结论
- cc2 选Q正确: P/R是类别错误(客户端参数不在服务端触发链), L数据薄+高成本, R无效+有害.
- overflow 触发机制勘定: NVCF assistantError 回推, 客户端 toolResultMaxChars/contextTokens 不在主触发链. → OC-R4/R5 讨论的 M/P/R 候选从机制层全部排除.
- max桶 18/18=100% 持续, 但样本仍不足以做L决策 (降xhigh=丢reasoning, 高成本).
- 下轮 OC-R7: 继续K累计; 若 max≥25 且跨≥2 NVCF 周期仍 100%, 可考虑 L 的预演(标不切); 否则继续NOP. 接受 R6-R8 全NOP 为合法收尾.

## ⏳ 轮到HM2反对者审视OC-R7 (L预演或继续NOP)
