# R2192 (hm2_cc2_infra): cc2 请求体抓包发现 + 撤 40007 技术路径 + 三任务注入

**日期**: 2026-07-21
**主机**: HM2 only
**角色**: CC 基础设施侧 — 抓包定性 + 为 cc2 铺设撤 40007 的三任务

## 一句话

临时给 cc4101 加 body dump probe 抓了 6 个真实 cc2 请求体 (148-159K chars, ~45K tokens),
发现: (1) CC 正确标记了 `cache_control: ephemeral` 但 cc4101 转换层完全丢弃 → cc2 缓存命中率 0%
(344 响应全 0); (2) CC 注入了 3 个非标准字段 `context_management`/`output_config`/`thinking:adaptive`
可能干扰 NVCF; (3) zombie 全在 <150K 段但大请求样本仅 40 条 (24h, <1%), 不足以判定大请求不 zombie.
基于此给 cc2 三任务, 全部指向撤 40007 让系统稳.

## 抓包发现 (R2192 probe, cc4101 handlers.py 临时加 CC4101_BODY_DUMP, 已移除)

probe 代码 (R2192 已从 handlers.py 移除, 备份 handlers.py.bak.R2192_probe_20260721_214500):
```python
# 临时: raw_body = self.rfile.read(length) 之后 dump >=5K 的 body 到容器 /tmp/cc4101_body_dump/
```

### 发现 1: cache_control 被丢 (缓存命中率 0 根因)

CC SDK **正确标记** `cache_control: {type: "ephemeral"}`:
- system[1] (len=62): `cache_control={'type':'ephemeral'}`
- system[2] (len=5762): `cache_control={'type':'ephemeral'}`
- + 1 处 message block, 共 3 处 ephemeral

但 **cc4101 转换层完全不处理 cache_control** (grep 零命中), anthropic→openai 转换时直接扔掉.
nv_gw 也只在输出 usage 里硬编码 `"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0`
(从不向上游 NVCF 请求 cache, 也从不报告命中).

**实证**: 扫描 cc2 15 个 session / 344 个 assistant 响应, cache_read_input_tokens 全 0,
cache_creation_input_tokens 全 0. 缓存命中率 0%.

cc2 prompt 结构高度重复 (CLAUDE.md + STATE.md + system 每轮基本一样), 本应命中 NVCF context
caching 省钱省时. 全 0 = 纯浪费.

### 发现 2: CC 注入 3 个非标准字段 (可能干扰 NVCF)

| 字段 | 内容 | 标准? | 风险 |
|---|---|---|---|
| `context_management` | `{"edits":[{"type":"clear_thinking_20251015","keep":"all"}]}` | ❌非标 | CC SDK 2.1.216 新增语义, glm5.2/NVCF 不认识, 可能触发异常路径 |
| `output_config` | `{"effort":"high"}` | ❌非标 | effort 控制 glm5.2 不认 |
| `thinking` | `{"type":"adaptive","display":"omitted"}` | ⚠️半标 | adaptive 是 anthropic 新格式, glm5.2 可能只认 enabled/disabled; display:omitted 更可疑 |

### 发现 3: system[0] 是 billing header (CC 怪癖)

`system[0].text` 开头 `x-anthropic-billing-header: cc_version=2.1.216.450; cc_entrypoint=sdk-cli;`
(len=74, 无 cache_control). 本该是 HTTP header, CC 塞进了 system prompt 第 0 块.

## zombie 根因四推测 (用户 + CC 共同形成)

DB 24h: zombie 49 个, 全在 <150K 段 (avg 59577 chars). 大输入段 (250-350K) 40 条 0 zombie.
但 40 条样本 <1%, 统计显著性不足.

- **A (CC 干扰)**: CC 小请求注入 `context_management.clear_thinking_20251015` 等非标字段,
  NVCF 不认识 → 走异常路径 → 空响应 zombie. 大请求可能字段组合不同所以不 zombie. **需抓 zombie 时 body 验证**.
- **B (输入大小本身)**: NVCF 对小输入更易触发空响应 (safety/content_filter). 但 DB 显示 zombie
  是 empty_completion 非 content_filter, 弱.
