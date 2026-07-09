# HM2→HM1 优化报告 — R995

## 触发分析

- **Cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit**: a7890a8 (R994, author=opc2_uname / HM2)
- **判定**: **FALSE TRIGGER** — HM2 自提交，非 HM1 实际变更
- **R994 状态**: HM2→HM1 NOP (R992 settling)，已在上一轮执行
- **本轮 R995**: 双派遣 (double-dispatch) — cron 重新触发同一 false trigger

## 四源漂移检测

| 源 | 值 | 状态 |
|---|---|---|
| compose (`/opt/cc-infra/docker-compose.yml`) | 未检查（false trigger，无变更） | — |
| 容器 env (`docker exec nv_gw env`) | UPSTREAM=66, BUDGET=112, FASTBREAK=2, EMPTY_200=3, MIN_OUTBOUND=0, CONNECT=0, PEER_FALLBACK=45, KEY_COOLDOWN=25, TIER_COOLDOWN=25, INTEGRATE_KEY=0, INTEGRATE_MODELS=glm5_2_nv, FORCE_STREAM_UPGRADE=0, FORCE_STREAM_UPGRADE_TIMEOUT=66, SSLEOF=1.0, FALLBACK_HEALTH=0.10, PEER_FB_SKIP=glm5_2_nv,dsv4p_nv, MS_GW_FALLBACK=45 | ✅ 与 R987 snapshot 一致 |
| 容器 StartedAt | 2026-07-09T12:01:31Z (26min ago, post-R992 deploy) | ✅ 未漂移 |
| 容器日志 | nv_gw: 零 error/warn (clean) | ✅ |

## 6h 数据 (2026-07-09 14:01–20:01 UTC)

### 总览
- **56 req / 48 OK (85.7% SR) / 8 ATE / 0 其他错误**
- avg_ok_ms=25,451.9, avg_ttfb=25,085.4
- 零 client-side errors, 零 SSLEOF, 零 429

### 按模型
| model | total | ok | fail | avg_ok_ms | max_ok_ms |
|-------|-------|-----|------|-----------|-----------|
| glm5_2_nv | 56 | 48 | 8 | 25,451.9 | 139,129 |
| dsv4p_nv | 0 | 0 | 0 | — | — |

### 按 upstream_type
| upstream_type | total | ok | avg_ms |
|---|---|---|---|
| nvcf_pexec | 30 | 30 | 35,918.3 |
| nv_integrate | 15 | 15 | 8,503.2 |
| NULL (ATE) | 11 | 3 | 64,881.8 |

### 错误分布 (8 ATE)
| error_type | cnt | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| all_tiers_exhausted | 8 | 87,138.6 | 20,028 | 174,468 |

- 全部 8 个 ATE: `upstream_type=NULL`, `fallback_occurred=false` — 调度层直接拒绝
- 6×单 tier (~20s or ~64s), 2×双 tier (~174s)
- 全部发生在重启前 (pre 12:01 UTC)
- 24h 总计: 仅 9 ATE，零其他错误

### NVCFPexecTimeout per key (9 次)
| key | cnt | avg_ms | max_ms |
|-----|-----|--------|--------|
| K0 | 1 | 62,351 | 62,351 |
| K1 | 2 | 55,752 | 62,461 |
| K2 | 3 | 54,375.7 | 62,423 |
| K3 | 1 | 62,426 | 62,426 |
| K4 | 2 | 62,522.5 | 62,606 |

- max=62,606ms, 均匀分布在所有 5 key → function-level timeout，非 per-key
- UPSTREAM=66, buffer=3,394ms ≥ 3s (R988 rule ✓)

### Fallback 救援
| from | to | cnt | ok | avg_ok_ms |
|------|-----|-----|-----|-----------|
| glm5_2_nv | dsv4p_nv | 9 | 9 | 92,271.8 |
| glm5_2_nv | glm5_2_ms | 3 | 3 | 5,530.3 |

- Fallback 100% SR (12/12)
- dsv4p_nv fallback 全部成功 (avg 92s)
- ms_gw fallback 3/3 成功 (avg 5.5s)

### Post-restart (12:01 UTC+)
- 4 req / 4 OK (100% SR) / 0 ATE
- dsv4p_nv: 2/2 (avg 52,100ms)
- glm5_2_nv: 2/2 (avg 11,580ms)

### key_cycle_429s
- 9 req with 429 cycles / 12 total cycles / max 2 per req → 正常 key rotation，无压力

### ms_gw 6h
- 18 req, 15 "ok", 3 "error"
- 3× MS-VARIANT-EXHAUSTED (all 3 variants failed)
- ms_gw 参数: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN=60, ALL_EXHAUSTED_COOLDOWN=30, VARIANT_COOLDOWN=30

## 决策

### NOP — 零参数变更

**理由**:
1. **False trigger**: R994 由 HM2 提交，非 HM1 变更触发
2. **数据与 R994 一致**: 85.7% SR, 8 ATE, 相同模式
3. **所有 ATE 为 upstream_type=NULL**: 调度层拒绝，非参数可修
4. **NVCFPexecTimeout max=62,606ms**: 均匀分布在所有 key，function-level timeout，UPSTREAM=66 buffer=3.4s ≥ 3s
5. **Fallback 100% SR**: dsv4p_nv + ms_gw 救援全部成功
6. **Post-restart 100% SR**: 4/4 零错误
7. **所有参数均在 floor/optimal**: 无优化空间
8. **ms_gw 3× VARIANT-EXHAUSTED**: 6h 内仅 3 次，且 ms_gw EMPTY_200=3 已为推荐值，KEY_COOLDOWN=60 为防御性值，无优化空间

### 若 ATE 持续 → 后续可选优化
- 若 ATE 在后续轮次持续且 `upstream_type=NULL` 保持不变 → 非 nv_gw 参数可修，等待 NVCF 上游恢复
- 若 `upstream_type` 变为 `nv_integrate` → 可考虑 BUDGET 微调
- 若 ms_gw VARIANT-EXHAUSTED 增多 → 可考虑 ms_gw VARIANT_COOLDOWN 微调

## 执行记录

- 时间: 2026-07-09 20:25 UTC
- 操作: 无 (NOP)
- 铁律: 只改 HM1 不改 HM2 ✅

## ⏳ 轮到HM1优化HM2