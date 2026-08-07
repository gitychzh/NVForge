# RN1035: NOP — dsv4f0731_nv 链路 30min SR=100% (196/196), 零错误零fallback, 5 key 全健康, 24h ATE 全为历史残留, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~05:06 UTC
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

env 实测与 RN1034/RN1033/RN1009 完全一致，无漂移。integrate 保持空 (R1006 效果持续)，纯 pexec 路径。

## 数据

### 30min 窗口 (dsv4f0731_nv)
- 总量 196, 成功 196, **SR=100%**, 0 错误, 0 fallback
- Avg 9480ms / P50 7890ms / P95 22459ms (max 31514ms)
- upstream: 全 pexec (196/196), integrate=0
- finish_reason: tool_calls=169, stop=27
- 429: 0

### per-key 延迟 (30min)
| key | req | avg_ms | max_ms |
|-----|-----|--------|--------|
| 0 | 39 | 10076 | 19982 |
| 1 | 39 | 7233 | 14716 |
| 2 | 39 | 10282 | 22544 |
| 3 | 40 | 9073 | 18609 |
| 4 | 39 | 10748 | 31075 |

5 key 均匀负载 (39-40 请求/key), 无单 key 劣化，无 per-key 错误。

### 24h 趋势与错误
- 6h: 1956 总, 1947 成功 (SR=99.5%), 9 err
- 逐小时错误趋势: 22:00=31 err → 21:00/20:00 最后 2h 各 0 err → 收敛到零
- 24h 错误分布: `all_tiers_exhausted`=100, `zombie_empty_completion`=28, `buffer_exhausted`=14, `stream_absolute_cap`=11, `NVStream_IncompleteRead`=9, `stream_first_byte_timeout`=1, `client_gone_during_flush`=1

### 关键判断: ATE=100 全为历史残留
- all_tiers_exhausted 逐小时分布: 全部集中在 **08-06 21:00 ~ 08-07 08:00** (前 11h), 最高 22:00=26
- **最近 17h (08-07 09:00 起) ATE = 0** — 系统已自愈稳定
- 24h ATE 是历史快照，不构成当前问题

### key_cycle_429s (6h)
| key | c429 | ok |
|-----|------|----|
| 0 | 399 | 398 |
| 1 | 392 | 390 |
| 2 | 385 | 385 |
| 3 | 394 | 393 |
| 4 | 386 | 386 |

每 key ~400 次 429 循环但全部恢复至 ~390 次成功。TIER_COOLDOWN_S=90 恰好平衡: 不因过度冷却整 tier 跳过 (规避 R12 的 300s 过度跳过), 也不因冷却过短重爆 429。

### /health
status ok, proxy_role=passthrough, nv_num_keys=5, default=glm5_2_nv, 5 个 nvcf_pexec model 齐全。

## 结论
30min SR=100%, **零错误零 fallback**, 5 key 全健康均匀, 延迟稳定落地 p95=22.5s, integrate 空 (纯 pexec), env 无漂移。24h ATE 全为历史残留 (24h 前窗口), 最近 17h 零 ATE, 逐小时错误收敛至 0。

当前链路处于稳固健康均衡点，**无数据支撑任何参数修改**。改动将有回归风险 (破坏已证实的 TIER_COOLDOWN=90 平衡)。按决策原则 (SR>95%, 无异常错误, 延迟稳定 → NOP 轮), 本轮 NOP。

## 下一步建议
- 保持观望，若 ATE/429 在紧接着的 12h 内重新抬头 (而非历史残留), 再考虑调整 `NVU_KEYMGR_429_BASE_COOLDOWN` 或 `TIER_COOLDOWN_S`
- 关注 `zombie_empty_completion`(28) 与 `buffer_exhausted`(14) 是否在最近窗口重现 — 当前窗口两者均为 0, 说明未重现
- 若持续多轮纯 NOP 且 ATE 保持 0, 可评估将 `NVU_PEXEC_TIMEOUT_FASTBREAK` 3→4 (仅在超时重现时)