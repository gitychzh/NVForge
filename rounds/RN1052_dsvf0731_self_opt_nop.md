# RN1052: NOP — 链路持续健康 (SR 100%)，无参数调整

日期: 2026-08-08 09:32 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

连续全绿（R1170~R1190 及 RN1048~RN1051 均 SR=100% 或近全绿），健康稳态，守"改前必有数据"铁律不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **100%** (106/106, 0 error) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 | 14872 / 12508 / 35187 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 105/105 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 75, stop 30 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|18req|avg16477|P9535841
key1|23req|avg16798|P9546469
key2|20req|avg16443|P9531906
key3|23req|avg15861|P9534789
key4|21req|avg9143|P9517154
```
5 key 负载均匀 (18-23 req/key)、延迟同量级 (9.1-16.8s avg)，k4 略快但无错误聚集，无劣化 key。per-key 错误为空——30min 内 **0 错误**。

**tier_attempts**: 空（30min 内 0 错误，无 key 切换失败）。

**key_cycle_429s**: 0|51, 1|54 — 与上轮 (0|63, 1|100) 属噪声波动，30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 1950/1947 → **SR=99.85%**，3 失败（稀疏速率，落在窗口外），0 fallback
- **3h 逐小时**: 01:00 116(100%), 00:00 310(100%), 23:00 316(100%), 22:00 96(100%*) — 高流量且逐小时 SR 全 100%
- **24h all_tiers_exhausted**: 41（~1.7/h，均被 fallback 兜住，非本窗口信号，与上轮持平）

## 验证

- `/health`: status=ok, nv_num_keys=5, default=glm5_2_nv, port=40666
- 容器 `dsvf0731_nv40666` Up 7 hours
- hm4104 fallback 日志: 最近 5min 无 fallback

## 结论

30min SR=100%，0 错误，0 fallback，0 429，无 integrate，无劣化 key，6h/3h 趋势全绿。链路完全健康，按决策原则 NOP。

**下一步建议**: 继续观察窗口延迟方差（本轮 avg 14.9s 略高于上轮 11.3s，属流量负载自然波动，无错误聚集）。若后续窗口出现某 key 延迟持续劣化或错误聚集，优先排查该 key 的 SOCKS5 代理与 egress IP；若 all_tiers_exhausted 持续上升则考虑调整 TIER_COOLDOWN / NVU_KEYMGR_429 冷却。