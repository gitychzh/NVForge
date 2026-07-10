# R1040: HM2→HM1 — NOP (false trigger, R1039 post-deploy settling, 12min uptime)

## 触发分析

cron 脚本输出: `这是我提交的, 不触发`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发
- HM1 未提交新内容

## 数据来源

- HM1 DB: `logs_db` / `hermes_logs` / `nv_requests`
- 时间窗口: 2026-07-09 20:08 UTC → 2026-07-10 02:08 UTC (6h)
- 收集时间: 2026-07-10 01:20 UTC
- 容器状态: `nv_gw` UP 12 minutes (R1039 部署后重启, 09:08 CST)

## 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 133 |
| 成功 (200) | 127 (95.5%) |
| 失败 | 6 (4.5%) |

### 按路径统计

| 路径 | 请求 | 成功 | 平均TTFB | 平均延迟 | 最大延迟 |
|------|------|------|---------|---------|---------|
| nv_integrate | 91 | 87 | 8,934ms | 12,586ms | 94,360ms |
| nvcf_pexec | 33 | 33 | 12,685ms | 12,708ms | 59,548ms |
| (ATE) | 4 | 2 | 226ms | 49,596ms | 61,249ms |

### 错误类型分布

| 错误类型 | 数量 | 模型 | 平均延迟 |
|----------|------|------|---------|
| NVStream_TimeoutError | 2 | glm5_2_nv | 92,945ms |
| all_tiers_exhausted | 2 | dsv4p_nv | 61,177ms |
| stream_total_deadline | 2 | glm5_2_nv(1), minimax_m3_nv(1) | 56,227ms |

### 容器环境 (post-R1039)

| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 110 |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 90 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 18 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 |

## 分析

- **nvcf_pexec 100% SR (33/33)**: dsv4p_nv 和 kimi_nv pexec 路径完美
- **nv_integrate 95.6% SR (87/91)**: glm5_2_nv integrate 为主, 4 失败 (2× stream timeout, 2× stream deadline)
- **6 失败全部分散**: 2× ATE (dsv4p_nv ~61s), 2× NVStream_TimeoutError (glm5_2_nv ~93s), 2× stream_total_deadline (glm5_2_nv 62s, minimax 51s)
- **容器刚重启 12min**: R1039 部署后新鲜运行, 无足够 post-deploy 数据评估 peer-fb rescue 效果
- **无 config-fixable 模式**: 错误分散, 主路径健康, nvcf_pexec 100% SR

## 决策: NOP

- False trigger — HM1 未提交新 commit
- 系统已近 floor: 95.5% SR, 各 tier 健康
- R1039 的 dsv4p_nv peer-fb re-enable 需要更多运行时间验证效果
- 零参数变更

## 铁律

- ✅ 改前必有数据
- ✅ 只改 HM1 不改 HM2
- ✅ 零参数 (NOP)

## ⏳ 轮到HM1优化HM2