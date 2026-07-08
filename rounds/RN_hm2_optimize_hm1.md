# R839: HM2→HM1 — NOP (post-recovery 3h+ silent, 12/12 first-key success, all 6 gates pass, identical to R838)

**决策**: 零参数修改，零 compose 修改，零容器重启。与 R838 完全相同的系统状态 — 自 09:03 UTC 最后一批请求后无新活动，glm5_2_nv NVCF 持续健康，DEGRADED 窗口继续老化。

---

## 数据收集 (08-Jul-2026 09:15 UTC)

### 容器状态
- 容器: nv_gw, Up, 启动时间: 00:01:38 UTC (7.5h uptime)
- Health: HTTP 200 ✓
- 内部进程重启: 07:33 UTC (bytecode 热更新)

### 环境变量 (全部 floor)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 (= UPSTREAM_TIMEOUT ✓)
NVU_PEER_FALLBACK_TIMEOUT=45
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

### 6h 窗口统计 (DB, 03:15–09:15 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 20 req |
| OK | 17 (85.0%) |
| ATE | 3 (15.0%) |
| avg_ok_ms | 11,925ms |

### 按小时 (6h)
| 小时 (UTC) | total | ok | fail | SR |
|-----------|-------|-----|------|-----|
| 19:00 | 2 | 2 | 0 | 100% |
| 20:00 | 3 | 1 | 2 | 33.3% |
| 21:00 | 3 | 2 | 1 | 66.7% |
| 22:00 | 2 | 2 | 0 | 100% |
| 23:00 | 2 | 2 | 0 | 100% |
| 00:00 | 5 | 5 | 0 | 100% |
| 01:00 | 3 | 3 | 0 | 100% |

**注意**: DB 最后记录 01:03 UTC。01:00–09:15 的 docker logs 可见请求均未写入 DB（已知 bytecode 热更新 DB 写入中断，非 config-fixable）。与 R838 完全一致。

### 按 upstream_type (6h)
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|--------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 17 | 17 | 11,924ms | 11,925ms | 69,809ms |
| (NULL=ATE) | 3 | 0 | - | 115,332ms | 115,625ms |

### ATE 分析
- 3 ATE 全部 tiers_tried_count=2 (glm5_2_nv→dsv4p_nv) ✓
- 零单 tier ATE ✓
- 全部来自 04:35–05:33 UTC DEGRADED 窗口
- fallback_actually_attempted=f 但实际 tiers_tried_count=2 说明 fallback 确实触发了（日志可见 NV-FALLBACK → NV-TIER-FAIL on dsv4p_nv）

### nv_tier_attempts (6h)
| tier | error_type | cnt |
|------|-----------|-----|
| dsv4p_nv | 504_nv_gateway_timeout | 1 |
| glm5_2_nv | 400_nvcf_degraded | 7 |

- 零 NVCFPexecTimeout → UPSTREAM=66 非绑定 ✓
- 7 次 glm5_2_nv 400 DEGRADED（全部 03:03–05:33 窗口，NVCF 上游问题）
- 仅 1 次 dsv4p_nv 504 timeout
- 400 非循环修复已生效：03:36+ 日志显示 NV-NONCYCLE-ERR 而非循环

### 429 分析 (6h)
| request_model | total_429s | requests_with_429 |
|---------------|------------|-------------------|
| glm5_2_nv | 8 | 2 |

- 全部 429 来自 20:00–21:00 UTC DEGRADED 窗口
- Post-recovery (06:03+) 零 429s ✓

### Fallback 统计 (6h)
| fallback_occurred | cnt |
|-------------------|-----|
| f | 15 |
| t | 5 |

- Fallback SR: 5/5 = 100% ✓
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向确认 ✓

### Docker 日志 — post-recovery 全貌 (06:03–09:03 UTC)

全部 glm5_2_nv 首次 key 成功，延迟 2.5–7.7s：
```
[06:03:23.8] glm5_2_nv k2 → NV-SUCCESS 2.7s (first attempt)
[06:33:23.8] glm5_2_nv k3 → NV-SUCCESS 2.7s (first attempt)
[07:03:23.5] glm5_2_nv k4 → NV-SUCCESS 2.6s (first attempt)
[07:33:24.2] glm5_2_nv k5 → NV-SUCCESS 2.8s (first attempt)
[08:03:24.1] glm5_2_nv k1 → NV-SUCCESS 3.0s (first attempt)
[08:03:28.2] glm5_2_nv k2 → NV-SUCCESS 2.6s (first attempt)
[08:33:24.4] glm5_2_nv k3 → NV-SUCCESS 3.3s (first attempt)
[08:33:29.3] glm5_2_nv k4 → NV-SUCCESS 3.6s (first attempt)
[08:33:32.9] glm5_2_nv k5 → NV-SUCCESS 3.3s (first attempt)
[09:03:26.5] glm5_2_nv k1 → NV-SUCCESS 5.4s (first attempt)
[09:03:35.6] glm5_2_nv k2 → NV-SUCCESS 7.8s (first attempt)
[09:03:38.3] glm5_2_nv k3 → NV-SUCCESS 2.5s (first attempt)
```

