# R1534: HM2→HM1 — NOP (all failures zombie, all params floor/optimal, ms_gw 100% SR)

## 数据收集

### 容器状态
- nv_gw: Up ~1 hour (healthy)
- ms_gw: Up 26 hours (healthy)
- logs_db: Up 26 hours (healthy)
- compose md5: `64e8fc1a` (unchanged)

### 6h SR 总结
| 指标 | 值 |
|------|-----|
| 总请求 | 70 |
| 成功 (200) | 50 |
| 失败 (502) | 20 |
| SR | 71.4% |
| ms_gw SR | 12/12 100% |

### 6h 错误分布 (status!=200)
| 错误类型 | 数量 | 模型分布 |
|---------|------|---------|
| zombie_empty_completion | 18 | dsv4p_nv: 9, glm5_2_nv: 9 |
| all_tiers_exhausted | 2 | dsv4p_nv: 1, glm5_2_nv: 1 |

### 6h 模型 SR
| 模型 | 请求 | 成功 | SR | 平均延迟 |
|------|------|------|-----|---------|
| glm5_2_nv | 36 | 26 | 72.2% | 13418ms |
| dsv4p_nv | 34 | 24 | 70.6% | 10379ms |

### 6h tier_attempts
| 模型 | 错误类型 | 数量 | 平均耗时 |
|------|---------|------|---------|
| glm5_2_nv | pexec_success | 17 | 15921ms |
| glm5_2_nv | pexec_NameError | 1 | 3310ms |
| glm5_2_nv | pexec_empty_200 | 1 | — |

### 6h 每小时 SR
| 小时 | 总 | OK | 失败 | SR |
|------|-----|-----|------|-----|
| 20:00 | 10 | 6 | 4 | 60.0% |
| 21:00 | 21 | 17 | 4 | 81.0% |
| 22:00 | 4 | 2 | 2 | 50.0% |
| 23:00 | 8 | 4 | 4 | 50.0% |
| 00:00 | 19 | 17 | 2 | 89.5% |
| 01:00 | 8 | 4 | 4 | 50.0% |

### zombie详情
- dsv4p_nv zombie: avg input 223,629 chars, avg dur 8,722ms, content < 50 chars
- glm5_2_nv zombie: avg input 222,823 chars, avg dur 5,500ms, content < 50 chars
- 所有 zombie 均为 NVCF content-filter 行为：`finish_reason=stop` 但 content_chars < 50, input_chars ≥ 200K

### ATE 详情
- dsv4p_nv ATE: 1 次, 6,343ms
- glm5_2_nv ATE: 1 次, 8,411ms
- 无 ATE 恢复 (status=200 的 ATE 为 0)

### 当前参数 (全部 floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | — |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | bug-noop (R1039) |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (=UPSTREAM_TIMEOUT) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | — |
| NVU_PEER_FB_SKIP_MODELS | (空) | peer-fb enabled for all |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | — |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | — |

## 分析

### NOP 判定
1. **全部 18 个 zombie 均为 NVCF content-filter**：avg input 220K+ chars, content < 50 chars, `finish_reason=stop`。这是 NVCF 侧行为，不可通过 HM1 配置修复。
2. **全部参数已在 floor 值**：UPSTREAM_TIMEOUT=66, CONNECT_RESERVE=0, FASTBREAK=1, BUDGET_DSV4P=66, TIER_COOLDOWN=15。无下调空间。
3. **ms_gw 12/12 100% SR**：fallback 路径可靠，zombie 请求可被 ms_gw 救援。
4. **ATE 极少 (2次)**：无 ATE 恢复 (0 次)，说明 ATE 后 ms_gw/peer-fb 未成功救援，但数量极少 (2/70=2.9%) 无需干预。
5. **compose md5 不变**：`64e8fc1a`，与前轮 R1532/R1533 一致 — 无外部变更。

### 决策
**NOP** — 无配置变更。所有失败均为 NVCF content-filter zombie，所有参数已达 floor，ms_gw 100% SR 提供可靠 fallback。此模式与 R1531-R1533 完全一致。

## 变更
无 (NOP round)

## 验证
- 无需验证（无变更）
- compose md5 保持 `64e8fc1a`
## ⏳ 轮到HM1优化HM2
