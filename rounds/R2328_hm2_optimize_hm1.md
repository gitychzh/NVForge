# R2328 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 170→120 — fail-fast on 504/conn-error retries

**Timestamp**: 2026-07-24 21:55 UTC
**Round type**: Config optimization (single param)
**Author**: opc2_uname (HM2)

## 1. 触发分析

cron 脚本检测到 HM1 有新 commit (df51c27 R2327), 判定轮到 HM2 执行优化。

## 2. 数据采集 (HM1: 100.109.153.83)

### 2.1 Container state

- nv_gw: Up healthy (started ~2h ago, R2327 deploy)
- All other containers: healthy

### 2.2 Docker logs (nv_gw --tail 100, 20:38–21:38 UTC)

**dsv4p_nv 504-retry pattern** (21:06–21:08, 21:35–21:38):
```
[21:06:00.5] NV-REQ mapped_model=dsv4p_nv tier_chain=['dsv4p_nv']
[21:06:00.5] NV-KEY tier=dsv4p_nv k3 → NVCF pexec
[21:07:04.3] NV-CYCLE k3 → 504 (504_nv_gateway_timeout)  [64s elapsed]
[21:07:04.3] NV-KEY k4 → NVCF pexec
[21:07:39.9] NV-CONN k4 connection error: Remote end closed  [36s elapsed]
[21:07:39.9] NV-KEY k5 → NVCF pexec
[21:08:46.4] NV-CYCLE k5 → 504 (504_nv_gateway_timeout)  [66s elapsed]
[21:08:46.4] NV-TIER-BUDGET budget 170.0s remaining 4.1s < 5s minimum, breaking
[21:08:46.4] NV-TIER-FAIL all 5 keys failed: other=3, elapsed=165936ms
[21:08:46.4] NV-ALL-TIERS-FAIL elapsed=165939ms, ABORT-NO-FALLBACK
```

Key observations:
- Each 504 takes ~60–66s (NVCF gateway timeout)
- Connection errors take ~35s
- 3 keys attempted: 64+36+66 = 166s, just under 170s budget
- Budget breaks with 4.1s remaining → full 170s wasted per ATE

**glm5_2_nv 429-storm** (21:03, 21:33):
```
[21:03:32] k3 429 (2.1s), k4 429 (1.6s), k5 429 (1.4s), k1 429 (1.8s), k2 429 (1.6s)
[21:03:40] TIER-FAIL all 5 keys 429, elapsed=8534ms
[21:03:40] NV-GLOBAL-COOLDOWN all keys cooling 10s
[21:03:45] TIER-SKIP all keys in cooldown, 8ms → ALL-TIERS-FAIL
[21:03:45] BIGINPUT-FAIL breaker OPEN count=4
```
- 429-storm: 5 keys in 8.5s (fast 429 responses, not 504 timeouts)
- Breaker catches subsequent requests (instant reject 8ms)
- Not addressable this round — 429 is NVCF rate-limit, not budget issue

### 2.3 DB nv_requests (24h window, 200 requests)

| model | total | 200 | 502 | 429 | SR | avg_ms (200) | avg_ms (502) | max_ms (502) |
|-------|-------|-----|-----|-----|-----|-------------|--------------|--------------|
| glm5_2_nv | 128 | 45 | 53 | 30 | 35.2% | 14479 | 11170 | 64871 |
| dsv4p_nv | 66 | 29 | 37 | 0 | 43.9% | 30977 | 46658 | 170057 |
| kimi_nv | 6 | 0 | 6 | 0 | 0% | — | 94651 | 167046 |

### 2.4 dsv4p_nv 502 failure breakdown (24h, 37 failures)

| error_type | count | avg_ms | max_ms | avg_input_chars | over100s | instant_reject |
|------------|-------|--------|--------|-----------------|----------|----------------|
| all_tiers_exhausted | 30 | 50189 | 170057 | 262657 | 9 | 18 |
| zombie_empty_completion | 7 | 31526 | 95117 | 265718 | 0 | 0 |

### 2.5 dsv4p_nv ATE >100s analysis (24h, 9 cases)

| ts | duration_ms | input_chars | input_size |
|----|-------------|-------------|------------|
| 14:05:58 | 170061 | 295268 | BIG_INPUT |
| 13:35:50 | 166164 | 295181 | BIG_INPUT |
| 13:06:00 | 165939 | 294484 | BIG_INPUT |
| 12:35:51 | 165824 | 294397 | BIG_INPUT |
| 08:05:58 | 170055 | 290345 | BIG_INPUT |
| 06:35:58 | 170046 | 288285 | BIG_INPUT |
| 03:36:22 | 170057 | 283146 | BIG_INPUT |
| 03:07:57 | 170028 | 282976 | BIG_INPUT |
| 18:03:52 (Jul23) | 160041 | 95567 | NORMAL |

**Critical finding**: 8/9 ATE >100s are BIG_INPUT (>250K chars), all hit ~170s budget ceiling.
The 1 NORMAL ATE (95567 chars, 160s) was from Jul23 before R2326 breaker tuning.

### 2.6 dsv4p_nv 200 success latency (24h)

| metric | value |
|--------|-------|
| count | 29 |
| avg_ms | 30977 |
| max_ms | 90721 |
| p95_ms | 74760 |
| p99_ms | 87194 |

### 2.7 12h focused window (dsv4p_nv)

| status | count | avg_ms | max_ms | over150s | instant_reject |
|--------|-------|--------|--------|----------|----------------|
| 200 | 1 | 52792 | 52792 | 0 | — |
| 502 ATE | 26 | 51857 | 170061 | 8 | 18 |
| 502 zombie | 1 | 51925 | 51925 | 0 | — |

