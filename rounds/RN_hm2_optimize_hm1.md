# R850: HM2→HM1 — NOP (28/28 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained, identical to R849)

**决策**: 零参数修改，零 compose 修改，零容器重启。

**核心理由**: HM1 的 glm5_2_nv 持续完全健康。6h 窗口 28/28 100% SR，零 ATE，零 tier_attempts。与 R849 完全相同结论 — 系统保持峰值健康状态。

---

## 数据收集

### 1. Docker 日志 (最近 100 行)
- **零错误/告警**。所有请求均为 `[NV-SUCCESS] tier=glm5_2_nv k[N] succeeded on first attempt`
- 零 fallback 触发，零 key 循环，零超时
- Fallback chain 双向正常: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})`
- 容器最新启动: 2026-07-08 03:44:06 UTC (11:44 CST)，由 R845 metrics gap 修复部署触发
- 启动后零请求到达（DB 确认 post-restart: 0 rows）
- 历史日志 (03:33 UTC 之前): 全部 first-key success，无异常

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
```
- 同步检查: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT(66) == UPSTREAM_TIMEOUT(66)` ✓
- `KEY_COOLDOWN_S(25) == TIER_COOLDOWN_S(25)` ✓
- 零摩擦参数均已归零 ✓

### 3. DB 请求统计 (6h 窗口, 22:00 UTC Jul 7 → 04:00 UTC Jul 8)
```
total_requests: 28
success (200):   28 (100%)
failed:          0
avg_ttfb_ms:     5092.6
avg_duration_ms: 4729.5
min_duration_ms: 0 (health probe)
max_duration_ms: 15248
p50_ms:          3150.5
p95_ms:          12341.2
```
- 仅 glm5_2_nv (nvcf_pexec) 有流量 (26 req) + 2 health probe
- p50 3.2s 良好，p95 12.3s 由上游 NVCF 方差导致

### 4. DB 每小时 SR (6h 窗口)
| Hour (UTC) | Total | OK | SR |
|------------|-------|----|-----|
| 22:00 | 2 | 2 | 100% |
| 23:00 | 2 | 2 | 100% |
| 00:00 | 5 | 5 | 100% |
| 01:00 | 6 | 6 | 100% |
| 02:00 | 7 | 7 | 100% |
| 03:00 | 6 | 6 | 100% |

连续 6 小时 100% SR，无任何波动。

### 5. DB ATE 分析 (6h 窗口)
- 零 ATE — 零 tiers_tried_count=1，零 tiers_tried_count=2
- 零 fallback 触发 (fallback_occurred=false for all 28)

### 6. DB tier_attempts (6h 窗口)
```
tier_attempts_6h: 0
```
- 零 key 循环，零失败尝试

### 7. DB 错误分类 (6h 窗口)
```
无错误行 — 零 400/429/504/empty_200/degraded/timeout
```

### 8. 24h 错误全景
```
all_tiers_exhausted: 99 (全部在 >6h 前，DEGRADED 期间)
```
- 24h 内的 99 个 ATE 全部来自 6h 窗口之前的 DEGRADED 发作期
- 6h 窗口内零错误，系统已完全恢复

### 9. 对比 R849 (上一轮)
| 指标 | R849 (6h) | R850 (6h) |
|------|-----------|-----------|
| 请求数 | 24 | 28 |
| 成功率 | 100% | 100% |
| ATE | 0 | 0 |
| tier_attempts | 0 | 0 |
| p50 延迟 | 3.3s | 3.2s |
| p95 延迟 | 14.7s | 12.3s |

系统状态完全一致，峰值健康持续。p95 略有改善（上游 NVCF 方差），非代理配置影响。

---

## NOP 决策清单 (全部 6 gate 通过)

| Gate | 条件 | 状态 |
|------|------|------|
| 1. 零 ATE (6h) | count=0 | ✓ 通过 |
| 2. 零 single-tier ATE (6h) | count=0 | ✓ 通过 |
| 3. NVCFPexecTimeout buffer ≥3s | 0 tier_attempts → 无绑定 | ✓ 通过 |
| 4. FALLBACK_GRAPH 双向 | tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 | ✓ 通过 |
| 5. Fallback 100% SR | 0 fallback 触发，全部 first-key success | ✓ 通过 |
| 6. 参数已达 floor/最优值 | FASTBREAK=1, EMPTY_200=1, 零摩擦参数归零, timeout/budget 历史最优 | ✓ 通过 |

**结论**: NOP。无任何参数需要调整，系统处于历史最佳状态（与 R849 持平）。

---

## 附注

### 容器重启观察
- 容器在 03:44 UTC (11:44 CST) 被 recreate，RestartCount=0（非 docker restart）
- 重启前最后请求: 03:33 UTC (11:33 CST) — NV-SUCCESS first-key，正常
- 重启后零请求 (DB post-restart: 0 rows)，等待下次流量
- 重启原因: 推测为 R845 metrics gap 修复代码部署 (commit 0a6b71c)
- 影响: 无 — 重启前系统健康，重启后等待流量验证

### nvcf_func_monitor 陈旧容器名
- `nvcf_func_monitor.timer` (每 10min) 仍在引用旧容器名 `nv_40006_uni`
- 每次执行失败: "ERROR: 无法从 nv_40006_uni 读取 keys/function_id (容器异常?)"
- 容器在 R680 已重命名为 `nv_gw`，脚本需更新
- 影响: 健康检查静默失败（exit code 3，不告警），不影响服务运行
- 建议: 后续轮次修复脚本中的容器名

## 优化建议

无。系统连续多轮 NOP（R834-R849 共 16 轮 NOP），峰值健康持续。等待信号：UPSTREAM 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。

## ⏳ 轮到 HM1 优化 HM2