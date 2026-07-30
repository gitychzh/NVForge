# R-dsv4p-deploy: dsv4p_nv 部署为 HM2 hermes+openclaw 主力模型

**Date**: 2026-07-30  
**Host**: HM2 (100.109.57.26)  
**Scope**: 3 adapter env + 2 agent config

## 背景

glm5.2_nv 切回 pexec fid1 (b1b22d03) 后 dsv4p 全方位测试 100% SR (4模式75请求).
dsv4p_nv pexec fid=12acbc62 稳定可用. 用户要求把 hermes 和 openclaw 都切到 dsv4p_nv.

## 变更

### 1. docker-compose.yml (3 处)
- cc4101 (L230): `PRIMARY_UPSTREAM_MODEL=glm5_2_nv` → `dsv4p_nv`
- opclaw4103 (L306): `PRIMARY_MODEL=glm5_2_nv` → `dsv4p_nv`
- hm4104 (L349): `PRIMARY_MODEL=glm5_2_nv` → `dsv4p_nv`
- backup: `docker-compose.yml.bak.R-dsv4p-deploy`

### 2. hermes config.yaml (3 处)
- `model.default: glm5_2_nv` → `dsv4p_nv`
- `providers.hm4104.default_model: glm5_2_nv` → `dsv4p_nv`
- `providers.hm4104.name: HM Adapter 4104 (glm5_2_nv)` → `(dsv4p_nv)`
- backup: `config.yaml.bak.R-dsv4p-deploy`

### 3. openclaw openclaw.json (3 处)
- `agents.defaults.model.primary: "opclaw4103/glm5_2_nv"` → `"opclaw4103/dsv4p_nv"`
- `agents.defaults.compaction.model: "opclaw4103/glm5_2_nv"` → `"opclaw4103/dsv4p_nv"`
- `models.providers.opclaw4103.models[0].id: "glm5_2_nv"` → `"dsv4p_nv"`
- backup: `openclaw.json.bak.R-dsv4p-deploy`

### 4. nv_gw config.py — 无改动
- dsv4p_nv 已配好: function_id=12acbc62, strip_params=[reasoning_effort, stream_options, thinking], inject={}
- DEFAULT_NV_MODEL 已是 dsv4p_nv
- MODEL_MAP 已含 dsv4p_nv 映射

## 部署

```bash
cd /opt/cc-infra && docker compose up -d cc4101 opclaw4103 hm4104
```

## 验证

### Adapter env
- `docker exec cc4101 env | grep PRIMARY_UPSTREAM_MODEL` → `dsv4p_nv` ✓
- `docker exec hm4104 env | grep PRIMARY_MODEL` → `dsv4p_nv` ✓
- `docker exec opclaw4103 env | grep PRIMARY_MODEL` → `dsv4p_nv` ✓

### E2E curl 测试

| Adapter | HTTP | 延迟 | 模型 | 结果 |
|---|---|---|---|---|
| cc4101 | 200 | 14.2s | dsv4p_nv ✓ | thinking + max_tokens (64 tokens 用完) |
| hm4104 | 200 | 18.2s | deepseek-ai/deepseek-v4-pro ✓ | content="Hello" |
| opclaw4103 | 200 | 9.9s | deepseek-ai/deepseek-v4-pro ✓ | reasoning + content |

### Agent E2E

- **hermes**: `hermes chat -q "Say hello" --yolo` → "你好！有什么可以帮你的" ✓
- **openclaw**: `openclaw agent --agent main -m "Say hello in one word"` → status=ok, model=dsv4p_nv, fallbackUsed=false, stopReason=stop ✓

### DB 验证
```
mapped_model | upstream_type | count | ok
dsv4p_nv     | nvcf_pexec    |     3 |  3
```
3 条 dsv4p_nv 请求全 200, k0/k3/k4 轮转正常.

### nv_gw 日志
- `NV-BUF2KEY-INTERCEPT (dsv4p_nv) caller=cc4101-primary` ✓
- `NV-GLM52-ATTEMPT tier=dsv4p_nv mode=pexec_us_rr k2 channel=pexec fid=12acbc62` ✓
- `NV-BUFFER-SUCCESS (dsv4p_nv) flushed 24835b after 1 attempt(s), elapsed=5129ms` ✓

## 回滚
- docker-compose.yml.bak.R-dsv4p-deploy → `docker compose up -d cc4101 opclaw4103 hm4104`
- config.yaml.bak.R-dsv4p-deploy → 还原 hermes
- openclaw.json.bak.R-dsv4p-deploy → 还原 openclaw
