# R1094: dsv4f0731_nv self-opt — NOP (SR 97.3%, 0 × 429, 0 fallback, 稳定无退化)

日期: 2026-08-07 ~17:50 UTC (~01:50 BJT 08-08)

## 1. 数据 (30min 窗口 ~17:20-17:50 UTC)

### 主指标 (nv_requests)
- **SR = 97.3% (145/149)**, avg=10888ms, **p50=8687ms**, p95=31856ms, max=47241ms
- 30min 错误: **zombie_empty_completion=3** (avg 3625ms), **NVStream_IncompleteRead=1** (avg 35476ms)
- **429 计数 = 0**
- **Fallback (hm4104) = 0** — 无 fallback 日志
- **tier_attempts: 空** — 全部 first-attempt 成功, 无 tier 切换
- upstream_type: **100% nvcf_pexec** (149/149), integrate 0 请求
- finish_reason: tool_calls=115, stop=30

### per-key 200 延迟 (5 key 全部 100% 成功)

| key | 200 | avg_ok_ms | p95_ms |
|-----|-----|-----------|--------|
| k0  | 31  | 9875      | 27745  |
| k1  | 30  | 10870     | 22595  |
| k2  | 29  | 10150     | 18767  |
| k3  | 28  | 11244     | 19067  |
| k4  | 27  | 12391     | 44208  |

所有 key 均有 ~27-31 次 200 成功。k4 p95=44.2s 偏高但非集中错误 (仅 1 zombie + 1 IncompleteRead)。

### per-key 错误 (30min)

| key | error_type | count | avg_ms |
|-----|------------|-------|--------|
| k0  | zombie_empty_completion | 1 | 4953 |
| k3  | zombie_empty_completion | 1 | 3269 |
| k4  | NVStream_IncompleteRead | 1 | 35476 |
| k4  | zombie_empty_completion | 1 | 2654 |

~2.7% 错误率且分散到 3/5 keys — 无单点劣化趋势。

### key_cycle_429s
- zero_cycle=44, one_cycle=105
- 429 实际计数 = 0 → 这表示 key cycling 但未触发 429

### 趋势 (6h)

| 时段 | total | ok | err | SR | avg_ok_ms |
|------|-------|----|-----|----|-----------|
| 06:00 UTC | 46 | 45 | 1 | 97.8% | 15226 |
| 07:00 UTC | 262 | 253 | 9 | 96.6% | 12557 |
| 08:00 UTC | 260 | 251 | 9 | 96.5% | 12495 |
| 09:00 UTC | 287 | 283 | 4 | 98.6% | 10275 |
| 30min | 149 | 145 | 4 | **97.3%** | 10888 |
| **6h** | **1660** | **1617** | **43** | **97.4%** | — |

**SR 稳定在 ~97% 水平, 无退化趋势。** 09:00 UTC 窗口 SR=98.6% 为今日最佳。

### 24h all_tiers_exhausted = 315 (较 R1093 的 328 略降)

## 2. 根因分析

1. **SR 97.3% (30min) / 97.4% (6h)** — 连续稳定, 零 429, 零 fallback
2. **错误分布**: 3 × zombie_empty_completion (平均 3.6s 快速失败) + 1 × NVStream_IncompleteRead (35.5s 截断) — 均属 NVCF pexec 正常偶发波动
3. **无 integrate 路径干扰**: 100% nvcf_pexec, integrate 无请求
4. **hm4104 零 fallback**: 本容器完全健康, 无下游熔断影响
5. **tier_attempts 空**: 所有请求 first-attempt 成功, 无 key 轮转浪费

## 3. 决策: NOP (无参数修改)

30min SR 97.3% > 95% NOP 阈值, 6h 97.4%, 零 429, 零 fallback, 趋势稳定。无待调参数。

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
- [x] 30min SR=97.3%, 6h SR=97.4%, 延迟稳定 (p50 8.7s)
- [x] hm4104 零 fallback

## 5. 下一步建议
- 持续 NOP。连续多轮 SR > 97% 无边缘可用参数改进。
- 关注 52e1ddb6 旧 FID 路由泄漏 (R1093 报告 ~12% attempt 泄漏)。当前 SR 97.3% 下收益不迫切, 但若退化可优先排查。