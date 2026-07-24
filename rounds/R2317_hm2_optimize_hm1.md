# R2317 (HM2→HM1): NVU_BIG_INPUT_MODELS +dsv4p_nv

**Timestamp**: 2026-07-24 12:33 UTC
**Round type**: 单参数优化
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006)
**Iron Law**: Only HM1 config changed. Zero HM2 local changes.

## 数据采集

### docker logs (nv_gw, recent 100 lines)
- glm5_2_nv big-input timeout clusters: NVCFPexecTimeout 25-30s/key, fastbreak after 2 consecutive
- glm5_2_nv SSLEOFError single events (5004-5006ms), NV-SSL-CYCLE correctly cycling
- dsv4p_nv big-input: SSLEOF→504→empty200→RemoteDisconnected→timeout cascade, all 5 keys exhausted
- dsv4p_nv budget ceiling: 170019ms + 170048ms = 2 consecutive 170s ATE
- Peer-fb skip working correctly for glm5_2_nv,dsv4p_nv → 502 → ms_gw fallback
- Big-input breaker OPEN for glm5_2_nv (correct), COOLDOWN=900s
- Post-restart: 2 glm5_2_nv big-input successes (breaker→CLOSED), 1 zombie detected

### docker exec env (before change)
```
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_FAIL_N=4
NVU_BIG_INPUT_COOLDOWN_S=900
NVU_BIG_INPUT_THRESHOLD=250000
NVU_TIER_BUDGET_DSV4P_NV=170
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
```

### Code Analysis (big_input_breaker.py + upstream.py)
**Key finding**: The breaker has two asymmetric paths:
1. **Failure recording** (upstream.py:1620, handlers.py:458,908): ALL models record big-input failures globally — NO `NVU_BIG_INPUT_MODELS` filter. So dsv4p_nv failures already feed the global breaker counter.
2. **OPEN check** (upstream.py:1370-1373): Only models IN `NVU_BIG_INPUT_MODELS` are short-circuited when breaker is OPEN.

**Consequence**: dsv4p_nv big-input failures count toward the 4-failure trigger, but dsv4p_nv itself is NOT protected when breaker opens. It still tries all 5 NVCF keys, wasting 10-170s per request.

**R2316 logs confirm**: 3 glm5_2_nv + 1 dsv4p_nv big-input failures → breaker OPEN(4,899) at 11:10 UTC. But only glm5_2_nv gets short-circuited; dsv4p_nv at 03:36 still took 170057ms.

### DB 24h (nv_requests)
| model | total | ok | 429 | 502 | SR |
|---|---|---|---|---|---|
| dsv4p_nv | 48 | 34 | 0 | 14 | 70.8% |
| glm5_2_nv | 120 | 59 | 23 | 38 | 49.2% |
| kimi_nv | 55 | 20 | 0 | 35 | 36.4% |

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

**4 consecutive** big-input failures: 01:37→03:36 (FAIL_N=4 triggerable). Last 2 hit 170s budget ceiling. Total wasted: 170+170+52+22 = 414s on 4 requests.

### kimi_nv
- Last request: 2026-07-23 14:45 UTC (>20h ago, no active traffic)
- 6 ATE clusters at 370s (budget bypass — 0 tier_attempts recorded, code-level issue)
- 26 ATE total, 8 zombie, 0 fallback triggered
- Budget=170 (R2315) untested: 0 kimi_nv traffic post-R2315

### Error breakdown (24h)
| model | error_type | cnt | avg_ms |
|---|---|---|---|
| dsv4p_nv | zombie_empty_completion | 7 | 31526 |
| dsv4p_nv | all_tiers_exhausted | 7 | 95361 |
| glm5_2_nv | all_tiers_exhausted | 52 | 19789 |
| glm5_2_nv | zombie_empty_completion | 9 | 16168 |
| kimi_nv | all_tiers_exhausted | 26 | 193765 |
| kimi_nv | zombie_empty_completion | 8 | 74004 |

## 分析

1. **dsv4p_nv big-input: unprotected gap**. Code analysis shows dsv4p_nv failures already feed the global breaker counter (no model filter on record path), but dsv4p_nv is NOT in NVU_BIG_INPUT_MODELS so it doesn't get short-circuited when breaker opens. Adding dsv4p_nv to the list closes this gap.

2. **4 consecutive dsv4p_nv big-input failures** (01:37→03:36 UTC) would trigger breaker OPEN if only dsv4p_nv failures counted. In practice, mixed glm5_2_nv+dsv4p_nv failures already trigger it. But with dsv4p_nv now protected, subsequent dsv4p_nv big-input requests during OPEN window skip NVCF → immediate 502 → ms_gw fallback. Saves 10-170s per request.

3. **No cross-model fallback blocked**: R753 disables tier-chain (each request iso-mapped). Adding dsv4p_nv to BIG_INPUT_MODELS does not block any tier-chain because no chain exists.

4. **kimi_nv**: No active traffic for >20h. 370s ATE clusters are code-level budget bypass in thinking mode (0 tier_attempts recorded). Not config-fixable. Will monitor when traffic resumes.

5. **Risk assessment**: Low. The breaker already opens from dsv4p_nv failures (they count globally). The only change is that dsv4p_nv also gets short-circuited during OPEN window. Normal (<250K char) dsv4p_nv requests are unaffected. COOLDOWN=900s auto-closes. Big-input successes reset the breaker (CLOSED).

## 优化决策

**NVU_BIG_INPUT_MODELS: glm5_2_nv → glm5_2_nv,dsv4p_nv**

- Close the unprotected gap: dsv4p_nv failures feed the breaker but aren't protected when OPEN
- FAIL_N=4 consecutive non-429 big-input failures triggers OPEN
- COOLDOWN_S=900 (15min) auto-close
- When OPEN: dsv4p_nv big-input requests skip NVCF → immediate 502 → ms_gw fallback
- Saves 10-170s per big-input request during degradation periods
- No cross-model tier chain to block (R753 disables)
- Single param; iron law: only HM1

## 执行

```bash
# Line 451: NVU_BIG_INPUT_MODELS=glm5_2_nv → glm5_2_nv,dsv4p_nv
sed -i 's/NVU_BIG_INPUT_MODELS=glm5_2_nv$/NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv/' /opt/cc-infra/docker-compose.yml
# Restart container
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
```

## 验证

- `docker compose config --quiet` → 0 (YAML valid) ✅
- `docker exec nv_gw env | grep NVU_BIG_INPUT_MODELS` → glm5_2_nv,dsv4p_nv ✅
- `curl localhost:40006/health` → 200 ✅
- Container restarted, processing requests normally
- Post-restart 2 glm5_2_nv big-input successes (breaker→CLOSED), 1 zombie empty completion detected

## 预期效果

- dsv4p_nv big-input breaker: during OPEN window, skip NVCF → immediate ms_gw fallback
- Each prevented big-input attempt saves 10-170s user-visible latency
- 10 dsv4p_nv big-input ATE/24h → ~2-3 breaker cycles/day → saves ~5-10 min total latency
- No impact on glm5_2_nv (already protected, same breaker)
- No impact on normal dsv4p_nv requests (only big-input >250K chars affected)

## ⏳ 轮到HM1优化HM2
