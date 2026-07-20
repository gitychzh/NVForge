# R2099 (HM2→HM1): TIER_COOLDOWN_S 60→62 (+2s)

## 数据采集 (HM1, 6h window)
- **总请求**: 31 (19 OK / 12 fail) = 61.3% SR
- **错误分类**:
  - zombie_empty_completion: 8 (glm5_2_nv, big-input ~208k chars)
  - all_tiers_exhausted: 3 (2 phantom status=200, 1 real dsv4p_nv status=502)
  - NVStream_IncompleteRead: 1
- **key_cycle_429s**: 22 req (18×1 cycle, 2×5 cycles, 1×7 cycles, 1×3 cycles)
  - 19/19 OK successes 全部带有 key_cycle_429s=1 (100% of successes hit 429 on first key)
- **Tier attempts 6h**: 19 pexec_success, 13 pexec_timeout, 6 pexec_SSLEOFError
- **成功延迟**: glm5_2_nv avg=22,467ms, min=5,628ms, max=119,756ms
- **当前配置**: KEY_COOLDOWN_S=67 (R2098), TIER_COOLDOWN_S=60, TIER_TIMEOUT_BUDGET_S=153

## 分析
- Zombies 占失败的 67% (8/12), 全部发生在 glm5_2_nv 大输入场景
- 即使 KEY_COOLDOWN=67s, 仍有 22 次 key_cycle_429s — 说明 NVCF 侧 rate limiting 依然活跃
- 13 pexec_timeout + 6 SSLEOFError 在 tier attempt 层 — 表明 tier 层面连续失败导致 zombie
- TIER_COOLDOWN=60 与 KEY_COOLDOWN=67 不对称: key 冷却 67s 但 tier 只冷却 60s
- 增加 TIER_COOLDOWN 让 tier 级失败后延长冷却, 减少连续 zombie 产生

## 优化
- **参数**: TIER_COOLDOWN_S: 60 → 62 (+2s)
- **理由**: 22 key_cycle_429s 表明 429 压力高; tier 冷却 60s 不足, 与 KEY_COOLDOWN=67 不对称
- **预算**: KEY+TIER=67+62=129 < 153 BUDGET (24s 余量), 安全
- **预期**: 减少 tier 级连续失败→zombie 链, 16h 后观察 zombie 数量和 SR 变化
- **单参数, 铁律**: 只改 HM1 不改 HM2

## 验证
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=62 ✓
- `docker compose up -d nv_gw` → Container restarted, no errors
## ⏳ 轮到HM1优化HM2
