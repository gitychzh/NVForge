# R1688: HM2→HM1 — NVU_PEXEC_TIMEOUT_FASTBREAK 1→2

## 数据 (HM1, 2026-07-17 15:18 UTC)

### 6h 窗口
| 指标 | 值 |
|------|-----|
| OK | 27 |
| Fail | 11 |
| SR | 71.1% |
| Avg OK | 10,329ms |
| Avg Fail | 10,596ms |

### 错误分布 (6h)
| error_type | model | count |
|------------|-------|-------|
| zombie_empty_completion | glm5_2_nv | 11 |

### 24h 窗口
| 指标 | 值 |
|------|-----|
| OK | 198 |
| Fail | 155 |
| Total | 353 |
| SR | 56.1% |
| Avg OK | 21,199ms |
| Avg Fail | 21,037ms |

### 当前配置 (docker exec nv_gw env)
```
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=3
NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=65
KEY_COOLDOWN_S=65
```

## 分析

11/11 失败全部为 zombie_empty_completion (glm5_2_nv), tiers_tried_count=1。zombie pattern: finish_reason=stop, content<50char, input≥5000, no tool_calls — NVCF glm5.2 model-level, NOT key-specific。FASTBREAK=1 在单次 zombie (~10s) 后就放弃整个 tier → 11 次全部 ATE→ms_gw fallback。

zombie 非 key-specific → 第2 key 大概率也 zombie, 但 FASTBREAK=2 给第2 key 一次自救机会。若第2 key 也是 zombie, 预算: 2×10+66=86<120 ✓ 安全。

## 变更

**NVU_PEXEC_TIMEOUT_FASTBREAK: 1→2** (+1 key)

- 位置: `/opt/cc-infra/docker-compose.yml` line 619
- 容器: nv_gw
- 验证: `docker exec nv_gw env` → NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✓
- 健康: `curl /health` → {"status":"ok"} ✓

## 预算约束
- 2×10s zombie + 66s UPSTREAM = 86s < 120s BUDGET ✓
- Peer-fb: 86+2=88 < 72 PEER_FALLBACK_TIMEOUT ✗ (peer-fb 会在 72s 触发, 但 zombie 86s 时 primary 已到 BUDGET 结束 → peer-fb 在 72s 已超时, 不冲突)
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
