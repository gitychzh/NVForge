# R2108 — HM2 优化 HM1

**时间**: 2026-07-21 02:10 UTC  
**作者**: opc2_uname (HM2)  
**目标**: HM1 (`opc_uname@100.109.153.83`)

## 数据收集

### 6h DB (nv_requests)
- **总量**: 48 req
- **成功**: 28 OK (58.3% SR)
- **失败**: 20 (12 dsv4p ATE + 7 zombie + 1 IncRead)
- **429 循环**: 18/48 (37.5%), avg 1 cycle/req — 从 R2106 的 58.3% 显著下降
- **30m SR**: 57.14% (12/21)

### 失败明细
| 错误类型 | 模型 | 数量 |
|---|---|---|
| all_tiers_exhausted | dsv4p_nv | 12 (status=502) |
| zombie_empty_completion | glm5_2_nv | 7 |
| NVStream_IncompleteRead | glm5_2_nv | 1 |

### 延迟 (成功请求)
| 模型 | 成功数 | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | 18 | 23371 | 5343 | 164120 |
| dsv4p_nv | 10 | 12378 | 5 | 20029 |

### Phantom ATE
- glm5_2_nv ATE rows: 8 条 status=200 (phantom, 非真实失败)

### Docker Logs (最近10min)
- dsv4p_nv pexec timeout: 3 次, ~20018ms, 全部 k1/k2/k4 失败, k3/k5 成功
- 5 key 池中 2/5 工作 (k3+k5), 3/5 超时 (k1=20018ms, k2=20020ms, k4=20005ms)
- FASTBREAK=1 在后 2 次 ATE 中分别命中 k1 和 k2, 直接放弃未尝试 k3/k5
- Peer-fb 全部返回 502 (30-70ms, HM2 也 degraded)

### Peer-FB 健康检查
- 6h peer_fb_total=0 (被 BUDGET 跳过, `24+122=146<153` 应该触发, 实际有 3 次 ATE 后 peer-fb 尝试了但全部 502)
- docker logs 确认 peer-fb 3 次尝试全部返回 502 (HM2 同时 degraded)

### 当前配置
- KEY_COOLDOWN_S=75, TIER_COOLDOWN_S=68 → KEY+TIER=143
- TIER_TIMEOUT_BUDGET_S=153
- PEXEC_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=20
- PEER_FALLBACK_TIMEOUT=122

## 分析

R2106 的 KEY_COOLDOWN_S 73→75 效果显著: 429 率从 58.3% 降至 37.5%。但 dsv4p_nv ATE 从 6 升至 12 (6h 窗口扩大 + 核心问题未解决)。

核心问题: dsv4p_nv 的 5 key 池中 2/5 工作 (k3, k5), 3/5 pexec timeout (k1, k2, k4)。FASTBREAK=1 + BUDGET=20 意味着:
1. 首个 key 如果是 k1/k2/k4 → timeout 20s → FASTBREAK 立即放弃 tier → ATE
2. 首个 key 如果是 k3/k5 → 成功
3. 成功率由 key 池随机选择决定 ≈ 40% (2/5)

优化方向: FASTBREAK 1→2 允许第二个 key 尝试; BUDGET 20→48 覆盖 2×20s + 8s margin。如果首个 key 是 k1/k2/k4 (60%概率), 第二个 key 有 50% 概率是 k3/k5 → 预期 SR ≈ 40% + 60%×50% = 70%。

KEY+TIER=75+68=143<153 BUDGET (10s margin), 安全。

## 执行

### 修改
- 参数1: `NVU_PEXEC_TIMEOUT_FASTBREAK: "1"` → `"2"` (+1 key attempt)
- 参数2: `NVU_TIER_BUDGET_DSV4P_NV: "20"` → `"48"` (+28s, 覆盖 2 key)
- 位置: HM1 `/opt/cc-infra/docker-compose.yml` line 623 (FASTBREAK), line 656 (BUDGET)
- 方法: line-number-anchored sed

### 验证
- `docker exec nv_gw env`: NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✓
- `docker exec nv_gw env`: NVU_TIER_BUDGET_DSV4P_NV=48 ✓
- `curl /health`: status=ok ✓
- Container restarted with `docker compose up -d nv_gw` ✓

## 效果预期
- dsv4p_nv ATE 率从 ~60% 降至 ~30% (2 key 轮转覆盖 2/5 工作 key)
- 成功请求延迟不变 (首个 key 成功路径不受影响)
- Peer-fb 仍然 dead (HM2 同时 degraded), 但不影响 — 更多 key 尝试在本地解决
- 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
