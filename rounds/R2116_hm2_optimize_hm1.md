# R2116 — HM2 优化 HM1

## 数据收集 (HM1)
- **6h窗口**: 46req/24OK(52.2%SR)/12ATE(dsv4p_nv)+10zombie(glm5_2_nv)+4phantom ATE(status=200)
- **ATE详解**: 全部 dsv4p_nv, status=502, tiers_tried=1, fallback_tiers_used={dsv4p_nv} only — R753 后无跨 model fallback, 仅 peer-fb 可救
- **Zombie详解**: 全部 glm5_2_nv, 均含 key_cycle_429s(1-7), NVCF empty completion cascade
- **30min窗口**: 0req — 极低流量, sleep 期
- **最后请求**: 2026-07-20 20:03 UTC (约8h前)
- **日志**: 容器 R2115 重启后干净，无运行时 error/warn
- **Tier budget**: dsv4p=48, glm5_2=25, kimi=153(default); UPSTREAM=24
- **Peer-fb**: dsv4p 不在 skip list (仅 kimi_nv); NVU_PEER_FALLBACK_ENABLED=1; PEER_FALLBACK_TIMEOUT=122

## 优化决策
- **参数**: `TIER_COOLDOWN_S` 68 → 66 (-2s)
- **理由**: NVCF storm 已完全自愈 (HM2 R2113: 0 429, 0 SSL)。R2110 风暴期间将 TIER 从 63 升到 72，R2112→R2114 已恢复至 68。本轮继续风暴恢复：walk back R2110 增量，加速 tier 级 error 恢复。
- **安全分析**: KEY+TIER=75+66=141 < 153 BUDGET (12s余量)
- **12 ATE + 10 zombie**: 52.2%SR 主要来自 dsv4p key pool NVCF exhaust + glm5_2 429 zombie; tier cooldown 66s 对低频零流量无害, 对 dsv4p 恢复 key 冷却有帮助
- **策略**: 单参数，少改多轮，保守 -2s

## 验证
- ✅ Compose 已更新: `TIER_COOLDOWN_S: "66"` (line 505, nv_gw section)
- ✅ 容器重启成功: `docker compose up -d nv_gw` → healthy
- ✅ 实时env确认: `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=66`
- ✅ 日志干净: nv_gw 正常启动，RR 恢复，no error

## 单参数 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2