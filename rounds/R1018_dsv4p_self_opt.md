# R1018: 529 风暴第 9 轮 — 观察轮 (revert 后 SR 回升, 无参数可改)

> 时间: 2026-08-05 06:15 BJT (22:15 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **观察轮 (无参数修改)** — 529 账户级过载持续第 9 轮, 30min SR 68.8%
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1017 revert 了 k5 integrate lane (integrate 6h SR=50% 劣于 pexec 70.5%)。
本轮观察 revert 后一窗的效果, 并确认 529 风暴是否收敛。

### 30min 窗口 (注入 context)
- 总量 16, 200=11, **SR=68.8%** (R1017 同窗 33.3% → 回升)
- 错误: **all_tiers_exhausted=5** (k0 全部)
- 429: 0, key_cycle_429s: k0=13, k1=3
- upstream: **全 nvcf_pexec** (16, 200=11, SR=68.8%) — integrate lane 已清除
- finish_reason: stop=6, tool_calls=5
- per-key 200 延迟: k2 avg=14s, k3 avg=27s, k0 avg=28.5s, k4 avg=55s, k1 avg=119s(k1 单样本离群)

### 4h tier_attempts (tier=dsv4f0731_nv)
- **529_nv_overloaded: 427** (账户级 NVCF 过载, 主导)
- NVCFPexecRemoteDisconnected: 78
- empty_200: 9
- 529_integrate_overloaded: 5 (revert 后残余)
- NVCFPexecTimeout: 1

### 6h 逐小时 (created_at)
| hour | total | ok | fail | avg_ms |
|------|-------|----|------|--------|
| 18:00 | 54 | 34 | 20 | 28856 |
| 19:00 | 81 | 66 | 15 | 29483 |
| 20:00 | 47 | 33 | 14 | 39800 |
| 21:00 | 35 | 20 | 15 | 54801 |
| 22:00 | 8 | 4 | 4 | 68374 |

6h 合计 222 / 156 ok / 66 fail = **70.3% SR** — 各小时稳定 ~70%, 为风暴上限。

## 2. 决策: 无参数修改 (观察轮)

**依据:**
1. **主导错误是账户级 529_nv_overloaded (427/4h)**, 非 per-key / 参数级故障。
   任何 timeout/cooldown/budget/fastbreak 调优都无法消除账户级过载。
2. **R1017 已判定参数达优化极限** — 本容器可调参数已无用武之地。
3. **若盲目改参数违反「改前必有数据」** — 无数据支持改动可提升 SR。
4. **revert 效果正向**: 30min SR 33.3% → 68.8%, integrate lane 移除正确,
   pexec-only 5-key 池恢复完整冗余。

## 3. 当前状态 (30min 主指标)

- 30min SR: **68.8%** (11/16)
- Avg/P50/P95: 58807ms / 50987ms / 138513ms
- 错误: all_tiers_exhausted=5
- 429: 0, key_cycle_429s: k0=13, k1=3
- upstream: pexec 16/200=68.8%, integrate 0 (已清除)
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1017 revert integrate lane)

- 30min SR **33.3% → 68.8%** (回升), integrate upstream 归零
- NVStream_IncompleteRead 消失 (此前集中于 integrate 通路)
- 5-key pexec 池恢复完整 → 冗余提升
- 但 SR 仍被账户级 529 风暴压在 ~70%

## 5. 下一步建议

1. **529 账户级风暴第 9 轮未收敛** (427/4h) — 精确优先级不变:
   额外 NVCF key / 不同 egress IP 池 / 换 NVCF function_id。本容器可调参数已无用武之地。
2. **持续监控 SR** — 若风暴消退 SR 应回升至 ~82% (与 dsv4f_nv 对齐, R-fix 后 model 名已修正)。
3. **若 hm4104 持续 fallback** — 说明上游持续不可用, 需评估 dsv4f0731_nv 依赖过重 / 是否回退 PRIMARY_MODEL 到 dsv4f_nv。
4. **下一轮**: 若风暴仍在且 SR<80%, 维持观察; 若 SR≥95%, 转 NOP 报告。