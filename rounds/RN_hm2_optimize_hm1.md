# R862: HM2→HM1 — NOP (38/38 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained, identical to R853–R861)

**决策**: 零参数修改，零 compose 修改，零容器重启。

**核心理由**: HM1 的 glm5_2_nv 持续完全健康。6h 窗口 38/38 100% SR，零 ATE，零 tier_attempts，零 fallback。与 R853–R861 完全相同结论 — 系统保持峰值健康状态。

---

## 数据收集

### 1. Docker 日志 (最近 100 行)
- **零错误/告警**。所有请求均为成功 first-key pexec。
- 零 fallback 触发，零 key 循环，零超时
- tier_chain: 双向 `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) 持续正常
- 容器最近重启于 2026-07-08T04:12:50Z，重启后所有请求正常
- 所有请求均为 openclaw caller，glm5_2_nv 模型，stream=True
- 最近日志 (11:33-14:04 UTC): glm5_2_nv k1/k2/k4/k5 交替 first-attempt success，key 轮转正常

### 2. 容器环境变量 (当前配置)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
NVU_FORCE_STREAM_UPGRADE=0
NVU_EMPTY_200_FASTBREAK=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_SSLEOF_RETRY_DELAY_S=1.0
```
- 同步检查: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT(66) == UPSTREAM_TIMEOUT(66)` ✓
- `KEY_COOLDOWN_S(25) == TIER_COOLDOWN_S(25)` ✓
- 零摩擦参数均已归零 ✓

### 3. DB 请求统计 (6h 窗口)
```
total:          38
success (200):  38 (100%)
failed:         0
avg_duration_ms: 7602
max_duration_ms: 58291
```
- 仅 glm5_2_nv (nvcf_pexec) 有流量 (36 req) + 2 NULL upstream_type (health probe)
- 全部 first-key success，零 fallback

### 4. DB 最近 10 条请求
```
06:04 UTC  glm5_2_nv  200    4028ms   nvcf_pexec  key_cycle=0
06:03 UTC  glm5_2_nv  200   58291ms   nvcf_pexec  key_cycle=0
06:03 UTC  glm5_2_nv  200    7342ms   nvcf_pexec  key_cycle=0
05:33 UTC  glm5_2_nv  200    4635ms   nvcf_pexec  key_cycle=0
05:33 UTC  glm5_2_nv  200   22642ms   nvcf_pexec  key_cycle=0
05:33 UTC  glm5_2_nv  200    8043ms   nvcf_pexec  key_cycle=0
05:03 UTC  glm5_2_nv  200    1933ms   nvcf_pexec  key_cycle=0
05:03 UTC  glm5_2_nv  200    7706ms   nvcf_pexec  key_cycle=0
05:03 UTC  glm5_2_nv  200   12053ms   nvcf_pexec  key_cycle=0
04:33 UTC  glm5_2_nv  200    3985ms   nvcf_pexec  key_cycle=0
```
全部成功，零 key_cycle_429s，延迟范围 1.9s-58.3s（max 58.3s 为单次大请求，ttfb≈58.3s 表明 NVCF 处理耗时，非超时）。

### 5. DB ATE 分析 (6h 窗口)
- 零 ATE — 零 tiers_tried_count=1，零 tiers_tried_count=2

### 6. DB tier_attempts (6h 窗口)
```
tier_attempts_6h: 0
```
- 零 key 循环，零失败尝试

### 7. DB 错误分类 (6h 窗口)
```
无错误行 — 零 400/429/504/empty_200/degraded/timeout
```

### 8. 按路径分组 (6h 窗口)
```
nvcf_pexec: 36 req, 36 OK (100%), avg_dur=8025ms, max=58291ms
NULL:        2 req,  2 OK (100%), avg_dur=0ms (health probe)
```

### 9. 按模型分组 (6h 窗口)
```
glm5_2_nv: 36 req, 36 OK (100%)
NULL:       2 req,  2 OK (100%)
```

### 10. 6h 持续时间分布
```
<5s:    20 个 (全部 200)
5-10s:  11 个 (全部 200)
10-15s:  4 个 (全部 200)
15-20s:  1 个 (全部 200)
20-30s:  1 个 (全部 200)
50-80s:  1 个 (全部 200)  ← 单次大请求，非超时
```

### 11. 6h 按小时 SR
```
00 UTC: 3/3   (100%)
01 UTC: 6/6   (100%)
02 UTC: 7/7   (100%)
03 UTC: 6/6   (100%)
04 UTC: 7/7   (100%)
05 UTC: 6/6   (100%)
06 UTC: 3/3   (100%)
```
连续 7 小时 100% SR，无任何波动。

### 12. 24h tier_attempts 全景 (上下文)
```
tier       error_type               cnt  avg_ms  max_ms
dsv4p_nv   504_nv_gateway_timeout    12       -       -
dsv4p_nv   NVCFPexecTimeout           9   50867   51227
dsv4p_nv   empty_200                  5       -       -
glm5_2_nv  400_nvcf_degraded         56       -       -  ← pre-R845/R846 code fixes
glm5_2_nv  504_nv_gateway_timeout     5       -       -
glm5_2_nv  NVCFPexecTimeout           1   50937   50937
glm5_2_nv  500_nv_error               1       -       -
```
- NVCFPexecTimeout max: dsv4p_nv=51,227ms, glm5_2_nv=50,937ms
- Buffer: UPSTREAM=66,000ms - 51,227ms = 14,773ms >> 3s minimum ✓
- 24h 数据包含 pre-R845/R846 窗口的 400_nvcf_degraded，6h 窗口完全干净
- 24h dsv4p_nv empty_200 从 R856 的 8 降至 5 (减少 3，无新增)，glm5_2_nv 24h 数据与 R856 完全一致

### 13. 对比 R861 (上一轮)
| 指标 | R861 (6h) | R862 (6h) |
|------|-----------|-----------|
| 请求数 | 38 | 38 |
| 成功率 | 100% | 100% |
| ATE | 0 | 0 |
| tier_attempts | 0 | 0 |
| fallback | 0 | 0 |
| avg_duration | 7602ms | 7602ms |
| max_duration | 58291ms | 58291ms |

系统状态与 R861 **完全一致**（请求数、avg_duration、max_duration 完全相同），峰值健康持续。

---

## NOP 决策清单 (全部 6 gate 通过)

| Gate | 条件 | 状态 |
|------|------|------|
| 1. 零 ATE (6h) | count=0 | ✓ 通过 |
| 2. 零 single-tier ATE (6h) | count=0 | ✓ 通过 |
| 3. NVCFPexecTimeout buffer ≥3s | 24h max=51,227ms, buffer=14.8s >> 3s | ✓ 通过 |
| 4. FALLBACK_GRAPH 双向 | tier_chain 双向 normal | ✓ 通过 |
| 5. Fallback 100% SR | 0 fallback 触发，全部 first-key success | ✓ 通过 |
| 6. 参数已达 floor/最优值 | FASTBREAK=1, EMPTY_200=1, 零摩擦参数归零, timeout/budget 历史最优, FORCE_STREAM=UPSTREAM 同步 | ✓ 通过 |

**结论**: NOP。无任何参数需要调整，系统处于历史最佳状态（与 R834–R861 共 28 轮 NOP 持平）。

---

## 优化建议

无。系统连续 28 轮 NOP（R834–R862），峰值健康持续。等待信号：UPSTREAM 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。

## ⏳ 轮到 HM1 优化 HM2