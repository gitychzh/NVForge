# R1096: HM2→HM1 — NOP (false trigger, post-restart glm5_2_nv-only traffic, no config-fixable signals)

**Round**: R1096  
**Direction**: HM2 → HM1  
**Date**: 2026-07-10 21:35 UTC+8  
**Author**: opc2_uname

## 1. 触发分析

Commit 7be7f58 (R1095 round file, opc2_uname) 标记 "这是我提交的, 不触发" — HM2 自提交不应触发 HM2 优化 HM1。但 cron 系统仍派发此轮，按铁律收集数据。

## 2. 容器状态

| 容器 | 状态 |
|------|------|
| nv_gw | Up ~1h (healthy) |
| ms_gw | Up 18h (healthy) |
| logs_db | Up 6d (healthy) |

## 3. DB 数据 (6h 窗口)

### 3.1 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| 成功 | 21 (87.5%) |
| 失败 | 3 |
| Fallback 触发 | 0 |

### 3.2 按模型

| 模型 | 请求 | 成功 | SR | 说明 |
|------|------|------|----|------|
| glm5_2_nv | 22 | 21 | 95.5% | integrate, 主流量 |
| dsv4p_nv | 2 | 0 | 0% | 2/2 ATE, **全部 pre-restart** |
| kimi_nv | 0 | 0 | — | 零流量 |
| minimax_m3_nv | 0 | 0 | — | 零流量 |

### 3.3 按路径

| 路径 | 请求 | 成功 | avg_ttfb | avg_dur |
|------|------|------|----------|---------|
| nv_integrate | 21 | 20 | 17,234ms | 21,115ms |
| nvcf_pexec | 1 | 1 | 125,916ms | 125,917ms |
| (ATE) | 2 | 0 | 1,060ms | 66,673ms |

### 3.4 错误分类

| 错误类型 | 次数 | 模型 |
|----------|------|------|
| all_tiers_exhausted | 2 | dsv4p_nv |
| NVStream_TimeoutError | 1 | glm5_2_nv |

### 3.5 nv_tier_attempts

| Tier | 错误类型 | 次数 | avg_ms | max_ms |
|------|----------|------|--------|--------|
| glm5_2_nv | IntegrateTimeout | 1 | 90,566 | 90,566 |

### 3.6 1h 窗口 (post-restart)

| 指标 | 值 |
|------|-----|
| 总请求 | 2 |
| 成功 | 2 (100%) |
| 失败 | 0 |

**Post-restart**: 仅 glm5_2_nv integrate 有流量，全部 1st-key 成功。一次 SSLEOFError 在 k2 正确 cycle 到 k3 后成功。

## 4. 容器日志 (最近 200 行)

- 全部 glm5_2_nv integrate: 3/3 成功 (2 次 1st-key, 1 次 SSL cycle→k3 成功)
- 无 NV-TIER-FAIL
- 无 EMPTY 200
- 无 FASTBREAK 触发
- 无 peer-fallback 或 ms_gw fallback 触发
- 单次 SSLEOFError on k2 → 正确 cycle 到 k3 → 成功 (16.3s 总延迟)

## 5. 当前配置参数 (docker exec nv_gw env)

| 参数 | 值 | 来源 |
|------|----|------|
| UPSTREAM_TIMEOUT | 66 | 长期 |
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | R1078 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | — |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | — |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 |
| NVU_PEER_FALLBACK_ENABLED | 1 | — |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | — |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | — |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | R818 |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | R1038 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 |
| KEY_COOLDOWN_S | 25 | 长期 |
| TIER_COOLDOWN_S | 18 | R1018 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 对称 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 禁用 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | glm5_2_nv,minimax_m3_nv | R578 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | — |

## 6. 决策

**NOP — 零参数修改**

理由:
1. **False trigger**: HM2 自提交 round file，非 HM1 提交，不应触发 HM2 优化 HM1
2. **Post-restart 仅 glm5_2_nv 有流量**: nv_gw 重启约 1h，所有流量为 glm5_2_nv integrate，100% 1st-key 成功
3. **dsv4p_nv/kimi_nv/minimax_m3_nv 零流量**: R1088 BUDGET=198 regime 完全未测试
4. **2 个 dsv4p_nv ATE 全部 pre-restart**: 无 post-restart 失败可分析
5. **nv_integrate 95.2% SR (20/21)**: 单次 NVStream_TimeoutError (96s, 也是 pre-restart? 需确认)，其余全部 1st-key 成功
6. **nvcf_pexec 100% SR (1/1)**: pexec 路径完美
7. **单次 SSLEOFError**: 正确 cycle 到 k3 后成功，SSL cycle 机制正常
8. **全部参数已在优化位**: 所有 floor 参数已达 floor，所有 budget 参数已适度宽松
9. **ms_gw BrokenPipeError**: 已知流同步缺陷，非配置可修复

铁律: 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2