# R2103 (HM2→HM1): TIER_COOLDOWN_S 64→66 (+2s)

## 数据来源
- HM1 (opc_uname@100.109.153.83): docker logs nv_gw, docker exec logs_db psql
- 6h 窗口: 31 req / 19 OK (61.3% SR) / 12 fail

## 错误分布 (6h)
| 错误类型 | 数量 | 模型 | 可修性 |
|---------|------|------|--------|
| zombie_empty_completion | 8 | glm5_2_nv | NVCF func-level, 不可修 |
| all_tiers_exhausted | 6 | glm5_2_nv | 3 ATE + 3 dsv4p_nv |
| dsv4p all_tiers_exhausted | 3 | dsv4p_nv | NVCF key exhausted (6-7ms), 不可修 |
| NVStream_IncompleteRead | 1 | glm5_2_nv | 罕见 |

## 429 状态
- 22/31 (71%) key_cycle_429s
- KEY=71, TIER=64 (before change)
- pexec_timeout: 12/38 tier attempts (31.6%)

## 变更
- **TIER_COOLDOWN_S: 64→66 (+2s)**
- 轮换模式: R2100(KEY+2)→R2101(TIER+2)→R2102(KEY+2)→R2103(TIER+2)
- KEY+TIER=71+66=137 < 153 BUDGET (16s margin)
- TIER+2s 推动 NVCF function rate window 恢复间隔
- 8 zombie 全为 NVCF func-level empty200 (不可本地修复)
- 3 dsv4p ATE 全为 NVCF key exhaustion (6-7ms 即时返回)
- 单参数; 铁律: 只改 HM1 不改 HM2

## 验证
- docker compose up -d nv_gw 重启成功
- env 确认: TIER_COOLDOWN_S=66, KEY_COOLDOWN_S=71
- docker logs 无错误

## ⏳ 轮到HM1优化HM2