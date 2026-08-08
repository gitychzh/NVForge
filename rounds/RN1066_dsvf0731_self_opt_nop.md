# RN1066: NOP — NVCF-side 持续劣化 (RemoteDisconnected 均匀分布全5key/5出口IP, 529 overload), 非本容器参数可归因, 不改参数

日期: 2026-08-08 17:40 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pxexe 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1065 的 30min 快照恰好落在健康窗口 (SR 98.41%)。但拉长到 **6h tier-attempts 与 3h request-level**，本窗口显示的是 **NVCF 侧持续劣化**，且证据链完整指向外部（NVCF overload），**非本容器可调参数可归因**。

### 数据证据（全部镜像自 DB / 日志）

**6h tier-attempts (dsv4f0731_nv)**:
```
error_type | count | avg_ms
pexec_success                 | 440 | 14943
NVCFPexecRemoteDisconnected   | 151 | 35879   ← 22.9% of attempts
NVCFPexecTimeout              |  65 | 45141
529_nv_overloaded             |   7 |
budget_exhausted_after_connect|   3 |  1934
```

**Per-key（6h, 5 key 全劣化, 无单点集中）**:
```
key | ok | disconn | timeout | 529
0   | 88 |      24 |      21 |  0
1   | 84 |      33 |      10 |  3
2   | 90 |      41 |      10 |  1
3   | 87 |      25 |      14 |  2
4   | 79 |      34 |      10 |  1
```
→ disconn 均匀分布在 24-41，5 个 key 各自独立 SOCKS5 出口 (7894-7899) + 5 个 egress IP (134.x.101.197/197/193/195/180) 全部劣化 → **NVCF 侧 overload，非单 key/单代理/单 IP**。

**30min request-level**:
- SR **82.9%** (34/41)
- 错误: all_tiers_exhausted 3 (avg 190845ms = 烧满 180s budget), buffer_exhausted 2, client_gone_during_flush 1, stream_absolute_cap 1

**3h 逐小时 request SR**（持续劣化, 非瞬态）:
```
06:00 | 40 | 35 | 87.5%
07:00 |101 | 88 | 87.1%
08:00 |110 | 96 | 87.3%
09:00 | 53 | 42 | 79.2%
```

**NV-CONN 小时趋势（proxy 日志, 恶化）**: 09:00=5, 11:00=13, 13:00=19, 14:00=26, 15:00=36, 16:00=34, 17:00=21

**fallback 触发**: hm4104 日志 05:18 与 05:19 UTC 出现 PRIMARY-FAIL(502 stream) + FALLBACK-FAIL(ms_gw timeout) → NVCF 劣化已实际造成 hermes 主链路切到 ms_gw。

### 排除本地因素
- mihomo **active**, 全部代理端口 (7880/7894-7899/7900-7903) LISTEN, NVCF 可达 (401) → 连通性正常
- 5 个 key / 5 个 egress IP 均匀劣化 → 非 key 配额 / 非单代理 / 非单 IP 墙
- 529_nv_overloaded 出现 7 次 → NVCF 显式返回 overload 信号

### 为何不改参数
- `UPSTREAM_TIMEOUT=50`: RemoteDisconnected 平均 35.9s 是 **NVCF 主动关闭连接**，非我方超时；调低/调高都无法阻止 NVCF 关闭。
- `TIER_BUDGET=180`: 3 次 ATE 烧满 budget 是「5 key 全劣化」期间的正常行为，非 budget 设置错误。
- `KEY_COOLDOWN/429_COOLDOWN/CONN_COOLDOWN`: 均针对 key 级/代理级故障，本场景 5 key 全劣化，冷却无收益。
- 铁律「不扰动稳定健康区间」：RN1048-1064 健康稳态用的是当前参数，为修复 NVCF 外部瞬态改参数属「对着幻影调参」。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | 440/660 (66.7% attempt-OK) | RemoteDisconnected 151, timeout 65, 529×7 |
| 3h | 87.5/87.1/87.3/79.2% | 持续劣化, 非瞬态 |
| 30min | 82.9% (34/41) | 3 ATE (190s each) |
| 24h | all_tiers_exhausted=31 (滚动口径) | 与 RN1065 的 27 相比证实现象在持续 |
| fallback | 2 (hm4104) | NVCF 劣化已推主链路到 ms_gw |

## 结论

链路劣化是 **NVCF 侧持续 overload**（RemoteDisconnected 均匀分布全 5 key/5 出口 IP + 显式 529 + 逐小时恶化），mihomo/代理/连通性/本容器参数均正常。**没有任何本地可调参数能改变 NVCF 关闭连接的行为**。为保持 RN1048-1064 健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测：若 NVCF 劣化在 6-12h 内消退（RemoteDisconnected 回落、SR 回到 >95%），则确认外部瞬态，无需参数变更。
- 若劣化持续 >24h 或进一步加剧（SR<80%），考虑在 **HM1 nv_gw 层面**（非本容器）评估：是否将 dsv4f0731_nv 的 tier 优先级下调、让 hm4104 更���走 ms_gw fallback —— 这是架构/路由层决策，需在 CC 主导的 nv_gw 优化轮中做，不在本容器自优化范围。
- 关注 fallback 频次：若 hm4104 频繁 primary→ms_gw，说明 DSV4F NVCF 链路对用户体验已不可靠，应向上反馈。
- 保持当前参数观测；仅在 NVCF 劣化消退后若仍有残余错误聚集，才重新评估超时/预算。