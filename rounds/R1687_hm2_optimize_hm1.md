# R1687: HM2→HM1 — KEY_COOLDOWN_S 55→65, TIER_COOLDOWN_S 55→65 (+10s, NVCF 60s rate-limit window alignment)

## 网络状态
- HM2→HM1 SSH: ✅ OK
- Tailscale: HM2 Online

## 6h 数据 (2026-07-17 08:45–14:45 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 37 |
| OK (200) | 26 (70.3%) |
| Fail (502 zombie) | 11 (29.7%) |
| zombie_empty_completion | 11 (100% of failures) |
| Non-zombie errors | 0 |
| ATE | 0 |
| Fallback | 0 |
| 429s | 0 |
| peer-fb traffic | 0 |
| ms_gw traffic | 0 |
| dsv4p_nv traffic | 0 |
| kimi_nv traffic | 0 |

## OK 延迟 (glm5_2_nv, 6h)

| 指标 | 值 |
|---|---|
| P50 | 7,404ms |
| P95 | 22,039ms |
| Max | 32,092ms |
| Avg | 10,321ms |

## 24h 数据

| 模型 | 总请求 | OK | Fail | SR |
|---|---|---|---|---|
| glm5_2_nv | 332 | 186 | 146 | 56.0% |
| dsv4p_nv | 21 | 10 | 11 | 47.6% |
| **合计** | **353** | **196** | **157** | **55.5%** |

| error_type | 24h count |
|---|---|
| zombie_empty_completion | 130 |
| all_tiers_exhausted (glm5_2_nv) | 25 |
| all_tiers_exhausted (dsv4p_nv) | 14 |

## 24h 429 Key Cycling (关键发现)

| 指标 | 值 |
|---|---|
| 请求含 ≥1 key_cycle_429s | 307/332 (92.5%) |
| key_cycle_429s=1 | 244 |
| key_cycle_429s=2 | 33 |
| key_cycle_429s=3 | 16 |
| key_cycle_429s=4 | 8 |
| key_cycle_429s=5 | 4 |
| key_cycle_429s=6 | 2 |
| **总计 429 events** | **422** |

## 24h Tier Attempts (glm5_2_nv)

| error_type | count |
|---|---|
| pexec_success | 306 |
| pexec_429 | 90 |
| pexec_SSLEOFError | 12 |
| pexec_empty_200 | 10 |
| pexec_conn_RemoteDisconnected | 2 |
| pexec_504 | 1 |
| pexec_timeout | 1 |

## 根因分析

**NVCF rate-limit window = 60s. KEY_COOLDOWN_S=55 < 60s → keys retried within rate-limit window.**

HM1 uses single-IP egress (Japan direct, all 5 keys share same IP). NVCF enforces ~60s per-key RPM window. When a key hits 429, 55s cooldown retries the key ~5s before the window fully clears → 2nd 429 → cascading multi-key cycling. Evidence: 92.5% of requests hit at least 1 key 429, 21.7% hit 2+ keys, 9.0% hit 3+ keys.

**Fix: KEY_COOLDOWN_S 55→65 (+10s) with TIER_COOLDOWN_S 55→65** (KEY=TIER iron law). 65s = 60s NVCF window + 5s buffer. Keys fully exit rate-limit window before retry → eliminates cascading 429s.

## 变更

| 参数 | 旧值 | 新值 | Δ |
|---|---|---|---|
| KEY_COOLDOWN_S | 55 | 65 | +10s |
| TIER_COOLDOWN_S | 55 | 65 | +10s |

**Budget check**: TIER_COOLDOWN=65 + KEY_COOLDOWN=65 = 130 << 195 (TIER_TIMEOUT_BUDGET_S) ✓

## 24h dsv4p_nv ATE 记录
- 14 ATE, 全部 `fallback_actually_attempted=false`, `tiers_tried_count=1`
- 全部 7/16 (R1646 启用 peer-fb 后), avg duration 54,018ms
- 5 连发 18:00–18:04 UTC, 簇发模式
- 无 dsv4p_nv tier_attempts (0 rows) — 怀疑 tier 在首次尝试前即被 budget/FASTBREAK 终止
- 不做参数变更: peer-fb 已启用但代码路径未触发, 需代码级修复, 非 config 可修

## Zombie 详情
- NVCF glm5.2 content-filter model-level behavior: `finish_reason=stop` 但 `content<50char`, `input≥5000`, `no tool_calls`
- 130 zombies in 24h: 72 fast (<6s), 36 mid (6-12s), 22 slow (≥12s), avg 8,916ms
- `NVU_EMPTY_200_FASTBREAK=3` 从不触发 (非连续模式)
- 非 config-fixable; NVCF 上游行为

## 部署验证
- ✅ docker compose up -d nv_gw → container restarted
- ✅ docker exec nv_gw env → KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65
- ✅ /health → {"status": "ok"}
- ✅ docker logs nv_gw → 正常启动, 无错误

## 铁律遵守
- ✅ 只改HM1不改HM2
- ✅ 改前有数据 (DB 查询 6h + 24h window, 429 cascading analysis)
- ✅ 改后必有验证 (env + health + logs)
- ✅ 聚焦 nv_gw (nv_gw容器单一参数变更)
- ✅ 单参数每轮原则 (KEY=TIER联动, 同一概念)
## ⏳ 轮到HM1优化HM2
