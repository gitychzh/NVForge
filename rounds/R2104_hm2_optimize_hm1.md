# R2104 (HM2→HM1): KEY_COOLDOWN_S 71→73 (+2s)

## 数据来源
- HM1 (opc_uname@100.109.153.83): docker logs nv_gw, docker exec logs_db psql
- 6h 窗口: 30 req / 18 OK (60.0% SR) / 12 fail

## 错误分布 (6h)
| 错误类型 | 数量 | 模型 | 可修性 |
|---------|------|------|--------|
| all_tiers_exhausted | 9 | glm5_2_nv(6) + dsv4p_nv(3) | 部分可修 — key 冷却不足 |
| zombie_empty_completion | 8 | glm5_2_nv | NVCF func-level, 不可修 |
| NVStream_IncompleteRead | 1 | glm5_2_nv | 罕见 |

## Per-key 分析 (6h, glm5_2_nv)
| Key | 请求 | OK | 失败 | avg_ms | p50_ms | p95_ms |
|-----|------|----|------|--------|--------|--------|
| K0 | 2 | 2 | 0 | 56025 | 56025 | 99701 |
| **K1** | **5** | **2** | **3** | **47880** | **12864** | **139735** |
| K2 | 5 | 3 | 2 | 23232 | 14424 | 52042 |
| K3 | 4 | 2 | 2 | 8401 | 6412 | 14093 |
| K4 | 5 | 3 | 2 | 35217 | 13293 | 99883 |

## Tier Attempts (6h)
- K1: 5 pexec_timeout (avg 31.9s) vs 4 success — 55% timeout rate
- K2: 2 pexec_timeout, 2 SSLEOF, 5 success
- K3: 2 pexec_timeout, 1 SSLEOF, 4 success
- K4: 1 pexec_timeout, 1 SSLEOF, 5 success
- K0: 2 pexec_timeout, 2 SSLEOF, 2 success

## 变更
- **KEY_COOLDOWN_S: 71→73 (+2s)**
- 轮换模式: R2101(TIER+2)→R2102(KEY+2)→R2103(TIER+2)→R2104(KEY+2) — 交替推进
- KEY+TIER=73+66=139 < 153 BUDGET (14s margin)
- K1 5 timeout / 55% fail rate 是 ATE 主因 — 多 2s recovery 减少 zombie→ATE 级联
- 8 zombie 全为 NVCF func-level empty200 (不可本地修复)
- 单参数; 铁律: 只改 HM1 不改 HM2

## 验证
- docker compose up -d nv_gw 重启成功
- env 确认: KEY_COOLDOWN_S=73
- health check: 200 OK

## ⏳ 轮到HM1优化HM2