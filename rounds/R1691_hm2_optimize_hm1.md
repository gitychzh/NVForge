# R1691: HM2→HM1 — NVU_SSLEOF_RETRY_DELAY_S 0.5→1.0 (+0.5s)

## 数据收集 (HM1, 2026-07-17 16:15 UTC)

### 6h 请求统计
| 指标 | 值 |
|---|---|
| 总请求 | 38 (glm5_2_nv only) |
| OK | 27 (71.1% SR) |
| Fail | 11 (zombie_empty_completion) |
| ATE | 0 |
| Fallback | 0 |
| Peer-FB | 0 |
| SSLEOF (tier) | 1 (nv_tier_attempts) |

### OK 延迟
| p50 | p95 | max | avg |
|---|---|---|---|
| 7758ms | 25736ms | 32092ms | 11288ms |

### Zombie 详情
所有 11 个 zombie 都来自 glm5_2_nv, tiers_tried=1, key_cycle_429s=1, input 61K-67K tokens, duration 4.5s-36.4s.
R1690 将 FASTBREAK 从 2→3 已部署, 容器刚重启, 无 post-deploy 数据.

### HM1 当前配置
- NVU_PEXEC_TIMEOUT_FASTBREAK=3 (R1690)
- NVU_EMPTY_200_FASTBREAK=3
- NVU_SSLEOF_RETRY_DELAY_S=0.5 (R1626)
- NVU_TIER_BUDGET_GLM5_2_NV=120
- TIER_COOLDOWN_S=65, KEY_COOLDOWN_S=65
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=195
- MIN_OUTBOUND_INTERVAL_S=0

### HM2 对比
- NVU_SSLEOF_RETRY_DELAY_S=1.0
- FASTBREAK=3, EMPTY_200_FASTBREAK=3
- TIER_COOLDOWN_S=25, KEY_COOLDOWN_S=25

## 分析

HM1 的 SSLEOF_RETRY_DELAY=0.5s (R1626 从 1.0→0.5). 6h 内仅 1 次 SSLEOF 错误 (glm5_2 pexec), 但 0.5s 可能不足以让 NVCF 连接充分重置. HM2 的 1.0s 已稳定运行多轮, 未引入问题. 对齐 HM2 值减少配置漂移, 提升 SSLEOF 重试可靠性.

## 优化

**NVU_SSLEOF_RETRY_DELAY_S: 0.5→1.0** (+0.5s)

- 对齐 HM2 的稳定值 1.0s
- 给 NVCF 连接重置更多时间
- 6h 仅 1 次 SSLEOF, 影响极小, 安全
- 单参数, 铁律: 只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep NVU_SSLEOF_RETRY_DELAY_S` → 1.0 ✓
- Compose 行号: 618
- Container 重启成功
- Health check: `{"status": "ok", "port": 40006}` ✓
## ⏳ 轮到HM1优化HM2
