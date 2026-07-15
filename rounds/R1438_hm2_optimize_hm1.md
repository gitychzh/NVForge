# HM2 Optimize HM1 — Round R1438

> **铁律**: 只改HM1不改HM2 | 改前必有数据 | 改后必有验证

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` — 误触发 (double-dispatch)
- 最新 commit `b663f3b` = R1437 (HM2→HM1 NOP), author = opc2_uname
- HM1 本地 git 未提交新内容
- 脚本正确检测到自提交并标记 "不触发"，但 cron 仍被派遣
- 这是 R1133 链的第 592 次 consecutive false-trigger dispatch

## 2. 改前数据

### 容器状态
- `nv_gw`: Up 13 minutes (healthy), 重启于 `2026-07-15T07:49:04Z` (R1436 deploy)
- `ms_gw`: 正常运行
- `logs_db`: 正常运行

### Compose MD5
```
e49a30d407b9ca888f81e8af8ee5c1d1  /opt/cc-infra/docker-compose.yml
```
(R1436 compose: NVU_MS_GW_FALLBACK_TIMEOUT 195→210)

### 容器环境 (关键参数)
| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 205 | R1436: 124→205 |
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 210 | R1436: 195→210 |
| NVU_TIER_BUDGET_DSV4P_NV | 124 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |

### 6h 请求总览 (02:00-08:00 UTC)
```
total: 58 | ok: 38 | err: 20 | SR: 65.5%
```
⚠️ 6h 窗口绝大部分为 R1435 配置时代 (BUDGET=124, FALLBACK_TIMEOUT=195) 的 pre-restart 数据。容器重启于 07:49 UTC。

### 按模型
| 模型 | 请求 | OK | 失败 | SR | 平均延迟 |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 42 | 32 | 10 | 76.2% | 11,776ms |
| dsv4p_nv | 16 | 6 | 10 | 37.5% | 43,613ms |

### 错误类型
| 错误类型 | 数量 | 平均延迟 |
|----------|------|---------|
| zombie_empty_completion | 16 | 11,049ms |
| all_tiers_exhausted | 4 | 116,556ms |

### Zombie 详情
| 模型 | 数量 | 平均输入字符 | 平均延迟 |
|------|------|-------------|---------|
| dsv4p_nv (pexec) | 6 | 210,222 | 17,574ms |
| glm5_2_nv (integrate) | 10 | 210,747 | 7,134ms |

NVCF content-filter 导致的 zombie empty completion — 输入 ~210K chars，输出 2-12 chars。非 config-fixable。

### ATE 详情
| 模型 | 数量 | tiers_tried | 平均延迟 | fallback_occurred |
|------|------|------------|---------|-------------------|
| dsv4p_nv | 4 | 1 | 116,556ms | f (全部) |

4 个 ATE 全部为 pre-restart (R1435 配置，BUDGET=124 时代)。NVU_TIER_BUDGET_DSV4P_NV=124, 延迟 ~124s 精确触及 budget cap。tiers_tried_count=1 说明 ms_gw fallback 未触发 (budget 耗尽)。

### Tier Attempts
```
0 rows (no key cycling)
```

### ms_gw 信号
```
total: 26 | ok: 26 | SR: 100%
```
ms_gw 完全健康，无 BrokenPipeError，无超时。

### 6h 小时 SR
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|-----|
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |
| 06:00 | 5 | 3 | 2 | 60.0% |
| 07:00 | 5 | 1 | 4 | 20.0% |

07:00 小时的 4 个失败全部为 dsv4p_nv ATE (pre-restart)。容器于 07:49 重启，08:00+ 小时数据极少。

### nv_gw 日志 (post-restart, tail 30)
```
[NV-PROXY] 启动于 0.0.0.0:40006 (passthrough)
[16:03:20] glm5_2_nv integrate k1 → SUCCESS (~4s)
[16:03:27] glm5_2_nv integrate k2 → SUCCESS (~6s)
[16:03:35] glm5_2_nv zombie empty completion (input=213K, content=12 chars) → 快速 abort
```
Post-restart 流量正常，glm5_2_nv integrate 成功，zombie 检测正常。

### ms_gw 日志
```
MS-OK-STREAM: glm5_2_ms (ZHIPUAI/glM-5.2) ~4s, 20KB
MS-OK-STREAM: dsv4p_ms (deepseek-ai/DEEPSEEK-V4-PRO) ~2s, 22-23KB
全部 stream 正常完成，无 BrokenPipeError
```

## 3. 分析

### 状态判定
- **容器重启**: 07:49 UTC (R1436 deploy)，已运行 13 分钟
- **6h 数据污染**: 02:00-07:49 UTC 为 pre-restart (R1435 配置)，post-restart 数据极少
- **4 dsv4p_nv ATE**: 全部 pre-restart，R1435 配置时代 (BUDGET=124, NVU_TIER_BUDGET_DSV4P_NV=124)
- **预算数学**: BUDGET=205, NVU_TIER_BUDGET_DSV4P_NV=124 → ms_gw fallback budget = 205-124 = 81s。NVU_MS_GW_FALLBACK_TIMEOUT=210 >> 81s。ms_gw fallback 有 81s 窗口
- **R1436 效果**: 未知 — 需要更多 post-restart 流量才能评估
- **16 zombie**: NVCF content-filter，非 config-fixable
- **0 tier_attempts**: 无 key cycling
- **ms_gw**: 26/26 100% SR，完全健康
- **所有参数**: floor/optimal，无优化空间

### 决策: NOP
- 这是第 592 次 consecutive false-trigger dispatch
- 4 个 ATE 全部 pre-restart，R1436 配置尚未积累足够数据
- 16 zombie 为 NVCF content-filter，非 config-fixable
- 所有参数已 floor/optimal
- 等待 R1436 配置 (BUDGET=205, FALLBACK_TIMEOUT=210) 积累数据后再评估

## 4. 结论

**NOP** — 零参数变更，零 compose 变更，零容器重启。铁律: 只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
