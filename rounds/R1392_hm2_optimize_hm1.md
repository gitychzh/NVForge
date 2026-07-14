# HM2 Optimize HM1 — Round R1392

## 触发分析
cron 脚本输出: "已处理过此commit(7648fdbfeed44241ad9f7fe07b13c87933618359), 等待新提交"
- 最新 commit = 7648fdb (R1391, author=opc2_uname)
- 脚本检测 HM1 已 pull 到 7648fdb，但 cron 仍被派遣
- 误触发 (double-dispatch, 551st chain of R1133)
- 零可修故障，所有参数 floor/optimal

## 数据收集 (改前必有数据)

### nv_gw 6h 总体
- 25req/16OK/9fail = 64.0% SR
- 7 zombie_empty_completion glm5_2_nv (NVCF content-filter, code-level, avg input 140K+ chars, avg dur 4.6s)
- 2 all_tiers_exhausted dsv4p_nv pexec (NVCF transient, self-recovered, avg dur 106s)
- 1 tier_attempt empty_200 dsv4p_nv
- 0 fallback_occurred

### 按上游路径
| Model | Total | OK | Fail | SR% | Avg Dur | Max Dur |
|---|---|---|---|---|---|---|
| glm5_2_nv | 14 | 7 | 7 | 50.0% | 5,808ms | 16,004ms |
| dsv4p_nv | 11 | 9 | 2 | 81.8% | 50,470ms | 106,059ms |

### glm5_2_nv 失败详情
- 7/7 zombie_empty_completion (NVCF content-filter)
- finish_reason=stop, content_chars=8-22 < 50, input_chars=90K-201K >= 5,000
- 代码级检测: NV-ZOMBIE-EMPTY passthrough → NV-ZOMBIE-ERROR-CHUNK → openclaw fallback
- 不可配置修复 — NVCF 端 content-filter 行为

### dsv4p_nv 失败详情
- 2 all_tiers_exhausted (NVCF transient, both self-recovered)
- 1 empty_200 k4 → cycle k3 empty_200 → cycle k4 empty_200 → ATE (106s, 5 keys exhausted)
- NV-TIER-FAIL: empty200=1, timeout=1, other=0
- NV-EMPTY-FASTBREAK 未触发 (EMPTY_200_FASTBREAK=2 但 R1039 代码 bug 不生效)
- NV-MS-FB 触发但 ms_gw relay TimeoutError 253s/254s (relay_started=True)

### ms_gw
- 3req/3OK = 100% SR (已从 R1390 退化恢复)

### 容器日志 (最近 100 行)
- NV-ZOMBIE-EMPTY pattern: 每 30min 批量触发 (glm5_2_nv, content_filter), 每次触发 openclaw fallback
- NV-EMPTY-200 cycle: dsv4p_nv k4→k3→k4 → ATE (106s)
- NV-MS-FB TimeoutError: 2× ms_gw relay 253s/254s 超时 (发生在 ATE 之后的 ms_gw fallback)
- NV-PEER-FB: 0 触发 (PEER_FB_SKIP_MODELS 为空, 但 dsv4p_nv ATE 未触发 peer-fb)
- 无 NV-GLOBAL-COOLDOWN / NV-EMPTY-FASTBREAK / NV-NONCYCLE 日志

### 环境变量
- 所有参数 floor/optimal，与 R1391 一致:
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1
  - NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
  - NVU_EMPTY_200_FASTBREAK=2 (R1031→R1039 bug: 不生效)
  - NVU_PEER_FB_SKIP_MODELS= (空)
  - NVU_PEER_FALLBACK_ENABLED=1
  - NVU_PEER_FALLBACK_TIMEOUT=66
  - NVU_MS_GW_FALLBACK_TIMEOUT=195
  - NVU_TIER_BUDGET_DSV4P_NV=106
  - NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_TIER_BUDGET_MINIMAX_M3_NV=100
  - TIER_COOLDOWN_S=15
  - KEY_COOLDOWN_S=25
  - UPSTREAM_TIMEOUT=66
  - TIER_TIMEOUT_BUDGET_S=205
  - NVU_SSLEOF_RETRY_DELAY_S=1.0
  - NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
  - NVU_STREAM_TOTAL_DEADLINE_S=42
  - NVU_FORCE_STREAM_UPGRADE=0
  - NV_INTEGRATE_THINKING_TIMEOUT_S=90
  - NV_INTEGRATE_KEY_COOLDOWN_S=0
  - FALLBACK_HEALTH_THRESHOLD=0.05
  - KEY_AUTHFAIL_COOLDOWN_S=60
  - MIN_OUTBOUND_INTERVAL_S=0
  - NVU_CONNECT_RESERVE_S=0
  - LOG_RETENTION_DAYS=7

### Compose md5
- f493494e2b41b17fbf5d9cff9093648e (不变)

## 决策: NOP (零可修故障)

### 故障分类
1. **zombie_empty_completion (7/9=77.8%)**: NVCF 端 content-filter，代码级检测+处理，不可配置
2. **all_tiers_exhausted (2/9=22.2%)**: NVCF 瞬态，自恢复，tier budget 已最优
3. **empty_200 (1 tier_attempt)**: EMPTY_200_FASTBREAK=2 不生效 (R1039 bug)，但不可配置修复

### 为什么不改
- 所有可调参数已 floor/optimal (已验证多轮)
- zombie 是 NVCF 端行为，代码级已有检测和 fallback 机制
- ATE 是 NVCF 瞬态，自恢复，tier budget 已正确设置
- EMPTY_200_FASTBREAK bug 是代码级 (R1039)，不能通过配置修复
- Compose md5 不变，不需要 docker-compose 重启

### 评判
- 更少报错: 7 zombie (NVCF 端，不可修) + 2 ATE (NVCF 瞬态) = 零可修故障
- 更快请求: 所有参数 floor/optimal
- 超低延迟: avg dur 5.8s (glm5_2_nv) / 50.5s (dsv4p_nv，含 ATE)
- 稳定优先: compose 不变，零重启风险

铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