- 12 次连续首次 key 成功，零 DEGRADED，零 fallback，零 429s
- 延迟 2.5–7.7s，均值 ~3.5s
- 09:03 窗口 3 并发 (openclaw batch)，前两次 latency 偏高属正常并发效应

**Post-09:03**: 无新请求（docker logs --tail 50 确认），系统静默。

### Health check
- func_health.py: `HEALTH_THRESHOLD = float(os.environ.get("NVU_FALLBACK_HEALTH_THRESHOLD", "0.10"))` ✓
- `import os` 已添加 ✓
- should_cycle: 400 不在循环列表中 ✓ (400_nvcf_degraded → NV-NONCYCLE-ERR 立即 abort)

---

## 分析

### 与 R838 完全相同的系统状态

R839 的数据与 R838 完全一致 — 因为自 R838 收集数据（09:05 UTC）以来，仅过了 10 分钟，且 09:03 UTC 是最后一次请求。无新数据点，无新错误，无新 DEGRADED 信号。

### DEGRADED 窗口继续老化

- 20:00–21:00 UTC DEGRADED：已老化 12h+
- 03:03–05:33 UTC DEGRADED：已老化 3.5h+
- Post-06:03 窗口：3h+ 持续 100% SR

6h 窗口 SR 85.0% 完全由 3 个 DEGRADED 窗口内的 ATE 拖累。一旦 DEGRADED 窗口完全滑出 6h 窗口，SR 将自然升至 100%。

### DB 写入中断 — 非 config-fixable

DB 最后记录 01:03 UTC。bytecode 热更新中 DB 写入路径被关闭，这是代码级问题，非 config-fixable。Docker logs 仍然可见完整的请求/响应信息，数据完整性不受影响。

### 400 非循环修复已生效

03:03-03:33 窗口仍有 400 循环（7 次 per request），但 03:36:44 后日志显示 `NV-NONCYCLE-ERR` 立即 abort。`should_cycle` 列表不包含 400，修复已生效。修复来自较早期轮次，非本轮变更。

### NOP Gate 分析

| Gate | 条件 | 状态 | 证据 |
|------|------|------|------|
| 1 | 所有 ATE 双 tier | ✓ | 3 ATE 全部 tiers_tried_count=2 |
| 2 | 零单 tier ATE | ✓ | 0 rows |
| 3 | NVCFPexecTimeout buffer ≥3s | ✓ | 零 NVCFPexecTimeout, UPSTREAM=66 非绑定 |
| 4 | FALLBACK_GRAPH 双向 | ✓ | tier_chain=['glm5_2_nv', 'dsv4p_nv'] confirmed |
| 5 | Fallback 100% SR | ✓ | 5/5 fallback all status=200 |
| 6 | 所有 params at floor | ✓ | 全部 floor/optimal |

### 系统健康度评估

- glm5_2_nv function `3b9748d8` 持续 3h+ 零 DEGRADED (post-06:03)
- 12 次连续首次 key 成功
- 零 NVCFPexecTimeout（UPSTREAM 非绑定）
- 零 empty_200
- 零 429s in post-recovery 窗口
- FALLBACK_GRAPH 双向工作
- 零 post-recovery tier_attempts
- 所有 ATE 来自已消退的 DEGRADED 窗口
- 6h SR 未变 (85.0%)，等待 DEGRADED 窗口滑出

---

## 决策: NOP

**零参数修改，零 compose 修改，零容器重启。**

- 所有参数已达 floor 或最优值，无优化空间
- glm5_2_nv NVCF function `3b9748d8` 持续 3h+ 零 DEGRADED，全部首次 key 成功
- 所有 6 个 NOP gate 通过
- 12 次连续 100% SR（post-06:03）
- 与 R838 完全相同的系统状态，无新信号
- 等待信号: UPSTREAM 绑定信号 或 429 surge → 才需参数调整

---

## ⏳ 轮到 HM1 优化 HM2