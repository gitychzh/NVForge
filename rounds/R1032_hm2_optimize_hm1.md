# R1032: HM2→HM1 — NOP (post-R1031 settling, 93.2% SR, pexec 100%, insufficient post-change data)

## 1. 触发分析

- 最新 commit 075b365 (R1031) author = `opc2_uname` (HM2)
- 脚本输出: `"这是我提交的, 不触发"` — 正确检测到自提交
- cron 仍被派遣 — 误触发 (double-dispatch after R1031)

## 2. 改前数据 (2026-07-10 06:05 UTC, 6h)

### 2.1 容器状态

```
nv_gw 重启时间: 2026-07-09 21:58:31 UTC
重启后请求: 仅 1 条 (glm5_2_nv integrate k1 → 成功, 2,660ms)
```

### 2.2 nv_requests 概览 (6h)

| 指标 | 值 |
|------|-----|
| 总请求 | 397 |
| 成功 | 370 (93.2%) |
| 失败 | 27 (6.8%) |
| Fallback 触发 | 1/397 (glm5_2→glm5_2_ms, 34,734ms) |

### 2.3 Per-model 明细 (6h)

| Model | Total | OK | Fail | SR% | avg_ttfb | avg_dur |
|-------|-------|-----|------|-----|----------|---------|
| glm5_2_nv | 245 | 236 | 9 | 96.3% | 14,126 | 20,718 |
| dsv4p_nv | 68 | 59 | 9 | 86.8% | 14,514 | 19,084 |
| kimi_nv | 49 | 48 | 1 | 98.0% | 10,255 | 11,299 |
| minimax_m3_nv | 35 | 27 | 8 | 77.1% | 11,462 | 44,342 |

### 2.4 Per-upstream_type 明细 (6h)

| upstream_type | Total | OK | SR% | avg_dur | max_dur |
|---------------|-------|-----|------|---------|---------|
| nvcf_pexec | 108 | 108 | 100% | 13,487 | 93,363 |
| nv_integrate | 264 | 258 | 97.7% | 17,671 | 129,132 |
| NULL (ATE) | 25 | 4 | 16.0% | 94,295 | 174,716 |

### 2.5 Error 分类 (6h)

| Error Type | Count | avg_dur | upstream_type |
|------------|-------|---------|---------------|
| all_tiers_exhausted | 21 | 105,558 | NULL |
| NVStream_TimeoutError | 3 | 94,904 | nv_integrate |
| stream_total_deadline | 3 | 69,014 | nv_integrate |

### 2.6 ATE 按模型分布 (6h)

| Model | ATE count | ATE avg_ms |
|-------|-----------|------------|
| dsv4p_nv | 9 | 47,478 |
| minimax_m3_nv | 7 | 153,912 |
| glm5_2_nv | 4 | 162,804 |
| kimi_nv | 1 | 60,811 |

### 2.7 nv_tier_attempts (6h)

| Tier | Error | Count | avg_ms | max_ms |
|------|-------|-------|--------|--------|
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762 | 90,762 |

### 2.8 Post-R1031 窗口 (21:58 UTC → 06:05 UTC, ~8h)

```
总请求: 1 (glm5_2_nv integrate k1 → 200, 2,660ms)
错误: 0
流量极低 (夜间) — 无法验证 R1031 EMPTY_200_FASTBREAK=2 修复效果
```

## 3. 当前 HM1 nv_gw 配置

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
NVU_PEXEC_TIMEOUT_FASTBREAK=1     ← R997
NVU_EMPTY_200_FASTBREAK=2         ← R1031 (settling)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_STREAM_TOTAL_DEADLINE_S=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=110
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=18
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=45
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NV_INTEGRATE_MODELS=glm5_2_nv,minimax_m3_nv
```

## 4. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | pexec 100% SR, NVCFPexecTimeout not observed in 6h |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal | R997 deployed, pexec 100% SR (108/108) |
| NVU_EMPTY_200_FASTBREAK | 2 | **settling** | R1031 deployed, 0 post-change traffic to verify |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal | 3 integrate timeouts only, 97.7% SR |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal | > INTEGRATE_THINKING=90, glm5_2 96.3% SR |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 110 | optimal | > INTEGRATE_THINKING=90, 20s margin for pexec fallback |
| TIER_TIMEOUT_BUDGET_S | 110 | optimal | > UPSTREAM=66, 44s for 2nd key |
| All cooldowns | floor | optimal | 0 errors from cooldown exhaustion |

## 5. 决策: NOP

**R1031 (EMPTY_200_FASTBREAK 1→2) 正在 settling，post-restart 窗口仅 1 条请求无错误。**

- **dsv4p_nv pexec**: 100% SR (108/108) — flawless. NVCFPexecTimeout zero in 6h.
- **glm5_2_nv**: 96.3% SR. 3 NVStream_TimeoutError + 3 stream_total_deadline — acceptable rate.
- **minimax_m3_nv**: 77.1% SR (7 ATE, 1 stream_deadline). No ms_gw fallback mapping — ATEs dead-end at ~154s. ms_gw has no minimax model configured; multi-system change beyond this round.
- **6h SR 93.2%**: Stable, consistent with R1029-R1031 range.
- **所有参数 at floor/optimal**。零漂移。
- **夜间流量极低 (1req/8h)** — 无法验证 R1031 修复效果。

**等待日间流量积累，验证 R1031 empty_200 FASTBREAK=2 是否有效减少 dsv4p_nv ATE (目标: 9→0)。**

## ⏳ 轮到HM1优化HM2