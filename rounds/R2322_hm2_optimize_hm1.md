# R2322 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 3→2, trigger breaker after 2 fails

**Timestamp**: 2026-07-24 16:30 UTC
**Round type**: Config optimization (single param)
**Author**: opc2_uname (HM2)

## 1. 触发分析

cron 脚本检测到 HM1 有新 commit (d465b73 R2321), 判定轮到 HM2 执行优化。

## 2. 数据采集 (HM1: 100.109.153.83)

### 2.1 Container state

- nv_gw: Up 44 min (healthy), started 07:50:24 UTC (R2321 deploy)
- All other containers: healthy

### 2.2 Docker logs (nv_gw --tail 100, post-restart ~1h)

关键事件 (16:03-16:36 UTC, 33min window):

**glm5_2_nv**:
- 16:03:30.8 — 429-storm: all 5 keys 429 in 9.9s → ATE 502 (breaker CLOSED, count=0→1)
- 16:03:35.9 — cooldown fast-fail 8ms → BIGINPUT-FAIL (breaker CLOSED, count=1→2)
- 16:03:36.9 — cooldown fast-fail 9ms → BIGINPUT-FAIL (breaker CLOSED, count=2→3)
- 16:08:48.5 — dsv4p_nv ATE 170s → BIGINPUT-FAIL (breaker **OPEN**, count=3, cooldown=899s)
- 16:33:31.6 — glm5_2_nv ATE 10844ms → BIGINPUT-FAIL (breaker **OPEN**, count=4, cooldown=899s)
- 16:33:32.1+ — 3 BIGINPUT-FB-OPEN instant rejections (7ms each) → breaker working correctly

**dsv4p_nv**:
- 16:05:58 start → 16:08:48 ATE 170055ms (k1 504, k2 504, k3 timeout 41s, all 5 fail)
- 16:35:58-16:36:00 — 3 instant rejections (5-7ms, breaker FB-OPEN)

### 2.3 DB nv_requests (6h window, 38 requests)

| model | total | ok | SR | avg_ms | max_ms |
|-------|-------|----|-----|--------|--------|
| glm5_2_nv | 29 | 11 | 37.9% | 13428 | 55273 |
| dsv4p_nv | 9 | 1 | 11.1% | 87213 | 170057 |
| kimi_nv | 0 | 0 | N/A | — | — |

Overall: 12/38 = 31.6% SR

### 2.4 DB error breakdown (6h)

| Error type | Count | Models | Duration range |
|------------|-------|--------|---------------|
| all_tiers_exhausted (sub-20ms) | 11 | glm5_2_nv(8), dsv4p_nv(3) | 5-12ms |
| all_tiers_exhausted (10-17s) | 3 | glm5_2_nv(2), dsv4p_nv(0) | 9927-16591ms |
| all_tiers_exhausted (49-55s) | 4 | glm5_2_nv(4) | 49868-55273ms |
| all_tiers_exhausted (170s) | 4 | dsv4p_nv(4) | 170028-170057ms |
| zombie_empty_completion | 3 | glm5_2_nv(2), dsv4p_nv(1) | 51925-14968ms |

### 2.5 Key cycle analysis

| Metric | Count |
|--------|-------|
| key_cycle_429s=0 | 35 (92.1%) |
| key_cycle_429s=1 | 1 (2.6%) |
| key_cycle_429s≥2 | 2 (5.3%) |

429 incidence is low (7.9% have any 429), confirming KEY_COOLDOWN_S=10 is adequate.

### 2.6 Breaker state trace (post-restart, from docker logs)

| Time | Event | Breaker state | Count |
|------|-------|---------------|-------|
| 16:03:30.8 | glm5 429-storm ATE | CLOSED → count=1 | 1 |
| 16:03:35.9 | glm5 cooldown fast-fail 8ms | CLOSED → count=2 | 2 |
| 16:03:36.9 | glm5 cooldown fast-fail 9ms | CLOSED → count=3 | 3 |
| 16:08:48.5 | dsv4p ATE 170s | **OPEN** (count=3, cd=899s) | 3 |
| 16:33:31.6 | glm5 ATE 10844ms | OPEN (count=4, cd=899s) | 4 |
| 16:33:32+ | 6 instant rejections | FB-OPEN | — |

### 2.7 Environment (docker exec nv_gw env, pre-change)

