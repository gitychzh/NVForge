# R1013: 529 风暴持续第 4 轮 — NOP (账户级过载, 参数维持最优)

> 时间: 2026-08-05 03:12 BJT (19:12 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: NOP (不改参数)
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502 触发)

## 1. 背景 (改前必有数据)

R1010/R1011/R1012 记录 NVCF 529_nv_overloaded 账户级过载风暴跨越三轮。本轮确认风暴**仍在持续未收敛** (第 4 轮)。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)
- 总量 43, 200=32, SR=**74.4%** (风暴期持续拖低)
- 502=11 (all_tiers_exhausted=11)
- 429: 0, key_cycle_429s: k0=19, k1=8, k2=5, k3=3, k4=3, k5=2, k6=3 (tier cycle 计数, 非真实 429)
- Avg/P50/P95: 34779ms / 25077ms / 123352ms

### 最近 15min 请求级 (18:54-19:08)
- 8/12 = **66.7%** — 风暴仍在间歇性高峰, 无收敛铁证

### tier_attempts (30min, tier=dsv4f0731_nv)
- **529_nv_overloaded: 118** (绝对主导)
- NVCFPexecRemoteDisconnected: 12 (avg 36705ms)
- empty_200: 2
- **成功 key attempt: 0** (成功在请求级记录, tier_attempts 层全失败)

### per-key 529 均匀性 (40min) — 铁证非 per-key 问题
| key | 529 | total |
|-----|-----|-------|
| 0 | 30 | 33 |
| 1 | 30 | 34 |
| 2 | 31 | 34 |
| 3 | 30 | 32 |
| 4 | 28 | 31 |

**5 key 完全均匀 (28-31/31-34)** → 账户级过载, 非单个 key/SOCKS5 代理劣化。

### 容器日志 (近 10min)
- 大量 `529_nv_overloaded cycling to next key` 跨全 key
- 多次 `all 5 keys failed: other=4/7, elapsed=123998ms / 19711ms` — 整 tier 失败
- NV-TIER-FAIL 后 TIER_COOLDOWN_S=90 启动, hm4104 触发 fallback

## 2. 根因定性

**529_nv_overloaded 是 NVCF 账户级持续过载, 非本容器可调参数可解决。**

本轮数据与 R1010/R1011/R1012 完全一致 (无 429, 5 key 均匀 529, 零成功 key attempt)。
既有三轮已数据反证 backoff 有害 (`R-dsv4f-backoff-revert`: 80%→60%)。
per-key 均匀分布同时排除 key 分配 / SOCKS5 代理根因。

## 3. 决策: NOP (不改参数)

- 当前参数已是最优组合 (R-dsv4f-adaptive: pexec-first + 快速 cycle + keymgr 429 cooldown 120s)。
- 任何退避改动都有 SR 下降风险 (既有数据反证: backoff 80%→60%)。
- 5 key 均匀 529 说明换 key/换 egress IP 无意义 — 全账户过载。
- 本轮不冒 SR 回归之险。

## 4. 当前状态 (30min 主指标)

- 30min SR: **74.4%** (32/43, 风暴持续期); 最近 15min 66.7%
- Avg/P50/P95: 34779ms / 25077ms / 123352ms
- 错误: all_tiers_exhausted=11 (30min 请求级)
- 429: 0, key_cycle_429s=0 (请求级)
- upstream: 全 nvcf_pexec (integrate 已清空 R1006), 30min 118 次 529
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502 触发)

## 5. 验证

- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启)
- [x] per-key 529 均匀 (28-31/31-34) — 账户级确认第 4 轮
- [ ] 若 529 持续超过 24h 需升级上游侧 (额外 NVCF key / egress IP 轮换)

## 6. 上次修改效果 (R1012 观察回归)

- R1012 记录 30min SR=73.9%, 本轮 74.4% — 波动收敛, 无回归。
- 参数维持不变 (仍是最优组合), 无任何参数改动。

## 7. 下一步建议

- 本容器无可调参数能解决账户级 529 过载 — 优先级在**上游侧**:
  额外 NVCF key / 不同 egress IP 池 / 换 NVCF function_id。
- 持续观察 30min SR 是否回升至 ~82% (与 dsv4f_nv 对齐)。
- 若 hm4104 持续 fallback, 说明 dsv4f0731_nv 上游持续不可用, 需评估是否依赖过重。
- 已连续 4 轮 (R1010-R1013) 确认同一账户级过载, 建议升级为**上游侧干预**而非无限 NOP。