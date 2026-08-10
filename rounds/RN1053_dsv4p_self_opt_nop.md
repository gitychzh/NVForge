# RN1053: NOP — SR 95.8%，单异型瞬态 NVStream_IncompleteRead，链路健康无参数改动依据

**时间**: 2026-08-10 09:48 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 30min SR=95.8% 高于 95% NOP 阈值，仅 1 个异型瞬态错误 (NVStream_IncompleteRead, k3)，无 429 无 fallback 无单 key 劣化，无参数改动依据。

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 24 / 23 / 1 |
| SR (30min) | **95.8%** |
| Avg / P50 / P95 | 36228ms / 27658ms / 105002ms |
| 429 计数 | 0 |
| 错误分类 | NVStream_IncompleteRead 1 (31985ms, k3) |

## 错误分析（为何判 NOP 而非调参）

1. **NVStream_IncompleteRead (31985ms, k3)**：流被上游截断，单次发生（错误计数 1），显著低于 fast-break 阈值 (NVU_PEXEC_TIMEOUT_FASTBREAK=3)。与 RN1052 同型同 key (k3)，均为独立瞬态，非配置可归因问题。
2. **无 all_tiers_exhausted**：本窗口 ATE=0。TIER_TIMEOUT_BUDGET=180 与 5-key 轮转正常，无预算耗尽。
3. **无 429 无 fallback**：key_cycle_429s (k0=16,k1=5,k2=2,k3=1) 为正常 key 轮转累计，非配额竞争。hm4104 fallback 日志最近 5min 为空。
4. **per-key 全部健康**：5 key 200 延迟正常（k0=6/61838, k1=6/39879, k2=3/13747, k3=4/31963, k4=4/14525），仅 k3 携带 1 次 IncompleteRead，无集中失败。

## 趋势与归因

- **6h**: 580 总 / 554 成功 / 26 错, SR=**95.5%**（整体稳定）
- **3h 逐小时**: 01:00=62/59(95.2%) / 00:00=101/93(92.1%) / 23:00=148/146(98.6%) / 22:00=15/14(93.3%)
  - 小时级稳定 92-99%，无持续性退化。00:00 波谷 (92.1%) 由低量子夜窗口瞬态驱动。
- **24h all_tiers_exhausted**: 291（日内累计，本窗口 0 例，主要源于白天高负载时段累积，非新增问题，与 RN1052 持平）
- **RN1052(97.9%) → RN1053(95.8%)**：单例 IncompleteRead 即可造成的小幅波动，属正常噪声，链路主体稳定。

## 其他状态

- upstream_type: nvcf_pexec 24 请求, SR 95.8%, 纯 pexec 路径 (100%)，无 integrate 分流失衡
- finish_reason: tool_calls 18 / stop 5（工具调用为主，正常长生成负载）
- hm4104 fallback: 0（最近 5min 无 fallback 日志，primary 链路直连稳定）
- tier_attempts: 空（本窗口无 key 级失败切换记录）
- /health: ok, 5 keys, port 40666
- 容器: Up About an hour

## 当前参数 (env 实测，无漂移)

```
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, UPSTREAM_TIMEOUT=45,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5,
NVU_PEER_FALLBACK_ENABLED=0, NVU_PEER_FB_SKIP_MODELS=全部,
NV_INTEGRATE_MODELS=空, NV_KEY_INTEGRATE_KEYS=空 (纯 pexec),
PROXY_ROLE=passthrough, PROXY_TIMEOUT=300
```
参数与上轮一致，全链稳定，无漂移。

## 验证

- [x] /health → status ok, nv_num_keys=5
- [x] `docker exec dsvf0731_nv40666 env` 参数未漂移 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, TIER_COOLDOWN=90, KEY_COOLDOWN=30, fast-break=3)
- [x] 容器 Up About an hour，无参数修改，无需重启

## 结论

本窗 30min SR=95.8% 稍高于 95% NOP 阈值，链路健康。�。仅 1 个异型瞬态错误 (NVStream_IncompleteRead, k3) 低于 fast-break 阈值，无 429 无 fallback 无单 key 劣化无 ATE。与 RN1052 同型同 key 的独立瞬态，非持续性退化。所有候选参数均无本地化数据支撑改动。遵循"改前必有数据 + 一次只改一个参数 + stability first"铁律，本窗 **NOP**。不追逐噪声。

## 下一步建议

1. **持续监视 k3 IncompleteRead**：RN1052 与 RN1053 连续两窗 k3 均出现单例 NVStream_IncompleteRead。若第 3 窗口 k3 再次出现且错误数上升，再针对 k3 的 SOCKS5 出口 (7904) 评估独立冷却/与 k0(7897) 交换代理槽。
2. **持续观察 24h ATE=291**：若负载回落后（非白天高峰期）仍继续频繁 ATE，再审视是否需临时放宽 NVU_TIER_BUDGET；否则确认为 NVCF 白天过载累积。
3. **维护 NOP** 是稳定优先的正确行为，仅当出现本地化/持续性退化信号才调参。