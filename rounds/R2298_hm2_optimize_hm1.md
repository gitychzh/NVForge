# R2298: HM2 -> HM1 optimization round -- PROXY_TIMEOUT 400->500 (kimi_nv peer-fb rescue)

## Patrol data (HM1 nv_gw, collected ~21:25 UTC)

### NV_GW logs (last 100, error/warn)
```
[20:55:40.5] [NV-CONN] tier=kimi_nv k4 connection error: Remote end closed connection without response
[20:57:45.8] [NV-TIER-FAIL] tier=kimi_nv all 5 keys failed: 429=0, empty200=2, timeout=0, other=1, elapsed=161052ms
[20:57:45.8] [NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['kimi_nv']), elapsed=161058ms, ABORT-NO-FALLBACK
[21:05:56.5] [ERR] NV-UPSTREAM-ERROR-CHUNK write failed: [Errno 32] Broken pipe
[21:12:21.5] [ERR] NV-STREAM-BUFFER-FLUSH write failed: [Errno 32] Broken pipe
[21:12:21.5] [ERR] NV-UPSTREAM-ERROR-CHUNK write failed: [Errno 32] Broken pipe
```

### 6h stats: 80 total, 40 ok, 40 fail, avg_ok=29373ms

### Per-model 6h
| model | total | ok | fail | avg_ok_ms | avg_all_ms | key_cycles |
|-------|-------|----|------|-----------|------------|------------|
| kimi_nv | 48 | 17 | 31 | 40919 | 122063 | 11 |
| glm5_2_nv | 31 | 22 | 9 | 19836 | 24988 | 7 |
| dsv4p_nv | 1 | 1 | 0 | 42888 | 42888 | 0 |

### Error breakdown 6h
| model | error_type | error_subcategory | n |
|-------|-----------|-------------------|---|
| kimi_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 22 |
| glm5_2_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 8 |
| kimi_nv | zombie_empty_completion | | 8 |
| glm5_2_nv | zombie_empty_completion | | 1 |
| kimi_nv | NVStream_IncompleteRead | | 1 |

### ATE detail (all kimi_nv, tiers_tried_count=1, no fallback)
22 kimi_nv ATE in 6h, all `ABORT-NO-FALLBACK`. Fallback never attempted.

## Root cause analysis

kimi_nv tier uses default `TIER_TIMEOUT_BUDGET_S=370` (no explicit `NVU_TIER_BUDGET_KIMI_NV`).
Gateway reserves 370s for kimi_nv tier. With `PROXY_TIMEOUT=400`:
- Remaining: 400 - 370 = 30s
- `NVU_PEER_FALLBACK_TIMEOUT=122` → 30 < 122 → ABORT-NO-FALLBACK
- `NVU_MS_GW_FALLBACK_TIMEOUT=120` → also unreachable

→ Every kimi_nv ATE is a dead end. Peer fallback to HM2 (`NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006`) and ms_gw fallback (`kimi_nv:kimi_ms`) are both unreachable because the proxy timeout kills the request before fallback can complete.

## Fix

**PROXY_TIMEOUT: 400 → 500** (single param, iron law: only HM1)

- 500 - 370 = 130s remaining for fallback
- 130 > 122 (peer_fb_timeout) → peer fallback to HM2 can now attempt
- After peer: 130 - 122 = 8s < 120 → ms_gw still blocked, but peer-fb is the critical rescue
- Next round: observe peer-fb effectiveness, then consider 500→612 for full ms_gw fallback chain

## Live env mismatch note

`KEY_COOLDOWN_S` was 5 in live container (R2297 compose=10, not restarted). This restart also applies R2297.

## Verification

- `docker exec nv_gw env | grep PROXY_TIMEOUT` → 500 ✓
- `curl localhost:40006/health` → ok ✓
- Container restarted with `docker compose up -d nv_gw`

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记