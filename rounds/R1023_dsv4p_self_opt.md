# R1023: 529 风暴收敛, RemoteDisconnected 残余主导 — 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 11:15 BJT (03:15 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — RemoteDisconnected 远程瞬断残余主导, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1022 为恢复观察轮 (SR 47%, RemoteDisconnected 17/20 主导)。本轮 30min 窗口显示
**529 账户级风暴已收敛**，RemoteDisconnected 残余主导，SR 较 R1022 回升至 61.4% (6h)。

### 30min 窗口 — nv_requests (live 查询)
- 总量 10, 200=3, 502=7, **SR=30%** (小样本高方差)
- Avg/P50/P95: 86927ms / 86277ms / 175829ms
- 错误: all_tiers_exhausted=6 (avg 122065ms) + NVStream_IncompleteRead=1
- 429: 0, key_cycle_429s: k0=9, k1=1

### 40min tier_attempts 失败细分 (live 查询, 仅 dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 16 (绝对主导, avg 41459ms)**
- empty_200: 7, NVCFPexecTimeout: 2 (avg 17951ms), 529_nv_overloaded: 1
- **per-key RemoteDisconnected 分布**: k0=3, k1=3, k2=2, k3=4, k4=4 — **5 key 均匀分布**,
  非单 key 劣化。empty_200 亦跨 k0/k1/k2/k3 均匀。

### 6h 趋势 (nv_requests)
- 207 总, 127 ok, **SR=61.4%** (较 R1022 同窗 47% 回升)
- 24h all_tiers_exhausted: 124 (早前风暴累积)

### 3h 逐小时 (趋势方向)
| hour(UTC) | total | ok | err | avg_ok_ms |
|-----------|-------|----|-----|-----------|
| 03:00 | 3  | 0  | 3  | -   |
| 02:00 | 28 | 14 | 14 | 31363 |
| 01:00 | 21 | 8  | 13 | 50796 |
| 00:00 | 26 | 17 | 9  | 50469 |

SR 在 00:00→02:00 区间回升 (9→14 ok), 03:00 小样本波动。

## 2. 决策: 无参数修改 (恢复观察轮, 第 6 轮)

**依据:**
1. **主导错误 RemoteDisconnected 16 (40min) — 远程段 read-stage 瞬断**, 5 个不同 mihomo
   出口 (7894-7897/7904 → 134.195.101.197/193/195/180) 全部均匀命中, 非单 key/单出口问题。
2. **远程瞬断非 timeout/cooldown/budget/fastbreak 可消除** — 与 R1017-R1022 结论一致。
3. **529_nv_overloaded 已大幅收敛** (40min 内仅 1 次, 较 R1020 峰值 187/hr、R1022 81/6h
   显著下降) — 账户级风暴已解除, 剩余 RemoteDisconnected 为纯远程链路瞬断。
4. **改前必有数据**: 无任何数据支持本容器参数改动可提升 SR (错误为远程段断开, 均匀跨
   5 key 5 出口, 非本容器可归因)。
5. **SR 回升趋势已现** (47% → 61.4%), 无参数干预下正在自然恢复, 不应在恢复期扰动参数。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **30%** (3/10, 小样本高方差) / **6h SR: 61.4%** (127/207, 恢复中)
- Avg/P50/P95: 86927ms / 86277ms / 175829ms
- 错误: all_tiers_exhausted=6 (RemoteDisconnected 链式触发), NVStream_IncompleteRead=1
- 429: 0
- upstream: pexec 全部 (10/200=3), integrate 0
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1022 观察轮 / R1017 revert integrate lane)

- **529_nv_overloaded 显著收敛**: 81/6h → 1/40min (账户级风暴解除)
- **SR 回升**: 47% → 61.4% (6h), 自然恢复中, 无参数扰动
- integrate upstream 保持归零, 5-key pexec 池冗余完整
- RemoteDisconnected 残余主导 (远程瞬断), 非本容器参数劣化

## 5. 下一步建议

1. **若 RemoteDisconnected 持续高位 (>70%)**: 无本容器参数可解, 属 NVCF 上游/mihomo 出口到
   NVCF 的远程瞬断。评估是否需额外 NVCF egress IP 池或冗余 NVCF key / 备用 upstream provider。
2. **若 hm4104 持续 fallback**: 主链路尚未稳定, 容忍 fallback 到 dsv4f0731_ms 是当前最稳
   路径, 不建议强行回主。
3. **下一轮**: 若 SR≥95% 且 RemoteDisconnected 下降 → NOP; 若 RemoteDisconnected 仍主导
   (>70%) 且 SR<80% → 维持观察, 等待远程侧恢复; 若出现单 key 劣化 (非均匀分布) → 才考虑
   key 级参数调整。

## 验证清单
- [x] /health 正常 (pre-collection: status ok, proxy_role passthrough, 5 keys)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 决策数据驱动: 16/40min RemoteDisconnected 均匀跨 5 key 5 出口 → 远程瞬断, NOP