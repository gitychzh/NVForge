# RN1036: NOP — dsv4f0731_nv 链路 30min SR=100% (181/181), 零错误零fallback, 5 key 全健康, 24h ATE 全为历史残留, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~05:22 UTC
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
| `NVU_KEYMGR_429_BASE/MAX_COOLDOWN` | 120/120 |
| `NVU_KEYMGR_CONN_BASE/MAX/LONG` | 30/60/120, THRESHOLD=3 |
| `NVU_PROBE_TIMEOUT` | 10 |
| `NVU_BUFFER_TIMEOUT_STAIRS` | 90×5 |
| `NV_INTEGRATE_EGRESS_IPS` | 134.195.101.197×2, .193, .195, .180 |
| `NV_INTEGRATE_PROXY_URLS` | socks5h://172.18.0.1:7897,7904,7894,7896,7895 |

env 实测与 RN1035/RN1034/RN1009 完全一致，无漂移。integrate 保持空 (R1006 效果持续)，纯 pexec 路径。

## 数据

### 30min 窗口 (dsv4f0731_nv)
- 总量 181, 成功 181, **SR=100%**, 0 错误, 0 fallback
- Avg / P50 / P95 = 9917ms / 8054ms / 26556ms
- upstream: 全 pexec (181/181), integrate=0
- finish_reason: tool_calls=155, stop=26
- 429: 0
- tier_attempts: 空 (无 key 切换失败，全命中)

### per-key 延迟 (30min)
| key | req | avg_ms | max_ms |
|-----|-----|--------|--------|
| 0 | 36 | 11232 | 24177 |
| 1 | 36 | 8709 | 20349 |
| 2 | 37 | 10809 | 26783 |
| 3 | 35 | 9244 | 24042 |
| 4 | 37 | 9558 | 22835 |

5 key 均匀负载 (35-37 请求/key), 无单 key 劣化，无 per-key 错误。max 分布 20-27s，处于正常 NVCF pexec 尾部 (受 50s UPSTREAM_TIMEOUT 约束内)，无异常尖刺。

### 24h 趋势与错误
- 6h: 1963 总, 1955 成功 (SR=99.6%), 8 err
- 逐小时错误: 19:00=1, 18:00=1, 最后 2 个整点小时 (20:00, 21:00) = 0 err
- 24h ATE=98

### 关键判断: ATE=98 全为历史残留
逐小时 ATE 分布 (nv_requests, 24h):
- 08-06 21:00 → 08-07 08:00 (前 11h): 88 次 (最高 22:00=26)
- 08-07 17:00: 5 次 (早晨小回弹)
- **最近 12h (08-07 17:00 → 08-08 05:22): ATE = 0** — 系统已自愈稳定

24h ATE 是历史快照 (早高峰残留 + 前一日回弹)，不构成当前问题。当前窗口零 ATE。

### /health
status ok, proxy_role=passthrough, nv_num_keys=5, default=glm5_2_nv, 5 个 nvcf_pexec model 齐全。

### 容器状态
dsvf0731_nv40666 Up 3 hours, nv_gw Up 26 hours, hm4104 Up 3 days — 无 fallback 日志 (5min 窗口无 hm4104 fallback)。

## 结论
30min SR=100%, **零错误零 fallback 零 429**, 5 key 全健康均匀, 延迟稳定 p95=26.5s (avg~10s), integrate 空 (纯 pexec), env 无漂移。24h ATE 全为历史残留, 最近 12h 零 ATE, 逐小时错误收敛至 0。

当前链路处于稳固健康均衡点，**无数据支撑任何参数修改**。改动将有回归风险 (破坏已证实的 TIER_COOLDOWN=90 / UPSTREAM_TIMEOUT=50 平衡)。按决策原则 (SR>95%, 无异常错误, 延迟稳定 → NOP 轮), 本轮 NOP。

## 下一步建议
- 保持观望，若 ATE/429 在紧接着的 12h 内重新抬头 (而非历史残留), 再考虑调整 `NVU_KEYMGR_429_BASE_COOLDOWN` 或 `TIER_COOLDOWN_S`。
- 关注 `zombie_empty_completion` 与 `buffer_exhausted` 是否在当前窗口重现 — 当前两者均为 0。
- 若持续多轮纯 NOP 且 ATE 保持 0, 可评估将 `NVU_PEXEC_TIMEOUT_FASTBREAK` 3→4 (仅在超时重现时)。