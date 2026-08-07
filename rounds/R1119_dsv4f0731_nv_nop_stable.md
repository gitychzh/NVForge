# R1119 — dsv4f0731_nv40666 NOP (持续稳定)

## 结论
**不修改参数。** 系统维持高稳定运行状态：30min SR=99.2%，0 次 429，0 fallback，all pexec。

## 当前状态 (30min 窗口 00:40~01:10 UTC+8)

| 指标 | 值 |
|------|------|
| 请求数 | 129 |
| 成功数 | 128 |
| SR | 99.22% |
| Avg/P50/P95/P99 | 13,194ms / 9,592ms / 40,963ms / 70,124ms |
| 错误 | 1 NVStream_IncompleteRead (k3, 55,488ms) |
| 429 | 0 |
| fallback (hm4104, 5min) | 0 |
| upstream | 100% nvcf_pexec |
| finish_reason: tool_calls | 102 (79.1%) |
| finish_reason: stop | 26 (20.2%) |
| key_cycle_429s | k0=22, k1=106, k2=1 (cycle counts, not errors) |

## Per-Key 性能 (30min)

| Key | Success | avg_ms | max_ms | Errors |
|-----|---------|--------|--------|--------|
| k0 | 29 | 13,203 | 31,666 | 0 |
| k1 | 26 | 13,733 | 27,886 | 0 |
| k2 | 19 | 10,138 | 35,875 | 0 |
| k3 | 32 | 15,751 | 44,710 | 1 NVStream_IncompleteRead (55,488ms) |
| k4 | 22 | 9,544 | 15,612 | 0 |

Per-key 分布均衡。k3 有 1 次 IncompleteRead（55s 截断）— 大概率是 NVCF 远端流截断，非容器侧可调参数。k1 的 key_cycle_429s=106 是 cycle 计数（跨 key 尝试次数），并非实际 429 错误（实际 429=0）。

## 趋势

| 时段 | Total | Success | Failed | Fallback | Avg Latency |
|------|-------|---------|--------|----------|-------------|
| 30min | 129 | 128 | 1 | 0 | 13,194ms |
| 3h 14:00 | 245 | 244 | 1 | 0 | 11,915ms |
| 3h 15:00 | 292 | 291 | 1 | 0 | 11,967ms |
| 3h 16:00 | 273 | 273 | 0 | 0 | 13,430ms |
| 3h 17:00 | 40 | 39 | 1 | 0 | 12,625ms |
| **6h total** | **1,761** | **1,748** | **13** | **0** | — |
| **6h SR** | | **99.26%** | | | |

### 24h all_tiers_exhausted: 132

## 当前参数 (未改动)

| 参数 | 值 |
|------|------|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |
| NVU_PROBE_TIMEOUT | 10 |
| NV_KEY_INTEGRATE_KEYS | (空 — 未启�� integrate) |

## NOP 原因

1. **30min SR=99.2%** — 高于 95% 阈值，无需修改
2. **6h SR=99.3%** — 持续稳定，无退化趋势
3. **0 次 429** — 无 rate limit 问题
4. **0 fallback** — hm4104 无 fallback 触发
5. **错误极低** — 仅 1 NVStream_IncompleteRead（NVCF 流截断，非可调参数范围）
6. **Per-key 均衡** — 各 key 延迟分布在 9,544~15,751ms，无单 key 劣化
7. **全部 pexec** — integrate 未启用，pexec 链路质量好
8. **24h all_tiers_exhausted=132** — 约 2.2% ATE 率（基于 24h ~6k 请求），正常范围

## 上次修改效果 (R1118 → R1119)

R1118 报告 30min SR=99.3%，当前 30min SR=99.2% — 持续稳定在 99%+ 级别。6h SR 99.3% 与 R1118 持平。未发生退化。

## 下一步建议

- 保持观察。当以下信号出现时考虑调整：
  - 429 回升 → 增加 `KEY_COOLDOWN_S` 到 60s
  - RemoteDisconnected/overloaded 频发（30+/h）→ 降低 `UPSTREAM_TIMEOUT` 到 60s 加速 key 循环
  - 某 key 错误率 >10% → 考虑从路由池移除
- 当前不启用 integrate.api — pexec 链路表现好，无切换必要