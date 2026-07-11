# HM2 Optimize HM1 — Round R1169

## 1. 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（37th chain of R1133）
- HM1 本地 git log 停留在 R821（348 轮落后）

## 2. HM1 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up 9 hours (healthy), started 2026-07-10T19:03:27Z
- 无重启，compose md5: 7975939c245761e451a8813852dcb9bf (unchanged)

### DB 6h 统计
- 35req/13OK(37.1%)/22zombie
- 全部 glm5_2_nv integrate
- 22x zombie_empty_completion (3.5-12.6s, NVCF content-filter stop+12chars, 164K-169K input)
- 0 fallback (fallback_occurred=f for all 35)
- nv_tier_attempts: 3x 429_integrate_rate_limit (glm5_2_nv)
- dsv4p_nv: 0 traffic 6h
- ms_gw: 0 traffic 6h

### 小时分布
| Hour | Total | OK | Fail | SR% |
|------|-------|-----|------|-----|
| 22:00 | 5 | 1 | 4 | 20.0 |
| 23:00 | 9 | 4 | 5 | 44.4 |
| 00:00 | 7 | 1 | 6 | 14.3 |
| 01:00 | 4 | 2 | 2 | 50.0 |
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 4 | 2 | 2 | 50.0 |
| 04:00 | 2 | 1 | 1 | 50.0 |

### 日志确认
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — FALLBACK_GRAPH={} 正常状态
- NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK: gateway 检测 + error-chunk 正确
- 无 NV-TIER-FAIL, 无 NV-EMPTY-FASTBREAK, 无 NV-MS-FB
- 无 NVStream_TimeoutError (zombie detection 已替代旧 96s hang)

### 关键参数
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- 全部参数 floor/optimal

## 3. 诊断

zombie_empty_completion = code-level detection feature (R1107)，非 config-fixable。
NVCF content-filter 对大输入 (164K-169K chars) 返回 stop+12chars，gateway 正确检测并 abort (3.5-12.6s vs 旧 96s hang)。
所有参数已 floor/optimal，compose 48h+ 未变。

## 4. 决策

**NOP** — false trigger, 37th chain of R1133.
- 零参数变更，零 compose 变更，零容器重启
- zombie_empty_completion: code-level 特性，非 config-fixable
- 铁律: 只改HM1不改HM2

## 5. 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
