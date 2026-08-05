# R-kimi-k3: kimi-k3 多角度多链路可用性测试

## 背景

用户要求: "多角度多链路测试 kimi-k3 的可用性"。
此前 R2289 测试时 kimi-k3 (3ea2c6ee) 返回 404, 但当时 function 刚创建不久。
2026-08-05 重新全面测试, 确认 kimi-k3 当前状态。

## 测试设计 (多角度 × 多链路)

| 角度 | 链路 | 详情 |
|---|---|---|
| pexec × 5 keys | key1-4 via SOCKS5 7894-7897 | 每个 key 独立 US IP |
| pexec × model name | 13+ 种 model name 变体 | 探测 vllm 后端实际模型名 |
| pexec × stream/non-stream | stream=True/False | 穿透 NVCF 平台层到 vllm |
| pexec × headers | browser伪装 vs plain API | 排除 header 问题 |
| pexec × versionId path | /functions/{fid}/versions/{vid} | 尝试指定版本 |
| integrate × 4 model names | integrate.api.nvidia.com | OpenAI 兼容路径 |
| E2E via nv_gw 40006 | kimi_nv 通过 gateway | 完整链路 |

## 数据 (改前必有数据)

### 1. NVCF functions list — kimi 相关 function

| FID (前12位) | Name | Status | Created |
|---|---|---|---|
| f966661c-790 | nvquery-kimi-k2_6 | **INACTIVE** | 2026-06-30 |
| 3ea2c6ee-b43 | vllm-gb300-kimi-k3 | **ACTIVE** | 2026-08-04 |

- NVCF 账户上 kimi 只有这 2 个 function
- k2.6 已 INACTIVE (之前是 ACTIVE, R2289 时 10/10 100%)
- k3 是 2026-08-04 新创建, 标记 ACTIVE

### 2. kimi-k3 pexec (3ea2c6ee) — 5 keys × SOCKS5

| Key | Port | HTTP | Time | Error |
|---|---|---|---|---|
| k1 | 7894 | 404 | 0.7s | "Inference error" |
| k2 | 7895 | 404 | 0.5s | "Inference error" |
| k3 | 7896 | 404 | 0.7s | "Inference error" |
| k4 | 7897 | 404 | 0.7s | "Inference error" |
| k5 | 7898 | ERR | - | Connection refused (port down) |

- nvcf-status: "errored"
- Content-Type: application/problem+json
- 非 stream 模式被 NVCF 平台层拦截, 不到达 vllm

### 3. kimi-k3 pexec stream — model name 探测 (vllm 穿透)

stream=True 穿透 NVCF 到 vllm 后端, 返回更详细的错误:

| Model Name | HTTP | Error |
|---|---|---|
| moonshotai/kimi-k3 | 404 | "model does not exist" |
| moonshot/kimi-k3 | 404 | "model does not exist" |
| moonshotai/Kimi-K3 | 404 | "model does not exist" |
| moonshot-ai/kimi-k3 | 404 | "model does not exist" |
| moonshotai/kimi-k3-instruct | 404 | "model does not exist" |
| moonshotai/kimi_k3 | 404 | "model does not exist" |
| moonshotai/kimi-k3-chat | 404 | "model does not exist" |
| moonshotai/Kimi-K3-Instruct | 404 | "model does not exist" |
| moonshotai/kimi-k2.6 | 404 | "model does not exist" |
| vllm-gb300-kimi-k3 | 404 | "model does not exist" |
| moonshotai/kimi-k3-vllm | 404 | "model does not exist" |
| moonshot-ai/Kimi-K3 | 404 | "model does not exist" |
| moonshot/Kimi-K3-Instruct | 404 | "model does not exist" |
| (no model field) | 404 | "Inference error" |
| kimi-k3 / Kimi-K3 / kimi-k3-instruct | 404 | "model does not exist" |

- 所有 model name 变体在 vllm 后端都 "does not exist"
- 说明 vllm 实例上根本没有加载任何 kimi 模型

