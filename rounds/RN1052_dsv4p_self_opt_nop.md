# RN1052: NOP — SR 回升至 97.9%，单异型瞬态 NVStream_IncompleteRead，链路健康无参数改动依据

**时间**: 2026-08-10 08:45 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 30min SR=97.9% 高于 95% NOP 阈值，仅 1 个异型瞬态错误 (NVStream_IncompleteRead, k3)，无 429 无 fallback 无单 key 劣化，无参数改动依据。

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 47 / 46 / 1 |
| SR (30min) | **97.9%** |
| Avg / P50 / P95 | 32344ms / 16699ms / 119716ms |
| 429 计数 | 0 |
| 错误分类 | NVStream_IncompleteRead 1 (35621ms, k3) |

## 错误分析（为何判 NOP 而非调参）

1. **NVStream_IncompleteRead (35621ms, k3)**：流被上游截断，单次发生（错误计数 1），显著低于 fast-break 阈值 (NVU_PEXEC_TIMEOUT_FASTBREAK=3)。NVCF 端瞬时抖动，非配置可归因问题。
2. **无 all_tiers_exhausted**：本窗口 ATE=0（对比 RN1051 的 1 例，已消除）。TIER_TIMEOUT_BUDGET=180 与 5-key 轮转正常，无预算耗尽。
3. **无 429 无 fallback**：key_cycle_429s (k0=36,k1=5,k2=4,k3=2) 为正常 key 轮转累计，非配额竞争。hm4104 fallback 日志最近 5min 为空。
4. **per-key 全部健康**：5 key 全部 0 错误。k0=7req/28144, k1=10/49914, k2=14/30345, k3=8/27072, k4=7/20999。k1 avg=49914 略高但无错误、无集中失败，属健康方差，非劣化信号。

## 趋势与归因

- **6h**: 516 总 / 492 成功 / 24 错, SR=**95.3%**（整体稳定）
- **3h 逐小时**: 00:00=55/52(94.5%) / 23:00=148/146(98.6%) / 22:00=115/112(97.4%) / 21:00=77/76(98.7%)
  - 小时级稳定 94-99%，高负载时段 (21:00-23:00) 稳定 97-99%，无持续性退化。
- **24h all_tiers_exhausted**: 290（日内累计，本窗口 0 例，主要源于白天高负载时段累积，非新增问题）
- **RN1051(90.3%) → RN1052(97.9%)**：波谷由低量子夜窗口 3 个异型瞬态错误驱动，本窗口已自然恢复，确认属 NVCF 过载瞬态而非参数退化。

## 其他状态

- upstream_type: nvcf_pexec 47 请求, SR 97.9%, 纯 pexec 路径 (100%)，无 integrate 分流失衡
- finish_reason: tool_calls 41 / stop 5（工具调用为主，正常长生成负载）
- hm4104 fallback: 0（最近 5min 无 fallback 日志，primary 链路直连稳定）
- tier_attempts: 空（本窗口无 key 级失败切换记录）
- /health: ok, 5 keys, port 40666
- 容器: Up 3 hours

## 当前参数 (env 实测，无漂移)

```
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, UPSTREAM_TIMEOUT=45,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5, NVU_BUFFER_MAX_RETRIES=5,
NVU_PEER_FALLBACK_ENABLED=0, NVU_PEER_FB_SKIP_MODELS=全部,
NV_INTEGRATE_MODELS=空, NV_KEY_INTEGRATE_KEYS=空 (纯 pexec),
PROXY_ROLE=passthrough, PROXY_TIMEOUT=300
```
参数与上轮一致，全链稳定，无漂移。

## 验证

- [x] /health → status ok, nv_num_keys=5
- [x] `docker exec dsvf0731_nv40666 env` 参数未漂移 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, TIER_COOLDOWN=90, KEY_COOLDOWN=30, fast-break=3)
- [x] 容器 Up 3 hours，无参数修改，无需重启

## 结论

本窗 30min SR=97.9% 高于 95% NOP 阈值，链路健康。仅 1 个异型瞬态错误 (NVStream_IncompleteRead, k3) 低于 fast-break 阈值，无 429 无 fallback 无单 key 劣化无 ATE。RN1051 的波谷已自然恢复（90.3%→97.9%），确认属低流量窗口 NVCF 过载瞬态而非参数退化。所有候选参数均无本地化数据支撑改动。遵循"改前必有数据 + 一次只改一个参数 + stability first"铁律，本窗 **NOP**。不追逐噪声。

## 下一步建议

1. **设监视判据**：若 SR<95% 连续 ≥2 个窗口复现，或某单一错误类型/某单一 key 在后续窗口集中出现（而非异型散布），再针对该 key 的 SOCKS5 出口评估给独立冷却/标记。当前 k1 avg=49914 略高，若 3 轮内持续领先并伴随错误再考虑 key 隔离。
2. **持续观察 24h ATE=290**：若负载回落后（非白天高峰期）仍继续频繁 ATE，再审视是否需临时放宽 NVU_TIER_BUDGET；否则确认为 NVCF 白天过载累积。
3. **维护 NOP** 是稳定优先的正确行为，仅当出现本地化/持续性退化信号才调参。