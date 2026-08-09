# RN1048: NOP — 链路健康，SR 稳定在 95%+，无需调整

**时间**: 2026-08-10 07:38 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 数据健康，符合 NOP 阈值 (SR>95%, 无异常错误, 延迟稳定)

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 85 / 83 / 2 |
| SR (30min) | **97.6%** |
| Avg / P50 / P95 | 25230ms / 15969ms / 84502ms |
| 错误分类 | NVStream_IncompleteRead 1 (40433ms), all_tiers_exhausted 1 (180073ms) |
| 429 计数 | 0 |

**独立复核**（采集脚本后自取数据）: 最近 20min **66/66 = 100% SR**, avg 24015ms —— 确认当前链路完全健康，采集窗口的 2 个错误已消失且未复发。

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | p95_ms | 错误 |
|---|---|---|---|---|
| k0 | 17 | 22573 | 54868 | NVStream_IncompleteRead 1 + all_tiers_exhausted 1 |
| k1 | 17 | 20110 | 50163 | 0 |
| k2 | 17 | 22789 | 64802 | 0 |
| k3 | 17 | 28166 | 79781 | 0 |
| k4 | 15 | 22144 | 52799 | 0 |

所有 key 分布均匀 (15-17 请求)，仅 k0 出现 2 个错误（1 流截断 + 1 全域耗尽），属单点瞬态，其它 4 key 全 0 错误、延迟均衡。无劣化 key。

## 趋势

- 6h: 455 总 / 429 成功 / 26 错, SR=94.3%
- 3h 逐小时: 93.3% (14/15) / 95.2% (100/105) / 97.4% (113/116) / 98.1% (102/104) —— **逐小时稳步回升且收敛**
- 20min 复核: **100% (66/66)** —— 延续回升趋势
- 24h all_tiers_exhausted: 291（分布全日在高负载时段，当前窗口已回到 1）

## 其他状态

- upstream_type: nvcf_pexec 85 请求, SR 97.6%, 纯 pexec 路径 (100%)，无 integrate 分流
- finish_reason: tool_calls 72 / stop 11 (工具调用为主，正常)
- hm4104 fallback: 0 (最近 5min 无 fallback 日志)
- /health: ok, 5 keys, port 40666
- 容器: Up 2 hours

## 当前参数 (env 实测，无漂移)

```
UPSTREAM_TIMEOUT=45, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5,
NV_INTEGRATE_MODELS=空 (纯 pexec 路径)
注: UPSTREAM_TIMEOUT 已由上轮记录的 50 → 45 (后续轮次调整，实测确认无漂移)
```

## 结论

链路健康：30min SR=97.6%，20min 复核 100% SR，小时级 SR 从 93.3% 收敛至 98.1%，0 429、0 fallback，5 key 均匀健康。两个采集窗口错误（1 流截断 + 1 全域耗尽 180s）均为瞬态上游抖动，被 key 循环正确吸收且未复发。上一小时上游层仍有 32 次 NVCFPexecRemoteDisconnected + 11 次 NVCFPexecTimeout（上游瞬态），但请求级 SR 不受影响（HTTPS 层 key 轮转在 budget=180s 内兜住）。遵循"改前必有数据 + 一次只改一个参数"铁律，无劣化数据则不改。**NOP 轮**。

## 验证

- /health → status ok
- 容器 Up 2 hours
- 无参数修改，无需重启

## 下一步建议

保持当前参数不变（纯 pexec + UPSTREAM_TIMEOUT=45 + TIER_COOLDOWN=90 + TIER_TIMEOUT_BUDGET=180 正在产出收敛中的高 SR）。继续观察：(1) 上一小时 32 次 PexecRemoteDisconnected 是否随时间衰减——若持续高企需关注 NVCF 上游稳定性而非本地参数；(2) k0 的 2 个错误是否单点复发；(3) 高负载时段的 all_tiers_exhausted (24h=291) 是否因简单并行突发引起 budget 打满。持续 NOP 是稳定优先的正确行为。