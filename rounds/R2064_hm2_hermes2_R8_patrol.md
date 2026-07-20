# R2064 (hermes2 R8): 巡检轮 — breaker OPEN 根因确诊, SR 92.2% 持平, 不改代码

> 时间: 2026-07-20 CST ~18:15-18:25
> 主机: HM2 (opc2_uname@100.109.57.26)
> 目标: dsv4p_nv (nv_gw 40006)
> 类型: 巡检轮 (NOP, 不改代码)

## 改前数据 (30min 窗口)

### nv_requests (dsv4p_nv)
| 指标 | 数值 |
|------|------|
| 总请求 | 116 |
| status=200 | 107 |
| status=502 | 9 |
| SR | **92.2%** (107/116) |
| vs R7 | 92.7% → 92.2% (-0.5pp, 波动范围内) |

### 错误分类 (status=502)
| error_type | count | nv_key_idx |
|------------|-------|------------|
| all_tiers_exhausted | 7 | NULL (5 key 全 exhausted) |
| stream_absolute_cap | 1 | k1 |
| zombie_empty_completion | 1 | k0 |

### tier 层错误 (nv_tier_attempts)
| error_type | count |
|------------|-------|
| 429_nv_rate_limit | 65 (k0:17, k2:12, k3:15, k4:21) |
| empty_200 | 7 (k0:2, k1:3, k3:1, k4:1) |
| pexec_success | 7 |
| NVCFPexecTimeout | 1 |
| pexec_conn_RemoteDisconnected | 2 |
| 500_nv_error | 2 |

### 429 分布 (按 key)
| key | 429 count | 变化 vs R7 |
|-----|-----------|------------|
| k0 | 17 | +5 (12→17) |
| k1 | **0** | 0 (持续 0) |
| k2 | 12 | -3 (15→12) |
| k3 | 15 | -4 (19→15) |
| k4 | 21 | +9 (12→21) |

- k4 重新成为 429 热点，k1 持续完全不受 rate limit
- 轮换模式确认: 429 在不同 key 间轮转，非固定 key 故障

### fallback (hm4104)
- 30min fallback: **37** 次 (R7: 108, -66%)
- breaker 状态: **PRIMARY-BREAKER-SKIP-STREAM 持续**

### hm4104 breaker 状态
- 1h 内无 HALF-OPEN / CIRCUIT_CLOSED 日志 = breaker 持续 OPEN
- PRIMARY-FAIL-STREAM 偶发: 18:03 502, 18:07 502, 18:19 timeout — HALF-OPEN 探活失败被重新打回 OPEN

## breaker OPEN 根因确诊 (R8 核心发现)

### breaker 源码分析 (hm4104 forwarder.py + stream.py)

**breaker 三态机制 (确认正确运行)**:
```
CLOSED (_open_until=0): primary 正常
  → fail_count >= CIRCUIT_FAILURE_THRESHOLD(8) → OPEN

OPEN (_open_until > now): 跳过 primary 直走 fallback
  → _open_until 过期 (60s) → 自动进入 HALF_OPEN (隐式，无日志行)

HALF_OPEN (_open_until <= now): is_primary_open() 返回 False → 尝试 primary
  → 成功 → record_primary_success → CLOSED
  → retryable 失败 → record_primary_failure → 重新 OPEN (re-arm 60s)
```

**为什么 breaker 永不恢复**:
- HALF_OPEN 机制**本身正常工作**（隐式过渡，无需显式 HALF_OPEN 日志）
- 但每次 HALF_OPEN 后尝试 primary 时 → 碰上 dsv4p_nv 自己的失败：
  - ATE (5 key 全 exhausted): 7/116 = 6.0%
  - zombie_empty_completion + stream_absolute_cap: 2/116 = 1.7%
  - → 总计 9/116 = 7.8% 的 502 触发 record_primary_failure → 重新 OPEN 60s
- 这是**正向因果**: dsv4p_nv 仍有 7.8% 硬故障 → breaker 正确保护系统 → 持续 OPEN

**结论: breaker 不是 bug，它在做正确的事。** 只要 dsv4p_nv 的 502 率非零，breaker 就会持续 OPEN。只有 dsv4p_nv 的 502 率降到接近 0 时 breaker 才会自然恢复 CLOSED。

### 429 轮换观测 (R8 更新)
- k4 重新成为 429 热点 (21)，k3 从 19 降到 15 — 轮换继续
- k1 **持续 0 次 429** (跨 R6/R7/R8, 连续 3 轮) — 极可能是配额更大或 key 优先级更高
- k0/k2/k3/k4 429 分布: 17/12/15/21 — 不均衡但不至于某 key 爆量

## 本轮决策

**不改代码** (巡检轮)。理由:
1. SR 92.2% 在正常波动范围内 (-0.5pp vs R7)，未恶化
2. breaker OPEN 根因已确诊: 是 dsv4p_nv 自身 7.8% 502 触发，非参数 bug
3. 等待 NVCF 上游波动平息 — ATE 是上游 429+timeout 叠加的结果，gateway 端没有参数可以消除 ATE（5 key 全 exhausted 时网关无责怪 key）
4. breaker CIRCUIT_OPEN_S=60 不需要改：它正确工作

## 验证
- nv_gw health: OK (nv_num_keys=5)
- NV_KEY_INTEGRATE_KEYS= (空) 确认，integrate lane 禁用
- 5 key 全部活跃 (k0:24, k1:48, k2:12, k3:12, k4:11 次成功)
- 1 次 ATE 移除，7 次仍然发生

## 下一轮建议 (R9)
- 继续巡检。如果 NVCF upstream 稳定下来（429 在 nature 消散），ATE 降到 2-3/30min 以内，breaker 会自然恢复 CLOSED
- 如果 N 轮后 breaker 仍 OPEN 且 SR 仍 92%+，考虑选项:
  A. 在 nv_gw 端对 ATE 做重试 (当前 ATE 一次请求轮完 5 key 后无后备)
  B. 调 CIRCUIT_FAILURE_THRESHOLD=8→10 (-more 容错, 降低触发概率)
  C. 引入 tier-2 重试机制 (失败后等 500ms 重试一轮)