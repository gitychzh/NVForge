# RN1034: NOP — dsv4f0731_nv 链路 30min SR=100% (204/204), 零错误零429零fallback, 5 key 全健康均匀, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~04:44 UTC
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**改动类型**: NOP (无修改)

## 当前参数 (实测 env 确认，无漂移)

| 参数 | 当前值 |
|------|--------|
| `UPSTREAM_TIMEOUT` | 50 |
| `KEY_COOLDOWN_S` | 30 |
| `TIER_COOLDOWN_S` | 90 |
| `TIER_TIMEOUT_BUDGET_S` | 180 |
| `NVU_TIER_BUDGET_DSV4F0731_NV` | 180 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 |
| `NVU_EMPTY_200_FASTBREAK` | 3 |
| `NV_KEY_INTEGRATE_KEYS` | (空) |
| `NVU_KEYMGR_429_BASE/MAX_COOLDOWN` | 120/120 |
| `NVU_KEYMGR_CONN_BASE/MAX/LONG` | 30/60/120, THRESHOLD=3 |
| `NVU_PROBE_TIMEOUT` | 10 |
| `NVU_BUFFER_TIMEOUT_STAIRS` | 90×5 |
| `NV_INTEGRATE_EGRESS_IPS` | 134.195.101.197×2, .193, .195, .180 |
| `NV_INTEGRATE_PROXY_URLS` | socks5h://172.18.0.1:7897,7904,7894,7896,7895 |

env 实测与 RN1033/RN1032/RN1009 完全一致，无漂移。integrate 保持空 (R1006 效果持续)，纯 pexec 路径。容器 Up ~2h (nv_gw Up 25h, nv_gw_stable Up 6d)，当前窗口完全健康。

## 数据

### 30min 主指标
| 指标 | 值 |
|------|-----|
| 总量 | 204 |
| 成功 | 204 |
| 失败 | 0 |
| SR | **100%** |
| Avg/P50/P95/Max | 9479ms / 8238ms / 21706ms / 30362ms |
| 429 计数 | **0** |

满负载窗口：204/204 全成功，零错误。延迟 avg 9.48s / p50 8.24s，处于健康稳定区间。

### 30min 错误分类 (request 级)
**空** — 零错误。

### 30min upstream_type 分布
| type | 计数 | 成功 | avg(ms) |
|------|------|------|---------|
| nvcf_pexec | 204 | 204 | 9479 |
| integrate | 0 | 0 | — |

100% pexec，integrate 持续闲置 (R1006 效果)。

### 30min per-key 200 延迟
| key | 计数 | avg_ms | max_ms |
|-----|------|--------|--------|
| 0 | 40 | 9625 | 20593 |
| 1 | 43 | 6987 | 11828 |
| 2 | 40 | 11040 | 23385 |
| 3 | 40 | 10650 | 21373 |
| 4 | 41 | 9285 | 21824 |

5 key 全部活跃健康 (40-43 req)，延迟均匀 (7.0-11.0s avg)，无单 key 劣化。k1 最快 (6987ms)，k2 略高 (11040ms) 但 max 23385ms 仍在 StdDev 内，非异常；且 k2 本轮零错误。

### 30min per-key 错误
**空** — 所有 key 零错误。

### finish_reason
| reason | 计数 |
|--------|------|
| tool_calls | 177 |
| stop | 27 |

正常工具调用分布，无空响应 (zombie_empty_completion=0)。

### key_cycle_429s (累计计数器，非本轮新增)
key0=87, key1=117 — 429 轮转历史累计，本轮窗口 429 计数为 0，无新事件。

### 30min tier_attempts
**空** — 无任何错误 attempt，链路无吸收性超时/断连/429 轮换，纯首击。

### 6h / 3h / 24h 趋势
- **6h: 1934 总, 1925 ok, SR=99.5%**, 9 err, 0 429
- 3h 逐小时: 20:00=302/302(100%), 19:00=349/348(99.7%), 18:00=347/346(99.7%), 17:00=61/56(91.8%)
  → 17:00 bucket 是较早窗口 SR 略低 (91.8%, 5 err)，最新时段 20:00 全绿 100%，趋势持续向好
- **24h all_tiers_exhausted: 104** (跨 tier 汇总窗口累计，本 30min 窗口 0)
- Fallback (hm4104, 5min): **无** — 主链路健康，未触发 fallback

## 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (204/204), 6h SR=99.5% (1925/1934)** — 远超 ≥95% 阈值。
2. **429=0, 错误=0, fallback=0** — 无任何冷却/轮转/fastbreak 压力。
3. **延迟健康**: avg 9479ms / p50 8238ms, 与 RN1033 (9361/8225) 基本持平 (avg +118ms 抽样噪声内)，处于稳态。
4. **5 key load 均匀 (40-43) + 延迟均匀 (7.0-11.0s) + 全 key 零错误** — 无 key 级问题。
5. **改前必有数据**: 无任何持续可归因问题; 链路处于最佳稳态，不应扰动。

## 当前状态 (30min 主指标)

- 30min SR: **100%** (204/204) / **6h SR: 99.5%** (1925/1934)
- Avg/P50/P95: 9479ms / 8238ms / 21706ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (204/204), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback)

## 上次修改效果 (RN1033 NOP → 本轮)

RN1033 报 30min SR=100% (207/207), Avg/P50/P95=9361/8225/21327。本轮 SR=100% (204/204)，持平。
Avg 9479ms 微升 (+118ms, 抽样噪声内)，P95 21706ms 近似。6h 仍 99.5% 量级。本轮未改任何参数，
系统延续 RN1033 稳态，零退化、零缺陷。连续第 4 轮 NOP (RN1031→RN1034 中 RN1032/1033/1034 连续 NOP)。

## 下一步建议

- **保持观察**。系统健康稳定，无需调整。
- 关注信号与预置对策:
  - 若 SR 跌破 99% 或 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - 若 pexec 死链/IncompleteRead 聚集 (≥3/30min 或单 key 集中) → 检查对应 key 的 SOCKS5 代理端口
  - 若 NVStream_IncompleteRead / stream_first_byte_timeout 反复出现 → 评估 UPSTREAM_TIMEOUT (50→60)
  - 若单 key 延迟持续劣化 (k2 avg 连续 >12s) → 考虑 key 级冷却调整或检查 k2 代理端口 7894
- 当前 5 个 SOCKS5 代理端口稳定，无需干预。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h趋势/24h ATE 均已采集
- [x] hm4104 近 5min 无 fallback 日志
- [x] 决策数据驱动: 30min SR=100%, 6h SR=99.5%, 429=0, 错误=0, fallback=0 → NOP