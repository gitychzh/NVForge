# SPEC-001: 双机模型链路审计与补全

## 背景
Boss 张要求建立"专家评审委员会"工作模式：4个模型（GLM 5.2, DS V4 Pro, Kimi K2.6, MiniMax M3）通过 API 组成专家委员会，评审方案后交由 Claude Code 执行。

本次为首次试运行：CC 负责探测远程主机(opc2)模型链路，收集配置数据，供4个模型评审。

## 任务

### 1. 探测 HM1（本机 opcsname）模型链路

收集以下数据并写入 `deploy_artifacts/R1003/hm1_audit.json`：

```json
{
  "hostname": "opcsname",
  "timestamp": "<UTC>",
  "containers": [
    {"name": "<name>", "status": "<status>", "ports": "<ports>", "image": "<image>"}
  ],
  "nv_gw": {
    "health": "<从 /health 端点获取完整 JSON>",
    "config_models": ["从 config.py NVCF_PEXEC_MODELS 提取：model_id, function_ids, strip_params, inject"],
    "env_vars": "关键环境变量：UPSTREAM_TIMEOUT, TIER_TIMEOUT_BUDGET_S, NVU_TIER_BUDGET_*, NVU_FORCE_STREAM_*, NVU_EMPTY_200_FASTBREAK, KEY_COOLDOWN_S, TIER_COOLDOWN_S, NVU_PEER_FB_SKIP_MODELS"
  },
  "ms_gw": {
    "health": "<从 /health 端点获取完整 JSON>",
    "env_vars": "关键环境变量：MS_BASEURL, PROXY_TIMEOUT, UPSTREAM_TIMEOUT, MIN_OUTBOUND_INTERVAL_S"
  },
  "openclaw_config": {
    "providers": ["provider_name, baseUrl, models[id, contextWindow, maxTokens, reasoning, supportsReasoningEffort]"],
    "primary_model": "<value>",
    "fallbacks": ["<values>"],
    "acp": {"enabled": true, "allowedAgents": [], "defaultAgent": ""}
  },
  "hermes_config": {
    "default_model": "<value>",
    "provider": "<value>",
    "models": ["model_id, max_tokens, supports_thinking, supports_vision"],
    "fallback_providers": ["<values>"]
  },
  "opencode_config": {
    "default_model": "<value>",
    "models": ["model_id, context, output, reasoning, tool_call"]
  },
  "codex_config": {
    "model": "<value>",
    "base_url": "<value>",
    "port_listening": true/false
  }
}
```

### 2. 探测 HM2（远程 opc2sname）模型链路

通过 `ssh -p 222 opc2_uname@100.109.57.26` 收集同样结构数据，写入 `deploy_artifacts/R1003/hm2_audit.json`。

注意 HM2 的 nv_gw 只注册了 3 个模型（无 minimax_m3_nv），agent 容器架构不同（opclaw4103/hm4104/oc4105/cx4102 分离容器）。

### 3. 双机差异对比

生成 `deploy_artifacts/R1003/diff_matrix.md`，包含：
- 模型注册差异（哪些模型在哪台机有/没有）
- 配置差异（timeout, budget, cooldown 等参数不同值）
- Agent 架构差异（容器化方式不同）
- 可用性问题（哪些模型测试失败及原因）

### 4. 4模型可用性测试（双机各4模型）

对每台机的 nv_gw 4 个模型执行简单测试：
```bash
curl -s -m 60 http://127.0.0.1:40006/v1/chat/completions \
  -H 'Authorization: Bearer nv-gw-token' \
  -H 'Content-Type: application/json' \
  -d '{"model":"<model>","messages":[{"role":"user","content":"respond with exactly: OK"}],"max_tokens":200,"stream":false}'
```

记录：content是否为"OK"、finish_reason、response_time_ms、有无错误。

⚠️ Kimi K2.6 和 GLM 5.2 有 thinking/reasoning，max_tokens 必须 >= 200 否则 reasoning 占满后 content 为 null。

### 5. 输出

所有文件写入 `deploy_artifacts/R1003/` 目录：
- `hm1_audit.json` — 本机完整审计
- `hm2_audit.json` — 远程完整审计
- `diff_matrix.md` — 双机差异矩阵
- `model_test_results.json` — 8次测试结果（2机×4模型）

完成后 git add + commit，message 格式：`R1003: HM1 audit — dual-machine model link audit for expert panel bootstrap`

### 约束

- 只读取和收集数据，不修改任何配置
- 远程操作通过 SSH，不改动 opc2 任何文件
- 遵循 NVForge 铁律：数据先行
- 不要重启任何容器或服务
