# RN1047: NOP — 链路健康，无需调整

**时间**: 2026-08-08 08:35 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 数据健康，符合 NOP 阈值 (SR>95%, 无异常错误, 延迟稳定)

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/超时/错误 | 149 / 149 / 0 / 0 |
| SR | **100%** |
| Avg / P50 / P95 | 11625ms / 9091ms / 30125ms |
| 错误分类 | 无 |
| 429 计数 | 0 |
| 键循环 429 (k0/k1) | 66 / 83 (历史累积旧值) |

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | p95_ms | 错误 |
|---|---|---|---|---|
| k0 | 30 | 12198 | 32419 | 0 |
| k1 | 31 | 11449 | 26760 | 0 |
| k2 | 27 | 9585 | 17907 | 0 |
| k3 | 32 | 11873 | 35607 | 0 |
| k4 | 29 | 12846 | 30385 | 0 |

所有 key 分布均匀 (27-32 请求)，per-key 错误全 0，无劣化 key。k3 p95 35607ms 略高于 35s 但 SR 100%、无错误、无误码，属正常长尾。k2 延迟最优 (avg 9585ms)。

## 趋势

- 6h: 1984 总 / 1979 成功 / 5 错误, SR=99.7%
- 3h 逐小时: 100% / 100% / 98.9% / 100% — 稳定
- 24h all_tiers_exhausted: 45 (低频，24h 内可忽略)

## 其他状态

- upstream_type: nvcf_pexec 149 请求全部成功 (100%)，无 integrate 分流
- finish_reason: tool_calls 124 / stop 25 (正常，工具调用为主)
- hm4104 fallback: 0 (无 fallback 日志)
- /health: ok, 5 keys, port 40666
- 容器: Up 6 hours

## 当前参数 (env 实测，无漂移)

```
UPSTREAM_TIMEOUT=50, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5,
NV_INTEGRATE_MODELS=空 (纯 pexec 路径)
```

## 结论

链路完全健康：30min SR=100%，6h SR=99.7%，0 错误、0 fallback、0 429，5 key 均匀健康，延迟稳定无劣化。P95 30125ms 较上轮 (28944ms) 微升、k3 p95 达 35.6s，但均在健康方差内且零错误。遵循"改前必有数据 + 一次只改一个参数"铁律，无劣化数据则不改。**NOP 轮**。

## 验证

- /health → status ok
- 容器 Up 6 hours
- 无参数修改，无需重启

## 下一步建议

保持当前参数不变（纯 pexec 路径 + UPSTREAM_TIMEOUT=50 + TIER_COOLDOWN=90 + TIER_TIMEOUT_BUDGET=180 持续产出 100% SR）。继续观察 k3 p95 (~35.6s) 与 k0/k1 key_cycle_429 是否抬升；若某 key 持续 >35s 且伴随错误，再做针对性调参。持续 NOP 是稳定优先的正确行为。