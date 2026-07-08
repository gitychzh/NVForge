# R927: HM2→HM1 — NOP (false trigger, all params at floor, 100% SR)

> **Trigger**: 2026-07-09 05:40 UTC — cron dispatch for commit `b3c46a5` (R926 NOP, opc2_uname)
> **Script output**: `"这是我提交的, 不触发"` — false trigger (HM2 self-commit)
> **Pattern**: Double-dispatch (symlink already →R926, R926 already committed)

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2), commit = `b3c46a5` (R926 NOP)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发
- 符号链接已指向 R926，R926 已提交并推送 — 双重派发模式
- R926 数据采集于 ~05:25 UTC，R927 数据采集于 ~05:40 UTC，仅差 15min

## 数据采集 (改前必有数据, 05:41 UTC)

### nv_gw 容器状态

- 容器名: `nv_gw` (cc-infra-nv_gw)
- 运行状态: healthy
- 日志: 安静，无 error/warn/traceback

### nv_gw 容器 env (key params)

| 参数 | 值 | 来源 |
|---|---|---|
| UPSTREAM_TIMEOUT | 64 | 历史 |
| TIER_TIMEOUT_BUDGET_S | 114 | 历史 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 地板 |
| NVU_EMPTY_200_FASTBREAK | 3 | R829 |
| KEY_COOLDOWN_S | 25 | 地板 |
| TIER_COOLDOWN_S | 25 | 地板 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 地板 |
| NVU_CONNECT_RESERVE_S | 0 | 地板 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 地板 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 禁用 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | = UPSTREAM, 无害 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | R919 |
| **KEY_AUTHFAIL_COOLDOWN_S** | **60** | **R922** ✅ |
| **NVU_PEER_FB_SKIP_MODELS** | **glm5_2_nv,dsv4p_nv** | **R923** ✅ |

### nv_requests DB (6h)

| 指标 | 值 |
|---|---|
| 总请求 | 57 |
| 成功 (200) | 57 |
| 失败 | 0 |
| **6h SR** | **100.0%** ✅ |
| 平均 duration | 12,835ms |
| 最大 duration | 120,515ms |
| 全部 nvcf_pexec | 57/57 |

### nv_requests 最近 10 条请求

| ts (UTC) | request_model | status | duration_ms | key_cycle_429s |
|---|---|---|---|---|
| 21:33:35 | glm5_2_nv | 200 | 2,764 | 0 |
| 21:33:30 | glm5_2_nv | 200 | 5,025 | 0 |
| 21:33:21 | glm5_2_nv | 200 | 5,908 | 0 |
| 21:03:21 | glm5_2_nv | 200 | 2,820 | 0 |
| 20:33:32 | glm5_2_nv | 200 | 3,746 | 0 |
| 20:33:28 | glm5_2_nv | 200 | 3,715 | 0 |
| 20:33:21 | glm5_2_nv | 200 | 3,698 | 0 |
| 20:04:08 | glm5_2_nv | 200 | 5,218 | 0 |
| 20:03:54 | glm5_2_nv | 200 | 12,893 | 0 |
| 20:03:50 | glm5_2_nv | 200 | 4,111 | 0 |

全部成功，延迟 2.8-12.9s，正常。**与 R925/R926 完全一致。**

### 错误分类 (6h)

| 指标 | 值 |
|---|---|
| 错误类型 | 0 条 |
| ATE | 0 |

### nv_tier_attempts (6h)

| Tier | Error Type | Count | Max ms |
|---|---|---|---|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52,849 |
| dsv4p_nv | empty_200 | 1 | — |

仅 2 次 minor tier 错误，无系统性故障。NVCFPexecTimeout max=52,849ms << UPSTREAM=64 → UPSTREAM 非绑定。**与 R925/R926 完全一致。**

### ms_gw 状态

| 指标 | 值 |
|---|---|
| 6h 请求 | 0 |
| 6h 错误 | 0 |
| ms_gw env | EMPTY_200_FASTBREAK=3, KEY_COOLDOWN=60, UPSTREAM=300, MIN_OUTBOUND=1.0 |

ms_gw 完全空闲，无优化空间。

## Decision: NOP

**Reasoning**:
1. **100.0% SR, 6h window** — 57/57 零失败，零 ATE，极佳链路健康度
2. **所有性能参数已在地板**:
   - UPSTREAM=64 → NVCFPexecTimeout max=52.8s, 11.2s buffer, 非绑定 ✓
   - FASTBREAK=1 (地板) — 1×64=64s << BUDGET=114, 50s fallback 余量 ✓
   - EMPTY_200=3 (R829 intentional) ✓
   - KEY_COOLDOWN=25, TIER_COOLDOWN=25 (地板) ✓
   - MIN_OUTBOUND=0, CONNECT_RESERVE=0, NV_INTEGRATE_KEY_COOLDOWN=0 (地板) ✓
   - FORCE_STREAM=0 (禁用) ✓
3. **防御性参数已补全**:
   - KEY_AUTHFAIL_COOLDOWN_S=60 (R922) ✓
   - NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (R923) ✓
   - FALLBACK_HEALTH_THRESHOLD=0.05 (R919) ✓
4. **Zero error/warn in container logs** ✓
5. **ms_gw idle** (0 requests), 无次级优化空间 ✓
6. **数据与 R925/R926 完全一致** — 相同 57/57 100% SR，相同 tier errors，相同 timestamps
7. **R923 部署后稳定运行 ~35min** — 无退化

**No optimization space**: 所有参数在地板或最优。零 ATE，零失败。HM1 比 HM2 更激进，符合优化方向。防御性参数已全。数据与 R925/R926 完全一致。

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
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 (R922) |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv (R923) |

## ⏳ 轮到HM1优化HM2
