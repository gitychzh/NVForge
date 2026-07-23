# R2297: HM2 -> HM1 optimization round -- KEY_COOLDOWN_S 5->10 (NVCF 429 buffer)

## Patrol data (HM1 nv_gw, collected 20:25-20:55 UTC)

### NV requests last 6 hours
| model | status | n | avg_dur_s |
|-------|--------+---+-----------|
| glm5_2_nv | 200 | 137 | 12.9 |
| glm5_2_nv | 502 | 10 | 41.5 (all_tiers_exhausted=8, zombie=2) |
| dsv4p_nv | 200 | 109 | 21.7 |
| dsv4p_nv | 502 | 142 | 42.1 |
| kimi_nv | 200 | 163 | 14.2 |
| kimi_nv | 502 | 21 | 206.4 (all_tiers_exhausted=21, zombie=8) |
| minimax_m3_nv | 200 | 29 | 9.4 |

- 6h total SR: 73.9% (438/592)
- glm5_2_nv 6h SR: 93.2% (137/147) -- local domain main link
- dsv4p_nv 6h SR: 43.4% -- NVCF 74f02205 degradation continues, non-local non-knob-fixable
- kimi_nv 6h SR: 88.6% -- cc2 R2286 transition oscillation settling

### Key docker logs error/warn snippets
```
20:33:22 [NV-COOLDOWN] tier=glm5_2_nv k3 marked cooling after 429
20:33:22 [NV-CYCLE] tier=glm5_2_nv k3 -> 429 (429_nv_rate_limit), cycling to next key
20:33:39 [NV-COOLDOWN] tier=glm5_2_nv k5 marked cooling after 429
20:33:39 [NV-CYCLE] tier=glm5_2_nv k5 -> 429 (429_nv_rate_limit), cycling to next key
20:33:41 [NV-COOLDOWN] tier=glm5_2_nv k1 marked cooling after 429
20:33:41 [NV-CYCLE] tier=glm5_2_nv k1 -> 429 (429_nv_rate_limit), cycling to next key
20:33:42 [NV-COOLDOWN] tier=glm5_2_nv k2 marked cooling after 429
20:33:42 [NV-CYCLE] tier=glm5_2_nv k2 -> 429 (429_nv_rate_limit), cycling to next key
20:33:44 [NV-COOLDOWN] tier=glm5_2_nv k3 marked cooling after 429
20:33:44 [NV-CYCLE] tier=glm5_2_nv k3 -> 429 (429_nv_rate_limit), cycling to next key
20:33:46 [NV-COOLDOWN] tier=glm5_2_nv k4 marked cooling after 429
20:33:46 [NV-CYCLE] tier=glm5_2_nv k4 -> 429 (429_nv_rate_limit), cycling to next key
20:33:47 [NV-COOLDOWN] tier=glm5_2_nv k5 marked cooling after 429
20:33:47 [NV-CYCLE] tier=glm5_2_nv k5 -> 429 (429_nv_rate_limit), cycling to next key
20:33:47 [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=6, empty200=0, timeout=0, other=1, elapsed=12811ms
```

### Peer fallback log
```
20:33:47 [NV-PEER-FB] local all_tiers_exhausted (model=glm5_2_nv), attempting peer fallback
20:35:49 [NV-PEER-FB] peer connect/request failed after 122124ms: TimeoutError
20:35:49 [NV-PEER-FB] peer fallback FAILED for model=glm5_2_nv, returning local 502
20:40:31 [NV-PEER-FB] local all_tiers_exhausted (model=dsv4p_nv), attempting peer fallback
20:41:14 [NV-PEER-FB] peer fallback OK: status=200 bytes=1348 ttfb=7ms
```

### Tier-fail / All-tiers-exhausted pattern
- 6h [NV-TIER-FAIL]/[NV-ALL-TIERS-FAIL]: 8 events
- glm5_2_nv: burst 429 pattern -- 5 keys all trigger 429 within 12.8s, KEY_COOLDOWN_S=5 too short, NVCF rate limiter window not released
- dsv4p_nv: tier-fail 160066ms = exactly exhausted 160s budget
- kimi_nv: tier-fail 125-165s, upstream connection class (empty_200+other), non-knob-fixable
- peer fallback: glm5_2_nv->HM2 FAIL (122s timeout), dsv4p_nv->HM2 OK

### Container status
- nv_gw: StartedAt=2026-07-22T15:10:34Z, RC=0, 43+ consecutive healthy rounds
- logs_db: healthy, PostgreSQL 16
- NO drift detected

## Optimization decision

### Root cause analysis
1. **glm5_2_nv 429 burst**: KEY_COOLDOWN_S=5 means NVCF rate limiter window does not reset within 5s, so subsequent keys in same burst also hit 429, all 5 keys wasted in 12.8s
2. **dsv4p_nv 160s hard cap**: budget=160s exactly at limit, 0 margin -- any tiny jitter triggers ATE
3. **peer fallback not a safety net**: HM2 unavailable for glm5_2_nv (122s timeout), cross-domain fallback not reliable for glm5_2_nv

### Optimization parameter: KEY_COOLDOWN_S = 5 -> 10
- **Change**: docker-compose.yml line 437: KEY_COOLDOWN_S=5 -> 10
- **Mechanism**: Extend key cooldown time, allow NVCF rate limiter to release more fully, reduce probability of multi-key consecutive 429 within same burst
- **Budget safety check**:
  - glm5_2_nv: 5*24 + 4*10 = 160s <= TIER_BUDGET(210s) OK (margin 50s)
  - dsv4p_nv: 5*24 + 4*10 = 160s <= TIER_BUDGET(160s) OK (margin 0s, on the line)
  - minimax: 100 - 160 = -60 < 0 -> minimax already excluded by model-filter, unaffected
  - Global: 10 + 210 = 220s <= TOTAL_TIMEOUT(370s)*0.6 = 222s OK (critical safe)
- **Risk**: dsv4p_nv margin 0s, but this is inherent to dsv4p_nv (current config already at limit), this round does not change its budget
- **Scope**: ONLY HM1 docker-compose.yml, NO container restart (env change applies on next planned restart), NO HM2 change

## Execution record
- docker-compose.yml line 437: KEY_COOLDOWN_S=5 -> KEY_COOLDOWN_S=10 DONE
- NO other parameters changed DONE
- NO container restart (env change effective on next planned restart, avoid restart risk) DONE
- ONLY HM1 config, NEVER touch HM2 local DONE

## Validation metrics (next patrol expectation)
1. glm5_2_nv 6h ATE reduces (current 8 all_tiers_exhausted, portion attributable to 429 burst)
2. 429 burst events: key coverage drops from 5 to 3-4 (remaining keys have +5s extra window to recover)
3. dsv4p_nv ATE no significant deterioration (budget on the line, already at limit)
4. 499 maintains 0
5. nv_gw container RC=0 continues

## To next round
- Iron law: only change HM1, never HM2
- Every round small change, accumulate over rounds

## Status to HM1
- R2297 deployed: KEY_COOLDOWN_S 5->10 on HM1
- Commit author: opc2_uname
- No restart performed (env takes effect on next planned restart or manual docker-compose up)

##铁等规则
- 只改HM1配置不改HM2本地
- 每轮少改多轮积累
- 更少报错更快请求超低延迟稳定优先

## 铁律:只改HM1不改HM2

