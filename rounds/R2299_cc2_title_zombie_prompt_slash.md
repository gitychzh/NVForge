# R2299 (HM2 only): cc2 自优化 title-zombie 根治 — 瘦身 prompt + STATE 不预贴入

> 承接 R2192 task3 数据证伪后的方向重定。用户洞察：title zombie 是自优化项目 prompt 形态诱发，非纯 NVCF 病。走层次 A（改 prompt 从源头消灭），非路由分流/识别短路。

## 改前数据（36h, HM2 nv_requests + nv_gw zombie_dumps）

### zombie 按请求特征拆分
- nv_gw R2192-t2 zombie body dump probe 抓 29 个样本：
  - **21/29 (72%) 是 title 生成请求**：system 含 `Generate a concise...title`，msgs=2，tools=0，max_tokens=8192
  - 21 条 title zombie **全部** 带 `cc_entrypoint=sdk-cli` + `cc_version=2.1.217.*` → **100% 来自 Claude Code SDK（cc2 自身）**，hermes/openclaw 不发此类请求
  - 21 条 user 消息内容：14 条 = openclaw2 自优化交接棒 STATE.md；7 条 = cc2 自优化任务框架 — **零条来自正常任务**
- 按输入分桶 zombie 率（36h）：glm5_2_nv `<30k` **8.4%** (39/470)，`30-80k` 0.4%，`80-150k` 0.4% → title 区（9-15k）是 zombie 重灾区

### 根因链
1. cc2 resume 脚本把 **PROMPT heredoc（~4k 任务框架）+ STATE.md 全文（12.8k）** 拼成一条 user 消息 → `claude -p "$FULL_PROMPT"`
2. cc SDK 拿首条 user 消息后自动触发 title 生成请求，把整条 user 消息当"会话样本"喂标题模型
3. title 请求输入 ≈ 14k → 落入 NVCF 对"长结构化输入 + 极短期望输出（3-7 词）"系统性吐极少 content 就 `finish_reason=stop` 的区间 → zombie
4. 同一 title 请求裸测 ms_gw（glm5_2_ms）30s 正常返回 `"nv_gw self-optimization round R2300"`，finish_reason=stop，内容正常 → **NVCF 后端对该输入形态有缺陷（50% 责任），自优化 prompt 膨胀是诱发因素（50% 责任）**

### 频率
glm5_2_nv <16k 请求 8-12 次/小时，zombie 0-5 次/小时 → 分流/根治后 ms_gw 不会过载（但本方案是源头消灭不经 ms_gw）

## 改动（HM2 only, 单文件, 不碰 nv_gw/cc4101/ms_gw 源码）

`~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh`（备份 `.bak.R2301`）：

**改法 1（STATE 不预贴入）**：删掉
```bash
STATE_CONTENT=$(cat "$STATE" ...)
FULL_PROMPT="$PROMPT$NO_OUTPUT_WARN\n---\n## 当前交接棒 STATE.md 内容:\n$STATE_CONTENT"
```
改为 `FULL_PROMPT="$PROMPT$NO_OUTPUT_WARN"`，STATE.md 改由 cc2 步骤 1 自己 `cat`（已写进新 PROMPT）。

**改法 2（PROMPT heredoc 瘦身）**：旧 heredoc ~4k（含重复的铁律段/详细步骤展开，与 CLAUDE.md L21/L93/L63 重复）→ 新 heredoc **1396 字节**骨架，7 步工作流 + 指向 CLAUDE.md/STATE.md 的引用。

**效果**：cc2 首条 user 消息 ~14k → ~1.4k（降 90%），title 生成请求的输入随之降到 <2k，远低于 NVCF zombie 触发区间。

## 预期
- title 请求 input_chars 从 ~14k 降到 <2k
- title zombie 归零（改前 21/29 zombie dump 均为此类）
- cc2 本身仍能正常跑完一轮（prompt 改为让 cc2 主动 cat STATE/CLAUDE.md，行为风险点：需观察 cc2 是否执行 cat 接上任务）

## 验证清单（shadow 2-6h）
- [ ] `docker exec nv_gw ls -lt /app/logs/zombie_dumps/ | head` — 新 dump 是否停止增长（尤其 title 类）
- [ ] `psql ... SELECT total_input_chars ... WHERE total_input_chars<30000 AND error_type LIKE '%zombie%'` — 小输入 zombie 是否归零
- [ ] cc2 本轮正常跑完（`tail ~/cc_ps/cc2_repair_self/.claude/cc2.log`）且 STATE.md 被正常覆写
- [ ] 无新增 zombie dump（非 title 类不受影响）

## 回滚
`cp ~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh.bak.R2301 ~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh`

## 关联
- 铁律遵守：改前有数据（36h + 29 dump 样本），聚焦 40006 间接（减其 zombie 输入），只改 HM2，写入仓库。不碰 nv_gw/cc4101/ms_gw 源码，不碰 agent 模型选择。
- 待 openclaw2 同步（14/21 title zombie 来自 openclaw2，同款 STATE 预贴入问题），待 cc2 验证有效后再改。
