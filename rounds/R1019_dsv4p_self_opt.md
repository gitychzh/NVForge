# R1019: 529 账户级风暴收敛 — 恢复观察轮 (SR 68.8%→88.9%, 无参数修改)

> 时间: 2026-08-05 06:56 BJT (22:56 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — 账户级 529 风暴收敛, SR 回升至 88.9%
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1018 为观察轮 (SR 68.8%, 529 风暴第 9 轮未收敛)。本轮确认风暴已收敛。

### 529 账户级过载逐小时 (nv_tier_attempts, tier=dsv4f0731_nv)
| hour(UTC) | 529_nv_overloaded | total attempts |
|-----------|-------------------|----------------|
| 18:00 | 118 | 129 |
| 19:00 | **191** (峰值) | 207 |
| 20:00 | 113 | 135 |
| 21:00 | 5 | 38 |
| 22:00 | **3** | 39 |

**风暴已收敛**: 191/hr → 3/hr (下降 98.4%)。

### 30min 窗口 (注入 context)
- 总量 27, 200=24, **SR=88.9%** (R1018 同窗 68.8% → 回升)
- Avg/P50/P95: 38651ms / 29898ms / 78623ms
- 错误: **all_tiers_exhausted=3** (累积 87402ms avg, 残余)
- 429: 0, key_cycle_429s: k0=16, k1=11 (风暴残余 key 轮转)
- upstream: **全 nvcf_pexec** (27, 200=24) — integrate lane 保持清除
- finish_reason: tool_calls=19, stop=5

### 30min tier_attempts 失败细分 (20 次 key 尝试全失败)
- **NVCFPexecRemoteDisconnected: 17** (远程瞬断, 主导)
- 529_nv_overloaded: 2
- empty_200: 1
- 分布: k0=1, k1=3(+empty_200), k2=6, k3=6(+529), k4=4(+529)

## 2. 决策: 无参数修改 (恢复观察轮)

**依据:**
1. **主导错误已从账户级 529 (191/hr) 转为瞬态 NVCFPexecRemoteDisconnected (17/30min)** —
   后者是远程断开, 非 timeout/cooldown/budget/fastbreak 可消除。
2. **SR 已从 68.8% 回升至 88.9%**, 方向正确, 不需干预。
3. **R1017 revert + R1018 确认已达参数优化极限** — 本容器可调参数已无用武之地。
4. **改前必有数据**: 无任何数据支持改动可进一步提升 SR (残余错误为远程瞬断)。

## 3. 当前状态 (30min 主指标)

- 30min SR: **88.9%** (24/27), 较 R1018 68.8% 回升
- Avg/P50/P95: 38651ms / 29898ms / 78623ms
- 错误: all_tiers_exhausted=3 (残余, 风暴衰退)
- 429: 0, key_cycle_429s: k0=16, k1=11
- upstream: pexec 27/200=88.9%, integrate 0 (已清除)
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1018 观察轮 / R1017 revert integrate lane)

- 30min SR **68.8% → 88.9%** (持续回升)
- 529_nv_overloaded **427/4h → 3/hr** (账户级风暴收敛)
- integrate upstream 保持归零, 5-key pexec 池冗余完整
- NVStream_IncompleteRead 保持消失

## 5. 下一步建议

1. **若 SR 继续回升并稳定 ≥95%** → 转 NOP 报告, 本容器达健康基线。
2. **若残余 NVCFPexecRemoteDisconnected 持续高位** → 无参数可解, 属远程瞬断,
   评估是否需额外 NVCF key / 不同 egress IP 池。
3. **若 hm4104 持续 fallback** → 说明 dsv4f0731_nv 上游仍不稳定, 评估 PRIMARY_MODEL
   依赖是否过重。
4. **下一轮**: 风暴已收敛, 趋势是恢复; 若 SR≥95% 转 NOP, 否则维持观察。