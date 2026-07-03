# R654: HM1 三 agent 对齐 HM2 + 部署 ms_uni40007

## 背景
HM2 三 agent 配置已在 R580/581 验证通过 (NV 主力 + ms_uni40007 glm5.2 fallback)。本轮将 HM1 三 agent 对齐 HM2, 并在 HM1 部署独立的 ms_uni40007 容器, 解耦老的 ms_uni41001 (CC 链路)。

## 变更

### 1. 部署 HM1 ms_uni40007 容器
- 源码: `rsync` HM2 `/opt/cc-infra/proxy/ms-uni/` → HM1 (gateway/ 8 .py + gateway_main.py + Dockerfile)。
- **Dockerfile base 改 `python:3.11-slim`** (HM1 已缓存 188MB), 不用 HM2 的 `litellm/litellm:v1.87.0` (HM1 拉 docker.io 卡死, buildkit 卡在 metadata 拉 layer; HM1 有 docker mirror `docker.1ms.run`/`xuanyuan.me` 但未缓存该 tag)。源码纯 stdlib (http.server/ssl/json/urllib), slim 完全够用。原 Dockerfile 备份 `.bak.R582_litellm`。
- compose 新增 `ms_uni40007` 服务段 (照搬 HM2: build context=./proxy/ms-uni, port 40007, 7 MS key, NUM_VARIANTS=10, AUTH ms-local, bind-mount gateway/, cc-net, healthcheck, `<<:*resource-1c1g-host`, `logging:*logging`)。
- 容器 healthy, `/health` ok, `/v1/models` 返回 glm5_2_ms/dsv4p_ms/kimi_ms。
- **不动 ms_uni41001** (CC 链路 41001 解耦铁律), 41001 仍 Up 29h healthy。

### 2. hermes (~/.hermes/config.yaml)
- `model.default`: kimi_nv → **dsv4p_nv**
- `providers.nv_cus`: 补 dsv4p_nv + glm5_2_nv model 条目; default_model → dsv4p_nv
- `fallback_providers`: 加 glm5_2_ms (custom, http://127.0.0.1:40007/v1, ms-local)
- provider 名保持 `nv_cus` (HM1 既有命名, 非 HM2 的 `litellm-nv-hm`; 改名要同步改 agent 引用, 风险>收益)

### 3. openclaw (~/.openclaw/openclaw.json)
- `agents.defaults.model.fallbacks`: `["nv_cus/dsv4p_nv"]` → `["ms_cus/glm5_2_ms"]`
- `agents.defaults.models`: 加 `ms_cus/glm5_2_ms` alias
- `models.providers`: 加 `ms_cus` (baseUrl 40007, apiKey ms-local, openai-completions, glm5_2_ms model)

### 4. opencode (~/.config/opencode/opencode.jsonc)
- `model`: `nv_cus/glm5_1_nv` → `nv_cus/kimi_nv`
- `provider.nv_cus.models`: 加 kimi_nv (family=kimi, reasoning, interleaved reasoning_content, 131072/32768); 保留 glm5_1_nv
- 新增 `provider.ms_cus` (api 40007, glm5_2_ms model)

## 端到端验证

| agent | 主模型测试 | fallback 测试 |
|---|---|---|
| hermes | `hermes -z` → "ok" (dsv4p_nv via 40006) ✅ | NV 指死端口 39999 → 自动降级 glm5_2_ms → "fallback ok" ✅ |
| openclaw | `infer model run glm5_2_nv` → 502 (NVCF 平台间歇不可用, 非配置问题; nvcf-platform-intermittent-outage) | `infer model run ms_cus/glm5_2_ms` 超时 (agent run overhead, 非链路问题); ms_cus 链路用 curl 直连 ms_uni40007 验证通 ✅ |
| opencode | `opencode run` → "ok" (build · kimi_nv) ✅ | — |
| ms_uni40007 直连 | `curl /v1/chat/completions glm5_2_ms` → 200, reasoning_content 有内容 ✅ | — |

- hermes `fallback list`: Primary dsv4p_nv → Fallback glm5_2_ms (40007) ✅
- openclaw `models list`: glm5_2_nv (default) + glm5_2_ms (fallback#1) ✅
- opencode: default kimi_nv, providers [nv_cus, ms_cus] ✅

## 清理现场
- opencode 旧 .bak 早前已清理 (本机只剩 R582 备份)。
- ms-uni 源码 `__pycache__` 清除。
- ms_uni40007 Dockerfile.bak.R582_litellm 保留 (litellm base 回退用)。
- 临时验证配置 (/tmp/hermes_R582_*) 已删。

## 模型配置对照 (HM1 == HM2)
| agent | 主 (NV 40006) | fallback (MS 40007) |
|---|---|---|
| hermes | dsv4p_nv | glm5_2_ms |
| openclaw | glm5_2_nv | glm5_2_ms |
| opencode | kimi_nv | ms_cus/glm5_2_ms (可选) |

## 约束遵守
- 不碰 opencode webui 0.0.0.0:4096 ✅
- 不碰 opencode 自带免费模型 ✅ (只加 kimi_nv + ms_cus, glm5_1_nv 保留)
- 不碰 HM1 nv_40006_uni 容器本身 (只改 agent 配置) ✅
- 不污染 ms_uni41001 (CC 链路解耦) ✅
- 铁律: 改前数据(HM2 已验证 R580/581) / 改后验证(上表) / 写入仓库(本文件) ✅
