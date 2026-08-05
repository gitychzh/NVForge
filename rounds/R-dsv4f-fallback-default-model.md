# R-dsv4f-fallback: dsv4f_nv 注册 nv_gw + 设置为 DEFAULT_NV_MODEL 兜底

## 摘要

三模型多链路实测: dsv4f (deepseek-v4-flash) 最稳定最快 (pexec 5/5 avg 3.7s), dsv4p 次之 (5/5 avg 6.3s), glm5.2 最差 (3/5 pexec, 0/5 integrate timeout). 将 dsv4f_nv 注册到 nv_gw 并设为 DEFAULT_NV_MODEL, 裸名请求自动走 dsv4f.

## 测试数据

### 测试条件
- 5 key × SOCKS5 proxy 7894 (US IP)
- 每组 5 请求, `{"messages":[{"role":"user","content":"Say hi"}],"stream":false,"max_tokens":10}`
- 容器内 python http.client + PySocks (与 nv_gw 完全相同的请求方式)

### pexec via US proxy (SOCKS5 7894)

| 模型 | FID | SR | avg | min | max |
|---|---|---|---|---|---|
| **dsv4f** | 52e1ddb6 | **5/5** | **3.7s** | 1.5s | 7.3s |
| dsv4p | 74f02205 | 5/5 | 6.3s | 2.5s | 12.1s |
| glm5.2 | 3b9748d8 | 3/5 | 23.5s | 21.3s | 26.4s |

### integrate via US proxy (SOCKS5 7894)

| 模型 | SR | avg | 备注 |
|---|---|---|---|
| **dsv4f** | **4/5** | **5.5s** | 1 次 SSLEOFError |
| dsv4p | 5/5 | 8.9s | |
| glm5.2 | 0/5 | — | 全 timeout (>30s) |

### 直连 CN Mobile
全卡住 — NVCF 对 China IP 直连返回 axum 500 error (`Missing request extension`). 非 model 级问题, 是 NVCF 平台对 China IP 的限制.

### 结论: dsv4f_nv 最稳最快
- pexec SR 100%, avg 3.7s (dsv4p 6.3s, glm5.2 23.5s)
- integrate SR 80%, avg 5.5s (dsv4p 8.9s, glm5.2 0%)
- FID 52e1ddb6 ACTIVE, 响应稳定

## 配置变更

### config.py: 注册 dsv4f_nv

```python
# NVCF_PEXEC_MODELS 新增:
"dsv4f_nv": {
    "function_ids": ["52e1ddb6-c745-4802-93f5-ba012d04c336"],
    "strip_params": ["reasoning_effort", "stream_options", "thinking"],
    "inject": {},
}

# NV_MODEL_TIERS 新增 dsv4f_nv
NV_MODEL_TIERS = ["kimi_nv", "dsv4p_nv", "dsv4f_nv", "glm5_2_nv", "minimax_m3_nv"]

# NV_MODEL_IDS 新增
"dsv4f_nv": "deepseek-ai/deepseek-v4-flash"

# DEFAULT_NV_MODEL 改为 dsv4f_nv
DEFAULT_NV_MODEL = os.environ.get("DEFAULT_NV_MODEL", "dsv4f_nv")

# MODEL_MAP 新增
"dsv4f_nv": "dsv4f_nv",
"deepseek-v4-flash": "dsv4f_nv",
"deepseek-ai/deepseek-v4-flash": "dsv4f_nv",

# MODEL_INPUT_TOKEN_SAFETY 新增
"dsv4f_nv": 131072,
```

### docker-compose.yml: 新增 tier budget

```yaml
NVU_TIER_BUDGET_DSV4F_NV=60
```

## 部署

```bash
cd /opt/cc-infra && docker compose up -d nv_gw
```

## 验证

### E2E via nv_gw (40006)

| 模型 | SR | avg | 备注 |
|---|---|---|---|
| dsv4f_nv | 5/5 | 3.7s | 1.2-7.6s |
| dsv4p_nv | 1/1 | 13.1s | 无回归 |
| 裸名 (default) | 1/1 | 34.5s | → dsv4f_nv (deepseek-v4-flash) |

### /health 确认
```json
{
    "nv_default_model": "dsv4f_nv",
    "nvcf_pexec_models": ["kimi_nv", "dsv4p_nv", "glm5_2_nv", "dsv4f_nv", "minimax_m3_nv"]
}
```

## 不改的部分
- dsv4p_nv 的 R-dsv4p-adaptive (pexec→integrate fallback) 保持不变
- glm5_2_nv 的 MODE_CHAIN 保持不变
- NV_KEY_INTEGRATE_KEYS=dsv4p_nv:3,4;minimax_m3_nv:5 保持不变
- 各 adapter (cc4101/hm4104/opclaw4103) 的 PRIMARY_MODEL 不改 — 它们指向 glm5_2_nv/dsv4p_nv, 不受 DEFAULT_NV_MODEL 影响
