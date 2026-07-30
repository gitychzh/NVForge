# R-agent-model-split: HM2 agent 模型配置对齐

**日期**: 2026-07-30  
**主机**: HM2 (100.109.57.26)  
**触发**: 用户要求 openclaw 用 dsv4p_nv, hermes 用 glm5_2_nv, cc 用 glm5_2_nv

## 变更摘要

目标: openclaw 从 kimi_nv → dsv4p_nv, hermes 从 kimi_nv → glm5_2_nv, cc 保持 glm5_2_nv.

执行中 dsv4p_nv NVCF 后端挂掉 (all_tiers_exhausted, 5key 全 502), 用户决策: openclaw 也改用 glm5_2_nv.

### 最终配置 (全 glm5_2_nv)

| Adapter | Container | PRIMARY_MODEL | Agent Config | Status |
|---------|-----------|---------------|--------------|--------|
| cc4101 | cc4101 | glm5_2_nv | ~/.claude/settings.json (cc-glm5-2) | ✅ |
| opclaw4103 | opclaw4103 | glm5_2_nv | ~/.openclaw/openclaw.json (opclaw4103/glm5_2_nv) | ✅ |
| hm4104 | hm4104 | glm5_2_nv | ~/.hermes/config.yaml (glm5_2_nv) | ✅ |

### 修改的文件

1. **`/opt/cc-infra/docker-compose.yml`** (line 306):
   - opclaw4103 `PRIMARY_MODEL`: kimi_nv → dsv4p_nv → glm5_2_nv (dsv4p_nv NVCF down, fallback to glm5_2_nv)
   - 备份: `docker-compose.yml.bak.Ragent_model_split`

2. **`~/.hermes/config.yaml`**:
   - `model.default`: kimi_nv → glm5_2_nv
   - `model.default_model`: kimi_nv → glm5_2_nv
   - `providers.hm4104.default_model`: kimi_nv → glm5_2_nv
   - `providers.hm4104.name`: 更新描述
   - 备份: `config.yaml.bak.Ragent_model_split`

3. **`~/.openclaw/openclaw.json`**:
   - `model.primary`: opclaw4103/kimi_nv → opclaw4103/dsv4p_nv → opclaw4103/glm5_2_nv
   - `compaction.model`: 同步
   - 备份: `openclaw.json.bak.Ragent_model_split`

### dsv4p_nv 不可用诊断

dsv4p_nv 在 NVCF 后端挂掉: 5 key 全部 `all_tiers_exhausted` (502), 不是 key/IP 问题, 是 NVCF function 级故障. kimi_nv/dsv4p_nv 的 NVCF function 与 glm5_2_nv 不同, glm5_2_nv 仍可用 (间歇性 zombie 但有成功).

## 端到端验证

重启三个 adapter (清除 circuit breaker 状态), 小请求测试:

| Adapter | HTTP | Model | Time | Response |
|---------|------|-------|------|----------|
| cc4101 | 200 | glm5_2_nv | 106.8s | CC_GLM52_OK |
| opclaw4103 | 200 | z-ai/glm-5.2 | 38.8s | OPENCLAW_GLM52_OK |
| hm4104 | 200 | z-ai/glm-5.2 | 48.0s | HERMES_GLM52_OK |

**注意**: hermes CLI 端到端 (带 27 tools ~73K chars input) 仍间歇性 502 (zombie_empty_completion / all_tiers_exhausted), 这是 NVCF 后端对大请求性能降级, 非配置问题. 配置链路已通过 adapter 层 E2E 验证.

## 回滚

- compose: `cp /opt/cc-infra/docker-compose.yml.bak.Ragent_model_split /opt/cc-infra/docker-compose.yml && cd /opt/cc-infra && docker compose up -d opclaw4103`
- hermes: `cp ~/.hermes/config.yaml.bak.Ragent_model_split ~/.hermes/config.yaml`
- openclaw: `cp ~/.openclaw/openclaw.json.bak.Ragent_model_split ~/.openclaw/openclaw.json`
