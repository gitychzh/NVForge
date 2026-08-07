# RN1038: NOP — dsv4f0731_nv 链路 30min SR=100% (160/160), 零错误零fallback零429, 5 key 全健康, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~05:40 UTC
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**改动类型**: NOP (无修改)

## 当前参数 (脚本 env 实测确认，无漂移)

| 参数 | 当前值 |
|------|--------|
| `UPSTREAM_TIMEOUT` | 50 |
| `KEY_COOLDOWN_S` | 30 |
| `TIER_COOLDOWN_S` | 90 |
| `TIER_TIMEOUT_BUDGET_S` | 180 |
| `NVU_TIER_BUDGET_DSV4F0731_NV` | 180 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 |
| `NVU_EMPTY_200_FASTBREAK` | 3 |
| `NVU_KEYMGR_429_BASE_COOLDOWN` | 120 |
| `NVU_KEYMGR_429_MAX_COOLDOWN` | 120 |
| `NVU_KEYMGR_CONN_BASE/MAX/LONG` | 30/60/120, THRESHOLD=3 |
| `NVU_PROBE_TIMEOUT` | 10 |
| `NVU_BUFFER_TIMEOUT_STAIRS` | 90×5 |
| `NV_INTEGRATE_MODELS/KEYS` | 空 (纯 pexec 路径) |
| `NV_INTEGRATE_EGRESS_IPS` | 134.195.101.197×2, .193, .195, .180 |
| `NV_INTEGRATE_PROXY_URLS` | socks5h://172.18.0.1:7897,7904,7894,7896,7895 |

env 实测与 RN1037 完全一致，无漂移。integrate 保持空 (纯 pexec 路径，R1006 效果持续)。

## 数据

### 30min 窗口 (dsv4f0731_nv)
- 总量 160, 成功 160, **SR=100%**, 0 错误, 0 fallback, 0 429
- Avg / P50 / P95 = 10970ms / 8631ms / 27289ms
- upstream: 全 pexec (160), integrate=0
- finish_reason: tool_calls=136, stop=24 (正常 agent 工作负载)
- tier_attempts: 空 (无 key 切换失败，全命中)
- key_cycle_429s: 0 (raw 字段 key0=60/key1=100 为历史聚合残留，无当前 429)

### per-key 延迟 (30min) — 5 key 全健康，零错误
| key | req | avg_ms | max_ms |
|-----|-----|--------|--------|
| 0 | 34 | 11075 | 33515 |
| 1 | 32 | 11554 | 27376 |
| 2 | 31 | 10812 | 24800 |
| 3 | 30 | 9102 | 20887 |
| 4 | 33 | 12143 | 30886 |

负载均衡 (30-34 req/key)，延迟同质 (9102-12143ms avg)，无异常 key。

### 趋势
- **6h**: 1974 总, 1966 成功, 8 失败, 0 all_tiers_exhausted → 99.6% SR
- **3h 逐小时**: 21:00=226/226 (100%), 20:00=405/405 (100%), 19:00=349/348, 18:00=102/101
- **24h all_tiers_exhausted=94**: 全为历史残留 (6h/3h 窗内 ATE=0)，非当前问题

### fallback
hm4104 最近 5min 无 fallback 日志 → dsv4f0731_nv 当前完全可用。

### /health
`status: ok`, 5 key, 5 model tiers, port 40666。容器 Up 3 hours。

## 结论

SR=100%, 零错误, 零 fallback, 零 429, 5 key 全健康 (负载均衡 + 延迟同质), 纯 pexec 路径无 integrate 劣化。所有指标满足 NOP 阈值 (SR>95%, 无异常错误, 延迟稳定)。

**无修改参数** — 铁律要求"改前必有数据"，当前数据不支撑任何参数调整。避免为改动而改动引入漂移。

## 验证清单
- [x] /health ok
- [x] 30min SR=100%, 0 errors, 0 fallback, 0 429
- [x] per-key 零错误、负载均衡
- [x] 6h SR=99.6%, 最近窗口 ATE=0
- [x] 无参数改动 (NOP)

## 下一步建议
保持现状。下一轮继续监控 24h ATE 是否回升 (当前为历史残留)；若 per-key 延迟方差继续增大或某 key 开始报错，再评估 integrate key 分配或 KEY_COOLDOWN。无维护动作。