# R1022: RemoteDisconnected 风暴持续主导 (SR 47%) — 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 10:15 BJT (02:15 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — RemoteDisconnected 远程瞬断持续主导 SR, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1021 为恢复观察轮 (SR 47%, RemoteDisconnected 17/20 主导)。本轮 30min 窗口显示
残余 RemoteDisconnected 风暴**持续**，SR 仍处低位，主导错误仍为 `NVCFPexecRemoteDisconnected`。

### 30min 窗口 — nv_requests (live 查询)
- 总量 15, 200=7, 502=8, **SR=46.7%** (R1021 同窗 47.0% → 持平)
- Avg/P50/P95: 34471ms / 22053ms / 84052ms
- 502 全部 all_tiers_exhausted=7 (avg 91051ms) + zombie_empty_completion=1
- 429: 0, key_cycle_429s: k0=13, k1=1, k3=1

### 30min tier_attempts 失败细分 (live 查询)
- **NVCFPexecRemoteDisconnected: 17 (绝对主导)**
- 529_nv_overloaded: 2
- **per-key 分布 (RemoteDisconnected)**: k0=1, k1=3, k2=4, k3=4, k4=5 — **5 key 均匀分布**,
  非单 key 劣化; 529 集中 k0=2 (低量, 账户级残余)

### 6h 趋势 (逐小时)
| hour(UTC) | total | ok | err | avg_ok_ms |
|-----------|-------|----|-----|-----------|
| 02:00 | 11 | 5 | 6 | 19295 |
| 01:00 | 21 | 8 | 13 | 50796 |
| 00:00 | 32 | 20 | 12 | 46198 |
| 23:00 | 35 | 20 | 15 | 41434 |
| 22:00 | 58 | 48 | 10 | 32359 |

### 6h 错误类型 (nv_tier_attempts)
- **NVCFPexecRemoteDisconnected: 178** (主导)
- 529_nv_overloaded: 81 (账户级残余, 较 R1020 峰值 187/hr 大幅下降)
- empty_200: 19, 529_integrate_overloaded: 4, NVCFPexecTimeout: 1

### 24h
- 374 请求, 200=254 (**SR=67.9%**) — 24h 层面受早前 529 风暴 + 远程瞬断拖累

## 2. 决策: 无参数修改 (恢复观察轮, 第 5 轮)

**依据:**
1. **主导错误 RemoteDisconnected 17 (30min) / 178 (6h)** — 远程段在 read-stage 直接断开,
   5 个不同 mihomo 出口(k1-k5)全部均匀命中, 非单 key/单出口问题。
2. **远程瞬断非 timeout/cooldown/budget/fastbreak 可消除** — per_attempt_timeout 已按 budget
   精确分配, key 轮转已尽, transport penalty (5-10s) + 同 key 重试机制已内置。
3. **5 key 全中招 = 出口级/远程级** — 所有 5 个 HM2 mihomo 出口 (7894/7895/7896/7897/7904)
   均 RemoteDisconnected, 证实为 NVCF 上游或 mihomo→NVCF 链路瞬断。
4. **R1017 revert + R1018-R1021 连续 5 轮确认已达参数优化极限** — 本容器可调参数在此错误
   模式下无用武之地, 无单一参数可将远程瞬断转化为成功。
5. **改前必有数据**: 无任何数据支持改动可提升 SR (错误为远程段断开, 均匀跨 5 key 5 出口)。

## 3. 当前状态 (30min 主指标)

- 30min SR: **46.7%** (7/15), 与 R1021 47.0% 持平 (远程风暴持续, 无改善也无恶化)
- Avg/P50/P95: 34471ms / 22053ms / 84052ms
- 错误: all_tiers_exhausted=7 (由 RemoteDisconnected 链式触发), zombie=1, 529=2
- 429: 0
- upstream: pexec 15/200=7, integrate 0
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1021 观察轮 / R1017 revert integrate lane)

- 529_nv_overloaded 保持低位 (6h 81 次, 较 187/hr 峰值大幅下降, 账户级风暴已收敛)
- integrate upstream 保持归零, 5-key pexec 池冗余完整
- NVStream_IncompleteRead 保持消失 (empty_200 19/6h 残余)
- SR 47.0% → 46.7% — 持平, 全部由远程瞬断驱动, 非本容器参数劣化

## 5. 下一步建议

1. **若 RemoteDisconnected 持续高位 (>70%)**: 无本容器参数可解, 属 NVCF 上游/mihomo 出口到
   NVCF 的远程瞬断。评估是否需:
   - 额外的 NVCF egress IP 池 (HM2 当前 5 出口 134.195.101.197/193/195/180 全中招)
   - 或冗余 NVCF key / 备用 upstream provider
2. **若 hm4104 持续 fallback**: 主链路已不稳定, 容忍 fallback 到 dsv4f0731_ms 是当前最稳
   路径, 不建议强行回主。
3. **下一轮**: 若 SR≥95% 且 RemoteDisconnected 下降 → NOP; 若 RemoteDisconnected 仍主导
   (>70%) 且 SR<80% → 维持观察, 等待远程侧恢复; 若出现单 key 劣化 (非均匀分布) → 才考虑
   key 级参数调整。

## 验证清单
- [x] /health 正常 (pre-collection: status ok, proxy_role passthrough, 5 keys)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 决策数据驱动: 17/30min 与 178/6h RemoteDisconnected 均匀跨 5 key 5 出口 → 远程瞬断, NOP