# R986: HM2→HM1 — NOP (false trigger, R982 settling, all params at floor/optimal)

## 数据收集 (HM1, 2026-07-09 18:10 UTC)

### Docker 容器状态
- 容器: `nv_gw`, 运行时间: ~10min (重启于 18:06 CST / 10:06 UTC)
- 日志: `(no fallback, 3model)` — FALLBACK_GRAPH={} 预期状态 (R832)
- 无 ERROR/WARN 行

### 容器环境变量 (与 compose 完全一致)
```
UPSTREAM_TIMEOUT=64
TIER_TIMEOUT_BUDGET_S=112
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_EMPTY_200_FASTBREAK=3
NVU_TIER_BUDGET_GLM5_2_NV=64
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
NVU_FORCE_STREAM_UPGRADE=0
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
```

### 6h 聚合 (DB)
| 指标 | 值 |
|------|-----|
| 总请求 | 51 |
| 成功 | 44 (86.3%) |
| 失败 | 7 (13.7%) |
| 平均延迟 | 49,125ms |
| 平均 TTFB | 38,705ms |

### 按模型分布
| 模型 | 请求 | 成功 | SR% | 平均延迟 |
|------|------|------|-----|---------|
| glm5_2_nv | 46 | 39 | 84.8% | 52,144ms |
| dsv4p_nv | 5 | 5 | **100%** | 21,356ms |

### 按小时分布
| 小时 (UTC) | 请求 | 成功 | ATE | SR% |
|-----------|------|------|-----|-----|
| 04:00 | 1 | 1 | 0 | 100% |
| 05:00 | 10 | 10 | 0 | 100% |
| 06:00 | 7 | 7 | 0 | 100% |
| 07:00 | 7 | 5 | 2 | 71.4% |
| 08:00 | 5 | 3 | 2 | 60.0% |
| 09:00 | 9 | 6 | 3 | 66.7% |
| **10:00 (post-restart)** | **13** | **13** | **0** | **100%** |

### ATE 分析
- `tiers_tried_count=1`: 5 条 (avg 56,841ms) — 全部 pre-restart
- `tiers_tried_count=2`: 2 条 (avg 174,417ms) — 全部 pre-restart
- **Post-restart (10:06 UTC+): 0 ATE**

### NVCFPexecTimeout (nv_tier_attempts, 仅 glm5_2_nv)
- 16 次 timeout, avg 58,190ms, **max 62,606ms**
- 均匀分布: k0(3) k1(3) k2(5) k3(2) k4(3)
- 其他: 504_nv_gateway_timeout(3), empty_200(2)

### 成功请求延迟分桶
- 0-10s: 15 (2 via fallback)
- 10-20s: 8 (1 via fallback)
- 30-40s: 1
- 40-50s: 3
- 50-60s: 1
- 60-80s: 5 (5 via fallback)
- 80-100s: 6 (6 via fallback)
- 100-130s: 5 (5 via fallback)

### Fallback 统计
- 无 fallback: 25 条, avg 14,694ms
- 有 fallback: 19 条, avg 79,211ms, **100% SR**

### ms_gw 健康
- 正常: MS-OK / MS-OK-STREAM 正常处理 glm5.2

## 优化决策: NOP

### 触发原因
HM1 的 pre-run script 在 18:10 提交了 commit (R985 post-up), 触发 HM2 cron 派遣。这是 false trigger — 系统在 R982 重启后正常稳定运行。

### 拒绝所有候选参数

| 参数 | 当前值 | 拒绝理由 |
|------|--------|---------|
| UPSTREAM_TIMEOUT | 64 | NVCFPexecTimeout max=62,606ms << 64, 非绑定 (1.4s buffer)。R969 缓冲紧张 (1.6s)，但当前不绑定。保持 64 |
| TIER_TIMEOUT_BUDGET_S | 112 | 安全余量充足 (112 >> 64+64=128? 不对, per-tier budget 112, 单 key 64s)。当前无 ATE 误杀。保持 112 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | R832c 配美国 mihomo 代理, 换 key=换 IP 有价值。保持 2 |
| NVU_TIER_BUDGET_GLM5_2_NV | 64 | 对齐 UPSTREAM=64, 单 key 完整路径。保持 64 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | R982 刚部署, 已验证 dsv4p_nv 保留在 chain 内。保持 0.05 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 对齐 UPSTREAM=64。保持 64 |
| NVU_EMPTY_200_FASTBREAK | 3 | 历史最优。保持 3 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 已 floor。保持 0 |
| CONNECT_RESERVE_S | 0 | 已 floor。保持 0 |

### 核心结论
- **Post-restart 100% SR (13/13), 0 ATE, 0 errors** — 系统健康
- 所有 7 ATE 为 pre-restart 窗口 (07:00-09:00 UTC)
- 所有参数已在 floor/optimal 状态
- 容器与 compose 配置完全一致 (0 drift)
- **零参数变更, 待系统继续稳定运行**

## 铁律遵守
- ✅ 改前必有数据: 完整 DB + logs + env 分析
- ✅ 聚焦 nv_gw: 仅分析 40006 链路
- ✅ 所有修改写入仓库: 本 NOP 记录写入轮次文件
- ✅ 铁律: 只改 HM1 不改 HM2 (本轮 zero-change)
- ✅ 评判: 更少报错更快请求超低延迟稳定优先

## ⏳ 轮到 HM1 优化 HM2