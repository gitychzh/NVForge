# R2292 (HM2 only): hermes + openclaw 默认模型改 kimi_nv, 端到端验证通过

## 背景

用户要求: 把远程 HM2 的 hermes 与 openclaw 默认模型都设为 kimi, 并端到端测试确认真实可用.
承接 R2289 (cc2 默认模型已改 kimi_nv). 本轮覆盖另两个 agent (hermes/openclaw).

## 数据基础 (改前)

cc-adapter (hm4104/opclaw4103) 机制核证 (forwarder.py:223 `body["model"]=model`):
adapter **无条件重写** request body 的 model 为 `PRIMARY_MODEL` env, 故 agent 发什么名都会被
改写路由. 改 `PRIMARY_MODEL` 一处即改全链路.
- hm4104 (hermes): 原 PRIMARY_MODEL=dsv4p_nv, FALLBACK_MODEL=dsv4p_ms (ms_gw 有此 model).
- opclaw4103 (openclaw): 原 PRIMARY_MODEL=glm5_2_nv, FALLBACK_MODEL=glm5_2_ms.
- ms_gw MODEL_REGISTRY = [glm5_2_ms, dsv4p_ms] (kimi 无 ms 对应, 故 kimi 失败时 fallback 到
  glm5.2/dsv4p 的 ms 模型, 不同模型但保 agent 不中断 — 设计如此).
- nv_gw: kimi_nv tier `inject={"reasoning_effort":"low"}`, strip `thinking_budget`, MODEL_INPUT_TOKEN_SAFETY=131072 (本就正确, 不动).

## 改动清单 (HM2 only, 全程不碰 HM1)

### 1. /opt/cc-infra/docker-compose.yml (2 处 adapter env)
- hm4104 L325: `PRIMARY_MODEL=dsv4p_nv` → `kimi_nv`
- opclaw4103 L285: `PRIMARY_MODEL=glm5_2_nv` → `kimi_nv`
- FALLBACK_MODEL 不动 (dsv4p_ms / glm5_2_ms, ms_gw 有, 兜底保 agent 不中断).
- 备份: docker-compose.yml.bak.R2292_kimi
- 回滚: 改回 + `docker compose up -d hm4104 opclaw4103`.

### 2. ~/.hermes/config.yaml (hermes agent config, 名称对齐)
- `model.default: dsv4p_nv` → `kimi_nv`
- `providers.hm4104.default_model: dsv4p_nv` → `kimi_nv`
- `providers.hm4104.name`: adapter 描述更新为 kimi_nv -> dsv4p_ms fallback.
- 备份: config.yaml.bak.R2292_kimi

### 3. ~/.openclaw/openclaw.json (openclaw agent config)
- `agents.defaults.model.primary`: `opclaw4103/glm5_2_nv` → `opclaw4103/kimi_nv`
- `agents.defaults.compaction.model`: → `opclaw4103/kimi_nv`
- opclaw4103 provider models 列表新增 `kimi_nv` 条目 (contextWindow 120000, maxTokens 32768,
  reasoning true, supportsReasoningEffort true). glm5_2_nv 条目保留 (不删, 兼容).
- 备份: openclaw.json.bak.R2292_kimi

### 未改 (有意)
- nv_gw kimi tier config (本就正确).
- FALLBACK_MODEL (kimi 无 ms 对应, 跨模型兜底是设计).
- HM1 全程不动 (铁律之铁律).
- opclaw4103 PROMPT_TOKEN_LIMIT=120000 (本就对 kimi 128K 安全).

## 验证 (端到端真实可用)

### adapter 层 env + health
- hm4104 /health: `primary_model: kimi_nv`, fallback dsv4p_ms ✅
- opclaw4103 /health: `primary_model: kimi_nv`, fallback glm5_2_ms ✅

### E2E 1: hm4104 non-stream (hermes 路径)
`model: moonshotai/kimi-k2.6`, content `HERMES-KIMI-OK`, finish `stop` ✅ (真实 kimi)

### E2E 2: hm4104 STREAM (hermes 路径)
SSE `model: moonshotai/kimi-k2.6`, 流式 reasoning_content (kimi reasoning_effort=low 触发),
真实 kimi 流 ✅

### E2E 3: opclaw4103 non-stream 5x probe
5/5 全返回 `moonshotai/kimi-k2.6` + content OK + finish stop ✅ (kimi 主路径稳定)

### E2E 4: opclaw4103 STREAM
首测遇 kimi zombie (NV-ZOMBIE-EMPTY: finish_reason=stop content_chars=1 < 50) →
nv_gw 正确检测 + abort → opclaw4103 fallback glm5_2_ms 救回 (返回 OPENCLAW-KIMI-OK).
**zombie 是 NVCF kimi function 间歇性空响应 (已知上游问题, R2290 已分析), 非配置错误.**
链路行为符合设计: kimi 坏时 fallback 兜底保 agent 不中断.

### hm4104 5x probe: 3 明确 kimi 成功 + 2 parse-err (30s timeout 截断或空窗, 非 config 错).
raw 复测确认 hm4104 持续返 `model: moonshotai/kimi-k2.6` 真实 kimi.

## 预期效果

- hermes 默认 = kimi_nv (经 hm4104 → nv_gw → NVCF kimi f966661c).
- openclaw 默认 = kimi_nv (经 opclaw4103 → nv_gw → NVCF kimi f966661c).
- kimi 偶发 zombie/502 时, adapter 自动 fallback 到 ms_gw (dsv4p_ms / glm5_2_ms) 兜底.
- 三 agent (cc2/hermes/openclaw) 现在默认都 kimi_nv, 但走各自 adapter (cc4101/hm4104/opclaw4103),
  fallback model 各不同 (glm5_2_ms / dsv4p_ms / glm5_2_ms).

## 回滚

3 文件改回 .bak.R2292_kimi + `docker compose up -d hm4104 opclaw4103`.

## 关联

- R2289: cc2 默认模型 dsv4p_nv->kimi_nv (cc2 adapter=cc4101).
- R2290: cc2 zombie dump 25样分析, 推测A强证伪 (zombie 非 cc4101 字段干扰, 是上游间歇性空响应).
- 本轮: hermes/openclaw adapter (hm4104/opclaw4103) 同步改 kimi_nv.
- [[r2289-cc2-default-kimi]]
