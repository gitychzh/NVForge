# R1020: 529 风暴彻底收敛 + 残余远程瞬断 — 恢复观察轮 (SR 88.9%→82.8%, 无参数修改)

> 时间: 2026-08-05 07:15 BJT (23:15 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — 账户级 529 风暴彻底收敛, 残余错误为远程瞬断
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1019 为恢复观察轮 (SR 88.9%, 529 风暴第 9 轮收敛)。本轮确认风暴**彻底**收敛,
残余主导错误为 `NVCFPexecRemoteDisconnected` (远程瞬断, 非本容器可调参数可解)。

### 529 账户级过载逐小时 (nv_tier_attempts, tier=dsv4f0731_nv)
| hour(UTC) | 529_nv_overloaded | RemoteDisconnected | total attempts |
|-----------|-------------------|--------------------|----------------|
| 18:00 | 118 | 9 | 129 |
| 19:00 | **187** (峰值) | 16 | 203 |
| 20:00 | 117 | 15 | 139 |
| 21:00 | 5 | 28 | 38 |
| 22:00 | 3 | 31 | 37 |
| 23:00 | **1** | 13 | 16 |

**风暴彻底收敛**: 187/hr → 1/hr (下降 99.5%)。残余错误已从账户级 529 转为
RemoteDisconnected (远程瞬断, 非配额/超时类)。

### 30min 窗口 (注入 context)
- 总量 29, 200=24, **SR=82.8%** (R1019 同窗 88.9% → 略降, 仍处恢复期)
- Avg/P50/P95: 39385ms / 26628ms / 83247ms
- 错误: **all_tiers_exhausted=5** (avg 80080ms)
- 429: 0, key_cycle_429s: k0=18, k1=11 (风暴残余 key 轮转计数)
- upstream: **全 nvcf_pexec** (29, 200=24) — integrate lane 保持清除
- finish_reason: tool_calls=19, stop=5

### 30min tier_attempts 失败细分 (26 次 key 尝试失败)
- **NVCFPexecRemoteDisconnected: 22** (远程瞬断, 主导)
- 529_nv_overloaded: 2
- empty_200: 2
- **per-key 分布 (RemoteDisconnected)**: k0=5, k1=3, k2=6, k3=4, k4=4 — **5 key 均匀分布**,
  非单 key 劣化, 证实为远程级/出口级瞬断, 非 key 代理问题

### 30min nv_requests 交叉验证
- status: 200=16, 502=7 (fallback 触发窗口内的请求)
- 全部 fallback_occurred=f, avg duration=51987ms (fallback 延迟偏高, 因 primary 侧超时消耗)

## 2. 决策: 无参数修改 (恢复观察轮)

**依据:**
1. **主导错误已从账户级 529 (187/hr) 转为 NVCFPexecRemoteDisconnected (22/30min)** —
   后者是远程断开, 5 key 均匀分布, 非 timeout/cooldown/budget/fastbreak 可消除。
2. **upstream.py 已内置处理**: line 85 注释 "RemoteDisconnected/SSL EOF -> short penalty
   (5-10s), do not freeze key" — 已有短惩罚 + 同 key 重试机制, 本容器参数无法进一步优化。
3. **R1017 revert + R1018/R1019 确认已达参数优化极限** — 本容器可调参数已无用武之地。
4. **SR 维持 82.8%**, 风暴收敛方向正确, 无参数改动可将残余远程瞬断转化为成功。
5. **改前必有数据**: 无任何数据支持改动可进一步提升 SR (残余错误为远程瞬断)。

## 3. 当前状态 (30min 主指标)

- 30min SR: **82.8%** (24/29), 较 R1019 88.9% 略降 (仍处恢复期, 振幅正常)
- Avg/P50/P95: 39385ms / 26628ms / 83247ms
- 错误: all_tiers_exhausted=5 (残余, 由 RemoteDisconnected 链式触发)
- 429: 0, key_cycle_429s: k0=18, k1=11
- upstream: pexec 29/200=82.8%, integrate 0 (已清除)
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1019 观察轮 / R1017 revert integrate lane)

- 529_nv_overloaded **187/hr → 1/hr** (账户级风暴彻底收敛, 99.5% 下降)
- integrate upstream 保持归零, 5-key pexec 池冗余完整
- NVStream_IncompleteRead 保持消失
- SR 振幅 68.8%/88.9%/82.8% — 恢复期波动, 无单调劣化

## 5. 下一步建议

1. **若残余 RemoteDisconnected 持续高位 (22/30min)**: 无本容器参数可解, 属远程瞬断,
   评估是否需额外 NVCF key 或不同 egress IP 池 (HM2 5 出口 134.195.101.197/193/195/180).
2. **若 hm4104 持续 fallback**: 说明 dsv4f0731_nv 上游仍不稳定, 评估 PRIMARY_MODEL
   依赖是否过重, 或容忍 fallback 到 dsv4f0731_ms.
3. **下一轮**: 若 SR≥95% 且 RemoteDisconnected 下降 → NOP; 若 SR 持续 <85% 且
   RemoteDisconnected 仍主导 → 维持观察, 等待远程侧恢复。