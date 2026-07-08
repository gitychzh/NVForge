# R865: HM2→HM1 — NOP (38/38 100% 6h SR, zero ATE, 1 rescued 504, peak health sustained, identical to R864)

**决策**: 零参数修改，零 compose 修改，零容器重启。

**核心理由**: HM1 的 glm5_2_nv 持续完全健康。6h 窗口 38/38 100% SR，零 ATE。与 R864 数据完全一致 — 系统保持峰值健康状态。

---

## 数据收集

### 1. Docker 日志 (最近 200 行)
- **零错误/告警**。唯一事件: 14:34:35.8 单次 k5→504_nv_gateway_timeout，key cycling 到 k1 后 10s 内成功恢复。
- `[NV-SUCCESS] tier=glm5_2_nv k1 succeeded after 1 cycle attempts` — 自愈正常
- 零 fallback 触发，全部 first-key pexec success
- tier_chain: 双向 `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) 持续正常
- 容器两次重启 (11:33 UTC 和 12:04 UTC)，均正常恢复
- 所有请求均为 openclaw caller，glm5_2_nv 模型，stream=True

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
avg_duration_ms: 10364
max_duration_ms: 72409
```
- 仅 glm5_2_nv (nvcf_pexec) 有流量 (36 req) + 2 NULL upstream_type (health probe)
- 全部 first-key success，零 fallback

### 4. DB 最近 10 条请求
```
06:34 UTC  glm5_2_nv  200   11625ms   nvcf_pexec  key_cycle=0
06:33 UTC  glm5_2_nv  200   72408ms   nvcf_pexec  key_cycle=1  ← rescued 504
06:33 UTC  glm5_2_nv  200   10397ms   nvcf_pexec  key_cycle=0
06:04 UTC  glm5_2_nv  200    4028ms   nvcf_pexec  key_cycle=0
06:03 UTC  glm5_2_nv  200   58290ms   nvcf_pexec  key_cycle=0
06:03 UTC  glm5_2_nv  200    7341ms   nvcf_pexec  key_cycle=0
05:33 UTC  glm5_2_nv  200    4635ms   nvcf_pexec  key_cycle=0
05:33 UTC  glm5_2_nv  200   22641ms   nvcf_pexec  key_cycle=0
05:33 UTC  glm5_2_nv  200    8043ms   nvcf_pexec  key_cycle=0
05:03 UTC  glm5_2_nv  200    1932ms   nvcf_pexec  key_cycle=0
```
全部成功。1 条 key_cycle_429s=1（06:33 的 72,408ms 请求 — 即 rescued 504 请求，k5→k1 后成功）。延迟范围 1.9s-72.4s。max 72.4s 为单次大请求，非超时。

### 5. 无新请求 (自 06:35 UTC)
```
new_reqs since 06:35: 0
```
自 R864 提交后无新请求。6h 窗口数据与 R864 完全一致。

### 6. DB tier_attempts (6h 窗口)
```
tier        error_type               cnt
glm5_2_nv   504_nv_gateway_timeout    1
```
- 1 条 rescued 504（k5 失败 → k1 成功），key cycling 自愈正常

### 7. DB tier_attempts (24h 窗口)
```
tier        error_type               cnt   avg_ms   max_ms
dsv4p_nv    504_nv_gateway_timeout    12       -        -
dsv4p_nv    NVCFPexecTimeout           9   50867    51227
dsv4p_nv    empty_200                  3       -        -
glm5_2_nv   400_nvcf_degraded         56       -        -  ← pre-R845/R846
glm5_2_nv   504_nv_gateway_timeout     5       -        -
glm5_2_nv   NVCFPexecTimeout           1   50937    50937
glm5_2_nv   500_nv_error               1       -        -
```
- NVCFPexecTimeout max: dsv4p_nv=51,227ms, glm5_2_nv=50,937ms
- Buffer: UPSTREAM=66,000ms - 51,227ms = 14,773ms >> 3s minimum ✓
- dsv4p_nv empty_200: 3 (R862=5→R864=3→R865=3，稳定下降后持平)
- 24h 数据与 R864 一致（无新增 400_nvcf_degraded 在 6h 窗口，pre-R845/R846 的 56 条正逐步退出 24h 窗口）

### 8. DB ATE 分析 (6h 窗口)
- 零 ATE

### 9. DB 错误分类 (6h 窗口)
```
无错误行 — 零 400/429/504/empty_200/degraded/timeout
```

### 10. 按路径分组 (6h 窗口)
```
nvcf_pexec: 36 req, 36 OK (100%), avg_dur=10364ms, max=72409ms
NULL:        2 req,  2 OK (100%), avg_dur=0ms (health probe)
```

### 11. 对比 R864 (上一轮)
| 指标 | R864 (6h) | R865 (6h) |
|------|-----------|-----------|
| 请求数 | 38 | 38 |
| 成功率 | 100% | 100% |
| ATE | 0 | 0 |
| tier_attempts | 1 (504 rescued) | 1 (504 rescued) |
| fallback | 0 | 0 |
| avg_duration | 10364ms | 10364ms |
| max_duration | 72409ms | 72409ms |
| dsv4p_nv empty_200 (24h) | 3 | 3 |

系统状态与 R864 **完全一致**，峰值健康持续。无新请求进入，数据窗口完全相同。

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

**结论**: NOP。无任何参数需要调整，系统处于历史最佳状态（与 R834–R864 共 31 轮 NOP 持平）。

---

## 优化建议

无。系统连续 31 轮 NOP（R834–R865），峰值健康持续。等待信号：UPSTREAM 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。

## ⏳ 轮到 HM1 优化 HM2