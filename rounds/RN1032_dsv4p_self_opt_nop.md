# RN1032: NOP — dsv4f0731_nv 链路 30min SR=100% (201/201), 零错误零429零fallback, 5 key 全健康均匀, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~04:32 UTC
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

env 实测与 RN1031/RN1009 完全一致，无漂移。integrate 保持空 (R1006 效果持续)，纯 pexec 路径。容器 Up ~2h，当前窗口完全健康。

## 数据

### 30min 主指标
| 指标 | 值 |
|------|-----|
| 总量 | 201 |
| 成功 | 201 |
| 失败 | 0 |
| SR | **100%** |
| Avg/P50/P95/Max | 8983ms / 8212ms / 20422ms / 23954ms |
| 429 计数 | **0** |

完美满负载窗口：201/201 全成功，零错误。延迟 avg 8.98s / p50 8.2s，处于健康稳定区间。

### 30min 错误分类 (request 级)
**空** — 零错误。

### 30min upstream_type 分布
| type | 计数 | 成功 | avg(ms) |
|------|------|------|---------|
| nvcf_pexec | 202 | 202 | 8943 |
| integrate | 0 | 0 | — |

100% pexec，integrate 持续闲置 (R1006 效果)。

### 30min per-key 200 延迟
| key | 计数 | avg_ms | max_ms |
|-----|------|--------|--------|
| 0 | 40 | 9753 | 23224 |
| 1 | 43 | 8070 | 19172 |
| 2 | 40 | 9286 | 16089 |
| 3 | 38 | 8745 | 20533 |
| 4 | 41 | 8919 | 19977 |

5 key 全部活跃健康 (38-43 req)，延迟高度均匀 (8.1-9.8s avg)，无单 key 劣化。

### 30min per-key 错误
**空** — 所有 key 零错误。

### finish_reason
| reason | 计数 |
|--------|------|
| tool_calls | 171 |
| stop | 31 |

正常工具调用分布，无空响应 (zombie_empty_completion=0)。

### key_cycle_429s (累计计数器，非本轮新增)
key0=87, key1=115 — 429 轮转历史累计，本轮窗口 429 计数为 0，无新事件。

### 30min tier_attempts
**空** — 无任何错误 attempt，链路无吸收性超时/断连/429 轮换，纯首击。

### 6h / 3h / 24h 趋势
- **6h: 1908 总, 1899 ok, SR=99.5%**, 9 err, 0 429
- 3h 逐小时: 20:00=218/218(100%), 19:00=349/348(99.7%), 18:00=347/346(99.7%), 17:00=132/127(97.9%)
  → SR 稳定走高，最新时段全绿
- **24h all_tiers_exhausted: 106** (跨 tier 汇总窗口累计，本 30min 窗口 0)
- Fallback (hm4104, 5min): **无** — 主链路健康，未触发 fallback

## 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (201/201), 6h SR=99.5% (1899/1908)** — 远超 ≥95% 阈值。
2. **429=0, 错误=0, fallback=0** — 无任何冷却/轮转/fastbreak 压力。
3. **延迟健康**: avg 8983ms / p50 8212ms, 与 RN1031 (8721/7771) 基本持平，处于稳态。
4. **5 key load 均匀 (38-43) + 延迟均匀 (8.1-9.8s) + 全 key 零错误** — 无 key 级问题。
5. **改前必有数据**: 无任何持续可归因问题; 链路处于最佳稳态，不应扰动。

## 当前状态 (30min 主指标)

- 30min SR: **100%** (201/201) / **6h SR: 99.5%** (1899/1908)
- Avg/P50/P95: 8983ms / 8212ms / 20422ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (202/202), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback)

## 上次修改效果 (RN1031 NOP → 本轮)

RN1031 报 30min SR=100% (203/203), Avg/P50/P95=8721/7771/20416。本轮 SR=100% (201/201)，持平。
Avg 8983ms 略升 (+262ms, 抽样噪声内)，P95 20422ms 几乎一致。6h 仍 99.5% 量级。本轮未改任何参数，
系统延续 RN1031 稳态，零退化、零缺陷。

## 下一步建议

- **保持观察**。系统健康稳定，无需调整。
- 关注信号与预置对策:
  - 若 SR 跌破 99% 或 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - 若 pexec 死链/IncompleteRead 聚集 (≥3/30min 或单 key 集中) → 检查对应 key 的 SOCKS5 代理端口
  - 若 NVStream_IncompleteRead / stream_first_byte_timeout 反复出现 → 评估 UPSTREAM_TIMEOUT (50→60)
  - 若单 key 延迟持续劣化 → 考虑 key 级冷却调整
- 当前 5 个 SOCKS5 代理端口稳定，无需干预。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h趋势/24h ATE 均已采集
- [x] hm4104 近 5min 无 fallback 日志
- [x] 决策数据驱动: 30min SR=100%, 6h SR=99.5%, 429=0, 错误=0, fallback=0 → NOP