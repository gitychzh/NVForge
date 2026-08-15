# RN1051: NOP — SR 下滑至 90.3% 为低量窗口 NVCF 过载瞬态（3 异型错误于 3 不同 key），无本地化可调杠杆

**时间**: 2026-08-10 08:26 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 30min SR=90.3% 虽跌破 95% 阈值，但 3 个错误为 3 种异型 (ATE/IncompleteRead/zombie) 分布于 3 个不同 key，属 NVCF 过载瞬态，无本地化 key/代理/超时可归因问题。无参数改动依据。

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 31 / 28 / 3 |
| SR (30min) | **90.3%** |
| Avg / P50 / P95 | 43297ms / 23156ms / 163772ms |
| 429 计数 | 0 |
| 错误分类 | NVStream_IncompleteRead 1 (35621ms), all_tiers_exhausted 1 (180030ms), zombie_empty_completion 1 (43561ms) |

**3 种异型错误，各 1 次，分布在 3 个不同 key**：k0=all_tiers_exhausted, k3=NVStream_IncompleteRead, k4=zombie_empty_completion。无单类型集中、无单 key 集中。

## 错误分析（为何判 NOP 而非调参）

1. **all_tiers_exhausted (180030ms, k0)**：跑满整个 180s TIER_TIMEOUT_BUDGET 后 5 key 全部瞬时不可用。这是 **NVCF 全域瞬态过载**（所有 key 同时短暂不可用），非预算不足——RN1009 已把 UPSTREAM_TIMEOUT 90→50→45，预算内已可试 180/45=4 key；若 5 key 全挂，加预算只是烧更多时间。**非可调杠杆**。
2. **NVStream_IncompleteRead (35621ms, k3)**：流被上游截断。单次发生，显著低于 fast-break 阈值 (NVU_PEXEC_TIMEOUT_FASTBREAK=3)。NVCF 端抖动，非配置问题。
3. **zombie_empty_completion (43561ms, k4)**：报告 200 但无内容。单次发生，< NVU_EMPTY_200_FASTBREAK=3。上游劣化瞬态，fast-break 机制已就位。
4. **无 429、无 fallback**：key_cycle_429s (k0=21,k1=6,k2=2,k3=2) 小于 RN1049, 无配额竞争。
5. **per-key 延迟均衡，无劣化 key**：k0=8req/41610, k1=6/47167, k2=7/36188, k3=5/35730, k4=2/17572。k4 请求少 (2) 且延迟最低，非劣化。

## 趋势与归因

- **6h**: 495 总 / 470 成功 / 25 错, SR=**95.0%**（整体稳定）
- **3h 逐小时**: 00:00=23/20(87%) / 23:00=148/146(98.6%) / 22:00=115/112(97.4%) / 21:00=89/87(97.8%)
  - **SR 下滑集中在低量子夜窗口 (00:00 UTC)**：仅 23 req/hr，3 个瞬态错误对低量窗口 SR 冲击放大；高负载时段 (21:00-23:00) 稳定 97-98%。
- **24h all_tiers_exhausted**: 291（日内累计，主要源于白天高负载时段；本窗仅 1 例 ATE）

**归因结论**：RN1049(98.9%)→RN1050(100%)→RN1051(90.3%) 的波谷出现在低流量窗口且由 3 个异型瞬态错误驱动，非持续性退化。低量窗口绝对错误数 (3) 与 RN1049 (1) / RN1050 (0) 同量级，只因分母小 (31 vs 64/90) 被放大。连续窗口趋势看无误码率级退化。

## 其他状态

- upstream_type: nvcf_pexec 31 请求, 全 pexec 路径 (100%)，无 integrate 分流失衡
- finish_reason: tool_calls 23 / stop 5（工具调用为主，正常长生成负载）
- hm4104 fallback: 0（最近 5min 无 fallback 日志，primary 链路直连稳定）
- tier_attempts: 空（本窗口无除 k0 ATE 外的 key 级失败切换）
- /health: ok, 5 keys, port 40666
- 容器: Up 3 hours

## 当前参数 (env 实测，无漂移)

```
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, UPSTREAM_TIMEOUT=45,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NV_INTEGRATE_MODELS=空, NV_KEY_INTEGRATE_KEYS=空 (纯 pexec),
PROXY_ROLE=passthrough, PROXY_TIMEOUT=300
```

## 验证

- [x] /health → status ok, nv_num_keys=5
- [x] `docker exec dsvf0731_nv40666 env` 参数未漂移 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, TIER_COOLDOWN=90, KEY_COOLDOWN=30)
- [x] 容器 Up 3 hours，无参数修改，无需重启

## 结论

本窗 30min SR=90.3% 跌破 95% NOP 阈值，但经数据归因确认为**低流量子夜窗口 + NVCF 过载瞬态**（3 异型错误分处 3 键，fast-break 均未触发，无 429 无 fallback 无单 key 劣化），非持续性参数退化。所有候选参数（TIER_TIMEOUT_BUDGET/UPSTREAM_TIMEOUT/fast-break/路由）均无本地化数据支撑改动。高负载时段稳定 97-98%，6h=95.0%。遵循"改前必有数据 + 一次只改一个参数 + stability first"铁律，本窗 **NOP**。不追逐噪声。

## 下一步建议

1. **设监视判据**：若 SR<95% 连续 ≥2 个窗口复现，或某单一错误类型/某单一 key 在后续窗口集中出现（而非异型散布），再针对该 key 的 SOCKS5 出口 (如 7904=key1 或对应 key 端口) 评估给独立冷却/标记。
2. **持续观察 24h ATE=291**：若负载回落后（非白天高峰期）仍继续频繁 ATE，再审视是否需临时放宽 NVU_TIER_BUDGET 配合更多 key 尝试；否则确认为 NVCF 白天过载累积。
3. **维护 NOP** 是稳定优先的正确行为，仅当出现本地化/持续性退化信号才调参。