# R987: HM2→HM1 — NOP (false trigger, R982 settling, all params at floor/optimal)

## 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- R986 由 pre-run script 在 18:26 提交
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger)
- 锚定文件 `RN_hm2_optimize_hm1.md` 仍指向 R985 (stale), 已修复 → R987

## 数据收集 (HM1, 2026-07-09 18:35 UTC)

### 容器状态
- 容器: `nv_gw`, 运行时间: ~31min (重启于 10:06 UTC)
- 健康检查: `(healthy)`
- 日志: `(no fallback, 3model)` — FALLBACK_GRAPH={} 预期状态 (R832)
- 无 ERROR/WARN 行

### 四源漂移检测 (compose ↔ env): 全部一致 ✓
| 参数 | compose | env | 匹配 |
|------|---------|-----|------|
| UPSTREAM_TIMEOUT | 64 | 64 | ✓ |
| TIER_TIMEOUT_BUDGET_S | 112 | 112 | ✓ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | 2 | ✓ |
| NVU_EMPTY_200_FASTBREAK | 3 | 3 | ✓ |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | ✓ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 64 | ✓ |
| NVU_FORCE_STREAM_UPGRADE | 0 | 0 | ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✓ |
| KEY_COOLDOWN_S | 25 | 25 | ✓ |
| TIER_COOLDOWN_S | 25 | 25 | ✓ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | ✓ |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | glm5_2_nv,dsv4p_nv | ✓ |
| NVU_TIER_BUDGET_GLM5_2_NV | 64 | 64 | ✓ |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 60 | ✓ |

### 6h 聚合 (DB)
| 指标 | 值 |
|------|-----|
| 总请求 | 54 |
| 成功 | 47 (87.0%) |
| 失败 | 7 (13.0%) |
| 平均延迟 | 47,798ms |
| 平均 TTFB | 37,893ms |

### 按模型分布
| 模型 | 请求 | 成功 | SR% | 平均延迟 |
|------|------|------|-----|---------|
| glm5_2_nv | 49 | 42 | 85.7% | 50,496ms |
| dsv4p_nv | 5 | 5 | **100%** | 21,356ms |

### 按重启前后分段
| 窗口 | 请求 | 成功 | ATE | SR% |
|------|------|------|-----|-----|
| pre-restart | 39 | 32 | 7 | 82.1% |
| **post-restart** | **15** | **15** | **0** | **100%** |

### ATE 分析
- `tiers_tried_count=1`: 5 条 (avg 56,841ms) — 全部 pre-restart
- `tiers_tried_count=2`: 2 条 (avg 174,417ms) — 全部 pre-restart
- **Post-restart (10:06 UTC+): 0 ATE**
- 所有 7 ATE 均为 `all_tiers_exhausted` — NVCF 上游问题, 非 config 可修

### NVCFPexecTimeout (nv_tier_attempts, 仅 glm5_2_nv)
- 16 次 timeout, avg 58,190ms, **max 62,606ms**
- 均匀分布: uniform across keys → function-level
- 其他: 504_nv_gateway_timeout(3), empty_200(2)

### Fallback 统计
- 无 fallback: 28 条, avg 15,824ms
- 有 fallback: 19 条, avg 79,211ms, **100% SR**

### ms_gw 健康
- 正常: 日志无异常

## 优化决策: NOP

### 拒绝所有候选参数

| 参数 | 当前值 | 拒绝理由 |
|------|--------|---------|
| UPSTREAM_TIMEOUT | 64 | NVCFPexecTimeout max=62,606ms << 64, 非绑定 (1.4s buffer)。R969 增加后稳定。保持 64 |
| TIER_TIMEOUT_BUDGET_S | 112 | 安全余量充足 (112 >> 64)。无 ATE 误杀。保持 112 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | 美国 mihomo 代理, 换 key=换 IP 有价值 (R832c)。保持 2 |
| NVU_TIER_BUDGET_GLM5_2_NV | 64 | 对齐 UPSTREAM=64, 单 key 完整路径。保持 64 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | R982 刚部署, 已验证有效。保持 0.05 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 对齐 UPSTREAM=64。保持 64 |
| NVU_EMPTY_200_FASTBREAK | 3 | 历史最优。保持 3 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 已 floor。保持 0 |
| NVU_CONNECT_RESERVE_S | 0 | 已 floor。保持 0 |

### 核心结论
- **Post-restart 100% SR (15/15), 0 ATE, 0 errors** — 系统健康
- 所有 7 ATE 为 pre-restart 窗口 (R982 重启前)
- 所有参数已在 floor/optimal 状态
- 容器与 compose 配置完全一致 (0 drift)
- **零参数变更, 待系统继续稳定运行**

## 铁律遵守
- ✅ 改前必有数据: 完整 DB + logs + env + 四源漂移检测
- ✅ 聚焦 nv_gw: 仅分析 40006 链路
- ✅ 所有修改写入仓库: 本 NOP 记录写入轮次文件
- ✅ 铁律: 只改 HM1 不改 HM2 (本轮 zero-change)
- ✅ 评判: 更少报错更快请求超低延迟稳定优先

## ⏳ 轮到 HM1 优化 HM2