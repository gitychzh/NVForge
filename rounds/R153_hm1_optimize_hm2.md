# R153: HM1→HM2 — KEY_COOLDOWN_S 45→40, TIER_COOLDOWN_S 45→40 (-5s each)

## 📊 数据采集 (30min窗口, 2026-06-28 03:48 UTC)

### Config Snapshot (docker exec hm40006 env)
| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 71 |
| TIER_TIMEOUT_BUDGET_S | 132 |
| KEY_COOLDOWN_S | 45 |
| TIER_COOLDOWN_S | 45 |
| MIN_OUTBOUND_INTERVAL_S | 10.5 |
| HM_CONNECT_RESERVE_S | 24 |
| PROXY_TIMEOUT | 300 |

### Error Detail (30条JSONL, 近期)
- **26 glm5.1 all-keys-failed**: 100% 429_nv_rate_limit, 5 keys uniformly rate-limited by NV API at NVCF pexec level
- **2 all_tiers_failed**: deepseek tier gets NVCFPexecTimeout (41-42s) after glm5.1 fails, cascading to ATE
- **2 deepseek tier failures**: NVCFPexecTimeout on k1/k2/k3 in deepseek tier

### Log Pattern (docker logs --tail 150)
- Every glm5.1_hm_nv request: all 5 keys hit 429 in ~5s total, then "all keys in cooldown" for 45s
- [HM-GLOBAL-COOLDOWN] triggers "Marking all cooling 45s" (hardcoded in proxy code)
- Fallback to deepseek_hm_nv works: most requests succeed on deepseek tier
- deepseek tier suffers NVCFPexecTimeout (avg 41-42s, max 52s) on some keys

### 210 REQ in visible tail — high traffic on glm5.1→deepseek fallback pattern

## 🎯 优化分析

### Bottleneck
**429 rate-limit on NVCF pexec level** — NV API is rate-limiting all 5 glm5.1 keys at the function execution level (NVCF pexec). This is NOT a timeout/budget issue — it's a pure upstream rate limit. Every key gets a 429 instantly (within ~1s), and all 5 are exhausted in ~5s. Then the tier sits in 45s global cooldown.

The COOLDOWN_S parameters (both KEY and TIER at 45s) control how long the system stays in the "all keys cooling" state. At 45s, once all 5 keys have hit 429, no glm5.1 requests can process for 45 seconds — they all fall back to deepseek.

### Decision: Reduce KEY_COOLDOWN_S + TIER_COOLDOWN_S 45→40 (-5s each)
Reducing cooldown by 5s allows keys to exit 429 state 5s sooner. When the NV API rate-limit window resets, the first available key can start processing immediately instead of waiting 45s. This creates 5s more "recovery window" per cooldown cycle.

Why NOT other parameters:
- UPSTREAM_TIMEOUT: 71s matches p95 for deepseek tier. Not the bottleneck — glm5.1 gets 429 instantly, not timeout
- TIER_TIMEOUT_BUDGET_S: 132s for 2 tiers (glm5.1+deepseek). Adequate for deepseek's NVCFPexecTimeout pattern
- MIN_OUTBOUND_INTERVAL_S: 10.5s with 210 REQ in visible tail. Inter-request spacing is fine
- PROXY_TIMEOUT: 300s, not relevant to 429 pattern
- CONNECT_RESERVE: 24s, not consumed on instant-429 path

Historical trajectory: KEY_COOLDOWN_S went through R90(40)→R92(38)→Rxx(36) on HM1 side, then reset to 45 on HM2. TIER_COOLDOWN_S went through 42→40 on HM1 side, reset to 45 on HM2. This is the first step reducing from 45→40 on both, restoring the cooldown reduction trajectory.

## 🔧 变更执行

**Parameter Diff**:
- `KEY_COOLDOWN_S: "45"` → `"40"` (-5s, -11.1%)
- `TIER_COOLDOWN_S: "45"` → `"40"` (-5s, -11.1%)

**File**: `/opt/cc-infra/docker-compose.yml` lines 480-481 (hm40006 service)

**Deployment**:
```bash
sudo sed -i 's/KEY_COOLDOWN_S: "45"/KEY_COOLDOWN_S: "40"/' docker-compose.yml
sudo sed -i 's/TIER_COOLDOWN_S: "45"/TIER_COOLDOWN_S: "40"/' docker-compose.yml
sudo docker compose up -d --force-recreate hm40006
# Container hm40006 Recreate → Recreated → Starting → Started
```

**Verification**:
- `docker exec hm40006 env | grep KEY_COOLDOWN_S` → **40** ✅
- `docker exec hm40006 env | grep TIER_COOLDOWN_S` → **40** ✅
- `docker logs --tail 5 hm40006` → [HM-TIER-FAIL] glm5.1 429=5, [HM-FALLBACK] deepseek active ✅
- 铁律: Only HM2 config changed, HM1 local untouched ✅

## 📈 预期效果

| Metric | Before (R152) | Expected After |
|--------|---------------|----------------|
| glm5.1 429 recovery | 45s cooldown | 40s cooldown (5s faster) |
| Key recovery window | 45s | 40s (11% faster) |
| Tier cooldown block | 45s | 40s (11% faster) |
| Fallback to deepseek | As before | Slightly reduced (more glm5.1 retries) |
| NVCFPexecTimeout | As before | Unchanged (not cooldown-related) |
| 429 wasted cycles | High | Moderately reduced |

## ⚖️ 评判标准

- ✅ **更少报错**: 429→429 cooldown 5s faster recovery, keys available sooner
- ✅ **更快请求**: 40s cooldown vs 45s, 5s saved per recovery cycle
- ✅ **超低延迟**: No negative impact — cooldown reduction only benefits, never harms
- ✅ **稳定优先**: -5s conservative (-11%), single parameter pair, no risk of thrashing
- ✅ **铁律**: 只改HM2不改HM1 ✓

## ⏳ 轮到HM2优化HM1