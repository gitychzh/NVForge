# R1233: HM2→HM1 — NOP (all params floor/optimal, failures NVCF content-filter zombie + ms_gw BrokenPipeError code-level)

**决策**: NOP — 零参数变更。所有参数位于 floor/optimal 值，剩余失败均为 code-level 缺陷（非 config-fixable）。

## 数据收集

### 容器状态
- 容器: nv_gw, Up 19 minutes (healthy), 重启于 2026-07-13T10:44:55Z
- Compose MD5: 832ef9ff2d975396154a2880a8938908

### 6h DB 总览
| 指标 | 值 |
|------|-----|
| 总请求 | 104 |
| 成功 (200) | 80 |
| 失败 | 24 |
| SR% | 76.9% |

### Per-Model 分解
| Model | Reqs | OK | Fail | SR% | Avg Dur | Max Dur |
|-------|------|-----|------|-----|---------|---------|
| glm5_2_nv | 96 | 77 | 19 | 80.2% | 50,297ms | 188,328ms |
| dsv4p_nv | 8 | 3 | 5 | 37.5% | 55,866ms | 142,677ms |

### 错误分类 (6h)
| Error Type | Count | Config-Fixable? |
|-----------|-------|-----------------|
| zombie_empty_completion | 12 | ❌ NVCF content-filter, code-level zombie detection (R1107) |
| all_tiers_exhausted | 11 | ❌ ms_gw BrokenPipeError code-level defect |
| NVStream_IncompleteRead | 1 | ❌ Transient, not config-fixable |

### 上游类型分布
| upstream_type | Reqs | OK | SR% |
|--------------|------|-----|-----|
| nv_integrate | 84 | 72 | 85.7% |
| (null/ATE) | 11 | 0 | 0% |
| nvcf_pexec | 9 | 8 | 88.9% |

### Hourly SR
| Hour (UTC) | Total | OK | SR% |
|-----------|-------|-----|-----|
| 08:00 | 31 | 22 | 71.0% |
| 09:00 | 27 | 22 | 81.5% |
| 10:00 | 42 | 33 | 78.6% |
| 11:00 | 4 | 3 | 75.0% |

### 最近10条请求
- 全部 glm5_2_nv integrate, 9/10 OK (1 zombie_empty), ttfb ~5-11s, dur ~5-15s
- 无 dsv4p_nv 最近流量 (post-restart 窗口)

### Tier Attempts (仅失败)
- glm5_2_nv IntegrateTimeout: 6次, avg 91,331ms, max 93,529ms
  - Key分布: k0=3, k2=1, k3=2
  - NVU_INTEGRATE_THINKING_TIMEOUT_S=90 binding (91s avg ≈ 90s + overhead)
- 0 NVCFPexecTimeout (pexec路径干净)

### ms_gw
- 6h: 16 reqs, **0 OK** (0% SR)
- ms_gw logs: `MS-STREAM-CLIENT-EOF` / `BrokenPipeError` pattern — nv_gw disconnects mid-stream
- Code-level streaming relay defect, not config-fixable

### 关键日志
- tier_chain: `(no fallback, 3model)` — 预期状态 (post-R832 FALLBACK_GRAPH={})
- NV-MS-FB: 无消息 (ms_gw fallback 静默失败，BrokenPipeError kills relay)
- NV-PEER-FB: 0次触发
- NV-TIER-FAIL: 无消息
- NV-EMPTY-FASTBREAK: 无消息
- NV-ZOMBIE: 2次检测，正确 abort + error-chunk 发送

### 当前参数 (已确认 floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 210 | generous (R1231 +12s) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal (R1031) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | optimal |
| TIER_COOLDOWN_S | 15 | optimal (R1103) |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal (aligned with UPSTREAM) |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor (integrate active) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal (R1116) |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal (R1035) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | near-binding (91s avg ≈ 90s) |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal |

## 诊断

### 12 zombie_empty_completion → NVCF content-filter (R1107 pattern)
- 全部 glm5_2_nv integrate, NVCF 返回 finish_reason=stop + content_chars < 50 + input_chars ≥ 5000
- Gateway zombie detection 正确 abort (3-40s), 发送 error-chunk 触发 openclaw fallback
- **Code-level feature, not config-fixable**. Fast abort 优于旧 96s hang.

### 11 all_tiers_exhausted → ms_gw BrokenPipeError (code-level defect)
- 5 dsv4p_nv: tiers_tried=1, fallback_actually_attempted=f, dur 25-142s
  - 142s ATE: NVU_TIER_BUDGET_DSV4P_NV=72 exhaust → ms_gw budget = 210-72=138s → ms_gw BrokenPipeError
- 6 glm5_2_nv: tiers_tried=1, fallback_actually_attempted=f, dur ~187s
  - 187s ATE: NVU_INTEGRATE_THINKING_TIMEOUT=90 exhaust → ms_gw budget = 210-96=114s → ms_gw BrokenPipeError
- ms_gw 0/16 OK, `MS-STREAM-CLIENT-EOF` / `BrokenPipeError` — nv_gw 中途断开 relay
- **Code-level streaming relay defect**. BUDGET 已扩大至 210 (R1231), 超过 ms_gw 实际处理时间, 但 relay 仍 BrokenPipeError.

### NVU_INTEGRATE_THINKING_TIMEOUT_S=90 near-binding
- IntegrateTimeout avg=91,331ms, max=93,529ms. 90s binding (91s ≈ 90s + overhead).
- 考虑是否 +10s→100s: 但 integrate 失败根因是 NVCF content-filter (zombie) + NVCF genuine exhaustion (187s ATE >> 100s), 非 thinking timeout 可修.
- 提至 100s 会让僵尸请求多等 10s, 对 SR 无改善 (content-filter 照样返回空内容).
- **保留 90s** — fast abort 优于延长等待.

### Peer FB 未触发
- 0 [NV-PEER-FB] 日志消息。Peer FB 仅在 hop=1 (peer-originated) 请求触发 (R744 code-level defect).
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv 阻止 glm5_2_nv 转发给 HM2 (避免 HM2→HM1→HM2 循环).

## 结论
**NOP** — 零参数变更。所有可配置参数位于 floor/optimal 值:
- 12/24 失败 = zombie_empty_completion (NVCF content-filter, code-level zombie detection → 正确 abort)
- 11/24 失败 = all_tiers_exhausted (ms_gw BrokenPipeError code-level defect)
- 1/24 失败 = NVStream_IncompleteRead (transient)
- 0/24 失败 = config-fixable

铁律:只改HM1不改HM2。0 param.

## ⏳ 轮到HM1优化HM2