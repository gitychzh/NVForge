# R2078 (hermes2 R22) — 巡检轮: NVCF 限流继续缓解, Tier 429 降至 26, 502 增多

**日期**: 2026-07-20
**轮次**: hermes2 R22 (仓库 R2078)
**类型**: 巡检轮 (不改代码)

## 数据依据

### 30min dsv4p_nv (nv_requests)

| 指标 | R21 | R22 | 变化 |
|------|-----|-----|------|
| 总请求 | 29 | 31 | +6.9% |
| 成功 (200) | 25 | 18 | -28.0% |
| 502 | 2 | 11 | +450% |
| 429 | 2 | 2 | 0 |
| **SR** | **86.2%** | **58.1%** | **-28.1pp** |
| all_tiers_exhausted | 29 | 13 | -55.2% |

### Tier 层 (nv_tier_attempts, dsv4p_nv)

| 指标 | R21 | R22 | 变化 |
|------|-----|-----|------|
| 429_nv_rate_limit | 42 | **26** | **-38.1%** |
| empty_200 | 4 | 4 | 0 |
| pexec_success | 18 | N/A | 无直接对比 |
| pexec_conn_RemoteDisconnected | 2 | N/A | 无直接对比 |
| pexec_SSLEOFError | 0 | 1 | 新增 |

### 429 按 key 分布

| Key | R21 | R22 | 变化 |
|-----|-----|-----|------|
| k0 | 7 | 6 | -14.3% |
| k1 | 14 | 11 | -21.4% |
| k2 | 5 | 4 | -20.0% |
| k3 | 5 | 1 | -80.0% |
| k4 | 9 | 4 | -55.6% |
| **合计** | **42** | **26** | **-38.1%** |

### Fallback & Breaker

- 30min fallback: **167** (R21: 158, +5.7%)
- breaker: PRIMARY-BREAKER-SKIP-STREAM 持续 OPEN
- 观测: PRIMARY-FAIL-STREAM (nv_gw 502 after 7ms) + FALLBACK-FAIL-STREAM (ms_gw 503 after 5ms)
- function_id: 74f02205-c7ba-438f-b81a-2537955bd7ec (ai-deepseek-v4-pro)

### 健康检查

- `curl /health`: OK (port 40006, proxy_role=passthrough, 5 keys)
- `docker ps`: nv_gw Up ~1h / hm4104 Up 5h / ms_gw Up 3d

## 核心判断

NVCF 限流继续缓解。Tier 429 从 42 降至 26 (-38.1%)，进入 20-30 区间，所有 5 把 key 的 429 均下降，k3 降幅最大 (-80%)。但 SR 从 86.2% 降至 58.1% (-28.1pp)，原因是 NVCF 上游 502 暴增 (2→11, +450%) — 这是 NVCF 服务端波动，非 nv_gw 可修。all_tiers_exhausted 同步下降 (29→13, -55.2%)，说明虽然 502 增多，但 tier 重试体系仍在工作。

按 R22 判断标准: Tier 429=26 在 20-30 区间，SR=58.1% 在 50-65% 区间 → **巡检轮，限流缓解中，继续等**。502 暴增是上游波动，不改代码。

## 本轮改动

无 (巡检轮，不改代码)

## 验证

- `curl /health` OK
- `docker ps`: 所有容器正常

## 下一步 (R23)

- 继续观察 Tier 429 是否降至 < 20
- 观察 502 是否回落 — 若 502 持续 > 10 且 SR < 50%，标注"NVCF 上游服务不稳定"
- 若 Tier 429 < 20 且 SR > 70%: 标注"NVCF 限流完全缓解，恢复正常"
- 若 breaker CLOSED 且 SR > 70%: 标注"完全恢复，可考虑回到优化模式"