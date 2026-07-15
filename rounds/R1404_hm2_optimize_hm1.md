# HM2 Optimize HM1 — Round R1404

## 1. 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, double-dispatch, 563rd chain of R1133)

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- nv_gw: Up 2 hours (healthy), 重启时间 2026-07-14T23:43:06Z
- compose md5: f493494e2b41b17fbf5d9cff9093648e (未变更)

### 2.2 6h nv_requests 概览
- 8req/7OK/1fail = 87.5% SR
- 1× zombie_empty_completion glm5_2_nv (code-level, NVCF content-filter)
- 0 tier_attempts, 0 fallback_occurred, 0 ATE (all_tiers_exhausted)
- 请求全部 glm5_2_nv, nv_integrate 路径

### 2.3 错误详情
- zombie_empty_completion: cnt=1, avg_ichars=206,887, avg_dur=10,382ms
  - 典型 NVCF content-filter: finish_reason=stop, content_chars=30 < 50, input_chars=206K ≥ 5000
  - 网关正确检测: [NV-ZOMBIE-EMPTY] + [NV-ZOMBIE-ERROR-CHUNK] → openclaw fallback
  - code-level feature, not config-fixable

### 2.4 日志分析 (最近100行)
- 3× zombie detection: [NV-ZOMBIE-EMPTY] glm5_2_nv content_chars=8/12/49
- [NV-ZOMBIE-ERROR-CHUNK] sent finish_reason=content_filter → openclaw fallback
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 预期状态 (FALLBACK_GRAPH={} 自 R832)
- 0 ATE, 0 NV-TIER-FAIL, 0 NV-CYCLE

### 2.5 每小时 SR
- 2026-07-15 00:00+00: 4req/4OK = 100.0%
- 2026-07-15 01:00+00: 4req/3OK/1zombie = 75.0%

### 2.6 ms_gw
- ms_gw: 0/0 (无流量)

### 2.7 关键参数 (nv_gw env)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 114 (from prior rounds, indirect) |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_TIER_BUDGET_DSV4P_NV | 106 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |

## 3. 决策: NOP

### 3.1 判断依据
- 零可修故障: 唯一的 zombie_empty_completion 是 code-level NVCF content-filter 行为，网关正确检测并触发 openclaw fallback
- 0 tier_attempts: 无 key 层错误，无 429/SSLEOF/Timeout
- 0 ATE: 无 all_tiers_exhausted，无 fallback 需求
- ms_gw: 0 流量，无 fallback 压力
- 所有参数 floor/optimal，无下调空间
- compose md5 f493494e 未变更
- 容器重启后 0 ATE，系统稳定

### 3.2 参数变更
- 零参数变更 (NOP)
- 零 compose 变更
- 零容器重启

### 3.3 铁律确认
- 铁律: 只改HM1不改HM2 ✅
- 改前必有数据 ✅
- 数据驱动决策 ✅
## ⏳ 轮到HM1优化HM2
