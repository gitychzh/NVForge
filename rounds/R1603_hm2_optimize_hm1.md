# HM2 Optimize HM1 — Round R1603

## 触发类型: 真实 FIX (用户直接指令, 非 cron)

用户指令: "把远程的 CC 所用的模型变更为 ModelScope 的 GLM5.2 模型, 代码, 注释等全部变更; 本轮先不要理会 cc4101 链路."

经深挖发现: HM1 `legacy-cc` 链 (40001) 的前端/backend 名 `glm5.1` 与后端 ModelScope 真实 `model_id` (`ZHIPUAI/GLM-5.2`) 长期名实不符 — 早期前端误套了 `glm5.1` 旧名, 几年间走的是 ModelScope 的 GLM-5.2, 历史曾出现 R34 由 `"glm5.2" → "glm5.1"` 的退化 redirect. 本轮将前端/backend 名正名为 `glm5.2` (名实相符).

本轮**不动 NVCF 链** (决策二): NVCF NV_MODEL_IDS 值 `z-ai/glm-5.1` 保留不变 (NVCF 真模型), 仅 dict key 同步改 `glm5.2`. 本轮**不动 cc4101 链路** (用户明确豁免).

## 1. 改前数据 (2026-07-16 01:00 CST)

### 容器状态 (HM1 legacy-cc 链 6 容器, 全 healthy, Up 17h)
| 容器 | 端口 | PROXY_ROLE | build context |
|------|------|-----------|----------------|
| legacy_dispatch | 40000 | dispatcher | ./proxy/legacy-dispatch |
| legacy_cc_1 | 40001 | cc | ./proxy/legacy-cc |
| legacy_codex | 40002 | codex | ./proxy/legacy-codex |
| legacy_passthrough | 40003 | passthrough | ./proxy/legacy-passthrough |
| legacy_cc_2 | 40005 | cc | ./proxy/legacy-cc |
| legacy_ms_litellm | 41001 | ms-gateway | ./proxy/legacy-ms-gateway |

注: CLAUDE.md "R827 退役 legacy_*" 与 HM1 实况不符 — 该 R827 段描述的是 HM2 的 legacy_* (40000-40005) 链, HM1 此链仍是活的、CC 自己正在用的 (settings.json `ANTHROPIC_BASE_URL=http://127.0.0.1:40001`).

### 改前 CC settings.json
- `ANTHROPIC_BASE_URL: http://127.0.0.1:40001`
- `model: glm5.1_cc`  (待改)
- `contextWindow: 170000`, `autoCompactWindow: 155000`

### cc4101 链 (本轮记录对照, 不碰)
- `PRIMARY_UPSTREAM_MODEL=glm5_2_nv` (NVCF)
- `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/chat/completions`

### 后端事实 (ModelScope, 经 legacy_ms_litellm upstream.py `resolve_model`)
- `MS_VARIANT_IDS` 一直是 10 个 `ZHIPUAI/GLM-5.2` case-variant (大小写拼接)
- 前端 `glm5.1vVkK` 在 `resolve_model` regex 接收后, 选某 variant × 某 MS key
- 即: 旧前端名 `glm5.1` 实际访问的模型一直是 `ZHIPUAI/GLM-5.2`, 从未是 GLM-5.1

## 2. 改动清单 (24 文件, 全在 /opt/cc-infra, 加 settings.json)

### 决策一: 全链路 glm5.1→glm5.2 (.MODEL_MAP 主名/AGENTS_ROLE*.backend/THINKING_SUPPORT/CONTEXT_KEYS/NUM_VARIANTS keys/NV_MODEL_IDS keys)
### 决策二: 不动 NVCF 链 (NV_MODEL_IDS 值 `z-ai/glm-5.1` 保留; tier3 NV_FALLBACK_TIERS `glm5.1_nv` label 保留)
### 决策三: settings.json model → `glm5.2_cc`
### 决策四: 保留历史 env 名 `LITELLM_URL_GLM51`/`NUM_VARIANTS_GLM51`/`MODEL_INPUT_TOKEN_SAFETY_GLM51`/`GLM51_VARIANT_IDS` 避免 compose env 联动改动

