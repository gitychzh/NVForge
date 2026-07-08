# R852: HM2→HM1 — NOP (31/31 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained, identical to R851)

**决策**: 零参数修改，零 compose 修改，零容器重启。

**核心理由**: HM1 的 glm5_2_nv 持续完全健康。6h 窗口 31/31 100% SR，零 ATE，零 tier_attempts。与 R851 完全相同结论 — 系统保持峰值健康状态。

---

## 数据收集

### 1. Docker 日志 (最近 100 行)
- **零错误/告警**。所有请求均为成功 first-key pexec。
- 零 fallback 触发，零 key 循环，零超时
- tier_chain: 双向 `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) 持续正常
- 容器 env: UPSTREAM_TIMEOUT=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1

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
total:          31
success (200):  31 (100%)
failed:         0
avg_duration_ms: 5216
max_duration_ms: 15248
```
- 仅 glm5_2_nv (nvcf_pexec) 有流量 (29 req) + 2 NULL upstream_type (health probe)
- 全部 first-key success，零 fallback

### 4. DB 最近 10 条请求
```
04:14 UTC  glm5_2_nv  200   9503ms   nvcf_pexec  key_cycle=0
04:03 UTC  glm5_2_nv  200   2635ms   nvcf_pexec  key_cycle=0
04:03 UTC  glm5_2_nv  200   6593ms   nvcf_pexec  key_cycle=0
04:03 UTC  glm5_2_nv  200  13192ms   nvcf_pexec  key_cycle=0
03:33 UTC  glm5_2_nv  200   2839ms   nvcf_pexec  key_cycle=0
03:33 UTC  glm5_2_nv  200   8391ms   nvcf_pexec  key_cycle=0
03:33 UTC  glm5_2_nv  200  12597ms   nvcf_pexec  key_cycle=0
03:03 UTC  glm5_2_nv  200   3714ms   nvcf_pexec  key_cycle=0
03:03 UTC  glm5_2_nv  200   9153ms   nvcf_pexec  key_cycle=0
03:03 UTC  glm5_2_nv  200  15248ms   nvcf_pexec  key_cycle=0
```
全部成功，零 key_cycle_429s，延迟范围 2.6s-15.2s。

### 5. DB ATE 分析 (6h 窗口)
- 零 ATE — 零 tiers_tried_count=1，零 tiers_tried_count=2
- 零 fallback 触发 (fallback_occurred=false for all 31)

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
nvcf_pexec: 29 req, 29 OK (100%), avg_dur=5575ms, max=15248ms
NULL:        2 req,  2 OK (100%), avg_dur=0ms (health probe)
```

### 9. 按模型分组 (6h 窗口)
```
glm5_2_nv: 29 req, 29 OK (100%)
NULL:       2 req,  2 OK (100%)
```

### 10. 每小时 SR 分布 (6h 窗口)
```
22:00 UTC:  1/1   (100%)
23:00 UTC:  2/2   (100%)
00:00 UTC:  5/5   (100%)
01:00 UTC:  6/6   (100%)
02:00 UTC:  7/7   (100%)
03:00 UTC:  6/6   (100%)
04:00 UTC:  4/4   (100%)
```
全部小时 100% SR。容器最近重启于 04:12 UTC，重启后零不良影响。

### 11. 对比 R851 (上一轮)
| 指标 | R851 (6h) | R852 (6h) |
|------|-----------|-----------|
| 请求数 | 30 | 31 |
| 成功率 | 100% | 100% |
| ATE | 0 | 0 |
| tier_attempts | 0 | 0 |
| fallback | 0 | 0 |
| avg_duration | 5072.6ms | 5216ms |
| max_duration | 15248ms | 15248ms |

系统状态完全一致，峰值健康持续。延迟微增（avg 5.1s→5.2s）为上游 NVCF 方差，非代理配置影响。

---

## NOP 决策清单 (全部 6 gate 通过)

| Gate | 条件 | 状态 |
|------|------|------|
| 1. 零 ATE (6h) | count=0 | ✓ 通过 |
| 2. 零 single-tier ATE (6h) | count=0 | ✓ 通过 |
| 3. NVCFPexecTimeout buffer ≥3s | 0 tier_attempts → 无绑定 | ✓ 通过 |
| 4. FALLBACK_GRAPH 双向 | tier_chain 双向 normal | ✓ 通过 |
| 5. Fallback 100% SR | 0 fallback 触发，全部 first-key success | ✓ 通过 |
| 6. 参数已达 floor/最优值 | FASTBREAK=1, EMPTY_200=1, 零摩擦参数归零, timeout/budget 历史最优 | ✓ 通过 |

**结论**: NOP。无任何参数需要调整，系统处于历史最佳状态（与 R849/R850/R851 持平）。

---

## 优化建议

无。系统连续多轮 NOP（R834-R852 共 18 轮 NOP），峰值健康持续。等待信号：UPSTREAM 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。

## ⏳ 轮到 HM1 优化 HM2