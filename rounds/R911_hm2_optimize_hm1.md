# R911: HM2→HM1 — NOP (false trigger, 28th consecutive, 77/76 98.7% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

> **触发**: cron 误触发 #28 (R884→R911 连续), 脚本输出 `这是我提交的, 不触发` — HM2 自提交 R910

## 1. 触发分析

- **cron 脚本输出**: `这是我提交的, 不触发`
- **最新 commit on HM2**: `69b094d R910: HM2→HM1 — NOP (false trigger, 27th consecutive...)`
- **commit author**: `opc2_uname` (HM2 自提交 R910)
- **判定**: FALSE TRIGGER — HM1 未提交任何新内容, cron 再次派遣

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 77 |
| 成功 (200) | 76 |
| 失败 | 1 |
| 成功率 | **98.7%** |

### 2.2 按路径统计

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|----------|---------|---------|
| nvcf_pexec | 76 | 76 | 26,277ms | 26,315ms | 120,515ms |
| (NULL) | 1 | 0 | — | 121,075ms | 121,075ms |

### 2.3 ATE 详情

| 字段 | 值 |
|------|-----|
| ts | 2026-07-08 13:21:01 UTC |
| request_model | glm5_2_nv |
| tiers_tried_count | 2 |
| duration_ms | 121,075ms |
| error_type | all_tiers_exhausted |
| fallback_tiers_used | {glm5_2_nv, dsv4p_nv} |

唯一 ATE 与 R906→R910 完全相同 (同一请求, 同一 6h 窗口) — 双 tier 耗尽 (NVCF 上游故障), 非 config 可修复。

### 2.4 Fallback 统计

| fallback_occurred | cnt |
|-------------------|-----|
| false | 70 |
| true | 7 |

7 次 fallback 全部成功 (dsv4p_nv↔glm5_2_nv 双向), fallback 链健康。

### 2.5 Tier Attempts (失败尝试)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52,849 | 52,849 |
| dsv4p_nv | empty_200 | 1 | — | — |
| glm5_2_nv | empty_200 | 6 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — | — |

- NVCFPexecTimeout max=52,849ms << UPSTREAM=64 — **未绑定** (余量 11.2s)
- empty_200 共 7 次 (glm5_2 6次, dsv4p 1次), NVU_EMPTY_200_FASTBREAK=3 有效处理
- 504_nv_gateway_timeout 3次 (glm5_2) — NVCF 网关侧超时, 非本地可修复

### 2.6 最近 10 条请求

| ts | model | status | ttfb_ms | dur_ms | fallback | key_429s |
|----|-------|--------|---------|--------|----------|----------|
| 18:01:55 | glm5_2_nv | 200 | 4,237 | 4,246 | f | 0 |
| 18:01:44 | glm5_2_nv | 200 | 11,103 | 11,103 | f | 0 |
| 18:01:29 | glm5_2_nv | 200 | 14,792 | 14,792 | f | 0 |
| 18:00:53 | glm5_2_nv | 200 | 34,478 | 34,492 | f | 0 |
| 18:00:31 | dsv4p_nv | 200 | 120,514 | 120,515 | **t** | 2 |
| 18:00:24 | dsv4p_nv | 200 | 6,473 | 6,474 | f | 0 |
| 18:00:18 | glm5_2_nv | 200 | 33,840 | 33,987 | f | 0 |
| 18:00:05 | glm5_2_nv | 200 | 12,345 | 12,346 | f | 0 |
| 18:00:01 | glm5_2_nv | 200 | 2,651 | 2,652 | f | 0 |
| 17:33:21 | glm5_2_nv | 200 | 2,704 | 2,704 | f | 0 |

- 全部 200 OK, 零错误
- dsv4p_nv 18:00:31 为 outlier: empty_200→k1 NVCFPexecTimeout 52.8s→fallback glm5_2→成功 (120.5s total), key_cycle_429s=2
- glm5_2_nv 延迟 2.6s–34.5s, 全部 first-attempt 成功

### 2.7 Docker 日志 (最近 100 行)

```
ZERO ERRORS — 全部 [NV-SUCCESS] first-attempt 成功, 零 ERROR/WARN/exception/traceback
唯一要注意: [NV-EMPTY-200] k5 (dsv4p_nv) → 200 Content-Length:0 → [NV-EMPTY-CYCLE] → k1 attempt 2/7
```

### 2.8 容器环境 (关键参数)

| 参数 | HM1 值 | 状态 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 64 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | off |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | floor |
| TIER_TIMEOUT_BUDGET_S | 114 | tuned |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 3 | tuned |
| KEY_COOLDOWN_S | 25 | tuned |
| TIER_COOLDOWN_S | 25 | tuned |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | tuned |
| NVU_PEER_FALLBACK_ENABLED | 1 | on |
| NVU_PEER_FALLBACK_URL | http://100.109.57.26:40006 | HM2 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | tuned |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | tuned |

### 2.9 ms_gw 6h

| 指标 | 值 |
|------|-----|
| 总请求 | 0 |
| 当前参数 | EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300 |

ms_gw 完全空闲 — 无优化空间。

### 2.10 24h 错误全景

| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 21 |

21 次 ATE 遍及 24h — 与 R910 数据一致, 全是 NVCF 上游故障 (双 tier 耗尽), 非 config 可修复。

## 3. 优化决策

### 3.1 nv_gw 判断

- **98.7% SR** — 比 R910 (98.5%) 微升 0.2pp, 无退化
- **1 ATE** — all_tiers_exhausted, 与 R906→R910 同一请求 (同一 6h 窗口), 非可修复
- **fallback 链健康** — 双向 tier_chain 正常, 7 次 fallback 全部成功
- **Docker 日志极干净** — 零错误, 全部 first-attempt 成功
- **NVCFPexecTimeout 未绑定** — max=52,849ms << UPSTREAM=64 (余量 11.2s), 无需上调
- **nv_gw 已达 floor** — 所有可调参数均已优化到底

### 3.2 决策

**NOP** — nv_gw 已达 floor (98.7% SR), ms_gw 空闲, 无任何优化空间。HM1 停留在 R821 (88 轮落后), 等待 HM1 恢复提交新内容。

**28 轮连续 false trigger (R884→R911)**: 系统极其稳定, 无退化。数据比 R910 微升 — 同一 ATE, 更高 SR。当 HM1 恢复提交时, 需要重新收集数据 — 88 轮间隔可能带来显著变化。

## 4. 参数变更

无。零参数、零 compose、零 restart。

## 5. 评判

- 更少报错: ✅ (1 ATE, 与 R910 一致, 无新错误, Docker 日志零异常)
- 更快请求: ✅ (avg_ttfb=26.3s, fallback 健康, 无退化)
- 超低延迟: ✅ (glm5_2_nv 2.6s–34.5s, dsv4p_nv 6.5s 正常路径)
- 稳定优先: ✅ (系统 98.7% SR, fallback 链健康, tier_chain 双向完整, 28 轮连续稳定)

---

## ⏳ 轮到HM1优化HM2