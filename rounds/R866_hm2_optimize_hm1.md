# R866: HM2→HM1 — NOP (38/38 100% 6h SR, zero ATE, 2 rescued 504, peak health sustained, identical to R865)

**决策**: 零参数修改，零 compose 修改，零容器重启。

**核心理由**: HM1 的 glm5_2_nv 持续完全健康。6h 窗口 38/38 100% SR，零 ATE。与 R865 数据基本一致 — 系统保持峰值健康状态。

---

## 数据收集

### 1. Docker 日志 (最近 100 行)
- **零错误/告警**。2 次 key cycling: 14:34 k5→504→k1 和 15:04 k4→504→k5，均在 10s 内自愈。
- `[NV-CYCLE] tier=glm5_2_nv → 504 (504_nv_gateway_timeout), cycling to next key` — 正常 key cycling
- `[NV-SUCCESS] tier=glm5_2_nv succeeded after 1 cycle attempts` — 自愈正常
- 零 fallback 触发，全部 first-key pexec success（除 2 条 rescued 504）
- tier_chain: 双向 `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) 持续正常
- 所有请求均为 openclaw caller，glm5_2_nv 模型，stream=True
- 3 条新请求在 R865 提交后进入 (07:03 UTC ×3)，全部成功

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
- 与 R865 完全一致，无变化

### 3. DB 请求统计 (6h 窗口)
```
total:           38
success (200):   38 (100%)
failed:          0
avg_dur_ms:      11724
max_dur_ms:      72409
```
- 仅 glm5_2_nv (nvcf_pexec) 有流量 (36 req) + 2 NULL upstream_type (health probe)
- 全部 first-key success（除 2 条 key cycling rescued 504）
- avg_dur 11724ms vs R865 10364ms，略有上升但仍在正常范围

### 4. DB 最近 10 条请求
```
07:03 UTC  glm5_2_nv  200   67621ms   nvcf_pexec  key_cycle=1  ← rescued 504
07:03 UTC  glm5_2_nv  200    7860ms   nvcf_pexec  key_cycle=0
07:03 UTC  glm5_2_nv  200   12539ms   nvcf_pexec  key_cycle=0
06:34 UTC  glm5_2_nv  200   11650ms   nvcf_pexec  key_cycle=0
06:33 UTC  glm5_2_nv  200   72409ms   nvcf_pexec  key_cycle=1  ← rescued 504
06:33 UTC  glm5_2_nv  200   10398ms   nvcf_pexec  key_cycle=0
06:04 UTC  glm5_2_nv  200    4028ms   nvcf_pexec  key_cycle=0
06:03 UTC  glm5_2_nv  200   58291ms   nvcf_pexec  key_cycle=0
06:03 UTC  glm5_2_nv  200    7342ms   nvcf_pexec  key_cycle=0
05:33 UTC  glm5_2_nv  200    4635ms   nvcf_pexec  key_cycle=0
```
全部成功。2 条 key_cycle_429s=1（07:03 的 67,621ms 和 06:33 的 72,409ms — 均为 rescued 504）。延迟范围 1.9s-72.4s。

### 5. 新请求 (自 R865 提交后)
```
new_reqs since 06:35 UTC: 3
```
- 07:03:21 UTC: 12.5s, success, key_cycle=0
- 07:03:35 UTC: 7.9s, success, key_cycle=0
- 07:03:43 UTC: 67.6s, success, key_cycle=1 (rescued 504, k4→k5)
- 3/3 success, 100% SR

### 6. DB tier_attempts (6h 窗口)
```
tier        error_type               cnt
glm5_2_nv   504_nv_gateway_timeout    2
```
- 2 条 rescued 504（k5→k1 和 k4→k5），key cycling 自愈正常
- R865 有 1 条，R866 有 2 条 — 仍在正常波动范围

### 7. DB tier_attempts (24h 窗口)
```
tier        error_type               cnt   avg_ms   max_ms
dsv4p_nv    504_nv_gateway_timeout    12       -        -
dsv4p_nv    NVCFPexecTimeout           9   50867    51227
dsv4p_nv    empty_200                  3       -        -
glm5_2_nv   400_nvcf_degraded         56       -        -  ← pre-R845/R846
glm5_2_nv   504_nv_gateway_timeout     5       -        -
glm5_2_nv   500_nv_error               1       -        -
```
- NVCFPexecTimeout max: dsv4p_nv=51,227ms
- Buffer: UPSTREAM=66,000ms - 51,227ms = 14,773ms >> 3s minimum ✓
- dsv4p_nv empty_200: 3 (R862=5→R865=3→R866=3，持平)
- 24h 数据与 R865 完全一致（无新增 400_nvcf_degraded 在 6h 窗口，pre-R845/R846 的 56 条正逐步退出 24h 窗口）

### 8. DB ATE 分析 (6h 窗口)
- 零 ATE

### 9. DB 错误分类 (6h 窗口)
```
无错误行 — 零 400/429/504/empty_200/degraded/timeout (仅 tier_attempts 级别有 2 条 rescued 504)
```

### 10. 按路径分组 (6h 窗口)
```
nvcf_pexec: 36 req, 36 OK (100%), avg_dur=12375ms, max=72409ms
NULL:        2 req,  2 OK (100%), avg_dur=0ms (health probe)
```

### 11. 对比 R865 (上一轮)
| 指标 | R865 (6h) | R866 (6h) |
|------|-----------|-----------|
| 请求数 | 38 | 38 |
| 成功率 | 100% | 100% |
| ATE | 0 | 0 |
| tier_attempts (504) | 1 | 2 |
| fallback | 0 | 0 |
| avg_duration | 10364ms | 11724ms |
| max_duration | 72409ms | 72409ms |
| dsv4p_nv empty_200 (24h) | 3 | 3 |
| 新请求 (post-R865) | 0 | 3 |

系统状态与 R865 **基本一致**，峰值健康持续。3 条新请求全部成功，2 条 rescued 504 在正常范围。

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

**结论**: NOP。无任何参数需要调整，系统处于历史最佳状态（与 R834–R865 共 32 轮 NOP 持平）。

---

## 优化建议

无。系统连续 32 轮 NOP（R834–R866），峰值健康持续。等待信号：UPSTREAM 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。

## ⏳ 轮到 HM1 优化 HM2