### 4. kimi-k3 integrate (integrate.api.nvidia.com)

| Model Name | HTTP | Error |
|---|---|---|
| moonshotai/kimi-k3 | 404 | "page not found" |
| moonshot/kimi-k3 | 404 | "page not found" |
| moonshotai/kimi-k3-instruct | 404 | "page not found" |
| moonshotai/kimi-k2.6 | 404 | "Function not found for account" |

- integrate 路径完全不识别 kimi-k3
- kimi-k2.6 integrate 返回 function not found (与 pexec INACTIVE 一致)

### 5. kimi-k2.6 pexec (f966661c) — 确认 INACTIVE

| Key | Port | HTTP | Error |
|---|---|---|---|
| k1 | 7894 | 404 | "Function not found for account" |
| k2 | 7895 | 404 | "Function not found for account" |

- 确认 f966661c 已从 NVCF 账户移除 (不是临时不可用, 是 INACTIVE)

### 6. E2E via nv_gw (40006)

```
curl http://localhost:40006/v1/chat/completions model=kimi_nv
→ 502 "All NV API tiers failed for kimi_nv after 1.2s"
→ 0 attempts (FID immediately rejected)
```

- nv_gw 仍使用旧 FID f966661c (INACTIVE), 0 成功
- nv_gw logs: `[NV-NONCYCLE-ERR] tier=kimi_nv k2 resp.status=404 non-cycling`
- peer-fb skip list 中, 不尝试 peer fallback

## 根因分析

**kimi-k3 (vllm-gb300-kimi-k3) 是一个 "空壳 function":**

1. NVCF 平台层: function 3ea2c6ee 存在且 ACTIVE, health check (/health, port 8000) 通过
2. vllm 后端: 没有加载任何 kimi 模型, 所有 model name 返回 "does not exist"
3. NVCF pexec 非 stream: 返回 "Inference error" (平台层拦截, 后端推理失败)
4. NVCF pexec stream: 穿透到 vllm, 返回 "model does not exist" (后端层面)
5. integrate 路径: 完全不识别 kimi-k3 model name

**对比 kimi-k2.6:**
- f966661c 之前是 ACTIVE 且 10/10 100% SR (R2289 测试)
- 现已 INACTIVE, NVCF 账户已移除该 function

**结论: kimi_nv 在 NVCF 上完全不可用。**
- k2.6 function 已下线 (INACTIVE)
- k3 function 存在但后端空壳 (vllm 无模型)
- 无法通过任何链路 (pexec/integrate/E2E) 获取推理结果

## 当前 nv_gw kimi_nv 配置 (未修改)

```python
# config.py
"kimi_nv": {
    "function_ids": ["f966661c-790d-4f71-b973-c525fb8eafd4"],  # INACTIVE
    "strip_params": ["thinking_budget"],
    "inject": {"reasoning_effort": "low"},
}
# NV_MODEL_IDS
"kimi_nv": "moonshotai/kimi-k2.6"
# NVU_TIER_BUDGET_KIMI_NV=370
# NVU_PEER_FB_SKIP_MODELS contains kimi_nv
```

## 建议

1. **kimi_nv 当前不可用, 不应作为任何 adapter 的 primary**
2. 当前四 adapter primary 已是 glm5_2_nv (R2293), kimi_nv 仅保留备份 — 无需改动
3. **不需要更新 config.py 中的 kimi FID**: 3ea2c6ee 虽 ACTIVE 但后端空壳, 换了也 404
4. 等 NVCF 后端加载 kimi-k3 模型后再重新测试
5. 可定期检查 NVCF functions list 看 f966661c 是否恢复 ACTIVE 或 3ea2c6ee 后端是否加载模型

## 验证

所有测试从 nv_gw 容器内执行, 使用 PySocks + NVU_KEY1-5 环境变量 + SOCKS5 7894-7897, 模式与 nvcf_conn.py 一致。
