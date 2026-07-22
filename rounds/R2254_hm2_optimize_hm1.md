# R2254 (HM2→HM1): BUDGET 102→120 + BIG_INPUT 250K→350K

## TL;DR
Two small parameter changes to reduce pre-empted ATE failures:
1. `NVU_TIER_BUDGET_DSV4P_NV`: 102→120 (+18s) — covers dsv4p ATE durations (62-102s) that were hitting the 102s budget ceiling
2. `NVU_BIG_INPUT_THRESHOLD`: 250000→350000 (+100K chars) — reduces false pre-emption for large legitimate requests (319-357K chars)

单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2254 部署后）

| # | 参数 | HM1 当前值 | 变化 |
|---|------|------------|------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 157 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | — |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | — |
| 5 | `TIER_COOLDOWN_S` | 0 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | — |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | — |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | — |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | — |
| 12 | `NV_INTEGRATE_ENABLED` | (not set) | — |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | — |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | — |
| 15 | `KEY_COOLDOWN_S` | 0 | — |
| 16 | `KEY_AUTHFAIL_COOLDOWN_S` | 25 | — |
| 17 | `NVU_TIER_BUDGET_DSV4P_NV` | **120** | 102→120 (+18s) |
| 18 | `NVU_BIG_INPUT_THRESHOLD` | **350000** | 250000→350000 (+100K) |

---

## 二、诊断数据（20:42 UTC 采集）

### 2.1 6h 窗口统计
| 指标 | 数值 |
|------|------|
| 总请求 | 61 |
| 成功 | 50 (82.0%) |
| 失败 | 11 (18.0%) |

### 2.2 错误分布
| 模型 | 错误类型 | 状态 | 数量 |
|------|----------|------|------|
| dsv4p_nv | all_tiers_exhausted | 502 | 7 |
| glm5_2_nv | all_tiers_exhausted | 502 | 3 |
| dsv4p_nv | zombie_empty_completion | 502 | 1 |

### 2.3 ATE 详情（全部 0 tier_attempts → 全部 pre-empted）
| 时间 | 模型 | 耗时(ms) | 输入(chars) | 预算(当时) |
|------|------|----------|-------------|-----------|
| 12:08 | dsv4p_nv | 102054 | 319272 | 102 |
| 12:04 | glm5_2_nv | 163246 | 323287 | 56 |
| 11:33 | glm5_2_nv | 137487 | 319248 | 56 |
| 10:37 | dsv4p_nv | 96030 | 356559 | 102 |
| 09:38 | dsv4p_nv | 61893 | 349327 | 102 |
| 09:05 | dsv4p_nv | 63081 | 342914 | 102 |
| 08:42 | dsv4p_nv | 64127 | 354223 | 102 |
| 08:07 | dsv4p_nv | 96043 | 338571 | 102 |
| 08:04 | glm5_2_nv | 192706 | 342802 | 56 |
| 07:36 | dsv4p_nv | 96043 | 337470 | 102 |

### 2.4 Phantom ATE (status=200 ATE)
| 时间 | 模型 | 耗时(ms) | 输入(chars) |
|------|------|----------|-------------|
| 12:44 | dsv4p_nv | 10447 | 338378 |
| 10:33 | glm5_2_nv | 30299 | 356534 |
| 08:37 | dsv4p_nv | 38867 | 348496 |
| 07:11 | dsv4p_nv | 32975 | 342507 |
| 07:08 | dsv4p_nv | 20727 | 338413 |

### 2.5 Docker 日志（nv_gw 最近错误）
```
[20:42:02.4] [NV-ERR] tier=dsv4p_nv k2 SSLEOFError: UNEXPECTED_EOF_WHILE_READING
[20:42:02.4] [NV-SSL-CYCLE] dsv4p_nv k2 SSL error (5004ms) → cycle to next key
[20:44:43.4] [NV-CONN] dsv4p_nv k3 connection error: Remote end closed connection
[20:45:18.9] [NV-CONN] dsv4p_nv k4 connection error: Remote end closed connection
[20:45:18.9] [NV-CONN-BREAK] dsv4p_nv 2 consecutive connection errors → fast-break
```

### 2.6 Per-model 成功请求延迟
| 模型 | 数量 | avg(ms) | min(ms) | max(ms) |
|------|------|---------|---------|---------|
| dsv4p_nv | 21 | 29832 | 5781 | 58328 |
| glm5_2_nv | 29 | 61798 | 6576 | 174770 |

---

## 三、变更分析

### Change 1: NVU_TIER_BUDGET_DSV4P_NV 102→120
**根因**: dsv4p ATE 耗时 62-102s，全部挤在 budget 102s 天花板。当 SSL/connection 错误发生后 key-cycle 到新 key，请求耗时轻易超过 102s 被 pre-empted。

**预算计算**: per-key cost = max(KEY_AUTHFAIL_COOLDOWN_S, KEY_COOLDOWN_S) + UPSTREAM_TIMEOUT = max(25,0) + 24 = 49s。MIN_BUDGET = 49 × FASTBREAK(1) = 49s。120s > 49s ✓，安全余量 71s。

**预期**: 覆盖 dsv4p ATE 的 62-102s 范围，允许 SSL/connection 恢复后完成请求，减少 dsv4p ATE。

### Change 2: NVU_BIG_INPUT_THRESHOLD 250000→350000
**根因**: 所有 10 个 ATE 的 total_input_chars 在 319-357K，全部超过旧的 250K 阈值。虽然 BIG_INPUT_MODELS 只覆盖 glm5_2_nv，但 dsv4p ATE 也同样被 budget 截断。将阈值提高到 350K 让合法大请求通过，同时仍拦截超大请求。

**BIG_INPUT 机制**: 只有列表中的模型（当前仅 glm5_2_nv）受此阈值控制。超过阈值→计数+1→达到 NVU_BIG_INPUT_FAIL_N(5) → 触发 cooldown 2100s。glm5_2 在该机制下继续受保护。

---

## 四、部署验证

```bash
# 重启 nv_gw
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
# 状态: Up 15 seconds (healthy) ✓
# 环境确认: NVU_TIER_BUDGET_DSV4P_NV=120 ✓, NVU_BIG_INPUT_THRESHOLD=350000 ✓
```

---

## ⏳ 轮到 HM1 优化 HM2