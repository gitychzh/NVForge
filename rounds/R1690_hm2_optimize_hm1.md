# R1690: HM2→HM1 — NVU_PEXEC_TIMEOUT_FASTBREAK 2→3 (+1 key)

## 数据收集 (HM1, 2026-07-17 15:45 UTC)

### 6h 请求统计
| 指标 | 值 |
|---|---|
| 总请求 | 38 (glm5_2_nv only) |
| OK | 27 (71.1% SR) |
| Fail | 11 (zombie_empty_completion) |
| ATE | 0 |
| Fallback | 0 |
| Peer-FB | 0 |
| SSLEOF | 1 (nv_tier_attempts) |
| Key-cycle 429s | 37×1, 1×2 |

### OK 延迟
| p50 | p95 | max | avg |
|---|---|---|---|
| 7758ms | 25736ms | 32092ms | 11086ms |

### Zombie 详情
所有 11 个 zombie 都来自 glm5_2_nv, tiers_tried=1, input 250K-274K 字符, duration 4.5s-36.4s.
尽管 FASTBREAK=2 (R1688), k1+k2 都尝试了 (日志确认), 但 NVCF 的 glm5.2 function 本身劣化导致两个 key 都返回空内容.

### HM1 当前配置
- NVU_PEXEC_TIMEOUT_FASTBREAK=2
- NVU_EMPTY_200_FASTBREAK=3
- NVU_TIER_BUDGET_GLM5_2_NV=120
- TIER_COOLDOWN_S=65, KEY_COOLDOWN_S=65
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=195
- NVU_SSLEOF_RETRY_DELAY_S=0.5
- cc4101: PRIMARY_HEADER_TIMEOUT=60, UPSTREAM_TIMEOUT=130

### HM2 对比
- NVU_PEXEC_TIMEOUT_FASTBREAK=3
- NVU_EMPTY_200_FASTBREAK=3
- TIER_COOLDOWN_S=25, KEY_COOLDOWN_S=25

## 分析

R1688 将 FASTBREAK 从 1→2 已验证 k1+k2 都尝试了, 但 zombie 仍然存在 (NVCF function 劣化). 
HM2 的 FASTBREAK=3 已稳定运行多轮, 未引入问题.
即使 NVCF function 劣化, 更多 key 尝试 = 更多机会命中可用实例.

## 优化

**NVU_PEXEC_TIMEOUT_FASTBREAK: 2→3** (+1 key)

- 预算: 3×10s + 66s = 96s << 120s (TIER_BUDGET_GLM5_2_NV) ✓
- 再给 1 个 key 机会, 3 key 尝试覆盖更多 NVCF 实例
- 与 HM2 对齐 (HM2 FASTBREAK=3 稳定)
- 单参数, 铁律: 只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep NVU_PEXEC_TIMEOUT_FASTBREAK` → 3 ✓
- Compose 行号: 619
- Container 重启成功
## ⏳ 轮到HM1优化HM2