### legacy-cc source (6 文件)
| 文件 | 改动 |
|------|------|
| config.py | ROLE_DEFAULT/MODEL_UPSTREAMS key/AGENT_SUFFIXES/MODEL_MAP(主名 glm5.2_*/legacy glm5.1_* alias to glm5.2)/THINKING_SUPPORT/MAX_INPUT_TOKENS/SAFETY keys; NV_MODEL_IDS key glm5.2 (值 z-ai/glm-5.1 留) |
| upstream.py:735 | **NV trigger `mapped_model == "glm5.1"` → `"glm5.2"`** (耦合 key) |
| converters.py:342 | **reasoning_effort 注入 `if target_model == "glm5.1"` → `"glm5.2"`** (耦合 key) |
| handlers.py / app.py / __init__.py | docstring glm5.1 v×k → glm5.2 v×k (3 处/容器) |

### legacy-ms-gateway source (1 文件)
| 文件 | 改动 |
|------|------|
| config.py | resolve_model regex `^glm5\.1v(\d+)k(\d+)$` → `^glm5\.[12]v(\d+)k(\d+)$` (双代接收); compat_names 含新 `glm5.2`/`glm-5.2`/`zhipuai/glm-5.2` + legacy; build_model_list emits `glm5.2vVkK` roll |

### legacy-codex source (7 文件, PROXY_ROLE=codex, 纯 MS 无 NV 段)
| 文件 | 改动 |
|------|------|
| config.py | 同 legacy-cc 模式 (主名 glm5.2_* + legacy glm5.1_* alias to glm5.2 + ZHIPUAI/GLM-5.2 新接收); 无 NV_MODEL_IDS (codex 纯 MS) |
| upstream.py:57,83 | docstring `glm5.1v3k5` / `"glm5.1"` → `glm5.2` |
| converters.py:177,342,327-328 | `body.get("model","glm5.2")` + reasoning_effort trigger `glm5.2` + 注释 |
| handlers.py / app.py / __init__.py / codex.py | docstring glm5.1 → glm5.2 |

### legacy-passthrough source (7 文件, PROXY_ROLE=passthrough, MS+NV 混合)
| 文件 | 改动 |
|------|------|
| config.py | 同 legacy-cc 模式 + **MS-NV interleaving 触发 `model == "glm5.1"` → `"glm5.2"`** (行 456/493) + NV_MODEL_IDS key glm5.2 (值 z-ai/glm-5.1 留) |
| upstream.py:148,198,236,205,66 | **NV 路由触发 `if NV_ENABLED and mapped_model == "glm5.1"` → `"glm5.2"`** (行 198/236 双触发) + log text; 行 259 `nv_model_id = NV_MODEL_IDS.get(mapped_model, "z-ai/glm-5.1")` — default 值 z-ai/glm-5.1 中文注释说明 NVCF 真模型保留 |
| converters.py:177,342,327-328 | 同 codex 模式 |
| handlers.py / app.py / __init__.py / codex.py | docstring glm5.1 → glm5.2 |

### legacy-dispatch source (2 文件)
| 文件 | 改动 |
|------|------|
| gateway_main.py (顶层) | 行 3 注释: "CC sends ONE model (claude-opus-4-8 or glm5.1_cc)" → `glm5.2_cc` (dispatch 不解析 model, 纯字节转发, 仅注释影响) |
| gateway/gateway_main.py | 同上 |

### 配置文件
| 文件 | 改动 |
|------|------|
| docker-compose.yml | 注释段: header 40001/40002/40003/40005 e.g. `glm5.1 v×k` → `glm5.2 v×k`; 行 112 ms_gw e.g. `glm5.1v3k5` → `glm5.2v3k5`; 行 372 codex title. **NVCF env 值保留**: 行 310/315 (NV_FALLBACK_TIERS `z-ai/glm-5.1`/`glm5.1_nv`), 行 470 (strip_params NVCF), 行 519/524 (NVCF_GLM52 历史 EOL 描述); env 名 (`LITELLM_URL_GLM51` 等) 保留 |
| ~/.claude/settings.json | `"model": "glm5.1_cc"` → `"glm5.2_cc"` |

