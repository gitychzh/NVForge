# HM2 Optimize HM1 — Round R923

## 触发

- **cron 脚本输出**: `"这是我提交的, 不触发"` (R922 was HM2→HM1, HM1 commit from `opc2_uname`)
- **最新 commit**: `7831613` (R922: fix anchor → rounds/R922_hm2_optimize_hm1.md)
- **判定**: **HM2 turn** — HM1 commit `7831613` 来自 HM2 的 `opc2_uname`, 触发 HM2→HM1 优化

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
| NVU_FORCE_STREAM_UPGRADE | 0 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| **NVU_PEER_FB_SKIP_MODELS** | **缺失 (pre-R923)** |

### nv_gw 容器状态

- 容器名: `nv_gw` (cc-infra-nv_gw)
- 运行状态: healthy, 启动后 8min
- 日志: 安静，仅正常请求成功日志，无 error/warn/crash
- fallback_chain: ['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']
- 最近请求: glm5_2_nv 直连成功, 3.2-4.7s 延迟, k1/k2/k5 轮转正常

### nv_requests DB (6h)

| 指标 | 值 |
|---|---|
| 总请求 | 59 |
| 成功 (200) | 59 |
| 失败 | 0 |
| **6h SR** | **100.0%** ✅ |
| 平均 duration | 15,451ms |
| 最大 duration | 120,515ms |
| dsv4p_nv | 5/5 = 100.0%, avg=26,603ms |
| glm5_2_nv | 52/52 = 100.0%, avg=11,247ms |
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

| ts | rid | request_model | mapped_model | tier_model | fallback | status | duration_ms |
|---|---|---|---|---|---|---|---|
| 20:04:08 | 94da8425 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 5,218 |
| 20:03:54 | cb25f1ee | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 12,893 |
| 20:03:50 | 3f13c047 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 4,111 |
| 20:03:41 | 340f8389 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 9,026 |
| 20:03:21 | 2e52b163 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 16,245 |
| 19:33:49 | 88ced2e3 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 3,004 |
| 19:33:44 | e949869a | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 4,851 |
| 19:33:36 | fd908773 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 7,197 |
| 19:33:27 | 7c9e4286 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 8,496 |
| 19:33:21 | e935a100 | glm5_2_nv | glm5_2_nv | glm5_2_nv | f | 200 | 3,227 |

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

### 24h 错误全景

| error_type | cnt |
|---|---|
| all_tiers_exhausted | 4 (全部 R919 前历史数据) |

### ms_gw 状态

- 6h 请求: 0 (完全空闲)
- 无错误

### HM2 对比

| 参数 | HM1 | HM2 |
|---|---|---|
| UPSTREAM_TIMEOUT | 64 | 66 |
| TIER_TIMEOUT_BUDGET_S | 114 | 180 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 3 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 150 |
| **NVU_PEER_FB_SKIP_MODELS** | **缺失** | **glm5_2_nv,dsv4p_nv** |
| NV_INTEGRATE_MODELS | (空) | glm5_2_nv |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 缺失 |

## 优化决定: 新增 NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv

**变更**: 在 HM1 nv_gw 的 docker-compose.yml 中新增 `NVU_PEER_FB_SKIP_MODELS: "glm5_2_nv,dsv4p_nv"`

**理由**:
1. **HM1 缺失此参数**，与 HM2 不对称。HM2 已显式设置 `glm5_2_nv,dsv4p_nv`。
2. **防御性参数**: 当 `glm5_2_nv` 或 `dsv4p_nv` 本地 ATE 时，禁止向 HM2 peer fallback 同模型（peer 大概率也已失败），省去一次无效跨机 fallback 尝试。
3. **正常路径零影响**: 当前 6h SR = 100.0%，0 ATE，0 peer fallback 触发。此参数仅在 ATE 场景才生效，正常路径完全不入。
4. **kimi_nv 不在 skip 列表中** — HM1 当前不使用 kimi_nv（0 请求），预留未来扩展。
5. **所有性能参数已在地板**: FASTBREAK=1, KEY_COOLDOWN=25, TIER_COOLDOWN=25, MIN_OUTBOUND=0, NV_INTEGRATE_KEY_COOLDOWN=0, CONNECT_RESERVE=0 — 仅剩防御性参数可补。
6. **少改多轮**: 本轮仅加一个防御性参数，不影响正常路径。

**验证**:
- 部署后 container 重启正常
- `docker exec nv_gw env | grep NVU_PEER_FB` → `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv` ✅
- `/health` → `{"status": "ok", ...}` ✅

**部署**: `cd /opt/cc-infra && docker compose up -d nv_gw` (env-only change, 无需 rebuild)

## 配置快照 (HM1 nv_gw 当前)

| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 (R919) |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NV_INTEGRATE_MODELS | (空) |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 (R922) |
| **NVU_PEER_FB_SKIP_MODELS** | **glm5_2_nv,dsv4p_nv (R923)** |

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记