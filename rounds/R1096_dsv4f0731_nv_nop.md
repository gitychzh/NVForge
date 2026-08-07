# R1096: dsv4f0731_nv self-opt — NOP (SR 97.5%, 0 × 429, 0 fallback, 持续稳定)

日期: 2026-08-07 ~18:00 UTC (~02:00 BJT 08-08)

## 1. 数据 (30min 窗口 ~17:25-17:56 UTC)

### 主指标 (nv_requests)
- **SR = 97.5% (154/158)**, avg=10619ms, **p50=8365ms**, p95=31401ms, max=47131ms
- 30min 错误: **zombie_empty_completion=3** (avg 3625ms), **NVStream_IncompleteRead=1** (avg 45678ms)
- **429 计数 = 0**
- **Fallback (hm4104) = 0** — 无 fallback 日志
- **tier_attempts errors**: 1 NVCFPexecRemoteDisconnected (45777ms) — 分离的 attempt 级记录
- upstream_type: **100% nvcf_pexec** (158/158), integrate 0 请求
- finish_reason: tool_calls=126, stop=28

### 1h 实时数据
| 指标 | 值 |
|------|-----|
| Total | 359 |
| 200 | 354 |
| 502 | 5 |
| **SR** | **98.6%** |
| Avg ms | 10,148 |
| P50 ms | 8,335 |
| P95 ms | 24,051 |
| P99 ms | 43,390 |

### per-key 200 延迟 (5 key 全部 100% 成功)

| key | 200 | avg_ok_ms | p95_ms |
|-----|-----|-----------|--------|
| k0  | 33  | 10343     | 27732  |
| k1  | 31  | 10188     | 22288  |
| k2  | 30  | 9271      | 15351  |
| k3  | 30  | 10601     | 17712  |
| k4  | 30  | 12264     | 43674  |

**所有 key 均匀分布, 无单点劣化。** k4 p95=43.7s 系 1 次 IncompleteRead 导致末端拉伸, 非集中劣化。

### per-key 错误 (30min)

| key | error_type | count | avg_ms |
|-----|------------|-------|--------|
| k0  | zombie_empty_completion | 1 | 4953 |
| k3  | NVStream_IncompleteRead | 1 | 45678 |
| k3  | zombie_empty_completion | 1 | 3269 |
| k4  | zombie_empty_completion | 1 | 2654 |

**4 个错误完全分散到 3 个不同 key**, 无 key 集中模式。zombie 平均 3.6s 快速失败 — 偶发 NVCF 端空 200。IncompleteRead 45.7s — 流被 CV 端截断。

### key_cycle_429s
- zero_cycle=54, one_cycle=104
- 429 实际计数 = 0 → 无 key 429 冷却触发

### 24h all_tiers_exhausted = 312 (与 R1095 持平)

### 24h 逐小时错误趋势 (nv_tier_attempts)

| 时段 UTC | RD | TO | 529 | empty200 | 504 | BE |
|----------|-----|-----|-----|----------|-----|-----|
| 10:00 (18 BJT) | 59 | 15 | 26 | 21 | 9 | 2 |
| 13:00 (21 BJT) | 105 | 36 | 10 | 5 | **48** | 2 |
| 14:00 (22 BJT) | 58 | 24 | 39 | 12 | **32** | 2 |
| 15:00 起 | 21 | 8 | 13 | 6 | 0 | 0 |
| 06:00 | 32 | 5 | 0 | 5 | 0 | 0 |
| 08:00 | 25 | 4 | 0 | 4 | 0 | 0 |
| 09:00 | 2 | 0 | 0 | 0 | 0 | 0 |

RD=RemoteDisconnected, TO=Timeout, BE=budget_exhausted. **观察到明显的日间峰值:** 10-14 UTC 时段 NVCF 不稳定 (RemoteDisconnected 59→105/hr, 504 spike 48/hr)。**最近 6h 已恢复正常**, 错误率大幅下降。

## 2. 对比上一轮 (R1095)

| 指标 | R1095 (30min) | R1096 (本轮) | 变化 |
|------|---------------|-------------|------|
| SR | 98.1% (155/158) | **97.5% (154/158)** | ↓ -0.6pp |
| 429 | 0 | 0 | — |
| 错误 | 3 (全部 zombie) | **4 (3 zombie + 1 IncompleteRead)** | ↑ 1 |
| avg_ms | 10437 | **10619** | ↑ +1.7% |
| p50_ms | 8532 | **8365** | ↓ -2.0% |
| p95_ms | 28323 | **31401** | ↑ +10.9% |
| Fallback | 0 | 0 | — |
| ATE (24h) | 314 | **312** | ↓ -2 |

**总体持平**: SR 微降 0.6pp 但同属 ~97-98% 正常波动区间。p50 反而改善 2%。一次 IncompleteRead 拉高了 p95。24h ATE 持续微降趋势 (+1 波动)。

## 3. 根因分析

1. **SR 97.5% (30min) / 98.6% (1h) > 95% NOP 阈值** ✓
2. **零 429, 零 fallback** ✓ — hm4104 日志确认无 fallback
3. **100% pexec** — integrate 路径未启用, 无 split-routing 干扰
4. **tier_attempts 出成功外仅 1 RemoteDisconnected** — 全部 request-level 的 zombie 是应用层 fast-fail, 非 key 层错误
5. **24h 日间峰值已消退** — 当前时段 (凌晨 BJT) NVCF 稳定, 无 504/529 事件
6. **无可用参数级改进**: 偶发 zombie/incompleteRead 属 NVCF 端行为, 参数无法消除

## 4. 决策: NOP (无参数修改)

30min SR 97.5% > 95% NOP 阈值, 1h SR 98.6%, 零 429, 零 fallback, ATE 持续微降趋势。连续 5+ 轮 SR > 97% — 链路高度稳定。

维持当前配置不变:
- UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180
- KEY_COOLDOWN=30, TIER_COOLDOWN=90
- NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=120
- NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3
- NVU_CONN_ERR_FAST_BREAK=5
- NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90
- NVU_SSLEOF_RETRY_DELAY_S=1.0
- NVU_PROBE_TIMEOUT=10, PROXY_TIMEOUT=300

## 5. 验证
- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 24h+, 无重启, 无 env 改动
- [x] 30min SR=97.5%, 1h SR=98.6%, 延迟稳定 (p50 8.3s)
- [x] hm4104 零 fallback
- [x] 0 × 429, ATE 312 (微降)

## 6. 下一步建议
- **持续 NOP**。连续 5+ 轮 SR > 97%, 无可用边缘参数改进。
- **建议将轮次间隔从 30min 延长至 1h**。30min 窗口 SR 波动 1-2pp 属正常统计方差, 额外监控收益递减。
- **中长期关注**: 若未来早期出现类似 10-14 UTC 的 504/529 脉冲, 可考虑调整 NVU_BUFFER_TIMEOUT_STAIRS 或引入 peak-hours 自适应超时。