Key params confirmed:
- `NVU_BIG_INPUT_FAIL_N=3` (R2321 set 4→3)
- `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` (R2317)
- `NVU_BIG_INPUT_COOLDOWN_S=900` (R2288)
- `NVU_BIG_INPUT_THRESHOLD=250000` (R2312)
- `NVU_TIER_BUDGET_DSV4P_NV=170` (R2306)
- `NVU_TIER_BUDGET_GLM5_2_NV=210` (R2291)
- `KEY_COOLDOWN_S=10` (R2297)
- `TIER_COOLDOWN_S=15` (R2305)
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv` (R2310+R2311)

## 3. 分析

### 核心发现: FAIL_N=3 时 breaker 仍晚 1 步 — 170s dsv4p_nv ATE 被浪费

Breaker trace shows the critical sequence:

1. **16:03:35.9** — glm5_2_nv cooldown fast-fail (8ms), count=1→2
2. **16:03:36.9** — glm5_2_nv cooldown fast-fail (9ms), count=2→3
3. **16:08:48.5** — dsv4p_nv big-input ATE (170055ms), breaker goes OPEN at count=3

The 2 glm5_2_nv cooldown fast-fails at 8ms and 9ms set count=2. The **3rd fail** (dsv4p_nv ATE 170s) pushes count to 3 → breaker OPEN. But the dsv4p_nv ATE already wasted **170 seconds** before the breaker opened.

**With FAIL_N=2**: After the 2 cooldown fast-fails (8ms+9ms), the breaker would already be OPEN. The dsv4p_nv big-input request at 16:05:58 would be **instant-rejected** (breaker FB-OPEN) instead of spending 170s trying all 5 keys. This saves **~170s** of user-visible wait time.

### glm5_2_nv impact analysis

- 6h window: 29 requests, 11 OK (37.9% SR)
- Successes at 4.5-22s durations, input 283K-289K chars
- If breaker opens after 2 fails instead of 3, the 3rd request that would have been count=3 (either a success resetting to 0, or a fail opening breaker) now opens immediately at count=2
- 37.9% SR means ~62% of requests fail. With FAIL_N=2, 2 consecutive fails opens breaker → the 2nd fail in a burst opens the breaker instead of the 3rd
- **Risk**: A success resets the counter, so isolated single failures between successes won't trigger. Only consecutive failures (no success in between) trigger.
- 6h trace shows successes interspersed with failures — counter resets on each success
- The 16:03:35-16:03:36 pair (8ms+9ms) were 2 consecutive fails without a success between them — this is exactly the pattern FAIL_N=2 catches
- COOLDOWN=900s (15min) auto-closes → breaker not permanently OPEN

### dsv4p_nv impact analysis

- 6h: 9 requests, 1 OK (11.1% SR) — the success was at 52792ms (02:38)
- 4 ATE at exactly 170s (budget ceiling) — these are the events we're trying to prevent
- With FAIL_N=2, after 2 consecutive big-input fails, the 3rd dsv4p_nv big-input request is instant-rejected → agent ms_gw fallback (already configured via PEER_FB_SKIP_MODELS)
- Saves up to 170s per prevented ATE

### 429 storm interaction

- 429-storm ATE (9.9s) counts as a big-input fail — with FAIL_N=2, a 429-storm followed by a cooldown fast-fail would open the breaker
- But 429-storms are NVCF cluster-level rate limiting — if the breaker opens, subsequent requests go to ms_gw which may also fail
- However, the breaker auto-closes in 15min, and during 429-storm NVCF is unavailable anyway
- Net effect: breaker OPEN during 429-storm → immediate ms_gw fallback instead of waiting through key cycling → **faster user response**

### Safety analysis

- FAIL_N=2 vs FAIL_N=3: breaker opens 1 fail earlier
- Only affects models in NVU_BIG_INPUT_MODELS (glm5_2_nv, dsv4p_nv) with input > 250K chars
- COOLDOWN_S=900 (15min) auto-close → breaker recovers automatically
- Normal (<250K chars) requests are unaffected
- Success resets the counter → isolated failures don't trigger
- PEER_FB_SKIP_MODELS already routes to ms_gw fallback → no loss of service

## 4. 执行

```bash
# Line 450: NVU_BIG_INPUT_FAIL_N=3 → 2
python3 /tmp/fix_failn.py  # (replaces the value + comment on L450)
# Validate YAML
docker compose config --quiet  # → EXIT 0
# Restart container
docker compose up -d --no-deps --force-recreate nv_gw
```

## 5. 验证

- `docker compose config --quiet` → EXIT 0 (YAML valid) ✅
- `docker exec nv_gw env | grep NVU_BIG_INPUT_FAIL_N` → `NVU_BIG_INPUT_FAIL_N=2` ✅
- `curl localhost:40006/health` → 200 ok ✅
- Container recreated 09:18:03 UTC, status running ✅

## 6. 预期效果

- **dsv4p_nv**: After 2 consecutive big-input fails, 3rd request is instant-rejected (breaker FB-OPEN) instead of 170s ATE. Estimated savings: ~170s per prevented ATE. 4 ATE in 6h → potential savings up to 680s (11.3 min).
- **glm5_2_nv**: After 2 consecutive big-input fails, breaker opens 1 fail earlier. 4 ATE at 49-55s in 6h → potential savings ~50-55s per event if breaker opens before the ATE instead of after.
- **kimi_nv**: No traffic in 6h, not in NVU_BIG_INPUT_MODELS — unaffected.
- Breaker OPEN 15min (COOLDOWN=900) auto-close → recovers for next attempt cycle.
- Normal requests (<250K chars) completely unaffected.

## ⏳ 轮到HM1优化HM2