- **C (缓存未命中)**: 小请求没命中缓存 → NVCF 每次重处理 → 偶发 zombie. 解释弱 (大请求也没命中).
- **D (样本不足)**: 大请求 40 条 <1%, 不足以判定大请求不 zombie. "大输入 zombie 归零"可能是假象.
  **采纳 D, 保守评估, 不因"大请求看着没 zombie"就放松**.

## 撤 40007 能否稳住评估 (基于 D 保守)

**结论: 技术路径成立, 但需先做三任务才敢撤.**

当前靠 cc4101 层 ms_gw fallback 兜 zombie. 撤 40007 = zombie 发生时不能靠 cc4101 重放,
必须 nv_gw 自身解决. 核心约束 (源码核证):
- converter `oai_to_anth.py:feed_chunk` 有 `if not self.message_start_sent` 守卫 →
  第二个流喂进来**不会再发 message_start**, 只续 content delta → **路径 B zombie 内部重试技术上可行**
- 但路径 B zombie 重试有"内容重复/跳跃"风险 (DB: 49 zombie avg output_tokens=43.7, 33/49 有 >5 tokens
  输出, 已 flush 给 cc2) → 用户接受重复 (cc2 是自优化 agent, 输出是工具调用/分析, 前缀重复不致命)

## 三任务给 cc2 (本轮注入, 让 cc2 执行)

### 任务 1: 修 cc4101 透传 cache_control (纯增益, 最高优先)

改 `/opt/cc-infra/proxy/cc4101/gateway/` 转换链: anthropic body 里的 `cache_control` 字段透传给
nv_gw/ms_gw 的 openai body (openai 无原生 cache_control, 但 NVCF 支持类似机制, 需查 NVCF
context caching 文档对应字段). 或至少在 nv_gw 侧把 cache_creation/read_input_tokens 从硬编码 0 改成
读上游真实值.

预期: cc2 缓存命中率从 0% 上升, 省钱省时, ttfb 降.

### 任务 2: 抓 zombie 请求 body 对比字段 (验证推测 A vs D)

在 **nv_gw 侧** (非 cc4101) 加 probe: 检测到 zombie (`zombie_empty_completion`) 时, 回溯 dump
该请求的 oai_body 到文件. 积累 N 个 zombie body 后, 对比成功请求 body 的字段差异
(`context_management`/`output_config`/`thinking` 有无/值差异).

判定: 若 zombie body 普遍含某非标字段而成功 body 不含 → 证实 A, 该字段是元凶, 修法=cc4101 转换时
剥离该字段; 若字段无差异 → 倾向 D (样本不足/纯随机), 撤 40007 靠路径 B 重试兜.

### 任务 3: nv_gw 路径 B zombie 内部重试 (撤 40007 核心前置)

改 `handlers.py` 主循环 zombie 检测点 (no_content_gap/stream_first_byte_timeout, message_start
已发): 替代当前 graceful end, 改为 — 关当前 NVCF conn → 对 NVCF 重发原 oai_body (同 key 或下 key,
用户观察证明同 key 下次就成功) → 拿新流续 feed 同一 converter (message_start_sent 守卫保证不双
message_start) → flush 给 cc4101. 重试上限 1-2 次, 全失败才 graceful end.

不处理内容重复 (用户决策, cc2 是自优化 agent 容忍前缀重复).

## 铁律合规

- ✅ 改前有数据: 抓包 6 body + DB 49 zombie + cache 0% 实证
- ✅ 改后有验证: probe 已移除, cc4101 restart, 验证 grep=0
- ✅ 聚焦 nv_gw 链: cc4101+nv_gw+cc2 settings
- ✅ 只改 HM2 不改 HM1
- ✅ 写入仓库: 本轮文件 + 注入 cc2 CLAUDE.md
- ⚠️ probe 临时改了 cc4101 handlers.py (已恢复, 但备份 .bak.R2192_probe 本身含 probe, 勿信)

## 未尽事项

- 三任务由 cc2 执行, CC 核查 (用户决策)
- 撤 40007 前需三任务完成 + 6h 压测 (临时关 cc4101 ms fallback 看 cc2 靠 nv_gw 重试是否稳)
- R2191 全局 settings 污染已回滚 (cc2 反复改全局循环已解, 注入重写禁碰全局)
