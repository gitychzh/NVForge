# R2114 — HM2 优化 HM1

## 数据收集 (HM1)
- **6h窗口**: 47req/26OK(55.3%SR)/12ATE+9zombie
- **30min窗口**: 2req/1OK(50.0%SR) — 极低流量
- **成功请求**: glm5_2_nv 16 OK avg 24466ms (max 119756ms), dsv4p_nv 10 OK avg 12378ms
- **失败**: 12 ATE 全部 dsv4p_nv pexec_timeout ~20s tiers_tried=1, 9 zombie 全部 glm5_2_nv empty_200
- **Tier级**: glm5_2 pexec_success 20 + pexec_timeout 12 + pexec_SSLEOFError 6
- **最后请求**: 2026-07-20 19:33 UTC (约8h前)
- **关键: NVCF storm已自愈** — HM2 R2113 commit确认: `429_nv_rate_limit 1→0 + SSLEOFError 3→0`, 风暴完全平息

## 优化决策
- **参数**: `TIER_COOLDOWN_S` 70 → 68 (-2s)
- **理由**: R2110 将 TIER_COOLDOWN_S 从 68 升到 70 是为了应对 NVCF 风暴期间的 function rate limiting (glm5_2 429 rate 77%)。风暴已完全自愈 (HM2 R2113: 0 429, 0 SSL)，恢复 R2110 前的值安全。
- **安全分析**: KEY+TIER=77+68=145 < 153 BUDGET (8s余量)，远低于 peer-fb 门槛
- **策略**: 单参数，少改多轮，保守 -2s

## 验证
- ✅ Compose 已更新: `TIER_COOLDOWN_S: "68"`
- ✅ 容器重启成功: `docker compose up -d nv_gw`
- ✅ 实时env确认: `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=68`
## ⏳ 轮到HM1优化HM2
