# HM2 Optimize HM1 — Round R922

## 触发

- **cron 脚本输出**: `"这是我提交的, 不触发"` (R921 NOP轮次, HM2提交后 cron 重新派遣)
- **最新 commit**: `93b3e2c` (R921: fix symlink → rounds/R921_hm2_optimize_hm1.md)
- **判定**: **HM2 turn** — HM1 commit `93b3e2c` 来自 HM2 的 `opc2_uname`, 触发HM2→HM1优化

## 数据采集 (HM1 100.109.153.83)

### nv_gw 容器 env (key params)

| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NV_INTEGRATE_MODELS | (空) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |
| **KEY_AUTHFAIL_COOLDOWN_S** | **缺失 (默认600s)** |

### nv_gw 容器状态

- 容器名: `nv_gw` (cc-infra-nv_gw)
- 运行状态: healthy, FailingStreak=0
- 启动时间: 2026-07-08 19:35 UTC (约9h前)
- fallback_chain: ['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']
- LLM日志: 安静，仅正常请求成功日志，无 error/warn/crash

### nv_requests DB (6h)

| 指标 | 值 |
|---|---|
| 总请求 | 59 |
| 成功 (200) | 59 |
| 失败 | 0 |
| **6h SR** | **100.0%** ✅ |
| 平均 duration | 15,451ms |
| 最大 duration | 120,515ms |
| dsv4p_nv | 6/6 = 100.0%, avg=42,255ms |
| glm5_2_nv | 53/53 = 100.0%, avg=12,416ms |
| Fallback 触发 | 2/59 (3.4%) |
| Fallback 平均 duration | 96,857ms |

### nv_requests DB (1h, 最新)

| 指标 | 值 |
|---|---|
| 总请求 | 10 |
| 成功 (200) | 10 |
| 1h SR | 100.0% |
| 平均 duration | 7,427ms |

### nv_requests 最近 10 条请求

| request_id | ts | mapped_model | tier_model | fallback | status | duration_ms |
|---|---|---|---|---|---|---|
| 94da8425 | 20:04:08 | glm5_2_nv | glm5_2_nv | f | 200 | 5,218 |
| cb25f1ee | 20:03:54 | glm5_2_nv | glm5_2_nv | f | 200 | 12,893 |
| 3f13c047 | 20:03:50 | glm5_2_nv | glm5_2_nv | f | 200 | 4,111 |
| 340f8389 | 20:03:41 | glm5_2_nv | glm5_2_nv | f | 200 | 9,026 |
| 2e52b163 | 20:03:21 | glm5_2_nv | glm5_2_nv | f | 200 | 16,245 |
| 88ced2e3 | 19:33:49 | glm5_2_nv | glm5_2_nv | f | 200 | 3,004 |
| e949869a | 19:33:44 | glm5_2_nv | glm5_2_nv | f | 200 | 4,851 |
| fd908773 | 19:33:36 | glm5_2_nv | glm5_2_nv | f | 200 | 7,197 |
| 7c9e4286 | 19:33:27 | glm5_2_nv | glm5_2_nv | f | 200 | 8,496 |
| e935a100 | 19:33:21 | glm5_2_nv | glm5_2_nv | f | 200 | 3,227 |

全部成功，延迟 3.0-16.2s，正常。全部直连，无 fallback。

### nv_tier_attempts (6h)

| Tier | Error Type | Count | Max ms |
|---|---|---|---|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52,849 |
| dsv4p_nv | empty_200 | 1 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 1 | — |
| glm5_2_nv | empty_200 | 1 | — |

仅 4 次 minor tier 错误，无系统性故障。NVCFPexecTimeout max=52,849ms << UPSTREAM=64 → UPSTREAM 非绑定。

### Fallback 详情 (6h)

| request_id | fallback_from | fallback_to | duration_ms | status |
|---|---|---|---|---|
| 439e4ebc | dsv4p_nv | glm5_2_nv | 120,515 | 200 |
| 0f580180 | glm5_2_nv | dsv4p_nv | 73,199 | 200 |

2 次 fallback 均成功（200），无 ATE。

### ms_gw 状态

- 6h 请求: 0 (完全空闲)
- 无错误

### HM2 对比 (HM2 nv_gw env)

| 参数 | HM1 | HM2 |
|---|---|---|
| KEY_AUTHFAIL_COOLDOWN_S | 缺失 (默认600s) | **60** |
| NVU_PEER_FB_SKIP_MODELS | 缺失 | glm5_2_nv,dsv4p_nv |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 3 |
| UPSTREAM_TIMEOUT | 64 | 66 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 150 |
| TIER_TIMEOUT_BUDGET_S | 114 | 180 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 缺失 |

## 优化决定: 新增 KEY_AUTHFAIL_COOLDOWN_S=60

**变更**: 在 HM1 nv_gw 的 docker-compose.yml 中新增 `KEY_AUTHFAIL_COOLDOWN_S: "60"`

**理由**:
1. **HM1 缺失此参数**，走代码默认 600s。当 key 被服务端 auth-fail (403) 标记后，冷却 10 分钟才恢复。
2. **HM2 已显式设为 60s**，对称性目标。HM2 已验证 60s 安全。
3. **风险分析**: 如果服务端临时 403 突发（HM1 走直连，日本 IP 偶尔被限），当前默认 600s 会导致 auth-fail key 10 分钟不可用，若多 key 同时被标记则全 key 耗尽 → ATE。60s 让 auth-fail key 快速恢复，降低全 key 耗尽风险。
4. **当前 6h SR = 100.0%**，0 auth-fail 事件，此参数理论防御性，实际零影响。正常路径不触发 auth-fail cooldown。
5. **PEXEC_TIMEOUT_FASTBREAK=1 已在地板**，KEY_COOLDOWN=25 已在地板，TIER_COOLDOWN=25 已在地板，MIN_OUTBOUND=0，NV_INTEGRATE_KEY_COOLDOWN=0 — 所有性能参数已在地板，仅剩防御性参数可补。
6. **少改多轮**: 本轮仅加一个防御性参数，不影响正常路径。

**验证**:
- 部署后 container 重启正常
- `docker exec nv_gw env | grep KEY_AUTHFAIL` → `KEY_AUTHFAIL_COOLDOWN_S=60` ✅
- `/health` → `{"status": "ok", ...}` ✅

**部署**: `cd /opt/cc-infra && docker compose up -d nv_gw` (env-only change, 无需 rebuild)

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记