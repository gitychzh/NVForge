# RN1018: NOP — dsv4f0731_nv 链路连续第九窗完美健康 (30min SR=100%, 零错误零 fallback), 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~02:48 UTC (RN1009 改后第九验证窗口)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Flash via NVCF)
**主机**: HM2 (opc2sname)
**改动类型**: NOP (无修改)

## 当前参数 (实测 env 确认，无漂移)

| 参数 | 当前值 | 设置轮次 |
|------|--------|---------|
| `UPSTREAM_TIMEOUT` | **50** | RN1009 |
| `KEY_COOLDOWN_S` | 30 | 默认 |
| `TIER_COOLDOWN_S` | 90 | R1007 |
| `TIER_TIMEOUT_BUDGET_S` | 180 | 默认 |
| `NVU_TIER_BUDGET_DSV4F_NV` / `NVU_TIER_BUDGET_DSV4F0731_NV` | 180 | 默认 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 | 默认 |
| `NVU_EMPTY_200_FASTBREAK` | 3 | 默认 |
| `NV_KEY_INTEGRATE_KEYS` | (空) | R1006 |
| `NVU_KEYMGR_429_BASE/MAX_COOLDOWN` | 120/120 | 默认 |
| `NVU_KEYMGR_CONN_*` | 30/60/3/120 | 默认 |

env 实测 (02:48 脚本 dump) 与 RN1017 完全一致，无漂移。integrate 保持空 (R1006 效果持续)，纯 pexec 路径。容器 StartedAt Up 29 min，当前窗口全线健康，无残留劣化。注: env 实际同时存在 `NVU_TIER_BUDGET_DSV4F_NV=180` 与 `NVU_TIER_BUDGET_DSV4F0731_NV=180` 两变量，值一致，稳态。

## 数据

### 30min 主指标
| 指标 | 值 |
|------|-----|
| 总量 | 172 |
| 成功 | 172 |
| 失败 | 0 |
| SR | **100%** |
| Avg/P50/P95/P99 | 12224ms / 9240ms / 26875ms / 51049ms |
| 429 总计数 | **0** |

### 30min 错误分类 (request 级)
无 (零错误)

### 30min upstream_type 分布
| type | 计数 | 成功 | 占比 |
|------|------|------|------|
| nvcf_pexec | 172 | 172 | 100% (172/172) |
| integrate | 0 | 0 | — |

### 30min per-key 200 延迟 (无错误)
| key | 计数 | avg_ms | p95_ms |
|-----|------|--------|--------|
| 0 | 34 | 12734 | 29731 |
| 1 | 35 | 13223 | 23724 |
| 2 | 35 | 10913 | 27255 |
| 3 | 35 | 13968 | 29307 |
| 4 | 33 | 10180 | 21475 |

5 key 分布均匀 (33-35 req/1.75h ≈ 流量相似)，零错误，p95 差距 (21.5-29.7s) 为正常 NVCF 长尾方差，无单 key 劣化。无 integrate 通路调用 → 无 直连/IP/SOCKS5 竞争。

### 30min per-key 错误
无

### finish_reason
| reason | 计数 |
|--------|------|
| tool_calls | 152 |
| stop | 20 |

### key_cycle_429s (累计计数器，非本轮新增)
key0=75, key1=97 — 为 429 轮转历史累计，本轮窗口 429 计数为 0，非新事件。

### 6h 趋势
| 窗口 | 总量 | 成功 | 失败 | fallback |
|------|------|------|------|----------|
| 6h | 1756 | 1745 | 11 | 0 |
| SR | — | **99.4%** | — | 0% |

### 3h 逐小时
| 小时 | 总量 | 成功 | 失败 | SR | avg_ms |
|------|------|------|------|----|--------|
| 18:00 | 286 | 286 | 0 | 100% | 11395 |
| 17:00 | 279 | 273 | 6 | 97.8% | 11786 |
| 16:00 | 273 | 273 | 0 | 100% | 13430 |
| 15:00 | 59 | 59 | 0 | 100% | 10268 |

17:00 的 6 次失败为已知的低频瞬时 event (RN1009 基线内存证，非持续劣化)，前后小时均 100%。

### 24h all_tiers_exhausted
**122** (≈5.1/hr) — 与 RN1009 基线一致的稳态预算耗尽频率，无恶化。

### hm4104 fallback 日志 (5min)
(无 fallback 日志) — dsv4f0731_nv 无 fallback 触发，链路可靠。

### /health
status ok, nv_num_keys=5, 5 个 nvcf_pexec_models 全列 (含 dsv4f0731_nv), proxy_role=passthrough, 端口 40666 正常。

## 判定

**NOP**。数据完全健康:
- 30min SR=100%, 零错误零 429 零 fallback
- 单 key 无劣化、无聚集错误，5 key 均匀分布
- 100% pexec 路径，integrate 保持关闭 (R1006 稳态)
- 6h SR=99.4%, 3h 逐小时 16:00/18:00 均 100%
- 参数 (UPSTREAM_TIMEOUT=50, TIER_COOLDOWN=90) 与 RN1009/R1007 一致，无漂移

连续第九窗健康，无需调整任何参数。保守维持稳态。

## 验证
- 容器 `Up 29 minutes`, 运行正常
- `/health` 返回 ok, 5 key, 模型列表完整
- env 无漂移，参数与配置一致

## 下一步建议
继续观察。若 ATE 频率在未来窗口显著高于 ~5/hr 基线或出现单 key 聚集错误，再考虑 per-key 冷却调整；当前链路健康，保持现状。