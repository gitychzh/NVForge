# R1521: HM2→HM1 — NOP (false trigger, zero post-restart ATEs, all params floor/optimal)

## 数据收集

- **容器状态**: nv_gw Up ~1h (healthy, started 2026-07-15T22:25:46Z), ms_gw Up 24h (healthy), logs_db Up 24h (healthy)
- **compose md5**: 9fb97661bf20dd1c41561af05395b516 (与R1517-R1520一致, 无变更)

## 6h 数据 (created_at >= NOW() - 6h)

| 指标 | 值 |
|------|-----|
| 总请求 | 70 |
| 200 OK | 48 (68.6% SR) |
| 失败 | 22 |
| zombie_empty_completion | 19 (86.4%) |
| all_tiers_exhausted | 3 (13.6%) |
| tier_attempts | 0 |
| fallback_occurred | 0 |
| ms_gw | 15/14 (93.3% SR) |

| 模型 | 请求 | OK | 失败 | SR% | avg_dur |
|------|------|-----|------|-----|---------|
| dsv4p_nv | 47 | 36 | 11 | 76.6% | 13280ms |
| glm5_2_nv | 23 | 12 | 11 | 52.2% | 9142ms |

## 每小时 SR

| 小时 | 总 | OK | 失败 | SR% |
|------|-----|-----|------|-----|
| 18:00 | 18 | 14 | 4 | 77.8% |
| 19:00 | 9 | 5 | 4 | 55.6% |
| 20:00 | 10 | 6 | 4 | 60.0% |
| 21:00 | 21 | 17 | 4 | 81.0% |
| 22:00 | 4 | 2 | 2 | 50.0% |
| 23:00 | 8 | 4 | 4 | 50.0% |

## 重启后数据 (created_at >= 2026-07-15T22:25:46Z)

| 指标 | 值 |
|------|-----|
| 总请求 | 10 |
| 200 OK | 6 (60.0% SR) |
| 失败 | 4 (全部 zombie_empty_completion) |
| ATE | 0 |
| tier_attempts | 0 |

| 模型 | 请求 | OK | 失败 | SR% | avg_dur |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 6 | 4 | 2 | 66.7% | 6496ms |
| dsv4p_nv | 4 | 2 | 2 | 50.0% | 6000ms |

## 日志分析

- **Zombie模式**: NV-ZOMBIE-EMPTY 主导 — finish_reason=stop 但 content_chars=12-48 <50, input_chars=223K+ (NVCF content-filter)
- **NV-ZOMBIE-ERROR-CHUNK**: 正确发送 timeout SSE chunk 给 openclaw 触发 fallback
- **NV-THINKING-TIMEOUT**: dsv4p_nv thinking 请求触发 extended timeout 66s
- **无 NV-TIER-FAIL / NV-CYCLE / NV-EMPTY / NV-MS-FB / NV-PEER-FB**: 尾部100行日志中无这些信号

## 当前关键参数 (全部 floor/optimal)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | =UPSTREAM_TIMEOUT (floor) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | adequate |
| TIER_COOLDOWN_S | 15 | floor (R1103) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal (R1031) |
| NVU_PEER_FB_SKIP_MODELS | (空) | 全部启用 peer-fb |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | =UPSTREAM_TIMEOUT |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | adequate |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |

## 判定: NOP

1. **Zombie 主导 (86.4%)**: 所有失败都是 zombie_empty_completion — NVCF content-filter 行为, 不可从 HM1 配置修复。Gateway 正确检测并发送 error chunk 给 openclaw fallback。
2. **零 ATE 重启后**: 3个 ATE 全部在重启前 (22:09/22:05/18:08/18:03)。重启后 0 ATE。
3. **零 tier_attempts**: 密钥池干净, 无 429 循环。
4. **ms_gw 健康**: 15/14 = 93.3% SR。
5. **全部参数 floor/optimal**: 无下调空间, 无上调需求。BUDGET=UPSTREAM_TIMEOUT 已达 floor。
6. **compose 无变更**: md5 与 R1517-R1520 一致。

**铁律: 只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2
