# RN1021: NOP — dsv4f0731_nv 链路健康稳态延续 (30min SR=99.3%, 单次瞬时 IncompleteRead), 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~03:02 UTC (RN1009 改后第十二验证窗口)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Flash via NVCF)
**主机**: HM1 (opcsname)
**改动类型**: NOP (无修改)

## 当前参数 (实测 env 确认，无漂移)

| 参数 | 当前值 | 设置轮次 |
|------|--------|---------|
| `UPSTREAM_TIMEOUT` | **50** | RN1009 |
| `KEY_COOLDOWN_S` | 30 | 默认 |
| `TIER_COOLDOWN_S` | 90 | R1007 |
| `TIER_TIMEOUT_BUDGET_S` | 180 | 默认 |
| `NVU_TIER_BUDGET_DSV4F0731_NV` | 180 | 默认 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 | 默认 |
| `NVU_EMPTY_200_FASTBREAK` | 3 | 默认 |
| `NV_KEY_INTEGRATE_KEYS` | (空) | R1006 |
| `NVU_KEYMGR_429_BASE/MAX_COOLDOWN` | 120/120 | 默认 |
| `NVU_KEYMGR_CONN_*` | 30/60/3/120 | 默认 |

env 实测与 RN1020 完全一致，无漂移。integrate 保持空 (R1006 效果持续)，纯 pexec 路径。容器 StartedAt Up 43 min，当前窗口健康。

## 数据

### 30min 主指标
| 指标 | 值 |
|------|-----|
| 总量 | 142 |
| 成功 | 141 |
| 失败 | 1 |
| SR | **99.3%** |
| Avg/P50/P95 | 15118ms / 11645ms / 39590ms |
| 429 总计数 | **0** |

### 30min 错误分类 (request 级)
| error_type | 计数 | avg_ms |
|------------|------|--------|
| NVStream_IncompleteRead | 1 | 33764 |

仅 1 次瞬时流截断，key1，0.7% 流量，无伴随 429/断连，非链路劣化信号。

### 30min upstream_type 分布
| type | 计数 | 成功 | avg(ms) |
|------|------|------|---------|
| nvcf_pexec | 142 | 141 | 15118 |
| integrate | 0 | 0 | — |

100% pexec，integrate 持续闲置 (R1006 效果)。

### 30min per-key 200 延迟
| key | 计数 | avg_ms | p95_ms |
|-----|------|--------|--------|
| 0 | 28 | 13166 | 25578 |
| 1 | 25 | 16178 | 54417 |
| 2 | 30 | 14428 | 33015 |
| 3 | 31 | 16320 | 40059 |
| 4 | 27 | 14858 | 36545 |

5 key 分布均匀 (25-31 req)，avg 13.2-16.3s 高度一致。k1 p95=54.4s 为 NVCF 正常长尾原始方差 (其唯一错误为瞬时 IncompleteRead)，非单 key 劣化。

### 30min per-key 错误
| key | error_type | 计数 | avg_ms |
|-----|------------|------|--------|
| 1 | NVStream_IncompleteRead | 1 | 33764 |

单次瞬时事件，无聚集。

### finish_reason
| reason | 计数 |
|--------|------|
| tool_calls | 124 |
| stop | 17 |

正常分布，无空响应 (zombie_empty_completion=0 于本轮窗口)。

### key_cycle_429s (累计计数器，非本轮新增)
key0=56, key1=87 — 429 轮转历史累计，本轮窗口 429 计数为 0，无新事件。

### 30min tier_attempts
**空** — 无任何错误 attempt，链路无吸收性超时/断连/429 轮换。

### 6h 趋势
| 窗口 | 总量 | 成功 | 失败 | fallback |
|------|------|------|------|----------|
| 6h | 1749 | 1737 | 12 | 0 |
| SR | — | **99.3%** | — | 0% |

### 3h 逐小时
| 小时 | 总量 | 成功 | 失败 | SR | avg_ms |
|------|------|------|------|----|--------|
| 19:00 | 12 | 12 | 0 | 100% | 11524 |
| 18:00 | 347 | 346 | 1 | 99.7% | 11992 |
| 17:00 | 279 | 273 | 6 | 97.8% | 11786 |
| 16:00 | 259 | 259 | 0 | 100% | 13643 |

17:00 的 6 次失败为已消褪旧故障簇残余 (RN1009 基线内存证)，前后小时 100%/99.7%，非持续劣化。

### 24h all_tiers_exhausted
**119** (≈5/hr) — 与 RN1009/RN1020 基线一致稳态预算耗尽频率 (~120)，无恶化，且触发集中在旧窗口 (00:00–23:00 UTC)，近 3 小时 ATE/zombie 归零。

### hm4104 fallback 日志 (5min)
02:59:58 出现一次 CONTENT_FILTER_ZOMBIE → hm4104 切 ms_gw fallback (R840 zombie 检测逻辑触发)。此为 content_filter 触发的主链 zombie 告警，属 hermes 适配层常规护栏，非 dsv4f0731_nv 可用性问题；本轮 request 级 window 无 zombie_empty_completion/ATE。30min SR 仍 99.3%。

### /health
status ok, nv_num_keys=5, 5 个 nvcf_pexec_models 全列 (含 dsv4f0731_nv), proxy_role=passthrough, 端口 40666 正常。

## RN1009 修改效果验证 (UPSTREAM_TIMEOUT 90→50), 连续十二窗稳态

| 指标 | RN1009后 | RN1010 | RN1011 | RN1012 | RN1013 | RN1014 | RN1015 | RN1016 | RN1017 | RN1018 | RN1019 | RN1020 | **RN1021** |
|------|---------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|-----------|
| 30min SR | 98.4% | 98.8% | 99.5% | 99.5% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | **99.3%** |
| 30min ATE | 3 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| 30min fallback | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| 429 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |

RN1009 改动连续十二窗: 30min SR 维持 99-100%，ATE 归零，fallback 维持 0，429=0。RN1021 的 99.3% 完全在稳态带内，无劣化。

## 判定

**NOP**。数据健康:
- 30min SR=99.3%, 仅 1 次瞬时 NVStream_IncompleteRead (0.7%), 零 429 零 ATE 零 fallback, tier_attempts 全空 (纯首击)
- 单 key 无劣化、无聚集错误，5 key 均匀分布
- 100% pexec 路径，integrate 保持关闭 (R1006 稳态)
- 6h SR=99.3%, 逐小时 16:00/18:00/19:00 均 99.7-100%
- 参数 (UPSTREAM_TIMEOUT=50, TIER_COOLDOWN=90, BUDGET=180) 与 RN1009/R1007 一致，无漂移

单次 IncompleteRead 不足以支撑任何超时/冷却参数调整 —— 参数已在 R1007-R1009 收敛，改而破坏稳态得不偿失。保守维持稳态。

## 验证
- 容器 `Up 43 minutes`, 运行正常
- `/health` 返回 ok, 5 key, 模型列表完整
- env 无漂移，参数与配置一致

## 下一步建议
继续观察。若单 key IncompleteRead 出现聚集 (>2/窗) 或 ATE 频率显著高于 ~5/hr 基线，再考虑 per-key 冷却调整；当前链路健康，保持现状。