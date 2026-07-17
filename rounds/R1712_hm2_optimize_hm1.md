# R1712: HM2→HM1 — KEY_COOLDOWN_S 70→60, TIER_COOLDOWN_S 70→60 (-10s each)

## 数据 (6h window, 2026-07-17 10:33–16:07 UTC)

- 54 requests: 43 OK (79.6% SR), 11 zombie_empty_completion (20.4%), 0 ATE, 0 pexec timeout, 0 fallback
- 100% key_cycle_429s: 50/54 cycle=1, 4/54 cycle=2 — k1/k4 share egress IP 134.195.101.193, effective 4-IP pool
- 11 zombies: total_input_chars 284K-315K, durations 4.9-13.4s, all finish_reason=stop+content_chars<50
- Success p50=9.85s, p95=38.9s, max=51.8s
- KEY_COOLDOWN=70, TIER_COOLDOWN=70, KEY+TIER=140<165 ✓

## 根因分析

R1708 KEY_COOLDOWN 65→70 未能降低 429 率 (100%→100%)。k1/k4 共享出口 IP 134.195.101.193, 有效 4-IP pool 交替 90s/60s 间隙, NVCF per-IP 限速总撞 60s 间隙 → per-key cooldown 70s 与此瓶颈无关。70s 仅增加人工 key 不可用时间, 不减少实际 429。

## 优化

**KEY_COOLDOWN_S 70→60 (-10s), TIER_COOLDOWN_S 70→60 (-10s)**

诊断探针: 若 429 率仍 100%, 确认 shared-IP 是唯一瓶颈, per-key cooldown 对 429 无效; 若恶化, 下轮 revert。KEY=TIER=60 per iron law。Budget: 60+60=120<<170 ✓。

## 验证

- `docker exec nv_gw env`: KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60 ✓
- `curl localhost:40006/health`: {"status":"ok"} ✓
- Restart: Container nv_gw Recreated+Started ✓

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
