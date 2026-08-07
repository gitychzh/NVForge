# RN1033: NOP — dsv4f0731_nv 链路 30min SR=100% (207/207), 零错误零429零fallback, 5 key 全健康均匀, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~04:40 UTC
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

env 实测与 RN1032/RN1031/RN1009 完全一致，无漂移。integrate 保持空 (R1006 效果持续)，纯 pexec 路径。容器 Up ~2h (nv_gw Up 25h, nv_gw_stable Up 6d)，当前窗口完全健康。

## 数据

### 30min 主指标
| 指标 | 值 |
|------|-----|
| 总量 | 207 |
| 成功 | 207 |
| 失败 | 0 |
| SR | **100%** |
| Avg/P50/P95/Max | 9361ms / 8225ms / 21327ms / 25494ms |
| 429 计数 | **0** |

完美满负载窗口：207/207 全成功，零错误。延迟 avg 9.36s / p50 8.2s，处于健康稳定区间。

### 30min 错误分类 (request 级)
**空** — 零错误。

### 30min upstream_type 分布
| type | 计数 | 成功 | avg(ms) |
|------|------|------|---------|
| nvcf_pexec | 207 | 207 | 9361 |
| integrate | 0 | 0 | — |

100% pexec，integrate 持续闲置 (R1006 效果)。

### 30min per-key 200 延迟
| key | 计数 | avg_ms | max_ms |
|-----|------|--------|--------|
| 0 | 41 | 9592 | 20457 |
| 1 | 42 | 7231 | 13636 |
| 2 | 40 | 11395 | 23385 |
| 3 | 41 | 10069 | 21165 |
| 4 | 43 | 8654 | 20956 |

5 key 全部活跃健康 (40-43 req)，延迟均匀 (7.2-11.4s avg)，无单 key 劣化。k1 最快 (7231ms)，k2 略高 (11395ms) 但 max 23385ms 仍在 StdDev 内，非异常。

### 30min per-key 错误
**空** — 所有 key 零错误。

### finish_reason
| reason | 计数 |
|--------|------|
| tool_calls | 180 |
| stop | 27 |

正常工具调用分布，无空响应 (zombie_empty_completion=0)。

### key_cycle_429s (累计计数器，非本轮新增)
key0=86, key1=122 — 429 轮转历史累计，本轮窗口 429 计数为 0，无新事件。

### 30min tier_attempts
**空** — 无任何错误 attempt，链路无吸收性超时/断连/429 轮换，纯首击。

### 6h / 3h / 24h 趋势
- **6h: 1929 总, 1920 ok, SR=99.5%**, 9 err, 0 429
- 3h 逐小时: 20:00=277/277(100%), 19:00=349/348(99.7%), 18:00=347/346(99.7%), 17:00=80/75(93.8%)
  → 17:00 bucket 是老窗口 SR 略低 (93.8%, 5 err)，最新时段 20:00 全绿 100%，趋势持续向好
- **24h all_tiers_exhausted: 104** (跨 tier 汇总窗口累计，本 30min 窗口 0)
- Fallback (hm4104, 5min): **无** — 主链路健康，未触发 fallback

## 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (207/207), 6h SR=99.5% (1920/1929)** — 远超 ≥95% 阈值。
2. **429=0, 错误=0, fallback=0** — 无任何冷却/轮转/fastbreak 压力。
3. **延迟健康**: avg 9361ms / p50 8225ms, 与 RN1032 (8983/8212) 基本持平 (avg +378ms 抽样噪声内)，处于稳态。
4. **5 key load 均匀 (40-43) + 延迟均匀 (7.2-11.4s) + 全 key 零错误** — 无 key 级问题。
5. **改前必有数据**: 无任何持续可归因问题; 链路处于最佳稳态，不应扰动。

## 当前状态 (30min 主指标)

- 30min SR: **100%** (207/207) / **6h SR: 99.5%** (1920/1929)
- Avg/P50/P95: 9361ms / 8225ms / 21327ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (207/207), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback)

## 上次修改效果 (RN1032 NOP → 本轮)

RN1032 报 30min SR=100% (201/201), Avg/P50/P95=8983/8212/20422。本轮 SR=100% (207/207)，持平。
Avg 9361ms 略升 (+378ms, 抽样噪声内)，P95 21327ms 近似。6h 仍 99.5% 量级。本轮未改任何参数，
系统延续 RN1032 稳态，零退化、零缺陷。连续第 3 轮 NOP (RN1032→RN1033)。

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