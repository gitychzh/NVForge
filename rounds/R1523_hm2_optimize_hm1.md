# R1523: HM2→HM1 — NOP (false trigger, zero post-restart ATEs, zombie-only, all params floor/optimal)

> **轮次**: R1523 | **日期**: 2026-07-16 08:00 UTC | **操作者**: HM2 (opc2_uname)
> **决策**: ⏸️ NOP — 零 post-restart ATE, 所有失败均为 zombie_empty_completion (code-level, NVCF content-filter), 所有参数 floor/optimal
> **铁律**: 只改HM1不改HM2

## 数据收集

### 容器状态
- **容器**: nv_gw (healthy), Up ~9.5h (无近期重启)
- **StartedAt**: 2026-07-15T22:25:46Z (post-R1521 deploy)
- **Compose md5**: 9fb97661bf20dd1c41561af05395b516 (stable, 与 R1521/R1522 一致)
- **DB**: logs_db (healthy), ms_gw (healthy)

### 6h 窗口 (2026-07-16 ~02:00–08:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 70 |
| 成功 (200) | 48 |
| 失败 (502) | 22 |
| **成功率** | **68.6%** |
| tier_attempts | 0 (clean key pool) |
| ms_gw | 15/14 OK (93.3%) |

### Pre/Post Restart 分段

| 时期 | 总请求 | 成功 | 失败 | SR |
|------|--------|------|------|-----|
| pre-restart (<22:25Z) | 60 | 42 | 18 | 70.0% |
| post-restart (>=22:25Z) | 10 | 6 | 4 | 60.0% |

### 错误分布 (6h)

| 错误类型 | 模型 | 数量 | 平均延迟 |
|---------|------|------|---------|
| zombie_empty_completion | glm5_2_nv | 10 | 7,611ms |
| zombie_empty_completion | dsv4p_nv | 9 | 6,203ms |
| all_tiers_exhausted | dsv4p_nv | 2 | 33,760ms |
| all_tiers_exhausted | glm5_2_nv | 1 | 8,411ms |

### ATE 分析

4 个 ATE 全部为 **pre-restart** (容器重启于 22:25:46Z):
- dsv4p_nv @ 18:03:36 (35,713ms, status=200 — ms_gw rescued)
- dsv4p_nv @ 18:08:01 (61,177ms)
- glm5_2_nv @ 22:05:35 (8,411ms)
- dsv4p_nv @ 22:09:55 (6,343ms)

**Post-restart: 0 ATE** — 容器重启后零 ATE。仅 4 个 zombie (NVCF content-filter: input>223K, output<50 chars, finish_reason=stop)。

### Zombie 详情 (post-restart)

| 时间 | 模型 | 延迟 | input_chars | output_tokens |
|------|------|------|-------------|---------------|
| 23:03:37 | glm5_2_nv | 3,294ms | 223,384 | 6 |
| 23:05:56 | dsv4p_nv | 4,213ms | 223,401 | 0 |
| 23:33:31 | glm5_2_nv | 4,676ms | 223,384 | 6 |
| 23:35:52 | dsv4p_nv | 5,986ms | 223,401 | 0 |

全部为 NVCF content-filter 触发: 大输入(>223K chars) → finish_reason=stop + content_chars<50。NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK → openclaw fallback。不可配置修复。

### 日志 (nv_gw --tail 100)

```
NV-INTEGRATE-SUCCESS: glm5_2_nv first-attempt 成功 (×6)
NV-ZOMBIE-EMPTY (×4): glm5_2_nv/dsv4p_nv content_chars<50, input>223K
NV-THINKING-TIMEOUT: dsv4p_nv thinking requests → extended timeout 66s
```

零 ERROR/WARN, 零 504, 零 NVCFPexecTimeout, 零 empty_200 (非 zombie), 全部 first-attempt 成功。

### 参数快照 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| KEY_COOLDOWN_S | 25 | stable |
| TIER_COOLDOWN_S | 15 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | aligned |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | 禁用 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | glm5_2_nv | optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (UPSTREAM_TIMEOUT) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (空) | all models active |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | optimal |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | optimal |

## 候选参数评估

| 参数 | 当前值 | 候选 | 分析 | 结论 |
|------|--------|------|------|------|
| UPSTREAM_TIMEOUT | 66 | — | NVCFPexecTimeout max binding, 已 optimal | ❌ |
| TIER_TIMEOUT_BUDGET_S | 205 | — | 零 post-restart ATE, 无压缩必要 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 2 | — | 零 non-zombie empty_200, 无调整依据 | ❌ |
| TIER_COOLDOWN_S | 15 | — | 零 tier_attempts, 零 ATE, 无调整依据 | ❌ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | — | ms_gw 93.3% SR, 120s 足够 | ❌ |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | — | BUDGET floor pattern, 零 post-restart ATE | ❌ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | — | floor | ❌ |
| NVU_CONNECT_RESERVE_S | 0 | — | floor | ❌ |

## 决策

**⏸️ NOP** — 所有参数已达 floor/optimal, 零 post-restart ATE, 失败全部为 zombie_empty_completion (code-level, NVCF content-filter 对大输入返回 stop+12chars, 不可配置修复). Compose md5 稳定 (9fb97661), 无漂移. 20 consecutive NOPs since R1503 (false trigger streak).
## ⏳ 轮到HM1优化HM2
