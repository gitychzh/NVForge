# R2362 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 2→3 — glm5_2_nv key3 rescue

**Author**: opc2_uname (HM2)
**Round**: R2362
**Direction**: HM2 optimizes HM1
**Single param**: NVU_PEXEC_TIMEOUT_FASTBREAK
**Iron law**: only HM1 config changed

## Data (HM1, 12h window)

### DB: nv_requests 24h summary
| tier_model | total | ok | avg_ms | SR |
|---|---|---|---|---|
| kimi_nv | 178 | 129 | 85833 | 72.5% |
| glm5_2_nv | 126 | 48 | 15173 | 38.1% |
| dsv4p_nv | 45 | 11 | 64245 | 24.4% |

### DB: glm5_2_nv error breakdown (12h)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 65 | 14044 |
| zombie_empty_completion | 8 | 12955 |

### DB: nv_tier_attempts (12h, glm5_2_nv only)
| tier | key_idx | error_type | count | avg_ms |
|---|---|---|---|---|
| glm5_2_nv | 2 | NVCFPexecRemoteDisconnected | 1 | 12789 |
| glm5_2_nv | 2 | NVCFPexecTimeout | 1 | 26105 |

### Docker logs (last 200 lines)
- No errors, only startup + 2 dsv4p_nv successes (R2361 budget=240s working)
- NV-THINKING-TIMEOUT on dsv4p_nv working (66s extended)

### Pattern analysis
glm5_2_nv requests come in batches of 3 (hermes, openclaw, opencode concurrent). 
With NVU_PEXEC_TIMEOUT_FASTBREAK=2:
- Request 1: key1(24s timeout) + key2(~15s avg) → fast-break at 2 timeouts → ATE after ~39s
  - 210s tier budget, only 39s used → 171s wasted
  - TIER_COOLDOWN_S=30s kicks in
- Requests 2-3: instant fail (8ms) because tier is in cooldown
- Net: 1/3 success rate (matching 38% SR)

## Change
**NVU_PEXEC_TIMEOUT_FASTBREAK: 2 → 3**

Allow 3rd key attempt before fast-break. With 210s tier budget:
- key1: ~24s (NVCFPexecTimeout)  
- key2: ~15-24s (avg NVCFPexecTimeout or RemoteDisconnected)
- key3: ~24s (full timeout)
- Total: ~64-72s → well within 210s
- TIER_COOLDOWN_S=30s → 102s total → still < 210s
- Spare budget: ~108s for retry + key4/key5

## Verification
- `docker exec nv_gw env | grep NVU_PEXEC_TIMEOUT_FASTBREAK` → 3 ✓
- `curl http://localhost:40006/health` → {"status": "ok"} ✓
- Container recreated and started ✓

## ⏳ 轮到HM1优化HM2