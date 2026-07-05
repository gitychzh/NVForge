# R721: HM2→HM1 — UPSTREAM_TIMEOUT 40→38 (−2s)

## TL;DR
dsv4p_nv primary NVCF function `74f02205` 健康度持续回升 (0.1→0.308)，FALLBACK_GRAPH 双向正常。dsv4p_nv NVCFPexecTimeout avg 31-33k ms << 38s 安全。38-40s 边缘桶 6h 仅 3 次成功 (0.5/hr) — 全部可通过 glm5_2 fallback 救回 (94.3% SR)。每请求节省 2s 超时等待。单参数每轮；铁律：只改 HM1 不改 HM2。

## 变更
- **UPSTREAM_TIMEOUT: 40 → 38 (−2s)**
- 其他参数不变：BUDGET=110, FASTBREAK=1, FALLBACK_HEALTH_THRESHOLD=0.10, KEY_COOLDOWN=25, CONNECT_RESERVE=0, MIN_OUTBOUND=0, FORCE_STREAM_UPGRADE=0/40

## 12h 整体数据 (截至 2026-07-05 09:36 UTC)
- **408 req / 295 OK (72.3%) / 117 ATE (28.7%)**
- dsv4p_nv: 206 req / 105 OK (51.0%) / avg 29,712ms
- glm5_2_nv: 194 req / 183 OK (94.3%) / avg 20,582ms
- kimi_nv: 8 req / 7 OK (87.5%)

## 2h 最近数据
- dsv4p_nv: 131 req / 64 OK (48.9%) — 大部分通过 fallback 成功
- glm5_2_nv: 97 req / 95 OK (97.9%) — 极稳定
- Fallback 成功: 50/50 (100%), avg 57,127ms, max 99,088ms

## ATE 分类 (12h)
- tiers_tried_count=1: 72 ATE, avg 46,243ms — **全部 fallback_actually_attempted=f, 全部 pre-05:23 UTC**
  - start_tier_idx=1 (dsv4p_nv): 60, avg 49,241ms — 旧容器 (pre-restart)
  - start_tier_idx=3 (glm5_2_nv): 11, avg 33,847ms
  - start_tier_idx=0: 1, avg 2,682ms
- tiers_tried_count=2: 45 ATE, avg 91,021ms — 双 tier NVCF 真正耗尽
- 06:00-09:00 UTC: 全部 ATE 均为 tiers_tried_count=2 (fallback 正常)

## NVCFPexecTimeout (dsv4p_nv, 12h 失败尝试)
- 69 timeouts, 5 keys 均匀分布: k0=14, k1=14, k2=19, k3=11, k4=11
- avg 31,479ms, max 40,492ms
- **avg 31-33k << 38s 安全** — 38s 容纳 avg + ~5s 余量

## NVCFPexecTimeout (glm5_2_nv, 12h 失败尝试)
- 15 timeouts, avg 30,012ms, max 40,271ms

## dsv4p_nv 成功延迟分布 (2h)
| Bucket | Count |
|--------|-------|
| 0-10s  | 10    |
| 10-20s | 16    |
| 20-30s | 16    |
| 30-40s | 6     |
| 40-50s | 7     |
| >50s   | 9     |

38-40s 边缘桶: 6h 仅 3 次成功 — 全部 fallback 可救回

## 小时级 SR 趋势
| 小时 (UTC) | 请求 | OK | ATE | SR% |
|-----------|------|-----|-----|-----|
| 19:00 (Jul 4) | 114 | 99 | 15 | 86.8 |
| 20:00 | 14 | 8 | 6 | 57.1 |
| 21:00 | 15 | 8 | 7 | 53.3 |
| 22:00 | 28 | 13 | 15 | 46.4 |
| 23:00 | 9 | 8 | 1 | 88.9 |
| 00:00 (Jul 5) | 2 | 2 | 0 | 100.0 |
| 01:00 | 13 | 8 | 5 | 61.5 |
| 02:00 | 49 | 35 | 14 | 71.4 |
| 03:00 | 27 | 20 | 7 | 74.1 |
| 04:00 | 21 | 14 | 7 | 66.7 |
| 05:00 | 20 | 7 | 13 | 35.0 |
| 06:00 | 29 | 22 | 7 | 75.9 |
| 07:00 | 24 | 21 | 3 | 87.5 |
| 08:00 | 23 | 13 | 10 | 56.5 |
| 09:00 | 21 | 17 | 4 | 81.0 |

## 健康度状态
- dsv4p_nv primary `74f02205`: health=0.1→0.308 (回升中)
- dsv4p_nv auto-switch `8915fd28`: health=0.091 (持续低)
- glm5_2_nv primary `3b9748d8`: health=0.6-0.75 (稳定)

## 日志确认
- FALLBACK_GRAPH 双向正常: dsv4p_nv→glm5_2_nv ✓, glm5_2_nv→dsv4p_nv ✓
- NV-FALLBACK-SUCCESS 持续出现
- 容器重启后 NV-PEER-FB 回退正常

## 安全分析
- BUDGET=110 >> 38+38=76s (每 tier 34s 余量)
- 38-40s 边缘成功仅 3 次/6h，fallback 100% 救回
- dsv4p_nv 超时 avg 31-33k、38s 仍 ≥ avg + 5s
- FASTBREAK=1 省 4 键 ~120s，加快失败路径
- 单参数每轮；铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2