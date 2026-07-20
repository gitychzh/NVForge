# R2105 (HM2→HM1): TIER_COOLDOWN_S 66→68 (+2s)

## 数据来源
- HM1 (opc_uname@100.109.153.83): docker logs nv_gw, docker exec logs_db psql
- 6h 窗口: 30 req / 18 OK (60.0% SR) / 12 fail

## 错误分布 (6h)
| 错误类型 | 数量 | 模型 | 可修性 |
|---------|------|------|--------|
| zombie_empty_completion | 8 | glm5_2_nv | NVCF func-level, 不可修 |
| all_tiers_exhausted | 3 | dsv4p_nv | 部分可修 — key 冷却不足 |
| NVStream_IncompleteRead | 1 | glm5_2_nv | 罕见 |

## 429 循环 (6h)
- 21/30 (70.0%) 请求命中 key_cycle_429s
- glm5_2_nv: 21/27 (77.78%) 429, avg 1.0 429s/req
- dsv4p_nv: 0/3 (0%) 429
- 分布: zero=9, one=16, two=1, three=1, five_plus=3

## Peer-Fallback (6h)
- 0 peer-fb 事件 (fallback_occurred 全为 false)
- 公式: UPSTREAM=24 + PEER=122 = 146 < 153 BUDGET (7s margin) — 理论上应触发
- 但 8 zombie 全为 glm5_2_nv func-level empty200 (非 key 耗尽), 不触发 peer-fb
- 3 dsv4p ATE 在 14:39 集中, 之前无 peer-fb 尝试记录

## OK 延迟 (6h)
- avg=23762ms, min=5628ms, max=119756ms
- glm5_2_nv OK 18 条: 42s, 15s, 104s, 5.6s, 6.4s, 13s, 8.6s, 119s, 12s, 6.7s, 10s, 13s, 13s, 7.5s, 7.2s, 15s, 14s, 10s

## 变更
- **TIER_COOLDOWN_S: 66→68 (+2s)**
- 轮换模式: R2101(TIER+2)→R2102(KEY+2)→R2103(TIER+2)→R2104(KEY+2)→R2105(TIER+2) — 交替推进
- KEY+TIER=73+68=141 < 153 BUDGET (12s margin)
- TIER+2s 继续推动 NVCF function rate window 恢复 — 每轮 +2s 积累
- 70% 429 循环率表明 KEY+TIER 仍不足够, 但 429 反模式要求 ≥60s, 当前 73+68 远超阈值
- 8 zombie 不可本地修复 (NVCF func-level empty200), 仅能通过 TIER 冷却缓解 cascade
- 单参数; 铁律: 只改 HM1 不改 HM2

## 验证
- docker compose up -d nv_gw 重启成功
- env 确认: TIER_COOLDOWN_S=68
- health check: 200 OK
## ⏳ 轮到HM1优化HM2
