# R1012: 529 风暴持续确认 — NOP (账户级过载, 参数维持最优)

> 时间: 2026-08-05 03:00 BJT (19:00 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: NOP (不改参数)
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502)

## 1. 背景 (改前必有数据)

R1010/R1011 记录 NVCF 529_nv_overloaded 账户级过载风暴。本轮确认风暴**仍在持续未收敛**。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)
- 总量 46, 200=34, SR=**73.9%** (风暴期持续拖低, 未达 R1011 期望的 ≥80%)
- 502=12 (all_tiers_exhausted=11, NVStream_IncompleteRead=1)
- 429: 0, key_cycle_429s: k0=23, k1=7, k2=4, k3=4, k4=4, k5=1, k6=3 (均为 tier cycle 计数, 非真实 429)

### tier_attempts (40min, tier=dsv4f0731_nv)
- **529_nv_overloaded: 132** (绝对主导)
- NVCFPexecRemoteDisconnected: 10 (avg 35206ms)
- empty_200: 2
- **成功 key attempt: 0** (成功在请求级记录, tier_attempts 层全失败)

### 逐分钟 529 分布 (18:32-19:02) — 持续未断
- 每个分钟都有 529, 无任何空白恢复期
- 18:32-19:02 全程 3-14 次/分, 无收敛迹象

### per-key 529 均匀性 (40min) — 铁证非 per-key 问题
| key | 529 数 |
|-----|--------|
| 0 | 26 |
| 1 | 26 |
| 2 | 27 |
| 3 | 27 |
| 4 | 26 |

**5 key 完全均匀 (26/26/27/27/26)** → 账户级过载, 非单个 key/SOCKS5 代理劣化。

## 2. 根因定性

**529_nv_overloaded 是 NVCF 账户级持续过载, 非本容器可调参数可解决。**

本轮数据与 R1010/R1011 完全一致 (无 429, 5 key 均匀 529, 零成功 key attempt)。
既有两轮已数据反证 backoff 有害 (`R-dsv4f-backoff-revert`: 80%→60%; `R-dsv4f-529-backoff-nop`)。
per-key 均匀分布同时排除 key 分配 / SOCKS5 代理根因。

## 3. 决策: NOP (不改参数)

- 当前参数已是最优组合 (R-dsv4f-adaptive: pexec-first + 快速 cycle + keymgr 429 cooldown 120s)。
- 任何退避改动都有 SR 下降风险 (既有数据反证: backoff 80%→60%)。
- 5 key 均匀 529 说明换 key/换 egress IP 无意义 — 全账户过载。
- 本轮不冒 SR 回归之险。

## 4. 当前状态 (30min 主指标)

- 30min SR: **73.9%** (34/46, 风暴持续期)
- Avg/P50/P95: 33383ms / 24786ms / 81136ms
- 错误: all_tiers_exhausted=11, NVStream_IncompleteRead=1
- 429: 0, key_cycle_429s=0 (请求级)
- upstream: 全 nvcf_pexec (integrate 已清空 R1006), 40min 全 key 132 次 529
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502 触发)

## 5. 验证
- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启)
- [x] per-key 529 均匀 (26/26/27/27/26) — 账户级确认
- [ ] 下一轮: 若 529 持续超过 24h 需升级上游侧 (额外 NVCF key / egress IP 轮换)

## 6. 上次修改效果 (R1011 观察回归)
- R1011 期望 10min SR ≥80% 认为风暴收敛, 本轮 30min SR=73.9% 反证**风暴未收敛仍在持续**。
- 参数维持不变, 无回归。

## 7. 下一步建议
- 本容器无可调参数能解决账户级 529 过载 — 优先级在**上游侧**:
  额外 NVCF key / 不同 egress IP 池 / 换 NVCF function_id。
- 持续观察 30min SR 是否回升至 ~82% (与 dsv4f_nv 对齐)。
- 若 hm4104 持续 fallback, 说明 dsv4f0731_nv 上游持续不可用, 需评估是否依赖过重。