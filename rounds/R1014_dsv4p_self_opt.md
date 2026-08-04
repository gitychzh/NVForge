# R1014: 529 风暴持续第 5 轮 — NOP (账户级过载, 参数维持最优)

> 时间: 2026-08-05 03:14 BJT (19:14 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 via NVCF)
> 状态: NOP (不改参数)
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502 触发)

## 1. 背景 (改前必有数据)

R1010-R1013 记录 NVCF 529_nv_overloaded 账户级过载风暴跨越 4 轮。本轮确认风暴**仍在持续未收敛** (第 5 轮)。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)
- 总量 32, 200=23, SR=**71.9%** (风暴期持续拖低)
- 502=9 (all_tiers_exhausted=9)
- 429: 0, key_cycle_429s: k0=12(请求级 cycle 计数, 非真实 429)
- Avg/P50/P95: 38469ms / 29494ms / 140987ms
- upstream: 全 nvcf_pexec (32), 200=23

### nv_tier_attempts (30min, tier=dsv4f0731_nv)
- **529_nv_overloaded: 110** (绝对主导)
- NVCFPexecRemoteDisconnected: 11 (avg 36696ms)
- empty_200: 1
- **成功 key attempt: 0** (tier_attempts 层全失败)

### per-key 529 均匀性 (30min) — 铁证非 per-key 问题
| key | 529 | disconn | empty200 |
|-----|-----|---------|----------|
| 0 | 24 | 2 | 0 |
| 1 | 21 | 3 | 0 |
| 2 | 23 | 2 | 0 |
| 3 | 21 | 1 | 1 |
| 4 | 22 | 3 | 0 |

**5 key 完全均匀 (21-24 529)** → 账户级过载, 非单个 key/SOCKS5 代理劣化。

### 12h 趋势 (nv_tier_attempts) — 铁证零成功
| hour(UTC) | total | success | c529 | c_discon | c_empty |
|-----------|-------|---------|------|----------|---------|
| 18:00 | 129 | **0** | 118 | 9 | 2 |
| 19:00 | 62 | **0** | 57 | 5 | 0 |

**12 小时内 tier_attempts 层零成功 key attempt**。所有 key 尝试要么 529 要么连接断开。
请求级 71.9% SR 说明: 当账户瞬时未过载时, 首 key 立即成功 (不记 tier_attempt); 过载窗口内 cycling 全 key 529 → all_tiers_exhausted (记 tier_attempt)。

### 容器日志 (近 15min)
- 56 次 `529_nv_overloaded cycling to next key`
- 多次 `all 5 keys failed: 429=0, empty200=0, timeout=0, other=4/6/7, elapsed=16.8s/123.9s/19.7s/37.7s/45.7s`
- k5 偶发 SSLEOFError (2 次, 60ms/17113ms) — 次要
- NV-TIER-FAIL 后 TIER_COOLDOWN_S=90 启动, hm4104 触发 fallback

## 2. 根因定性

**529_nv_overloaded 是 NVCF 账户级持续过载, 非本容器可调参数可解决。**

本轮数据与 R1010-R1013 完全一致 (无 429, 5 key 均匀 529, 12h 零成功 key attempt)。
既有 4 轮已数据反证 backoff 有害 (`R-dsv4f-backoff-revert`: 80%→60%)。
per-key 均匀分布同时排除 key 分配 / SOCKS5 代理根因。

## 3. 决策: NOP (不改参数)

- 当前参数已是最优组合 (pexec-first + 快速 cycle + keymgr 429 cooldown 120s)。
- 任何退避改动都有 SR 下降风险 (既有数据反证: backoff 80%→60%)。
- 5 key 均匀 529 说明换 key/换 egress IP 无意义 — 全账户过载。
- 本轮不冒 SR 回归之险。

## 4. 当前状态 (30min 主指标)

- 30min SR: **71.9%** (23/32, 风暴持续期)
- Avg/P50/P95: 38469ms / 29494ms / 140987ms
- 错误: all_tiers_exhausted=9 (30min 请求级)
- 429: 0, key_cycle_429s=0 (请求级)
- upstream: 全 nvcf_pexec (integrate 已清空 R1006), 30min 110 次 529
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502 触发)

## 5. 验证

- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启)
- [x] per-key 529 均匀 (21-24/5) — 账户级确认第 5 轮
- [ ] 若 529 持续超过 24h 需升级上游侧 (额外 NVCF key / egress IP 轮换)

## 6. 上次修改效果 (R1013 观察回归)

- R1013 记录 30min SR=74.4%, 本轮 71.9% — 波动收敛, 无回归。
- 参数维持不变 (仍是最优组合), 无任何参数改动。

## 7. 下一步建议

- 本容器无可调参数能解决账户级 529 过载 — 优先级在**上游侧**:
  额外 NVCF key / 不同 egress IP 池 / 换 NVCF function_id。
- 持续观察 30min SR 是否回升至 ~82% (与 dsv4f_nv 对齐)。
- 若 hm4104 持续 fallback, 说明 dsv4f0731_nv 上游持续不可用, 需评估是否依赖过重。
- 已连续 5 轮 (R1010-R1014) 确认同一账户级过载, 强烈建议升级为**上游侧干预**而非无限 NOP。