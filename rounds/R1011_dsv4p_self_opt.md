# R1011: 529 风暴恢复确认 — NOP (回归观察, 参数维持最优)

> 时间: 2026-08-05 02:44 BJT (18:44 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: NOP (不改参数)
> Fallback: hm4104 风暴期触发, 本轮观察窗口内已收敛

## 1. 背景 (改前必有数据)

R1010 记录 NVCF 529_nv_overloaded 账户级过载风暴 (02:37-02:41)。本轮回归确认风暴收敛。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)
- 总量 50, 200=31, SR=**62.0%** (含风暴期拖低)
- 502=17 (all_tiers_exhausted=16, NVStream_IncompleteRead=1)
- 429: 0, key_cycle_429s=0

### 逐分钟趋势 (18:26-18:49) — 风暴收敛铁证
| 期段 | 请求 | 200 | 说明 |
|------|------|-----|------|
| 18:26-18:30 | 9 | 0 | 全部 529 overloading (风暴高峰) |
| 18:31-18:35 | 12 | 11 | 恢复, 91.7% |
| 18:36-18:41 | 11 | 6 | 间歇 surge |
| 18:42-18:49 | 16 | 12 | 恢复, 75% |

**最近 10min: SR=80% (12/15)** — 确认风暴已过, 恢复收敛。

### tier_attempts (24h, tier=dsv4f0731_nv)
- 529_nv_overloaded: 93 (84%)
- NVCFPexecRemoteDisconnected: 6 (avg 35992ms)
- empty_200: 2
- 全 pexec (integrate 已清空), 全 key 均匀 529 (k1..k5 各 14-18)

## 2. 根因定性

**529_nv_overloaded 是 NVCF 账户级持续过载, 非本容器可调参数可解决。**

本轮数据与 R1010 一致: 无 429, 全 key 均匀 529, 恢复期请求在 3-6 次 cycle 后命中成功 key。
既有两轮已数据反证 backoff 有害 (`R-dsv4f-backoff-revert`: 80%→60%; `R-dsv4f-529-backoff-nop`)。

## 3. 决策: NOP (不改参数)

- 当前参数已是最优组合 (R-dsv4f-adaptive: pexec-first + 快速 cycle + keymgr 429 cooldown 120s)。
- 10min SR 已回升 80%, 风暴收敛, 无需干预。
- 任何退避改动都有降 SR 风险 (既有数据反证), 本轮不冒此险。

## 4. 当前状态 (30min 主指标)

- 30min SR: 62.0% (31/50, 含风暴期); 最近 10min SR=80% (12/15)
- 错误: all_tiers_exhausted=16, NVStream_IncompleteRead=1
- 429: 0, key_cycle_429s=0
- upstream: 全 nvcf_pexec (integrate 已清空, R1006), 94 attempts 全 529/连接错误
- fallback: hm4104 风暴期触发 (502→ms_gw), 恢复期已停止

## 5. 验证
- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启)
- [x] 10min SR=80% 恢复确认
- [ ] 下一轮 30min 回归: 若 SR ≥80% 确认风暴彻底过去

## 6. 上次修改效果 (R-dsv4f0731-fix / R1006)
- 修复 model 名 404 → 可成功 (R-dsv4f0731-fix)
- integrate 清空走全 pexec (R1006) — 当前数据证明 pexec-only 恢复期工作正常
- 修复正确, 无回归

## 7. 下一步建议
- 常规 30min 窗口回归, 确认 SR 稳定 ≥80% (与 dsv4f_nv 对齐)。
- 若 529 surge 持续周期性复发, 优先级在**上游侧**: 额外 NVCF key / egress IP 轮换, 非本容器参数。
- 观察 hm4104 fallback 是否随风暴收敛持续停止。