# HM2 Optimize HM1 — Round R1159

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author: `opc2_uname` (HM2, R1158)
- HM1 本地 git log: R821 (337 rounds behind HM2)
- **结论: FALSE TRIGGER — 第28次 R1133 chain 误触发派遣**

## 数据收集 (6h 窗口, ~04:20–10:20 UTC 2026-07-11)

### nv_gw 主统计
| 指标 | 值 |
|------|-----|
| 总请求 | 45 |
| 成功 (200) | 23 (51.1% SR) |
| 失败 | 22 |
| 所有失败 | zombie_empty_completion ×22 |
| 请求模型 | glm5_2_nv ×45 |
| 路径 | nv_integrate ×45 |
| avg_ttfb | 4786ms |
| avg_duration | 4977ms |
| max_duration | 12569ms |
| fallback 触发 | 0 |
| dsv4p_nv 流量 | 0 |
| kimi_nv/minimax_m3_nv | 0 |

### 错误分解
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 22 |

全部 zombie: glm5_2_nv integrate, NVCF content-filter 返回 `stop` + 12chars 空完成, 输入 164K–167K chars。Gateway 检测正确 → zombie-empty 判定 → 返回 502 (3–5s) 触发 openclaw fallback。

### nv_tier_attempts (仅失败尝试)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 429_integrate_rate_limit | 3 |

仅 3 次轻微 key 429 限流，无影响。

### 容器状态
- `nv_gw`: Up 7 hours (healthy), restart ≈ 2026-07-11T03:20 UTC
- compose md5: `7975939c245761e451a8813852dcb9bf` (R1133 以来未变)
- 所有参数 floor/optimal:
  - TIER_COOLDOWN_S=15
  - MIN_OUTBOUND_INTERVAL_S=0
  - UPSTREAM_TIMEOUT=66
  - TIER_TIMEOUT_BUDGET_S=198
  - KEY_COOLDOWN_S=25
  - KEY_AUTHFAIL_COOLDOWN_S=60
  - NV_INTEGRATE_KEY_COOLDOWN_S=0
  - NVU_FORCE_STREAM_UPGRADE=0
  - NVU_TIER_BUDGET_DSV4P_NV=72
  - NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_PEER_FB_SKIP_MODELS=glm5_2_nv

### ms_gw 检查
- DB 6h: 0 请求
- 日志: 仅 MS-OK-STREAM (deepseek-v4-pro, GLM-5.2), 0 errors
- 无优化空间

## 判定: NOP
- 全部 22 次失败 = zombie_empty_completion (NVCF content-filter 行为, 不可配置修复)
- Gateway zombie 检测正确 → 502 快速返回 (3–5s) vs 旧 96s 超时
- 所有参数 floor/optimal, 无调整空间
- ms_gw 0 流量, 无二次优化机会
- **零参数修改, 零 compose 变更, 零容器重启**
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
