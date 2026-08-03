# R-dsv4f-0731: DeepSeek V4 Flash 0731 独立容器部署 + 全方位测试

**Date:** 2026-08-04
**Host:** HM2 (opc2sname, 100.109.57.26)
**Status:** Deployed + Verified

## 背景

DeepSeek V4 Pro (dsv4p_nv, `ai-deepseek-v4-pro` 74f02205) pexec 链路近期频繁超时。
NVCF 上发现 `0731-deepseek-v4-flash` (function_id `6166b605-230c-4733-9a95-1fba214c5484`, ACTIVE) — 0731 版本的 flash 模型。

## 探测结果 (HM2 per-key SOCKS5 美国 IP)

| Function | pexec | integrate |
|---|---|---|
| 0731-deepseek-v4-flash (6166b605) | ❌ 超时/400 | ✅ 200 1.05s |
| ai-deepseek-v4-pro (74f02205) | ❌ 超时 | ❌ 超时 |
| ai-deepseek-v4-flash (52e1ddb6) | ❌ 529 | — |

**结论:** 0731 flash 走 `integrate.api.nvidia.com/v1/chat/completions` 可用, pexec 不可用.

## 部署内容

### 1. 新容器 dsvf0731_nv40666 (port 40666)

- Image: `cc-infra-nv_gw` (同 nv_gw, bind-mount `gateway/`)
- Model: `dsv4f_nv` = `deepseek-ai/deepseek-v4-flash`
- NVCF function_id: `6166b605-230c-4733-9a95-1fba214c5484` (0731 flash)
- `NV_INTEGRATE_MODELS=dsv4f_nv` — 强制走 integrate 路径 (pexec 不可用)
- 5-key SOCKS5 美国代理轮转 (7901-7904)
- `NVU_TIER_BUDGET_DSV4F_NV=180`
- 原 `dsv4p_nv40066` (port 40066) 保留不动

### 2. config.py 改动

- 新增 `dsv4f_nv` 到 `NVCF_PEXEC_MODELS`, `NV_MODEL_TIERS`, `NV_MODEL_IDS`, `MODEL_MAP`, `MODEL_INPUT_TOKEN_SAFETY`
- `NVU_FORCE_STREAM_EXCLUDE_MODELS` 默认值加 `dsv4f_nv`

### 3. Adapter 配置改动

| Adapter | 原 PRIMARY | 新 PRIMARY | 新 FALLBACK |
|---|---|---|---|
| hm4104 (hermes) | dsv4p_nv40066:40066/dsv4p_nv | dsvf0731_nv40666:40666/dsv4f_nv | ms_gw/glm5_2_ms (不变) |
| opclaw4103 (openclaw) | dsv4p_nv40066:40066/dsv4p_nv | dsvf0731_nv40666:40666/dsv4f_nv | dsv4p_nv40066:40066/dsv4p_nv |

### 4. Agent 配置

- hermes `~/.hermes/config.yaml`: `default: dsv4f_nv`, `default_model: dsv4f_nv`
- openclaw `~/.openclaw/openclaw.json`: `primary: nv_cus/dsv4f_nv`

## 测试结果

### E2E Adapter 测试

| Adapter | HTTP | Time | Content |
|---|---|---|---|
| hm4104 (4104) | 200 | 1.96s | Hello! |
| opclaw4103 (4103) | 200 | 4.26s | Hello! |

### 1M 上下文测试

| Context size | prompt_tokens | Result | Time |
|---|---|---|---|
| small (Hi) | 5-10 | ✅ 200 | 1.5-5s |
| 1K tokens | 688 | ✅ 200 | 33.8s (3 retries) |
| 10K tokens | 6688 | ✅ 200 | 15.6s |
| 50K tokens | 33355 | ✅ 200 | 5.9s |
| 100K tokens | — | ❌ 502 (529 overload) | — |
| 200K tokens | 133355 | ✅ 200 | 12.2s |
| 330K tokens (~1M) | 220022 | ✅ 200 | 17.7s, 15.5s |

**1M 上下文支持确认:** 220K prompt_tokens 成功返回, 正确提取 context 中的 secret code.
失败案例均为 NVCF 529 "Service temporarily overloaded" 间歇过载, 非上下文大小限制.

### Stream TTFB

- TTFB: 12.89s, total: 17.36s, 40 chunks

### dsv4p_nv (pro) 连通性

5/5 成功 via 40066 pexec, 延迟 2.2-5.8s (含 reasoning_content).
Pro 恢复正常 (之前超时是 NVCF 间歇故障, 测试时已恢复).

### dsv4f_nv (flash) 稳定性

5 次测试: 1/5 成功 (4 次 529 过载). NVCF integrate 后端间歇过载严重.
成功时延迟 1-5s, 失败时 502 ~7-10s.

## 参数表

| 参数 | 值 | 备注 |
|---|---|---|
| 新容器端口 | 40666 | dsvf0731_nv40666 |
| function_id | 6166b605-230c-4733-9a95-1fba214c5484 | 0731-deepseek-v4-flash |
| model name | deepseek-ai/deepseek-v4-flash | integrate 路径 |
| NV_INTEGRATE_MODELS | dsv4f_nv | 强制走 integrate |
| 5-key 代理 | 7901-7904 | per-key SOCKS5 美国 IP |
| context limit | 1048576 (1M) | 实测 220K tokens 成功 |

## 已知问题

1. **NVCF 529 间歇过载** — flash 0731 integrate 路径间歇返回 "Service temporarily overloaded".
   成功率约 30-40%. adapter 层 fallback 到 dsv4p_nv40066 (pro) 或 ms_gw 兜底.
2. **pexec 不可用** — 0731 flash pexec 全 key 超时/404, 仅 integrate 可用.
3. **pro 模型恢复** — dsv4p_nv pexec 测试时已恢复正常 (5/5 成功).

## 文件变更

- `/opt/cc-infra/proxy/nv-gw/gateway/config.py` — 新增 dsv4f_nv 模型定义
- `/opt/cc-infra/docker-compose.yml` — 新增 dsvf0731_nv40666 服务, 改 hm4104/opclaw4103 PRIMARY
- `~/.hermes/config.yaml` — default dsv4p_nv → dsv4f_nv
- `~/.openclaw/openclaw.json` — primary glm5_2_nv → dsv4f_nv
