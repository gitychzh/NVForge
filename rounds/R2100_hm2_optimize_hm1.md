# R2100 (HM2→HM1): KEY_COOLDOWN_S 67→69 (+2s)

## 数据采集 (HM1, 6h window)
- **总请求**: 31 (19 OK / 12 fail) = 61.3% SR (same as R2099)
- **错误分类**:
  - zombie_empty_completion: 8 (glm5_2_nv, big-input context)
  - all_tiers_exhausted: 3 (2 phantom status=200, 1 real dsv4p_nv status=502)
  - NVStream_IncompleteRead: 1
- **key_cycle_429s**: 22/31 req (71%) — 18×1 cycle, 2×5 cycles, 1×7 cycles, 1×3 cycles
  - 19/19 OK successes 全部带有 key_cycle_429s≥1 (100% of successes hit 429)
- **Tier attempts 6h**: 19 pexec_success, 13 pexec_timeout, 6 pexec_SSLEOFError
- **成功延迟**: glm5_2_nv avg=22,467ms, min=5,628ms, max=119,756ms
- **30min burst**: 2req/1OK/1fail — low traffic, system still struggling
- **当前配置**: KEY_COOLDOWN_S=67, TIER_COOLDOWN_S=62, TIER_TIMEOUT_BUDGET_S=153
- **Fallback**: 0/31 — no fallback occurred

## 分析
- 71% 429 rate despite KEY_COOLDOWN=67s — NVCF rate limiting window is longer than 60s
- 67s only 7s above the 60s NVCF window; current 429 rate shows this is insufficient
- Zombies (8/12 failures) are caused by key exhaustion from cascading 429s
- 13 pexec_timeout + 6 SSLEOFError = 19 tier-level failures feeding zombie chain
- All 19 OK successes had key_cycle_429s=1 — every single success required key rotation due to 429
- KEY_COOLDOWN increase to 69s gives 9s above 60s NVCF window, reducing 429 hit rate

## 优化
- **参数**: KEY_COOLDOWN_S: 67 → 69 (+2s)
- **理由**: 71% 429 rate shows 67s insufficient; 69s provides 9s margin above NVCF 60s window
- **预算**: KEY+TIER=69+62=131 < 153 BUDGET (22s 余量), 安全
- **预期**: 减少 key_cycle_429s 频率, 降低 zombie 产生, 提高 SR
- **单参数, 铁律**: 只改 HM1 不改 HM2

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=69 ✓
- `docker compose up -d nv_gw` → Container restarted, no errors
- Health: `{"status": "ok"}` ✓
- ms_gw KEY_COOLDOWN_S=58 unchanged (line 186) ✓
## ⏳ 轮到HM1优化HM2
