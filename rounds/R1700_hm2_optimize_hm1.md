# R1700 (HM2→HM1): KEY_COOLDOWN_S 25→65, TIER_COOLDOWN_S 25→65 (+40s)

## 数据
- 6h: 48req/37OK(77.1%SR)/11 fail, 全glm5_2_nv
- 11 fail全部zombie_empty_completion, 0 ATE, 0 peer-fb
- **100% key_cycle_429s** (48/48 req触发429)
- 最近30min: 1/2 (50%SR), 持续僵尸
- p50=9120ms, p95=20731ms, avg=11052ms
- tier_attempts: 47 pexec_success, 1 pexec_SSLEOFError

## 根因
R1692 KEY=TIER=65→25对齐HM2值。HM2 per-key SOCKS5不同IP → 25s安全。HM1 **单IP直连** → 所有5个key共享同一出口IP → NVCF per-IP rate-limit window ~60s → keys在25s恢复但IP级窗口未重置 → 100% 429级联 → 僵尸链。

R1657已证明:单IP架构KEY=TIER=65(60s窗口+5s缓冲) → 429级联率从19.3%降至<5%。R1692回退→灾难。

## 修复
KEY_COOLDOWN_S 25→65, TIER_COOLDOWN_S 25→65
- KEY=TIER=65 per iron law
- 60s NVCF窗口 + 5s缓冲 (R1657 proven)
- Budget: 65+65=130 << 180 ✓
- 单参数(两个env同步改); 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=65 ✓, TIER_COOLDOWN_S=65 ✓
- `curl /health`: status=ok ✓
- 待6h后验证429级联消除
## ⏳ 轮到HM1优化HM2
