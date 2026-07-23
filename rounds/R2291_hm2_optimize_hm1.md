# R2291 (HM2→HM1): glm5_2_nv budget 200→210

**Timestamp**: 2026-07-23 15:55 UTC
**Round type**: 单参数优化
**Author**: opc2_uname (HM2)

## 数据采集

### docker logs (nv_gw)
- 无error/warn, 正常运行
- glm5_2_nv 请求成功: 10-16s 延迟, NV-BIGINPUT-SUCCESS warm
- 无 zombie 日志在最近100行

### docker exec env
```
NVU_TIER_BUDGET_GLM5_2_NV=200 (before)
NVU_TIER_BUDGET_DSV4P_NV=160
KEY_COOLDOWN_S=0
TIER_COOLDOWN_S=0
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=275
NVU_PEER_FALLBACK_TIMEOUT=122
```

### DB 6h 窗口 (nv_requests)
| model | total | ok | fail | SR | avg_ok_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 23 | 16 | 7 | 69.6% | 31454ms |
| dsv4p_nv | 11 | 2 | 9 | 18.2% | 20518ms |

### 错误分解
| error_type | subcategory | count | model |
|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 13 | dsv4p_nv=9, glm5_2_nv=4 |
| zombie_empty_completion | | 3 | glm5_2_nv |

### ATE 详情
- dsv4p_nv: 9 ATE (all 502, all 6-11ms, tiers_tried=1, 0 tier_attempts) ← **pre-emption** (NVCF upstream 74f02205)
- glm5_2_nv: 4 ATE (3×200 phantom + 1×502, mixed 7ms pre-emption to 35s key exhaustion)
- glm5_2_nv: 3 zombie (empty-200, NVCF upstream)

### Tier Attempts
- Only 2 rows in 6h: glm5_2_nv NVCFPexecSSLEOFError=1, NVCFPexecTimeout=1
- Confirms massive pre-emption on dsv4p_nv

### Key Cycling
- 1 request with key_cycle_429s=2 (glm5_2_nv)
- 34 total, 0 cycle1, 1 cycle2+ → minimal

### Fallback
- fallback_occurred=f for all 34 requests → no peer-fb or ms-gw fallback triggered

## 分析

1. **dsv4p_nv**: NVCF upstream degradation 74f02205, all ATE are pre-emptions (0 tier_attempts, 6-11ms), not config-fixable. Skip.

2. **glm5_2_nv**: 69.6% SR. 3 zombies from NVCF empty-200 (not config-fixable). 4 ATE:
   - 2× phantom ATE (status=200, 31-46s) — key exhaustion after long zombie attempts
   - 1× 7ms pre-emption 
   - 1× 35s key exhaustion (status=502)
   
   Budget analysis: 200/5=40s/key, UPSTREAM=24s → 16s margin/key. Zombie storms eat through budget fast.

3. **No fallback triggered**: All 34 requests have fallback_occurred=false. No rescue path activated.

## 优化决策

**NVU_TIER_BUDGET_GLM5_2_NV: 200 → 210 (+10s, +2s/key)**

- 210/5=42s/key, UPSTREAM=24 → 18s margin/key (+2s)
- Global: 210+0=210 < 275 TIER_TIMEOUT_BUDGET → safe
- Target: reduce key-exhaustion ATE on glm5_2_nv by giving +10s zomibe-absorption headroom
- Single param, iron law: only HM1

## 执行

```bash
# Line 494: NVU_TIER_BUDGET_GLM5_2_NV=200 -> 210
sed -i 494s/200/210/ compose.yml
# Python rewrite for clean comment
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
```

## 验证

- `docker compose config --quiet` → 0 (YAML valid)
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV` → 210 ✅
- `curl localhost:40006/health` → 200 ✅
- Container restarted, no errors

## 预期效果

- glm5_2_nv ATE rate reduction: 4→2 (zombie pre-emptions not affected)
- Key margin: 16s→18s/key → better zombie absorption
- No impact on dsv4p_nv (NVCF upstream issue, not config-fixable)

## ⏳ 轮到HM1优化HM2