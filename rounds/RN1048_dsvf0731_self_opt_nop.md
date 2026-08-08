# RN1048: NOP — 链路健康，无需调整

**时间**: 2026-08-08 09:05 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 数据健康，符合 NOP 阈值 (SR>95%, 无异常错误, 延迟稳定)

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/超时/错误 | 150 / 150 / 0 / 0 |
| SR | **100%** |
| Avg / P50 / P95 | 13439ms / 9147ms / 75514ms |
| 错误分类 | 无 |
| 429 计数 | 0 |

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | p95_ms | 错误 |
|---|---|---|---|---|
| k0 | 30 | 10707 | 25679 | 0 |
| k1 | 27 | 12639 | 29129 | 0 |
| k2 | 31 | 14257 | 37254 | 0 |
| k3 | 30 | 14385 | 31588 | 0 |
| k4 | 32 | 14996 | 46791 | 0 |

所有 key 分布均匀 (27-32 请求)，per-key 错误全 0，无劣化 key。k4 p95 46791ms、整体 P95 75514ms 较上轮 (30125ms) 抬升，但为长尾延迟方差，**全部伴随 0 错误、0 超时、0 429**，属健康方差而非链路劣化。

## 趋势

- 6h: 1995 总 / 1991 成功 / 4 错误, SR=99.8%
- 3h 逐小时: 01:00=10/10(100%), 00:00=310/310(100%), 23:00=316/316(100%), 22:00=246/243(98.8%, 3 错误, >3h 前已恢复)
- 24h all_tiers_exhausted: 44 (低频，24h 内可忽略)

## 其他状态

- upstream_type: nvcf_pexec 150 请求全部成功 (100%)，无 integrate 分流
- finish_reason: tool_calls 128 / stop 22 (正常，工具调用为主)
- hm4104 fallback: 0 (无 fallback 日志)
- /health: ok, 5 keys, port 40666
- 容器: Up 7 hours

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

与 RN1047 完全一致，无漂移。

## 结论

链路完全健康：30min SR=100%，6h SR=99.8%，最近 3 个整点小时全 100%，0 错误、0 fallback、0 429，5 key 均匀健康。整体 P95 75514ms 较上轮抬升 (k4 长尾 46791ms)，但零错误伴随，属 long-tail 方差，**无劣化信号不足以触发调参**。遵循"改前必有数据 + 一次只改一个参数"铁律，无劣化数据则不改。**NOP 轮**。

## 验证

- /health → status ok
- 容器 Up 7 hours
- env 实测与配置一致，无参数修改，无需重启

## 下一步建议

保持当前参数不变（纯 pexec 路径 + UPSTREAM_TIMEOUT=50 + TIER_COOLDOWN=90 + TIER_TIMEOUT_BUDGET=180 持续产出 100% SR）。继续观察整体 P95 是否持续 >70s 或某 key p95 连续多轮 >45s 且伴随错误；若 P95 抬升同时出现超时/空响应，则考虑是否需扩展 budget 或检查 k4 SOCKS5 代理质量。当前持续 NOP 是稳定优先的正确行为。