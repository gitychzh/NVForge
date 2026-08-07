# R1095: dsv4f0731_nv self-opt — NOP (SR 98.1%, 0 × 429, 0 fallback, 连续多轮稳定)

日期: 2026-08-07 ~17:50 UTC (~01:50 BJT 08-08)

## 1. 数据 (30min 窗口 ~17:20-17:50 UTC)

### 主指标 (nv_requests)
- **SR = 98.1% (155/158)**, avg=10437ms, **p50=8532ms**, p95=28323ms, max=46901ms
- 30min 错误: **zombie_empty_completion=3** (avg 3625ms) — 全部是快速空响应
- **429 计数 = 0**
- **Fallback (hm4104) = 0** — 无 fallback 日志
- **tier_attempts: 空** — 全部 first-attempt 成功, 无 tier 切换
- upstream_type: **100% nvcf_pexec** (159/159), integrate 0 请求
- finish_reason: tool_calls=126, stop=30

### per-key 200 延迟 (5 key 全部 100% 成功)

| key | 200 | avg_ok_ms | p95_ms |
|-----|-----|-----------|--------|
| k0  | 33  | 9833      | 27732  |
| k1  | 32  | 10729     | 21981  |
| k2  | 30  | 9484      | 15351  |
| k3  | 30  | 10608     | 17712  |
| k4  | 30  | 12256     | 43674  |

**所有 key 均匀分布, 无单点劣化**。k4 p95=43.7s 偏高但仅 1 次 zombie 错误, 非集中劣化。

### per-key 错误 (30min)

| key | error_type | count | avg_ms |
|-----|------------|-------|--------|
| k0  | zombie_empty_completion | 1 | 4953 |
| k3  | zombie_empty_completion | 1 | 3269 |
| k4  | zombie_empty_completion | 1 | 2654 |

**3 个 zombie 错误完全分散到 3 个不同 key**, 平均 3.6s 快速失败。表明偶发的 NVCF 端空 200 响应, 而非特定 key/代理问题。

### key_cycle_429s
- zero_cycle=50, one_cycle=109
- 429 实际计数 = 0

### 趋势 (6h)

| 时段 | total | ok | err | SR | avg_ok_ms |
|------|-------|----|-----|----|-----------|
| 06:00 UTC | 36 | 35 | 1 | 97.2% | 14411 |
| 07:00 UTC | 262 | 253 | 9 | 96.6% | 12557 |
| 08:00 UTC | 260 | 251 | 9 | 96.5% | 12495 |
| 09:00 UTC | 307 | 303 | 4 | 98.7% | 10141 |
| 30min | 158 | 155 | 3 | **98.1%** | 10437 |
| **6h** | **1671** | **1628** | **43** | **97.4%** | — |

**SR 持续稳定 ~97-98%**, 09:00 UTC 窗口 98.7% 为最佳。无退化趋势。

### 24h all_tiers_exhausted = 314 (较 R1094 的 315 微降)

## 2. 对比上一轮 (R1094)

| 指标 | R1094 (30min) | R1095 (本轮) | 变化 |
|------|---------------|-------------|------|
| SR | 97.3% (145/149) | **98.1% (155/158)** | ↑ +0.8pp |
| 429 | 0 | 0 | — |
| 错误 | 4 (3 zombie + 1 IncompleteRead) | **3 (全部 zombie)** | ↓ 1 |
| avg_ms | 10888 | **10437** | ↓ -4.1% |
| p50_ms | 8687 | **8532** | ↓ -1.8% |
| p95_ms | 31856 | **28323** | ↓ -11.1% |
| Fallback | 0 | 0 | — |
| ATE (24h) | 315 | **314** | ↓ -1 |

**一致性改善**: SR ↑, 延迟 ↓, 错误数 ↓。R1094 的 NVStream_IncompleteRead (35.5s) 本次消失, 只剩 zombie。

## 3. 决策: NOP (无参数修改)

30min SR 98.1% > 95% NOP 阈值, 6h 97.4%, 零 429, 零 fallback, 趋势持续稳定改善。无待调参数。

维持当前配置不变:
- UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180
- KEY_COOLDOWN=30, TIER_COOLDOWN=90
- NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=120
- NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3
- NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90
- NVU_PROBE_TIMEOUT=10, PROXY_TIMEOUT=300

## 4. 验证
- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 24h+, 无重启, 无 env 改动
- [x] 30min SR=98.1%, 6h SR=97.4%, 延迟稳定 (p50 8.5s)
- [x] hm4104 零 fallback

## 5. 下一步建议
- **持续 NOP**。连续 5+ 轮 SR > 97% 且持续改善 (97.3%→98.1%), 无可用参数级改进。
- **考虑延长轮次间隔至 1h**: 链路高度稳定, 30min 窗口收益递减。建议下一轮改为 1h 数据窗口。
- 关注 R1093/R1094 报告的 FID 路由泄漏问题 (52e1ddb6 旧 FID 约 12% attempt 泄漏)。当前 SR 98.1% 下不迫切, 但若退化可优先排查上游代码。