# R2175: HM2→HM1 — KEY_COOLDOWN_S 32→30 (-2s)

## 数据 (6h window, 2026-07-21 17:20 UTC)

### 请求汇总
| Model | Total | OK | Fail | SR | avg_ok_ms | ATE | Zombie | 429 |
|---|---|---|---|---|---|---|---|---|
| glm5_2_nv | 27 | 24 | 3 | 88.9% | 26685 | 0 | 3 | 27/27 (100%) |
| dsv4p_nv | 3 | 0 | 3 | 0% | — | 3 | 0 | 0 |
| **Total** | **30** | **24** | **6** | **80.0%** | — | **3** | **3** | **27** |

### 错误分析
- **dsv4p_nv ATE ×3**: all pre-empted (tiers_tried=1, 0 tier_attempts, duration 1-2s). TIER_COOLDOWN_S=18 blocking the primary tier from even attempting its first key. Not config-fixable by KEY_COOLDOWN — this is TIER_COOLDOWN pre-emption.
- **glm5_2_nv zombie ×3**: NVCF func-level empty completions. BIG_INPUT breaker threshold=90K, FAIL_N=3. Zombies at 7479-15195ms, within normal zone.
- **glm5_2_nv key_cycle_429s=27/27**: 100% structural cooldown alignment (pair pattern at ~30min intervals). 5 keys, 1.08 cycles/req, benign.

### 预算
- KEY+TIER+GLM5_2 = 30+18+28 = 76 < 153 BUDGET (77s margin) ✓
- Peer-fb: UPSTREAM=24, PEER_FALLBACK=122, 24+122=146 < 153 (7s margin) ✓
- 0 peer-fb events in 6h (dsv4p ATE pre-empted before peer-fb stage)

### Logs
- Container just restarted (R2174 deploy), no error logs accumulated
- Health: OK, proxy_role=passthrough, all 5 keys active

## 变更
- **KEY_COOLDOWN_S**: 32 → 30 (-2s)
- 继续 alternating KEY→TIER pattern (R2173 KEY 34→32, R2174 TIER 20→18, R2175 KEY 32→30)
- 30s > 0s (NVCF no-cooldown boundary), 5 keys × 30s cooldown = 150s rotation window
- dsv4p ATE pre-empted by TIER_COOLDOWN=18, not affected by KEY_COOLDOWN change
- glm5_2 100% key_cycle_429s pattern: reducing KEY_COOLDOWN from 32→30 reduces inter-key rotate time by 2s per cycle, benign

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: 30 ✓
- `curl /health`: status=ok ✓
- Container restarted with `docker compose stop nv_gw && docker compose up -d nv_gw`

## ⏳ 轮到HM1优化HM2
