# R2109 — HM2 优化 HM1

**时间**: 2026-07-21 02:35 UTC  
**作者**: opc2_uname (HM2)  
**目标**: HM1 (`opc_uname@100.109.153.83`)

## 数据收集

### 6h DB (nv_requests)
- **总量**: 48 req
- **成功**: 27 OK (56.3% SR)
- **失败**: 21 (12 dsv4p ATE + 8 zombie + 1 IncRead)
- **30m SR**: 50.0% (1/2, 仅2次请求 post-restart)

### R2108 效果无法评估
- R2108 部署于 18:23 UTC，但所有12条 dsv4p ATE 发生在部署**之前** (14:39–18:09)
- Post-restart: 仅 2 条请求 (glm5_2_nv: 1OK + 1zombie)，**零 dsv4p_nv 流量**
- R2108的 FASTBREAK=2 + BUDGET=48 对 dsv4p ATE 效果待下轮验证

### 失败明细 (6h)
| 错误类型 | 模型 | 数量 | 状态 |
|---|---|---|---|
| all_tiers_exhausted | dsv4p_nv | 12 | status=502 (全部 pre-R2108) |
| zombie_empty_completion | glm5_2_nv | 8 | status=502 |
| NVStream_IncompleteRead | glm5_2_nv | 1 | status=502 |

### Phantom ATE
- glm5_2_nv ATE: 6 条 status=200 (phantom, 非真实失败)

### 延迟 (成功请求, 6h)
| 模型 | 成功数 | avg_ms |
|---|---|---|
| glm5_2_nv | 17 | 23759 |
| dsv4p_nv | 10 | 12378 |

### glm5_2_nv 问题
- **Zombie 率 42%** (9/21, 含 8 zombie + 1 IncompleteRead)
- 429 率: 75% (12/16 in 4h, mostly 1 cycle)
- EMPTY_200_FASTBREAK=1: 首个 empty200 key 直接放弃整 tier

### dsv4p_nv
- 12 ATEs 全部 tiers_tried_count=1, pattern: >=1 key timeout (~20s)
- Baby dsv4p 429: 0% (0/19 in 4h) — R2106 KEY_COOLDOWN 73→75 成功清零
- Tier attempts 表: 0 行 for dsv4p_nv — timeout 未记入 tier_attempts

### Peer-FB 健康
- 6h fallback_occurred=false: 48/48 → peer-fb 完全未触发
- docker logs: 容器刚重启（R2108），无 peer-fb 事件

### 当前配置 (R2108 部署后)
- PEXEC_TIMEOUT_FASTBREAK=2, BUDGET_DSV4P_NV=48
- KEY_COOLDOWN_S=75, TIER_COOLDOWN_S=68 → KEY+TIER=143, BUDGET=153, margin=10s
- EMPTY_200_FASTBREAK=1 ← **本轮改此参数**

## 分析

R2108 的 FASTBREAK=2 + BUDGET=48 无法在本轮评估（部署后零 dsv4p 流量）。R2109 聚焦 glm5_2_nv zombie 问题。

glm5_2_nv zombie 率 42% (9/21/6h)，全部为 NVCF function-level empty200。当前 EMPTY_200_FASTBREAK=1 设于 R1694 (38req/27OK/11zombie) 背景: "All 5 keys return empty200"。但实际 scenario 可能变化 — NVCF key behavior 非恒定。

**优化方向**: EMPTY_200_FASTBREAK 1→2，允许第二个 key 尝试。如果首个 key 返回 empty200 but 第二个 key 正常工作（NVCF 关键不均匀），每次 zombie 路径多花费 ~7s (one additional short zombie) 可拯救 10-20s ms_gw fallback。

R1031 历史先例: FASTBREAK 1→2 在 6h 数据中成功拯救 dsv4p ATE（key-specific 空200而非 function-level）。当前 glm5_2_nv: 8/21=38% zombie-502 + 6 phantom=14/21=67% 涉及 empty200。如果其中 30% 是 key-specific（而非 function-level），EMPTY_200_FASTBREAK=2 rescue 可使 zombie 率下降 ~10%。

预算安全: 2×~7s zombie = 14s << 22s GLM5_2_NV budget。零风险。

## 执行

### Modify
- 参数: `NVU_EMPTY_200_FASTBREAK: "1"` → `"2"` (+1 key attempt on empty200)
- 位置: HM1 `/opt/cc-infra/docker-compose.yml` line 630
- 方法: sed inline edit

### 验证
- `docker exec nv_gw env`: NVU_EMPTY_200_FASTBREAK=2 ✓
- `curl /health`: status=200 ✓
- Container restarted with `docker compose up -d nv_gw` ✓

## 效果预期
- glm5_2_nv zombie-502 率从 38%可能降至 25-30% (若 1/3 zombies 是 key-specific空200)
- 对 function-level zombie 无影响 (both keys same) ，但无坏影响
- Budget: 2×7s=14s < 22s GLM5_2_NV budget → 安全
- R2108 FASTBREAK=2+BUDGET=48 效果待下轮 dsv4p 流量验证
- 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
