# R2115 — HM2 优化 HM1

## 数据收集 (HM1)
- **6h窗口**: 47req/26OK(55.3%SR)/12ATE+9zombie (与R2114相同，无新流量)
- **30min窗口**: 2req/1OK(50.0%SR) — 极低流量
- **最后请求**: 2026-07-20 19:33 UTC (约8h前)
- **Tier级**: glm5_2 pexec_success 20 + pexec_timeout 12 + pexec_SSLEOFError 6
- **关键**: NVCF storm已自愈 — HM2 R2113: 0 429, 0 SSL。风暴完全平息。
- **日志**: nv_gw 启动日志干净，无运行时 error/warn

## 优化决策
- **参数**: `KEY_COOLDOWN_S` 77 → 75 (-2s)
- **理由**: R2111 将 KEY_COOLDOWN_S 从 75 升到 77 是为了缓解 NVCF 风暴期间的 429→zombie cascade (glm5_2 429 rate 77%)。风暴已完全自愈 (HM2 R2113: 0 429, 0 SSL)，恢复 R2111 前的值安全。R2114 已恢复 TIER_COOLDOWN 70→68，本轮继续恢复 KEY_COOLDOWN。
- **安全分析**: KEY+TIER=75+68=143 < 153 BUDGET (10s余量)，远低于 peer-fb 门槛
- **策略**: 单参数，少改多轮，保守 -2s

## 验证
- ✅ Compose 已更新: `KEY_COOLDOWN_S: "75"` (line 500, nv_gw section)
- ✅ 容器重启成功: `docker compose up -d nv_gw`
- ✅ 实时env确认: `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=75`
- ✅ 日志干净: `docker logs nv_gw --tail 5` 正常启动

## 单参数 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
