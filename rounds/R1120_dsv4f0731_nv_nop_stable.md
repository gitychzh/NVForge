# R1120 — dsv4f0731_nv40666 NOP (持续稳定)

## 结论
**不修改参数。** 系统维持高稳定运行状态：30min SR=99.3%，0 次 429，0 fallback，all pexec。

## 当前状态 (30min 窗口 00:32~01:02 UTC)

| 指标 | 值 |
|------|------|
| 请求数 | 136 |
| 成功数 | 135 |
| SR | 99.26% |
| Avg/P50/P95/P99 | 14,500ms / 9,989ms / 43,053ms / 103,375ms |
| 错误 | 1 NVStream_IncompleteRead (k3, 55,488ms) |
| 429 | 0 |
| fallback (hm4104, 5min) | 0 |
| upstream | 100% nvcf_pexec |
| finish_reason: tool_calls | 109 (80.1%) |
| finish_reason: stop | 26 (19.1%) |
| key_cycle_429s | k0=16, k1=118, k2=1, k3=1, k4=0 (cycle counts, not errors) |

## Per-Key 性能 (30min)

| Key | Success | avg_ms | Errors |
|-----|---------|--------|--------|
| k0 | 31 | 17,938 | 0 |
| k1 | 27 | 10,280 | 0 |
| k2 | 23 | 9,779 | 0 |
| k3 | 27 | 19,432 | 1 NVStream_IncompleteRead (55,488ms) |
| k4 | 27 | 12,342 | 0 |

Per-key 基本均衡。k3 单一 IncompleteRead 发生在 55.5s → 在 UPSTREAM_TIMEOUT=90s 范围内，属 NVCF 远端流截断。k0 avg=17.9s 略高于均值，但无实际错误。

## 趋势

| 时段 | Total | Success | Failed | Fallback | Avg Latency |
|------|-------|---------|--------|----------|-------------|
| 30min | 136 | 135 | 1 | 0 | 14,500ms |
| 3h 14:00 | 150 | 150 | 0 | 0 | 11,269ms |
| 3h 15:00 | 292 | 291 | 1 | 0 | 11,967ms |
| 3h 16:00 | 273 | 273 | 0 | 0 | 13,430ms |
| 3h 17:00 | 145 | 144 | 1 | 0 | 13,827ms |
| **6h total** | **1,738** | **1,728** | **10** | **0** | — |
| **6h SR** | | **99.42%** | | | |

### 24h request-level SR: 97.0% (5,793/5,974) — fallback: 0

24h 指标低于 30min/6h 的原因是前 12h (UTC 17:00~05:00) 有较多 NVCFPexecRemoteDisconnected (504 events) 和 529_nv_overloaded (65)，但在最后 6h 已完全消退。错误集中在过去时段，当前窗口稳定。

### 24h tier-level 错误分类:

| error_type | count | avg_ms | p50_ms | p95_ms |
|------------|-------|--------|--------|--------|
| pexec_success | 4,809 | 3,976 | 3,452 | 7,509 |
| NVCFPexecRemoteDisconnected | 504 | 40,050 | 35,648 | 60,640 |
| NVCFPexecTimeout | 88 | 28,738 | 26,249 | 56,697 |
| empty_200 | 66 | — | — | — |
| 529_nv_overloaded | 65 | — | — | — |
| 504_nv_gateway_timeout | 12 | — | — | — |

### 24h all_tiers_exhausted (dsv4f0731_nv 专查): 0

注意：预采集脚本报告的 "24h ATE=129" 来自其他模型 tier，dsv4f0731_nv 本窗口 ATE=0。

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
| NV_KEY_INTEGRATE_KEYS | (空 — 未启用 integrate) |

## NOP 原因

1. **30min SR=99.3%** — 高于 95% 阈值，无需修改
2. **6h SR=99.4%** — 持续稳定，无退化趋势
3. **0 次 429** — 无 rate limit 问题
4. **0 fallback** — hm4104 无 fallback 触发
5. **错误极低** — 仅 1 NVStream_IncompleteRead（NVCF 流截断，非可调参数范围）
6. **Per-key 均衡** — 各 key 延迟分布在 9,779~19,432ms，无单 key 劣化
7. **全部 pexec** — integrate 未启用，pexec 链路质量好
8. **24h ATE=0** — 无 tier 级耗尽事件
9. **24h 错误集中在过去 12h** — 最后 6h 已大幅压缩（VC 08:00~13:00 只有 24×RemoteDisconnected + 7×empty_200 的残余级别）

## 上次修改效果 (R1119 → R1120)

R1119 报告 30min SR=99.2% (129 req)，30min SR 分别为 99.2% → 99.3%。6h SR 从 99.26% 略升至 99.42%。整体稳定在 99%+ 级别。未发生退化。

## 下一步建议

- 保持观察。当以下信号出现时考虑调整：
  - 429 回升 → 增加 `KEY_COOLDOWN_S` 到 60s
  - RemoteDisconnected/overloaded 频发（30+/h）→ 考虑降低 `UPSTREAM_TIMEOUT` 到 60s 加速 key 循环
  - 某 key 错误率 >10% → 考虑从路由池移除
- 当前不启用 integrate.api — pexec 链路表现好，无切换必要