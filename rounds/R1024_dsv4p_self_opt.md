# R1024: RemoteDisconnected 持续主导, SR 稳定回升 — 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 17:45 BJT (09:45 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **恢复观察轮 (无参数修改)** — RemoteDisconnected 远程瞬断残余主导, 无本容器可解参数
> Fallback: hm4104 于 17:34 UTC 触发 fallback 到 ms_gw (primary 流式 502 after 69223ms)

## 1. 背景 (改前必有数据)

R1023 为恢复观察轮 (SR 61.4%, RemoteDisconnected 主导)。本轮 30min 窗口显示
**RemoteDisconnected 仍绝对主导**, SR 稳定略升至 66.8% (6h)。529 风暴已完全收敛
(40min 内 0 次)。

### 30min 窗口 — nv_requests (live 查询)
- 总量 15, 200=9, err=6, **SR=60%** (小样本高方差)
- Avg/P50/P95: 69753ms / 69215ms / 157127ms
- 错误: all_tiers_exhausted=3 (avg 99484ms) + NVStream_IncompleteRead=1 + stream_absolute_cap=1
- upstream: pexec 全部, integrate 0
- finish_reason: tool_calls=6, stop=2
- 429: 0, key_cycle_429s: k0=8, k1=3, k2=2

### 40min tier_attempts 失败细分 (live 查询, 仅 dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 16 (绝对主导, avg 47424ms)**
- empty_200: 5, NVCFPexecTimeout: 1 (avg 22196ms)
- **per-key RemoteDisconnected 分布**: k0=6, k3=3, k4=4, k1=2, k2=1 — **5 key 均匀分布**,
  非单 key 劣化。empty_200 亦跨 k1/k2/k3 均匀。

### 6h 趋势 (nv_tier_attempts)
- RemoteDisconnected=157, empty_200=26, 529_nv_overloaded=19, NVCFPexecTimeout=10
- 529 已基本收敛 (残余来自早前风暴), RemoteDisconnected 主导

### 6h 趋势 (nv_requests)
- 199 总, 133 ok, **SR=66.8%** (较 R1023 同窗 61.4% 续升)

### 3h 逐小时 (趋势方向)
| hour(UTC) | total | ok | err | avg_ok_ms |
|-----------+-------|----|-----|-----------|
| 09:00 | 17 | 10 | 7  | 47440 |
| 08:00 | 26 | 19 | 7  | 58722 |
| 07:00 | 31 | 17 | 14 | 33788 |
| 06:00 | 18 | 14 | 4  | 38356 |

SR 各小时稳定 (56%-73%), 无突变。

### Fallback 日志 (hm4104, 最近 5min)
- 17:34 UTC: primary 流式 status=502 after 69223ms → 切 fallback 到 ms_gw
- 单次 mid-stream 502 (RemoteDisconnected 特征), 非持续不可用

## 2. 决策: 无参数修改 (恢复观察轮, 第 7 轮)

**依据:**
1. **主导错误 RemoteDisconnected 16/22 (40min) — 远程段 read-stage 瞬断**, 5 个不同
   mihomo 出口 (7894-7897/7904 → 134.195.101.197/193/195/180) 全部均匀命中 (k0=6,
   k3=3, k4=4, k1=2, k2=1), 非单 key/单出口问题。
2. **远程瞬断非 timeout/cooldown/budget/fastbreak 可消除** — 与 R1017-R1023 结论一致。
3. **529_nv_overloaded 已完全收敛** (40min 内 0 次, 6h 残余 19 来自早前风暴) — 账户级
   风暴彻底解除, 剩余 RemoteDisconnected 为纯远程链路瞬断。
4. **SR 稳定略升** (61.4% → 66.8%, 6h), 无退化趋势, 不应在恢复期扰动参数。
5. **改前必有数据**: 无任何数据支持本容器参数改动可提升 SR (错误为远程段断开, 均匀
   跨 5 key 5 出口, 非本容器可归因)。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **60%** (9/15, 小样本高方差) / **6h SR: 66.8%** (133/199, 稳定)
- Avg/P50/P95: 69753ms / 69215ms / 157127ms
- 错误 (40min): RemoteDisconnected=16, empty_200=5, NVCFPexecTimeout=1
- 429: 0
- upstream: pexec 全部 (15/15), integrate 0
- fallback: hm4104 于 17:34 触发一次 fallback (primary 流式 502, mid-stream RemoteDisconnected)

## 4. 上次修改效果 (R1023 观察轮 / R1017 revert integrate lane)

- **529_nv_overloaded 完全收敛**: 81/6h → 0/40min (账户级风暴彻底解除)
- **SR 稳定续升**: 61.4% → 66.8% (6h), 无参数扰动下自然恢复
- integrate upstream 保持归零, 5-key pexec 池冗余完整
- RemoteDisconnected 仍主导 (远程瞬断), 非本容器参数劣化

## 5. 下一步建议

1. **若 RemoteDisconnected 持续高位 (>70%)**: 无本容器参数可解, 属 NVCF 上游/mihomo
   出口到 NVCF 的远程瞬断。评估是否需额外 NVCF egress IP 池或冗余 NVCF key / 备用
   upstream provider。
2. **若 hm4104 持续 fallback**: 主链路尚未完全稳定, 容忍 fallback 到 dsv4f0731_ms 是
   当前最稳路径, 不建议强行回主。
3. **下一轮**: 若 SR≥95% 且 RemoteDisconnected 下降 → NOP; 若 RemoteDisconnected 仍
   主导 (>70%) 且 SR<80% → 维持观察; 若出现单 key 劣化 (非均匀分布) → 才考虑 key 级
   参数调整。

## 验证清单
- [x] /health 正常 (pre-collection: status ok, proxy_role passthrough, 5 keys)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势 均已采集
- [x] 决策数据驱动: 16/40min RemoteDisconnected 均匀跨 5 key 5 出口 → 远程瞬断, NOP