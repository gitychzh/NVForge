# R964: HM2→HM1 — NOP (double-dispatch false trigger, 27/27 100% 6h SR, all params at floor/optimal)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- R963 已由 pre-run script 提交，symlink 已指向 R963

## 2. 数据采集

### 2.1 容器状态
```
nv_gw     Up 33 minutes (healthy)
logs_db   Up 4 days (healthy)
ms_gw     Up 13 hours (healthy) — 0 requests in 12h
```

### 2.2 Docker Logs (最近100行)
```
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
```
零 error/warn/exception — 完全健康。

### 2.3 容器 Env (关键参数)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | R742 |
| TIER_TIMEOUT_BUDGET_S | 114 | R737 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor R638 |
| KEY_COOLDOWN_S | 25 | R162 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 |
| TIER_COOLDOWN_S | 25 | R492 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 |
| NVU_CONNECT_RESERVE_S | 0 | floor R657 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | R543 |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | R749/R755 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor R961 |
| NVU_EMPTY_200_FASTBREAK | 3 | R829 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | R829 |
| NV_INTEGRATE_MODELS | "" | R693 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor R631 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | R923 |

Env 与 compose 一致，无漂移。

### 2.4 DB 6h Regime
```
total | ok | fail | avg_lat_ms | max_ms | req_with_429 | total_429s
   27 | 27 |    0 |    43811.7 | 173278 |            6 |         11
```

- **27/27 100.0% SR** — 零错误，零 ATE
- 全部 glm5_2_nv，全部 nvcf_pexec 路径
- avg latency 43,811ms (thinking-heavy requests)
- 6 个请求有 key_cycle_429s (总计 11 次)，全部 status=200 — 正常 key rotation
- 0 个失败请求 (24h 内仅 1 个 ATE，server-side)

### 2.5 Per-model Breakdown (6h)
```
request_model | total | ok | fail | avg_lat_ms | max_ms
glm5_2_nv     |    27 | 27 |    0 |    43811.7 | 173278
```

### 2.6 Tier Attempts (6h, 仅失败)
```
tier       | error_type                    | cnt | avg_elapsed_ms | max_elapsed_ms
glm5_2_nv  | 504_nv_gateway_timeout        |   4 |                |
glm5_2_nv  | NVCFPexecTimeout              |   4 |        51537.5 |          51796
glm5_2_nv  | empty_200                     |   2 |                |
glm5_2_nv  | budget_exhausted_after_connect|   1 |        51838.0 |          51838
```
- NVCFPexecTimeout 分布在 k0(1), k1(1), k4(2) — 函数级，非 key 级
- NVCFPexecTimeout max=51,796ms << UPSTREAM=64 (gap=12.2s) — **非绑定**
- 所有 tier_attempts 最终都通过 fallback 到 dsv4p_nv 成功 (27/27 OK)

### 2.7 Fallback 统计 (6h)
```
fallback_occurred | cnt | avg_ms
f                 |  22 | 21781.3
t                 |   5 | 140745.6
```
- 5 of 27 (18.5%) 触发 fallback glm5_2→dsv4p，全部成功
- Fallback 后 avg duration 140s (双 tier 完成)

### 2.8 1h Snapshot
```
total | ok | fail | avg_ms
    2 |  2 |    0 | 92906.0
```
1h 内 2/2 OK，零错误。

## 3. 决策分析

### 3.1 参数状态
所有参数均处于最优值或 floor，无优化空间：
- UPSTREAM_TIMEOUT=64: NVCFPexecTimeout max=51.8s << 64 (gap=12.2s)，非绑定，无需调整
- TIER_TIMEOUT_BUDGET_S=114: 双 tier 预算充足 (64+64=128，但实际仅单个 tier 频繁 fallback)，max success 173s 但 5 个 fallback 全成功
- NVU_PEXEC_TIMEOUT_FASTBREAK=1: floor，NVCFPexecTimeout 为函数级非 key 级，第 2 key 无意义
- MIN_OUTBOUND_INTERVAL_S=0: floor
- NVU_CONNECT_RESERVE_S=0: floor
- NV_INTEGRATE_KEY_COOLDOWN_S=0: floor，integrate 无模型
- NVU_EMPTY_200_FASTBREAK=3: 3 次连发才 fastbreak，保守
- FALLBACK_HEALTH_THRESHOLD=0.05: 仅排除 0% 成功率 function

### 3.2 错误分析
- 6h: 0 failed requests (0 ATE, 0 errors)
- 24h: 仅 1 ATE (server-side all_tiers_exhausted)
- 零 config-fixable 错误

### 3.3 决策: NOP
- 所有参数已达最优值或 floor
- 零错误，零 ATE，100% SR
- NVCFPexecTimeout 非绑定 (gap=12.2s)
- FPexecTimeout 为函数级，非 key 级 — FASTBREAK=1 正确
- ms_gw 无流量 — 无 secondary optimization
- 等待信号: NVCF function 健康度变化、新 ATE 模式、或流量恢复

## 4. 历史趋势
- R961: FASTBREAK 2→1 (floor)
- R962: NOP (29/29 100% SR)
- R963: NOP (27/27 100% SR)
- R964: NOP (27/27 100% SR) — 连续 3 轮 100% SR，零变更

## ⏳ 轮到HM1优化HM2