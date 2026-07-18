# R1833 (HM2→HM1): KEY_COOLDOWN_S=TIER_COOLDOWN_S 61→60 (-1s)

## 数据 (HM1, 6h窗口)
- 41req/37OK(90.2%SR)/4fail
- 4 kimi ATE: all `all_tiers_exhausted` NVCF function-level degraded, not config-fixable
- glm5_2_nv: 25/25 OK(100%), avg 7,674ms, max 21,582ms
- dsv4p_nv: 12/12 OK(100%), avg 15,025ms, max 40,603ms
- Docker logs: 零错误
- Fallback: 零事件
- Key cycle: glm5_2 25/25 key_cycle_429s=1 (正常轮转), dsv4p 2/12 key_cycle_429s=1 (其中2次429 rate_limit at tier level)
- Tier attempts: glm5_2_nv pexec_success 25, dsv4p_nv 429_nv_rate_limit 2

## 24h 回顾
- glm5_2_nv: 98/95 OK(96.9%), avg 8,286ms, max 21,582ms
- dsv4p_nv: 20/19 OK(95%), avg 27,399ms, max 100,418ms (1 true ATE 56.8s)
- kimi_nv: 4/0 OK(0%), all NVCF server-side degraded

## 分析
- KEY=TIER=61 (R1822) 已稳定运行 61→60 NVCF boundary +1s buffer
- 61→60→59→58→alt 轨迹从 R1819 开始持续压降, 每轮 -1s~-2s
- 当前 60s = NVCF 标准 boundary, 消除最后 1s buffer
- Budget: 60+60=120 << 180 TIER_TIMEOUT_BUDGET_S safe ✓
- Peer-fb: 60+2=62 ≤ 122 NVU_PEER_FALLBACK_TIMEOUT ✓
- 零漂移

## 变更
- `KEY_COOLDOWN_S`: 61 → 60 (-1s)
- `TIER_COOLDOWN_S`: 61 → 60 (-1s)
- KEY=TIER=60 per iron law
- 单参数对; 铁律:只改HM1不改HM2

## 验证
- `docker compose up -d nv_gw` ✓
- `/health` OK ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN` = 60 ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN` = 60 ✓
## ⏳ 轮到HM1优化HM2
