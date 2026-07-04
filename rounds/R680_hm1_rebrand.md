# R680 — HM1 框架重构: 命名消歧 (彻底版)

## 背景
cc2 红队审查 6 雷 (cc_postgres默认值/NO_PROXY/provider key牵连6处/代码硬编码容器名/HM2 ms_uni41002不对称/legacy容器依赖ms_uni41001), 全部纳入缓解。
三 agent (hermes/openclaw/opencode) 是独立 APP 自有链路, CC 作为基础设施方代为调整命名, 不改模型选择逻辑。

## 命名映射表

### 容器 / compose service / image
| 旧 | 新 |
|---|---|
| nv_40006_uni | nv_gw |
| ms_uni40007 | ms_gw |
| cc_postgres | logs_db |
| ms_uni41001 | legacy_ms_litellm |
| auth_to_api_40000 | legacy_dispatch |
| auth_to_api_40001 | legacy_cc_1 |
| auth_to_api_40002 | legacy_codex |
| auth_to_api_40003 | legacy_passthrough |
| auth_to_api_40005 | legacy_cc_2 |

### 源码目录 (/opt/cc-infra/proxy/)
| 旧 | 新 |
|---|---|
| nv-uni | nv-gw |
| ms-uni | ms-gw |
| cc-proxy | legacy-cc |
| dispatcher | legacy-dispatch |
| codex-proxy | legacy-codex |
| passthrough-proxy | legacy-passthrough |
| ms-gateway | legacy-ms-gateway |
| llm-glm51 | legacy-llm-glm51 |
| hm-proxy (空壳) | 删除 |

### provider key (三 agent 统一)
| 旧 | 新 |
|---|---|
| nv_cus (hermes HM1) | nv_gw |
| litellm-nv-hm (hermes HM2, 待 HM2 改) | nv_gw |
| ms_cus (openclaw/opencode) | ms_gw |

### api_key token (网关鉴权)
| 旧 | 新 |
|---|---|
| nv-local | nv-gw-token |
| ms-local | ms-gw-token |

### logs 目录
| 旧 | 新 |
|---|---|
| nv_40006_uni | nv_gw (含 rr_counter.json 合并) |
| ms_uni40007 | ms_gw |
| ms-gateway | legacy-ms-gateway |
| proxy40001..40005 | legacy-40001..40005 |
| proxy40006 | legacy-40006 |

## 联动点 (cc2 红队 6 雷缓解)
1. **db.py:41 默认值** `cc_postgres` → `logs_db` (compose NVU_DB_HOST 显式注入 + 代码默认值同改)
2. **NO_PROXY** 顶层更新全部容器名
3. **provider key** 逐 agent 改 + .bak.R680 + JSON 合法性校验 + 三 agent 重启验证
4. **代码硬编码容器名** sed 全替换 (nv-gw 37处注释 + ms-gw X-MS-Proxy header 2处 + error_mapping 错误消息)
5. **HM2 ms_uni41002** HM2 步骤 docker rm 孤立容器
6. **logs 目录** compose volumes 同步 + 旧数据合并 (cp -rn) 不删数据
7. **NVU_GATEWAY_API_KEY 隐藏契约** (cc2 补充第7雷): compose 未显式设 env, 代码默认 nv-local; 改 agent config token 后 401. 缓解: compose 加 NVU_GATEWAY_API_KEY: nv-gw-token + config.py 默认值同改

## agent config 对齐 (两机模型清单)
- opencode: kimi_nv only (两机一致)
- openclaw: dsv4p_nv + glm5_2_nv (去 glm5_1_nv, glm5.1 EOL; HM1 此轮对齐 HM2)
- hermes: dsv4p_nv primary + glm5_2_ms fallback (两机一致, 不动)

## HM1 验证
- 容器: nv_gw/ms_gw/logs_db + 5 legacy 全 healthy
- 40006/40007 health OK, 端口发布正确
- /v1/models 带 nv-gw-token 返回正常
- DB: nv_gw → logs_db 连接 OK, nv_requests 11781 条
- 三 agent 进程: hermes/openclaw(opencode-web.service) 全在跑, openclaw 18789 health OK, opencode 4096 OK

## 不改的 (铁律)
- 端口号 40006/40007/40000-40005/41001 不变
- NV/MS 真实上游 key 不变
- agent 进程名不变
- agent 模型选择逻辑/思考强度/tool_calls 不变
- pgdata volume 名 cc_pgdata 不改 (数据不丢)
- DB 库名 hermes_logs / 表名 nv_requests/nv_tier_attempts 不改

## 下一步
HM2 同步骤 + docker rm ms_uni41002 孤立容器 + hermes provider litellm-nv-hm→nv_gw。

## ⏳ 轮到 HM2 (CC 直改, rule-cancelled R569)
