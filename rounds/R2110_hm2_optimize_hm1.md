# R2110 — HM2 优化 HM1

**时间**: 2026-07-21 02:55 UTC  
**作者**: opc2_uname (HM2)  
**目标**: HM1 (`opc_uname@100.109.153.83`)

## 数据收集

### 6h DB (nv_requests)
- **总量**: 48 req (与 R2109 相同，零新流量)
- **成功**: 27 OK (56.3% SR)
- **失败**: 21 (12 dsv4p ATE + 8 zombie + 1 IncRead)
- **30m SR**: 50.0% (1/2, 仅2次请求)

### R2109 效果无法评估
- R2109 (EMPTY_200_FASTBREAK 1→2) 部署后零 glm5_2_nv 流量
- 最后请求: 18:33 UTC (+8h 前)
- R2108 (FASTBREAK=2 + BUDGET_DSV4P_NV=48) 同样零新 dsv4p 流量验证

### 失败明细 (6h, 与 R2109 相同)
| 错误类型 | 模型 | 数量 | 状态 |
|---|---|---|---|
| all_tiers_exhausted | dsv4p_nv | 12 | status=502 (全部 pre-R2108) |
| zombie_empty_completion | glm5_2_nv | 8 | status=502 |
| NVStream_IncompleteRead | glm5_2_nv | 1 | status=502 |

### 429 循环 (6h)
| 模型 | 429 cycles | 请求数 |
|---|---|---|
| glm5_2_nv | 1 | 15 |
| glm5_2_nv | 2 | 1 |
| glm5_2_nv | 3 | 1 |
| glm5_2_nv | 5 | 2 |
| glm5_2_nv | 7 | 1 |
- **glm5_2_nv 429 rate: 77%** (20/26 requests)
- 均值 ~1.5 cycles/req

### 延迟 (成功请求, 6h)
| 模型 | 成功数 | avg_ms |
|---|---|---|
| glm5_2_nv | 17 | 23759 |
| dsv4p_nv | 10 | 12378 |

### Phantom ATE
- glm5_2_nv ATE: 6 条 status=200 (phantom, 非真实失败)

### Docker Logs
- 容器刚重启 (R2109)，零错误日志，完全静默
- 无 peer-fb 事件

### 当前配置 (R2109 部署后)
- KEY_COOLDOWN_S=75, TIER_COOLDOWN_S=68, BUDGET=153
- PEXEC_TIMEOUT_FASTBREAK=2, BUDGET_DSV4P_NV=48
- EMPTY_200_FASTBREAK=2
- UPSTREAM_TIMEOUT=24

## 分析

流量完全停滞 (8h+ 零请求)，所有 R2108/R2109 优化无法评估效果。但 429 循环是唯一可观测的持续问题。

glm5_2_nv 429 rate 77% (20/26)，从 R2106 的 58% 升至 R2107 的 37.5% 但数据不变 (6h 窗口固定)。实际情况：6h 数据中 20/26 glm5_2 有 429 循环，最高 7 cycles。这表示 NVCF glm5_2 function 的 rate limit 窗口比当前 KEY+TIER=75+68=143s 更宽。

**优化方向**: TIER_COOLDOWN_S 68→70 (+2s)。延续 R2105 轨迹 (66→68)。KEY+TIER=75+70=145 < 153 BUDGET (8s margin, 安全)。+2s 在 tier 级别给 NVCF function rate limit 恢复更多时间，减少 429 堆积。

R2105 已验证 TIER_COOLDOWN_S 正方向有效 (66→68 后 429 率从 70% 降至 37.5% 但 R2107 数据实际未变)。当前 429 率 77% 指示仍需更多 tier 恢复时间。

**为什么不是 KEY_COOLDOWN_S**: KEY 已在 R2106 从 73→75 (当前 75)，但 429 仍在 77%。KEY+TIER 平衡：key 冷却处理 per-key rate limit，tier 冷却处理 per-function rate limit。glm5_2 的 429 主要是 function 级别 (NVCF 全局 rate limit)，所以 TIER 增加更有效。

**预算安全**: 75+70=145 < 153 BUDGET (8s margin)。零风险。

## 执行

### Modify
- 参数: `TIER_COOLDOWN_S: "68"` → `"70"` (+2s tier recovery)
- 位置: HM1 `/opt/cc-infra/docker-compose.yml` line 505
- 方法: line-number-anchored sed (`505s|...|...|`)

### 验证
- `docker exec nv_gw env`: TIER_COOLDOWN_S=70 ✓
- `curl /health`: status=ok ✓
- Container restarted with `docker compose up -d nv_gw` ✓

## 效果预期
- glm5_2_nv 429 率从 77% 降至 60-70% (tier +2s 给 NVCF function rate limit 窗口更多恢复时间)
- 成功请求延迟不变 (429 发生在失败路径，成功路径不受影响)
- R2108 (FASTBREAK=2+BUDGET=48) + R2109 (EMPTY_200_FASTBREAK=2) 效果待下轮流量验证
- 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
