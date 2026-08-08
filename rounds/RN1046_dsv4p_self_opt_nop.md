# RN1046: NOP — 链路健康，无需调整

**时间**: 2026-08-08 08:30 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 数据健康，符合 NOP 阈值 (SR>95%, 无异常错误, 延迟稳定)

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/超时/错误 | 155 / 155 / 0 / 0 |
| SR | **100%** |
| Avg / P50 / P95 | 11255ms / 9130ms / 28944ms |
| 错误分类 | 无 |
| 429 计数 | 0 |
| 键循环 429 (k0/k1) | 67 / 88 (历史累积旧值) |

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | p95_ms | 错误 |
|---|---|---|---|---|
| k0 | 30 | 10002 | 28403 | 0 |
| k1 | 33 | 11185 | 25948 | 0 |
| k2 | 29 | 10327 | 17765 | 0 |
| k3 | 32 | 10210 | 28280 | 0 |
| k4 | 31 | 14488 | 34170 | 0 |

所有 key 分布均匀 (~29-33 请求)，per-key 错误全 0，无劣化 key。k4 avg 略高 (14488ms) 但仍在正常方差内，p95 34170ms 略高于 30s 但无错误、无误码。

## 趋势

- 6h: 1991 总 / 1986 成功 / 5 错误, SR=99.7%
- 3h 逐小时: 100% / 100% / 98.9% / 100% — 稳定
- 24h all_tiers_exhausted: 46 (低频，24h 内可忽略)

## 其他状态

- upstream_type: nvcf_pexec 155 请求全部成功 (100%)，无 integrate 分流
- finish_reason: tool_calls 131 / stop 24 (正常，工具调用为主)
- hm4104 fallback: 0 (无 fallback 日志)
- /health: ok, 5 keys, port 40666
- 容器: Up 6 hours

## 当前参数 (env 实测，无漂移)

```
UPSTREAM_TIMEOUT=50, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F_NV=180,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5,
NV_INTEGRATE_MODELS=空 (纯 pexec 路径)
```

## 结论

链路完全健康：30min SR=100%，6h SR=99.7%，无错误、无 fallback、无 429，5 key 均匀健康，延迟稳定无劣化。无任何参数需要调整。遵循"改前必有数据 + 一次只改一个参数"铁律，无劣化数据则不改。**NOP 轮**。

## 验证

- /health → status ok
- 容器 Up 6 hours
- 无参数修改，无需重启

## 下一步建议

保持当前参数不变（纯 pexec 路径 + UPSTREAM_TIMEOUT=50 + TIER_COOLDOWN=90 持续产出 100% SR）。继续观察 k4 p95 (~34s) 是否抬升；若某 key 持续 >35s 且报错，再做针对性调参。持续 NOP 是稳定优先的正确行为。