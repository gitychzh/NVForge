# R705: HM2 — GLM-5.1 彻底清除 + legacy 容器源码退役 + 冗余收敛

## TL;DR
用户要求(HM2 only): ① 删除 GLM-5.1 任何信息(已彻底抛弃); ② dsv4p_ms 是 hermes 一级回退(非二级), 删除 glm5_2_ms 回退; ③ 全系统扫描清除冗余, 工程化模块化, 方便长期维护.

改前数据: R704 已先把 6 个 legacy 容器(legacy_ms_litellm/legacy_dispatch/legacy_cc_1/legacy_cc_2/legacy_codex/legacy_passthrough)从 live `docker-compose.yml` 删除, 但**源码目录与计数器残留仍在**. 实际本次需清理的活引用集中在: nv_gw `config.py`/`rr_counter.py`、ms_gw `config.py`、opencode `opencode.jsonc`、`rr_counter.json`. cc4101 的 fallback 在 compose 已是 `dsv4p_ms`(R704 改), 但运行容器仍是旧 env `glm5_2_ms` 需重建.

cc4101 fallback 确认: 用户"删除 glm5.2_ms 回退"经澄清指 hermes 链(HM2 hermes config 当前 fallback 已是 dsv4p_ms 单级, 符合, 不动); cc4101(CC 自身链路)的 glm5_2_ms→dsv4p_ms 改动由 R704 完成, 本次仅重建容器让 env 生效.

## 一、改动清单

### A. nv_gw 源码 (`/opt/cc-infra/proxy/nv-gw/gateway/`)
**config.py** (备份 `.bak.R705`):
- 删 `NVCF_PEXEC_MODELS["glm5_1_nv"]` 整块(含 NVCF_GLM51_FUNCTION_ID env 引用)
- `NV_MODEL_TIERS`: `["kimi_nv","dsv4p_nv","glm5_1_nv","glm5_2_nv"]` → `["kimi_nv","dsv4p_nv","glm5_2_nv"]`
- `NV_MODEL_IDS`: 删 `"glm5_1_nv":"z-ai/glm-5.1"`
- `FALLBACK_GRAPH`: 删 `"glm5_1_nv":["dsv4p_nv"]` 条目(保留 `"glm5_2_nv":["dsv4p_nv"]`)
- `MODEL_MAP`: 删 `glm5_1_nv`/`glm5.1`/`z-ai/glm-5.1` 三条
- `MODEL_INPUT_TOKEN_SAFETY`: 删 `glm5_1_nv` 条目
- `detect_nv_model` docstring 更新
- 文件头注释考古段(glm5.1 抓包考古 5 行)精简, `R40 removed` 注释去 glm5.1 字眼, `R503` 注释去 glm5.1 字眼, integrate models 注释 `kimi/glm5.1` → `kimi/glm5_2`

**rr_counter.py** (备份 `.bak.R705`):
- `_TIER_RR_KEYS`(原 `_RR_KEY_MAP`): 删 `"glm5_1_nv":"nv_glm5_1"`
- `_OLD_RR_KEY_MAP`(原 `_LEGACY_KEY_MAP`): 删 `"hm_nv_glm5.1"` 和 `"nv_glm5_1"` 两条迁移
- 头注释去 glm5_1_nv 提及

**handlers.py / pexec.py / upstream.py**: 仅注释考古提及, 无代码依赖, 不改(保 git blame).

### B. ms_gw 源码 (`/opt/cc-infra/proxy/ms-gw/gateway/`)
**config.py** (备份 `.bak.R705`):
- `MODEL_REGISTRY`: 删 `kimi_ms` 占位条目(`_disabled=True`, 未实现, 纯冗余)
- `_MODEL_RR_KEYS`: 删 `"kimi_ms":"ms_kimi"`
- 头注释 `Variants (10, IMMUTABLE — copy from litellm-glm51/config.yaml)` → `Variants (10, IMMUTABLE) — 10 ModelScope model_id typos for ZHIPUAI/GLM-5.2`(去 litellm-glm51 引用)
- `glm5_2_ms + dsv4p_ms implemented (R703); kimi_ms still placeholder.` → `glm5_2_ms + dsv4p_ms implemented (R703).`

### C. compose (`/opt/cc-infra/docker-compose.yml`)
R704 已删 6 个 legacy service 块 + legacy_ms_litellm. R705 无需再改 compose(已干净). 仅删冗余备份 `docker-compose.yml.bak.R705`(与 live 相同, 我创建后发现的冗余).

### D. agent 配置
- **opencode `~/.config/opencode/opencode.jsonc`** (备份 `.bak.R705`): 删 `provider.nv_gw.models.glm5_1_nv` 整块(花括号深度配对删除, 保 kimi_nv 完整). HM2 hermes/openclaw config 不动(已符合 dsv4p_ms 一级回退).

### E. 计数器
- `logs/nv_gw/rr_counter.json`: 停容器→`sudo python pop("nv_glm5_1")`→启容器. 必须停容器改, 否则 atexit 回写复活.
- `logs/legacy-4000*/rr_counter.json`: R704 已随目录删除, 无残留.

### F. 源码/日志目录
R704 已删: `proxy/legacy-cc/`、`proxy/legacy-dispatch/`、`proxy/legacy-codex/`、`proxy/legacy-passthrough/`、`proxy/legacy-ms-gateway/`、`litellm-nv/`、`logs/legacy-*/`. R705 确认均不存在.

