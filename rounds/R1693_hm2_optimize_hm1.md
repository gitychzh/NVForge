# R1693: HM2→HM1 — NVU_STREAM_TOTAL_DEADLINE_S 42→35 (-7s)

## 数据 (HM1 nv_gw, 6h window)
- **总计**: 38 req, 27 OK (71.1% SR), 11 fail
- **失败分析**: 全部 11 个 `zombie_empty_completion` on `glm5_2_nv`
  - 0 ATE, 0 fallback, 0 peer-fb, 0 429 cascading
  - tiers_tried=1, fallback_occurred=f, key_cycle_429s=1 (all)
  - Zombie 持续时间: 4.5s, 5.1s, 7.0s, 7.4s, 8.2s, 12.0s, 17.1s, 26.3s, 27.3s, 36.4s, 9.0s
  - 3/11 zombies >17s (慢速 zombie)
- **1h window**: 3 OK / 2 fail (60% SR)
- **成功请求**: max duration = 27.3s (glm5_2_nv pexec_success)
- **NVCF glm5_2 function**: 持续 degraded (返回 valid HTTP 200 + 空 SSE stream)

## 变更
- **NVU_STREAM_TOTAL_DEADLINE_S**: 42 → 35 (-7s)
- **理由**: 42s idle deadline 对 zombie 流太宽松。zombie 在首字节后 idle 时需等满 42s 才被 deadline 杀死。35s 仍在成功请求 max (27.3s) 之上留有 7.7s 余量，且远高于 FIRST_BYTE_DEADLINE=20s。已确认 NVCF glm5_2 成功请求在 27.3s 以内完成，35s 不会误杀正常请求。
- **预算**: 35 << 42 TIER_BUDGET=120 safe ✓
- **铁律**: 只改 HM1 不改 HM2

## 验证
- `docker exec nv_gw env | grep STREAM_TOTAL_DEADLINE` → `NVU_STREAM_TOTAL_DEADLINE_S=35` ✓
- Container restart OK
## ⏳ 轮到HM1优化HM2
