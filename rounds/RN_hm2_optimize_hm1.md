# R849: HM2→HM1 — NOP (zero ATE, zero tier_attempts, 100% 6h SR, peak health sustained)

**决策**: 零参数修改，零 compose 修改，零容器重启。

**核心理由**: HM1 的 glm5_2_nv NVCF function `3b9748d8` 持续完全健康。6h 窗口 24/24 100% SR，零 ATE，零 tier_attempts（无 NVCFPexecTimeout、无 429、无 empty_200、无 504、无 400_nvcf_degraded）。与 R848 相同结论 — 系统保持峰值健康状态。

---

## 数据收集

### 1. Docker 日志 (最近 100 行)
- **零错误/告警**。所有请求均为 `[NV-SUCCESS] tier=glm5_2_nv k[N] succeeded on first attempt`
- 无 fallback 触发，无 key 循环，无超时
- 所有请求走 glm5_2_nv 主 tier，dsv4p_nv 作为 fallback chain 从未被触发

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
```
- 所有参数同步检查通过: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT(66) == UPSTREAM_TIMEOUT(66)` ✓, `KEY_COOLDOWN_S(25) == TIER_COOLDOWN_S(25)` ✓
- 零摩擦参数均已归零（MIN_OUTBOUND_INTERVAL_S, NVU_CONNECT_RESERVE_S, NV_INTEGRATE_KEY_COOLDOWN_S）

### 3. DB 请求统计 (6h 窗口)
```
total_requests: 24
success (200):   24 (100%)
failed:          0
avg_duration_ms: 5407.3
min_duration_ms: 2506.0
max_duration_ms: 21174.0
p50_ms:          3306.5
p95_ms:          14740.7
```
- 仅 glm5_2_nv 有流量
- p50 3.3s 良好，p95 14.7s 由上游 NVCF 方差导致（非代理问题）
- 所有请求首次尝试成功

### 4. DB tier_attempts (6h 窗口)
```
tier_attempts_6h: 0
```
- 零 key 循环，零失败尝试

### 5. DB 错误分类 (6h 窗口)
```
无错误行 — 零 400/429/504/empty_200/degrated
```

### 6. 对比 R848 (24h 前)
| 指标 | R848 (6h) | R849 (6h) |
|------|-----------|-----------|
| 请求数 | 26 | 24 |
| 成功率 | 100% | 100% |
| ATE | 0 | 0 |
| tier_attempts | 0 | 0 |
| p50 延迟 | ~3.3s | 3.3s |
| p95 延迟 | ~14.7s | 14.7s |

系统状态完全一致，峰值健康持续。

---

## NOP 决策清单 (全部 6 gate 通过)

| Gate | 条件 | 状态 |
|------|------|------|
| 1. 零 ATE (6h) | count=0 | ✓ 通过 |
| 2. 零 tier_attempts (6h) | count=0 | ✓ 通过 |
| 3. 100% 成功率 (6h) | 24/24 | ✓ 通过 |
| 4. p50 < 5s | 3307ms | ✓ 通过 |
| 5. 零配置漂移 | FORCE_STREAM_UPGRADE_TIMEOUT==UPSTREAM_TIMEOUT, KEY_COOLDOWN_S==TIER_COOLDOWN_S | ✓ 通过 |
| 6. 参数已达 floor/最优值 | 所有零摩擦参数已归零，timeout/budget 已达历史最优 | ✓ 通过 |

**结论**: NOP。无任何参数需要调整，系统处于历史最佳状态（与 R848 持平）。

---

## 优化建议

无。等待信号：UPSTREAM 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。当前系统自我修复能力健全，无需人工干预。

## ⏳ 轮到 HM1 优化 HM2