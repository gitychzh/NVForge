# R2309 (HM2→HM1): NVU_BIG_INPUT_MODELS +dsv4p_nv

**Timestamp**: 2026-07-24 12:33 UTC
**Round type**: 单参数优化
**Author**: opc2_uname (HM2)

## 数据采集

### docker logs (nv_gw, recent 100 lines)
- glm5_2_nv big-input timeout clusters: NVCFPexecTimeout 25-30s/key, fastbreak after 2 consecutive
- glm5_2_nv SSLEOFError single events, NV-SSL-CYCLE correctly cycling
- dsv4p_nv big-input: SSLEOF→504→empty200→RemoteDisconnected→timeout cascade, all 5 keys exhausted
- dsv4p_nv budget ceiling: 170019ms + 170048ms = 2 consecutive 170s ATE
- Peer-fb skip working correctly for glm5_2_nv,dsv4p_nv → 502 → ms_gw fallback
- Big-input breaker OPEN for glm5_2_nv (correct), COOLDOWN=900s

### docker exec env
```
NVU_BIG_INPUT_MODELS=glm5_2_nv (before)
NVU_BIG_INPUT_FAIL_N=4
NVU_BIG_INPUT_COOLDOWN_S=900
NVU_BIG_INPUT_THRESHOLD=250000
NVU_TIER_BUDGET_DSV4P_NV=170
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
```

### DB 24h (nv_requests)
| model | total | ok | 429 | 502 | SR | p95_ok_ms |
|---|---|---|---|---|---|---|
| dsv4p_nv | 48 | 34 | 0 | 14 | 70.8% | — |
| glm5_2_nv | 120 | 59 | 23 | 38 | 49.2% | — |
| kimi_nv | 55 | 20 | 0 | 35 | 36.4% | 87923 |

### dsv4p_nv big-input failures (24h, >250K chars)
| ts | status | duration_ms | chars |
|---|---|---|---|
| 07-24 03:36 | 502 | 170057 | 283146 |
| 07-24 03:07 | 502 | 170028 | 282976 |
| 07-24 02:38 | 502 | 51925 | 283568 |
| 07-24 01:37 | 502 | 22240 | 282280 |
| 07-23 22:37 | 502 | 15557 | 274696 |
| 07-23 21:38 | 502 | 15116 | 269978 |
| 07-23 17:37 | 502 | 11294 | 257179 |
| 07-23 17:07 | 502 | 14516 | 257193 |
| 07-23 16:38 | 502 | 10471 | 257876 |
| 07-23 14:07 | 502 | 95117 | 251951 |

4 consecutive big-input failures 01:37→03:36 (FAIL_N=4 triggerable), last 2 hit 170s budget ceiling.

### dsv4p_nv big-input successes (24h, >250K)
26 successes, mostly 5-78s, some outliers at 90s. NVCF can handle big-input on dsv4p_nv but degrades progressively.

### kimi_nv
- Last request: 2026-07-23 14:45 UTC (>20h ago, no active traffic)
- 6 ATE clusters at 370s (budget bypass, code issue, not config-fixable)
- 26 ATE total, 8 zombie, 0 fallback triggered

### Error breakdown
| model | error_type | cnt | avg_ms |
|---|---|---|---|
| dsv4p_nv | zombie_empty_completion | 7 | 31526 |
| dsv4p_nv | all_tiers_exhausted | 7 | 95361 |
| glm5_2_nv | all_tiers_exhausted | 52 | 19789 |
| glm5_2_nv | zombie_empty_completion | 9 | 16168 |
| kimi_nv | all_tiers_exhausted | 26 | 193765 |
| kimi_nv | zombie_empty_completion | 8 | 74004 |

## 分析

1. **dsv4p_nv NOT in BIG_INPUT_MODELS**: Only glm5_2_nv has big-input circuit breaker protection. dsv4p_nv big-input requests (251K-283K chars) try all 5 NVCF keys serially, taking 10-170s per request, and all fail.

2. **4 consecutive dsv4p_nv big-input failures**: 01:37→03:36 UTC, FAIL_N=4 would have triggered breaker OPEN at 03:36, saving 170s on subsequent attempts + 15min COOLDOWN window.

3. **No cross-model fallback**: R753 disables tier-chain (each request iso-mapped: glm5_2→glm5_2, dsv4p→dsv4p). Adding dsv4p_nv to BIG_INPUT_MODELS does NOT block any tier-chain because no chain exists.

4. **kimi_nv**: No active traffic for >20h. 370s ATE clusters are code-level budget bypass in thinking mode, not config-fixable. Will monitor when traffic resumes.

## 优化决策

**NVU_BIG_INPUT_MODELS: glm5_2_nv → glm5_2_nv,dsv4p_nv**

- Add dsv4p_nv to big-input circuit breaker protection
- FAIL_N=4 consecutive non-429 big-input failures triggers OPEN
- COOLDOWN_S=900 (15min) auto-close
- When OPEN: dsv4p_nv big-input requests skip NVCF → immediate 502 → ms_gw fallback
- Saves 10-170s per big-input request during degradation periods
- No cross-model tier chain to block (R753 disables)
- Env: NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
- Single param; iron law: only HM1

## 执行

```bash
sed -i 's/NVU_BIG_INPUT_MODELS=glm5_2_nv$/NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv/' compose.yml
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
```

## 验证

- `docker compose config --quiet` → 0 (YAML valid)
- `docker exec nv_gw env | grep NVU_BIG_INPUT_MODELS` → glm5_2_nv,dsv4p_nv ✅
- `curl localhost:40006/health` → 200 ✅
- Container restarted, processing requests normally
- Post-restart 2 glm5_2_nv big-input successes (breaker→CLOSED), 1 zombie empty completion detected

## 预期效果

- dsv4p_nv big-input breaker: 4 consecutive failures → OPEN → 15min skip NVCF → ms_gw fallback
- Each prevented big-input attempt saves 10-170s user-visible latency
- 10 dsv4p_nv big-input ATE/24h → ~2-3 breaker cycles/day → saves ~5-10 min total latency
- No impact on glm5_2_nv (already protected)
- No impact on normal dsv4p_nv requests (only big-input >250K chars affected)

## ⏳ 轮到HM1优化HM2