12h: only 1 success vs 27 failures (3.7% SR). NVCF dsv4p_nv was severely degraded.

### 2.8 Environment (docker exec nv_gw env, pre-change)

Key params confirmed:
- `NVU_TIER_BUDGET_DSV4P_NV=170` (R2306)
- `NVU_BIG_INPUT_FAIL_N=2` (R2322) ✅ breaker working (18 instant rejects in 12h)
- `NVU_BIG_INPUT_COOLDOWN_S=120` (R2327)
- `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` (R2317)
- `NVU_BIG_INPUT_THRESHOLD=250000` (R2312)
- `KEY_COOLDOWN_S=10` (R2297)
- `TIER_COOLDOWN_S=10` (R2324)
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv` (R2323)

## 3. 分析

### 核心发现: dsv4p_nv 504-retry ATE 浪费 170s, 降预算到 120s 可省 50s/次

**问题**: 当 NVCF dsv4p_nv 后端故障 (504 gateway timeout / connection error), 每个 key 的 504 响应耗时 ~60s。当前 tier budget = 170s, 允许 3 个 key 尝试 (60+35+66=161s), 然后在 4.1s remaining 时 break。结果: 每次 ATE 浪费完整 170s。

**证据**: docker logs 显示:
- k3 → 504 at 64s, k4 → conn-error at 36s, k5 → 504 at 66s = 166s total
- Budget 170s, remaining 4.1s < 5s minimum → break
- 3 keys attempted, all failed, 170s wasted

**24h 数据**: 9 ATE >100s, 8 hit ~170s ceiling (all BIG_INPUT). 每次完整消耗 170s budget。

**Breaker 已在工作但不够**: NVU_BIG_INPUT_FAIL_N=2 + COOLDOWN=120s 的 breaker 确实在工作 (18 instant rejects in 12h = 18 × 170s saved)。但对于 30min 间隔的孤立请求, breaker 在 120s 后 HALF-OPEN, 下一个请求找到 CLOSED → 完整 170s ATE。

**优化**: 降低 NVU_TIER_BUDGET_DSV4P_NV 170→120

**效果计算**:
- 504 ~60s/key: 2 keys × 60s = 120s → budget breaks after 2 keys
- vs 170s: 3 keys × ~55s avg = 165s → 3 keys attempted
- 每次省 ~50s (第三 key 的 504 超时)
- 8 BIG_INPUT ATE in 12h × 50s = **400s (6.7min) saved in 12h**

**安全性分析**:
- 200 status max: 90721ms (90.7s)
- 200 status p99: 87194ms (87.2s)
- 新 budget 120s 给 33s margin above max success
- 120s > p99 (87.2s) by 33s → 不会误杀成功的长请求
- 120 < 415 TIER_TIMEOUT_BUDGET safe

**Breaker interaction**: breaker (FAIL_N=2, COOLDOWN=120s) 继续工作:
- 第一 ATE: 120s (was 170s) → count=1, breaker CLOSED
- 第二 ATE (within 120s): instant reject 8ms → count=2, breaker OPENS
- breaker OPEN 后: 后续 dsv4p_nv big_input 请求 instant reject → ms_gw fallback
- 降低 budget 不影响 breaker 逻辑, 只是让 ATE 更快结束

**不影响**:
- glm5_2_nv: 有自己的 budget (NVU_TIER_BUDGET_GLM5_2_NV=210), 不受影响
- kimi_nv: 有自己的 budget (NVU_TIER_BUDGET_KIMI_NV=170), 不受影响
- dsv4p_nv 正常请求 (<90s): 120s budget 远超 p99, 不受影响
- Single param change, minimal risk

## 4. 执行

```bash
# Line 493: NVU_TIER_BUDGET_DSV4P_NV=170 → 120
sed -i 's/NVU_TIER_BUDGET_DSV4P_NV=170  # R2306.*/NVU_TIER_BUDGET_DSV4P_NV=120  # R2328 (HM2->HM1): 170->120 dsv4p_nv ATE 504-retry ceiling. 12h: 8 ATE hit 170s ceiling (504 ~60s\/key, 3 keys). 120s: 2 keys x 60s = 120s break after 2 keys, saves ~50s per ATE. Safe: max success 90.7s p99 87.2s, 120s gives 33s margin. Single param; iron law: only HM1/' /opt/cc-infra/docker-compose.yml
# Validate YAML
docker compose config --quiet  # → EXIT 0
# Restart container
docker compose up -d --no-deps --force-recreate nv_gw
```

## 5. 验证

- `docker compose config --quiet` → EXIT 0 (YAML valid) ✅
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → `NVU_TIER_BUDGET_DSV4P_NV=120` ✅
- `curl localhost:40006/health` → 200 ✅
- Container recreated, status Up ✅

## 6. 预期效果

- **dsv4p_nv 504 ATE**: budget 170→120, 2 keys attempted (was 3), saves ~50s per ATE
- **8 BIG_INPUT ATE in 12h**: 8 × 50s = 400s (6.7min) saved
- **dsv4p_nv 正常请求** (max 90.7s, p99 87.2s): 不受影响, 120s 给 33s margin
- **Breaker** (FAIL_N=2, COOLDOWN=120s): 继续工作, 不受 budget 变化影响
- **glm5_2_nv, kimi_nv**: 不受影响 (各自独立 budget)

## ⏳ 轮到HM1优化HM2
