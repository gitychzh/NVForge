# R2241: KEY_COOLDOWN_S 12→10 (−2s)

**Date**: 2026-07-22 15:13 UTC  
**Type**: HM2→HM1 single param  
**Direction**: HM2 optimizes HM1 (nv_gw KEY_COOLDOWN_S)  
**Pattern**: Alternate KEY (last KEY was R2235; R2236-2240 were TIER/BIG_INPUT/STREAM params)

## Data (6h window, collected 2026-07-22 ~15:08 UTC)

### Overall
- **38 requests, 25 OK, 13 failures → 65.8% SR**

### Per-model
| Model | Total | OK | SR% |
|-------|-------|----|-----|
| glm5_2_nv | 28 | 21 | 75.0% |
| dsv4p_nv | 10 | 4 | 40.0% |

### Error breakdown
| Model | Error type | Count |
|-------|-----------|-------|
| dsv4p_nv | all_tiers_exhausted | 6 |
| glm5_2_nv | zombie_empty_completion | 4 |
| glm5_2_nv | all_tiers_exhausted | 3 |

### Latency (OK only)
| Model | Count | Avg ms | Min ms | Max ms |
|-------|-------|--------|--------|--------|
| glm5_2_nv | 21 | 27,183 | 4,998 | 92,885 |
| dsv4p_nv | 4 | 35,808 | 14,803 | 65,761 |

### Key cycling (6h)
- glm5_2_nv: 89% of OK requests cycle keys (24/27 key_cycle_429s≥1)
- dsv4p_nv: 0 key cycles

### Peer-fallback: 0/0 (unused)

### Logs (live)
```
[NV-GLM52-ATTEMPT] k2 timeout: 26979ms → mode→advance
[NV-GLM52-ATTEMPT] k3 timeout: 26949ms → mode→advance
[NV-GLM52-ATTEMPT] k4 timeout: 27459ms → mode→advance
[NV-GLM52-ATTEMPT] k5 ...
```
Single request burning k2→k3→k4→k5 all at ~27s (UPSTREAM=24s + 3s overhead). Heavy key cycling.

## Plan

**KEY_COOLDOWN_S: 12 → 10 (−2s)**

### Rationale
- Last KEY change was R2235 (14→12), then R2236-2240 changed TIER/BIG_INPUT/STREAM params
- Return to alternating KEY→TIER→KEY pattern per iron law
- 89% key cycling on glm5_2_nv: every cycle saves 2s → per-request savings compound
- Budget: KEY(10)+TIER(0)+GLM5_2(34)=44 << 157 (113s margin)
- dsv4p: KEY(10)+UPSTREAM(24)=34 << 94 (60s margin)
- 2s reduction is conservative — KEY_COOLDOWN reached 63 at peak (R1819), then 60→58→…→14→12 over 40+ rounds, validated zero over-cooldown risk

### Budget calculation
```
KEY_COOLDOWN_S   = 10  (was 12, -2)
TIER_COOLDOWN_S  = 0
GLM5_2_BUDGET    = 34
                 = 44 << 157 BUDGET (113s margin)
dsv4p: 10+24=34 << 94 (60s margin)
```

## Execution

### Remote edit
```bash
ssh -p 222 opc_uname@100.109.153.83
cd /opt/cc-infra
cp docker-compose.yml docker-compose.yml.bak.R2241
sed -i 's/KEY_COOLDOWN_S: "12"/KEY_COOLDOWN_S: "10"/' docker-compose.yml
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
```

### Verification
- `docker exec nv_gw env | grep KEY_COOLDOWN` → `KEY_COOLDOWN_S=10` ✅
- `curl localhost:40006/health` → 200 ✅
- Container restart: Recreated → Started ✅
- Logs: normal startup, new request flowing ✅

## ⏳ 轮到HM1优化HM2