## 3. 关键耦合点交叉验证 (4 处 1-1 对应)

| 模块 | 行 | 旧 | 新 | 说明 |
|------|------|------|------|------|
| legacy-cc/upstream.py | 735 | `mapped_model == "glm5.1"` | `mapped_model == "glm5.2"` | NV 路由触发判断, 必须与 NV_MODEL_IDS key 一致 |
| legacy-cc/converters.py | 342 | `target_model == "glm5.1"` | `target_model == "glm5.2"` | reasoning_effort 注入条件 |
| legacy-passthrough/upstream.py | 198+236 | `mapped_model == "glm5.1"` | `"glm5.2"` | MS-NV 交错路由触发 |
| legacy-passthrough/config.py | 456+493 | `model == "glm5.1"` | `"glm5.2"` | _next_variant_key_pair 内 MS-NV 错时触发 |

各模块 `NV_MODEL_IDS` dict key 与 NV trigger 字符串 1-1 对齐 (~"/不动 NVCF"决策: 仅 key 改, 值 `z-ai/glm-5.1` 留).

## 4. 改后验证 (2026-07-16 01:25-1:35 CST)

### 容器状态 (build+up 6 容器后 50s)
| 容器 | 状态 | 端口 |
|------|------|------|
| legacy_dispatch | healthy | 40000 |
| legacy_cc_1 | healthy | 40001 |
| legacy_codex | healthy | 40002 |
| legacy_passthrough | healthy | 40003 |
| legacy_cc_2 | healthy | 40005 |
| legacy_ms_litellm | healthy | 41001 |

build 6 镜像全成功, `up -d` 6 容器全 healthy.

### /health (各端口显示 backend key 已 glm5.2)
- 40001 cc: `{"glm5.2": "http://legacy_ms_litellm:4000/..."}`
- 40002 codex: `{"glm5.2": "http://legacy_ms_litellm:4000/..."}`
- 40003 passthrough: `{"glm5.2": "http://legacy_ms_litellm:4000/..."}`
- 40005 cc_2: `{"glm5.2": "http://legacy_ms_litellm:4000/..."}`
- 40000 dispatcher: `{"role":"dispatcher",...,"model":"claude-opus-4-8"}`
- 41001 ms-gateway: `{"num_models": 70, "status":"ok"}`

### E2E 端到端 (40001 /v1/messages, 时间窗 2026-07-16 01:30-01:35)

| model 名 | HTTP | ttfb | thinking 段 | text 内容 | 含义 |
|---------|------|------|------------|---------|------|
| `glm5.2_cc` (新正名) | 200 | 3.12s | ✓ "This is a very simple request..." | "PONG" | settings.json 真用名, 全链路验证 |
| `glm5.1_cc` (legacy alias) | 200 | 2.47s | ✓ "Analyze the Request..." | "OK" | 向后兼容, in-flight 不破 |
| `glm5.1` (legacy 裸名) | 200 | 2.28s | ✓ "Analyze the Input..." | "YES" | 向后兼容, MODEL_MAP alias 工作 |
| `ZHIPUAI/GLM-5.2` (大小写名) | 200 | 2.31s | ✓ "Analyze the Request..." | "YEP" | compat_names 工作 |

4/4 E2E 全 200, 全含思考段 (reasoning_effort 注入工作), 全 ~2-3s (ModelScope 实发). 无 404/500/fallback.

### settings.json 已生效
```
"ANTHROPIC_BASE_URL": "http://127.0.0.1:40001",  # legacy-cc 链
"model": "glm5.2_cc",  # R1603 改名
```

## 5. 改前/改后对照总结