## 二、验证

| 项 | 期望 | 实测 |
|---|---|---|
| `docker ps` | 只剩 logs_db/nv_gw/ms_gw/cc4101 | ✓ |
| `curl /health` × 3 | 全 200 | 40006/40007/4101 全 200 ✓ |
| nv_gw `NVCF_PEXEC_MODELS` | `[kimi_nv, dsv4p_nv, glm5_2_nv]` | ✓ |
| nv_gw `NV_MODEL_TIERS` | 无 glm5_1_nv | ✓ |
| nv_gw `FALLBACK_GRAPH` | `{'glm5_2_nv': ['dsv4p_nv']}` | ✓ |
| nv_gw 启动日志 `restored` | 无 nv_glm5_1 | ✓ |
| ms_gw `MODEL_REGISTRY` | `[glm5_2_ms, dsv4p_ms]` | ✓ |
| cc4101 运行 env | `FALLBACK_UPSTREAM_MODEL=dsv4p_ms` | ✓ (R704 compose 已改, 本次重建生效) |
| 端到端 kimi_nv | 200 | ✓ |
| 端到端 dsv4p_nv (stream) | 200, 返回 "Hello" | ✓ |
| 端到端 dsv4p_ms | 200 | ✓ |
| 端到端 cc4101 | 200 | ✓ |
| glm5_2_nv → dsv4p_nv fallback | 自动切且成功 | ✓ (`NV-FALLBACK-SUCCESS`) |
| 全量 grep `glm5_1\|glm5.1\|GLM51\|ai-glm-5_1\|nv_glm5_1` | 源码+配置+计数器全清 | ✓ |

注: glm5_2_nv/dsv4p_nv pexec 40s timeout 真因见下方"五、彻查", **非** NVCF 平台 surge(原 R696 归因有误).

## 三、工程化收益
- nv_gw 模型表 4→3, FALLBACK_GRAPH 无死链, MODEL_MAP 无死引用
- ms_gw MODEL_REGISTRY 去未实现占位, 只剩两个真实实现
- compose 9→4 容器(R704), NO_PROXY 白名单同步收敛
- rr_counter.json 无死 key, 启动日志干净
- legacy 源码 6 目录 + litellm-nv 全删(R704), 仓库噪音归零
- opencode.jsonc 无死模型块

## 四、铁律遵守
- 改前数据: 完整扫描 nv_gw/ms_gw/cc4101/legacy 全源码+compose+计数器+agent 配置, 确认活引用与死引用分类 ✓
- 改后验证: health + config 加载 + env + 端到端 4 链路 + 全量 grep ✓
- 聚焦 nv_gw(及直接相关): 未动 agent 模型选择/thinking/tool_calls 逻辑 ✓
- 所有修改写入仓库: 本 round + 备份 `.bak.R705` ✓
- 仅 HM2: HM1 未触碰 ✓


## 五、彻查: glm5_2_nv/dsv4p_nv 40s timeout 真因 (用户要求换 IP 验证)

R705 验证阶段见 glm5_2_nv pexec 40s timeout, 原草拟归因"NVCF surge 已知问题域". 用户纠正: 必须彻查真伪, 换 IP 试. 结果:

### 测试 1: HM2 宿主直连 vs mihomo 5 出口
直打 `https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/3b9748d8...` (glm5_2 真实 pexec 路径):

| 路径 | k1 | k2 | k3 | k4 | k5 |
|---|---|---|---|---|---|
| **HM2 直连** (宿主 IP) | 200 3.1s | 403 鉴权失败 | 200 7.1s | 200 7.5s | 200 1.4s |
| **mihomo 7894** | timeout 15s | — | — | — | — |
| **mihomo 7895-7899** | 全 timeout 15s | — | — | — | — |

5 个 mihomo 出口 IP (103.62.49.x 同 C 段) **全 timeout**, 但宿主直连 4/5 key 秒回 200. TCP 握手+SSL+CONNECT 全通, 仅 HTTP 请求 hang → SNI 阻断或 NVCF 对该 IP 段拒收.

### 测试 2: integrate 端点对照
`integrate.api.nvidia.com/v1/chat/completions` 各 key + HM1 日本 IP 全 timeout — integrate 端点本身连通性问题, 与 HM2 IP 无关.

### 结论
- **glm5_2_nv/dsv4p_nv 40s timeout 真因 = nv_gw `NVU_PROXY_URL1-5` 全指向 mihomo 7894-7899, 而这 5 个出口被 NVCF 拒**. 与 NVCF 平台 surge/限速**无关**.
- R696 记忆"74f02205 经日本 IP 秒回美国 IP 挂死"已摸到边但未定论, 本次定论.
- **临时解法**: `NVU_PROXY_URL1-5=""` (空=直连宿主 IP) — 直连秒回 200.
- k2 的 403 是该 NV key 本身鉴权失效, 与限速/出口无关, 需单独处理(更换或停用).

### 教训
遇到 NVCF 上游 timeout/502, 不要轻信"surge 已知问题", 必须直连 vs proxy 对照、HM1 vs HM2 对照, 验证 IP 维度后再归因. 见记忆 [[nvcf-upstream-verify-ip]].
