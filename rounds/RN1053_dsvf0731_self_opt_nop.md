# RN1053: NOP — 链路持续健康 (SR 100%)，无参数调整

日期: 2026-08-08 09:34 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

连续全绿（RN1048~RN1052 均 SR=100% 或近全绿）健康稳态。守"改前必有数据"+"一次只改一个参数"铁律不动作。无任何持续劣化数据可归因于参数，改动只会引入风险。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **100%** (104/104, 0 error, 0 timeout) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 | 14940 / 12466 / 35195 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 104/104 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 76, stop 28 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|17req|avg15466|P5 36078
key1|22req|avg17810|P5 47526
key2|19req|avg16721|P5 34099
key3|24req|avg15699|P5 34581
key4|22req|avg9299 |P5 17040
```
5 key 负载均匀 (17-24 req/key)、延迟同量级 (9.3-17.8s avg)，k4 略快但无错误聚集，无劣化 key。per-key 错误为空——30min 内 **0 错误**。

**tier_attempts**: 空（30min 内 0 错误，无 key 切换失败）。

**key_cycle_429s**: 0|48, 1|56 — 与上轮 (0|51, 1|54) 属噪声波动，30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 1949/1946 → **SR=99.85%**，3 失败（22:00 稀疏速率残留，落在本窗口外），0 fallback
- **3h 逐小时**: 01:00 127(100%), 00:00 310(100%), 23:00 316(100%), 22:00 87/84(97.7%, 3 错误 >1.5h 前残留) — **最近 3 个整点小时全 100%**
- **24h all_tiers_exhausted**: 41（陈旧累积口径，非近期事件；本窗口 0，均被兜住）

## 验证

- `/health`: status=ok, proxy_role=passthrough, nv_num_keys=5, default=glm5_2_nv, port=40666, dsv4f0731_nv 在 nvcf_pexec_models
- 容器 `dsvf0731_nv40666` Up 7 hours（nv_gw Up 30h, nv_gw_stable Up 6 days — 全栈稳定）
- hm4104 fallback 日志: 最近 5min 无 fallback

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

与 RN1052 完全一致，无参数修改生效，无需重启。

## 结论

链路完全健康且维持高度稳定：30min SR=100% (104/104)，6h SR=99.85% (1946/1949)，最近 3 个整点小时全 100%，0 错误 / 0 429 / 0 fallback / tier_attempts 空。5 key 负载与延迟完全均匀（无单 key 劣化），upstream 全 pexec 100% 成功。P95 35195ms 与 RN1052 (35187ms) 高度一致，P50 12466ms 与 RN1052 (12508ms) 一致，延迟稳定无漂移。遵循"改前必有数据"铁律，**NOP 轮**。

## 下一步建议

1. **维持现状**: 纯 pexec 路径 + UPSTREAM_TIMEOUT=50 + TIER_COOLDOWN=90 + TIER_BUDGET=180 持续产出 100% SR 为理想稳态，不改任何参数。
2. **关注 P95/P99 长尾**: 轮 P95 ≈35s 健康。若某 key p95 连续多轮 >45s 且伴错误，才排查该 key SOCKS5 代理 / egress IP。
3. **复核 24h ATE 口径**: all_tiers_exhausted=41 为陈旧累积，仅当 30min/6h 窗口内 ATE 增长才视为真实信号。
4. **观察 k4 稳定低延迟** (avg≈9.3s): 若持续显著快于其它 key，可作为未来 key 权重/integrate 分配参考，当前无修改必要。