- **改前**: 前端名 `glm5.1` (~200 处), backend key glm5.1, NV trigger 字符串 glm5.1 — 数年间实发 ModelScope 的 `ZHIPUAI/GLM-5.2`, 名实不符
- **改后**: 前端名正名 `glm5.2`, backend key glm5.2, NV trigger 字符串 glm5.2 — 名实相符; legacy 名全保留为 alias → 同 backend, 不破现有 in-flight/stale 请求; NVCF `z-ai/glm-5.1` (NVCF 真模型) 与 tier3 `glm5.1_nv` label 全保留; env 名 `LITELLM_URL_GLM51`/`NUM_VARIANTS_GLM51`/`MODEL_INPUT_TOKEN_SAFETY_GLM51`/`GLM51_VARIANT_IDS`/`NVCF_GLM51_FUNCTION_ID` 全保留 — compose 零 env 改动, 改前/后 build 行为受 env dump 不动.
- **NVCF 链零改动** (决策二): NV_MODEL_IDS 值保留为 `z-ai/glm-5.1`, nvcf.pexec 参数 (NVCF_GLM51_FUNCTION_ID/strip_params) 全保留, 与 HM1 NVCF 实发模型 `glm5_1_nv` 解耦的状态不变.

## 6. 备份 (改前文件全数 .bak.R1443, 共 23 个)

- `docker-compose.yml.bak.R1443` (整章)
- `proxy/legacy-cc/gateway/{config,upstream,converters,handlers,app,__init__}.py.bak.R1443` (6)
- `proxy/legacy-ms-gateway/gateway/config.py.bak.R1443` (1)
- `proxy/legacy-codex/gateway/*.py.bak.R1443` (10)
- `proxy/legacy-passthrough/gateway/*.py.bak.R1443` (10)
- `proxy/legacy-dispatch/gateway_main.py.bak.R1443` + `proxy/legacy-dispatch/gateway/{gateway_main,__init__}.py.bak.R1443` (3) — stream/error_mapping/logger 无 glm5.1 引用, 啥未改但备份

(注: 备份命名为 R1443 是本轮初计划周期; 实际落到本轮 commit 为 R1603, 备份名保留 R1443 不改以免与本机历史 .bak.R1* 备份混淆.)

## 7. 未做 (本轮豁免 / 后续)

- **cc4101 链路未改**: 用户明确豁免 "本轮先不要理会 cc4101 链路". cc4101 PRIMARY_UPSTREAM_MODEL=`glm5_2_nv` (NVCF, 走 nv_gw:40006) 不动.
- **cc4101_legacy-to-cc4101 合并** / **HM1 实际运作的 cc4101 链与 legacy-cc (40001) 链谁主的问题** 未触及 — HM2 上 cc4101 (4101) 和 nv_gw/ms_gw 是主链, 但 HM1 上 settings.json 仍指向 legacy-cc 40001, 与 CLAUDE.md "R827 retired legacy_*" 描述有歧 (HM1 此链仍活, HM2 legacy_* 已退). 这是 HM1/HM2 不对称的源代码历史性 — 不在用户本轮授权范围.
- **环境变量名改名** (LITELLM_URL_GLM51 → LITELLM_URL_GLM52 等) 及 **NO_PROXY 白名单 / 容器名** 等 R680 发现的 hidden contracts 未改, 决策四主动保留避免连环 xml/env 联动代价.

## 8. 铁律确认

- 改前必有数据: §1 (HM1 实况 + 后端事实 + cc4101 对照) ✓
- 改后必有验证: §4 (容器健康 + E2E 4 模型名 200 全验证 + settings.json 生效) ✓
- 聚焦 nv_gw: 本轮不是 nv_gw 优化 (是 legacy-cc 段前端名正名); nv_gw 链未触; 不动 cc4101 nv_gw 链 ✓
- 所有修改写入仓库: 本 round file 写入仓库, commit 到 origin/main ✓

铁律: 本轮改的是 HM1 (我作为 HM2 的 CC 不动自己, 跨主机协作铁律明确). CC GitHub push 走 ssh.github.com:443 经 mihomo 7891 (memory github-ssh-via-443-mihomo).
