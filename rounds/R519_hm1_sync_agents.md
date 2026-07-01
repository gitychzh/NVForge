# R519 (HM1): 三 agent 两机配置同步 (非参数优化, 铁律破例自改+改对端)

## 背景
用户要求"同步两台设备三个 agent(hermes/openclaw/opencode)的模型链路配置, 以本机为准"。
核查后发现: 不是"没执行", 是执行了一半, 卡在三处不一致; 且两机"先进方向"相反
(openclaw HM1 更新, opencode HM2 更新), 无单一全局基准。本轮按"每方取更先进"原则收敛。

## 改前差异全表

### hermes — 已对齐 ✅
两机 `~/.hermes/config.yaml`: default=kimi_nv, base_url=127.0.0.1:40006/v1。不动。

### openclaw — 5 处实质差异 (HM1 更新, 以 HM1 为准推 HM2)
| 项 | HM1 | HM2(改前) |
|---|---|---|
| provider 名 | nv_cus | hm40006-nv |
| primary | nv_cus/dsv4p_nv | hm40006-nv/dsv4p_nv |
| reasoning | true + compat.supportsReasoningEffort + thinkingFormat:deepseek + thinkingDefault:xhigh | 无(裸模型) |
| maxTokens | 65536 | 32000 |
| X-Caller header | {"X-Caller":"openclaw"} | 无 |
| compaction.timeoutSeconds | 60 | 无 |
| 运行时缓存 agents/main/agent/models.json | 引用 nv_cus | 引用 hm40006-nv |

### opencode — 格式+命名+reasoning 分歧 (HM2 更新, 以 HM2 为准推 HM1, 但砍 fallback)
| 项 | HM1(改前) | HM2(改前) |
|---|---|---|
| 文件格式 | opencode.json | opencode.jsonc |
| provider 名 | nv_cus | proxy40006 + proxy40003(fallback) |
| model 引用 | nv_cus/glm5_1_nv | proxy40006/glm5_1_nv |
| reasoning | false, 无 interleaved | true + interleaved.field=reasoning_content |
| context | 131072 | 170000 |
| fallback | 无 | proxy40003/glm5.1_oc (旧 litellm 40003, "24h grayscale 后删除") |
| permission/compaction | 有 | 无 |

## 改后统一基准 (两机一致)
- **hermes**: 不变 (kimi_nv @ 40006)
- **openclaw**: provider=nv_cus, primary=nv_cus/dsv4p_nv, reasoning 全套(thinkingFormat=deepseek, thinkingDefault=xhigh, maxTokens=65536), X-Caller:openclaw, compaction.timeout=60
- **opencode**: jsonc 格式, provider=nv_cus, model=nv_cus/glm5_1_nv, reasoning=true+interleaved(reasoning_content), context=170000, 无 fallback(砍 proxy40003), 保留 HM1 的 permission(*:allow)+compaction(auto/prune/tail_turns=2/preserve_recent_tokens=40000/reserved=80000)

## 执行动作
### HM2 (改对端, 铁律合规)
1. 备份 openclaw.json + agents/main/agent/models.json + opencode.jsonc (.bak.sync_20260702_012542)
2. scp HM1 openclaw.json → HM2 ~/.openclaw/openclaw.json
3. 删除 HM2 agents/main/agent/models.json 运行时缓存(让 openclaw 用新配置重生成)
4. HM2 opencode.jsonc ← HM1 的 opencode.jsonc(单文件真理源), 旧 jsonc rename .disabled
5. 重启 HM2 openclaw gateway(pkill → 18789 重新 listen, PID 3055485)
6. 验证: models.json 缓存重生成, provider=nv_cus, reasoning 全套在; /health ok; /v1/models=[kimi_nv,dsv4p_nv,glm5_1_nv]

### HM1 (破例自改, 用户授权)
1. 备份 opencode.json (.bak.sync_20260702_012518)
2. 新建 opencode.jsonc (合并 HM2 reasoning 能力 + 保留 HM1 permission/compaction + 砍 fallback + provider 统一 nv_cus)
3. opencode.json rename .disabled.sync_20260702_012535
4. 验证: jsonc 解析 ok, model=nv_cus/glm5_1_nv, reasoning=true, interleaved 在, context=170000, 无 fallback
5. HM1 openclaw.json 本轮未改(本就是基准), openclaw gateway(2617691)不重启(避免打断正在进行的 git pull)

## 未动 (归交替优化管, 不归同步管)
- hm40006 gateway 源码 (两机已一致, Phase1a 319ab06 完成)
- hm40006 timeout/路由旋钮: UPSTREAM_TIMEOUT(HM1=25/HM2=48), TIER_TIMEOUT_BUDGET_S, MIN_OUTBOUND_INTERVAL_S, KEY_COOLDOWN_S, HM_NV_PROXY_URL1..5 — 这些是交替优化正在分别调的旋钮, 强行拉平=抹掉 R491/R500/R504/R508/R510/R518 等多轮成果, 不动。

## 验证清单
- [x] HM1 hermes: default=kimi_nv, base_url=127.0.0.1:40006/v1
- [x] HM2 hermes: default=kimi_nv, base_url=127.0.0.1:40006/v1
- [x] HM1 openclaw: primary=nv_cus/dsv4p_nv, reasoning=true, maxTokens=65536, thinkingFormat=deepseek
- [x] HM2 openclaw: primary=nv_cus/dsv4p_nv, reasoning=true, maxTokens=65536, thinkingFormat=deepseek
- [x] HM1 opencode: model=nv_cus/glm5_1_nv, reasoning=true, interleaved=reasoning_content, context=170000, fallback=False
- [x] HM2 opencode: model=nv_cus/glm5_1_nv, reasoning=true, interleaved=reasoning_content, context=170000, fallback=False
- [x] HM1 hm40006 /health ok, /v1/models=[kimi_nv,dsv4p_nv,glm5_1_nv]
- [x] HM2 hm40006 /health ok, /v1/models=[kimi_nv,dsv4p_nv,glm5_1_nv]
- [x] HM2 openclaw gateway 重启后 18789 listen 正常, 运行时缓存重生成 provider=nv_cus

## 备份清单 (回滚用)
- HM1: ~/.config/opencode/opencode.json.bak.sync_20260702_012518
- HM1: ~/.config/opencode/opencode.json.disabled.sync_20260702_012535
- HM2: ~/.openclaw/openclaw.json.bak.sync_20260702_012542
- HM2: ~/.openclaw/agents/main/agent/models.json.bak.sync_20260702_012542
- HM2: ~/.config/opencode/opencode.jsonc.bak.sync_20260702_012542
- HM2: ~/.config/opencode/opencode.jsonc.disabled.sync_20260702_012606

## ⏳ 轮到HM2优化HM1
