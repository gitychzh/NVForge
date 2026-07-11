# HM2 Optimize HM1 — Round R1189

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, R1188→R1189)
- R1189 为 R1133 僵尸链的第 57th NOP

## 2. HM1 连接状态

- SSH: ✅ 连通
- nv_gw: Up 13 hours (healthy), StartedAt: 2026-07-10T19:03:27Z
- ms_gw: Up 36 hours (healthy)
- logs_db: Up 7 days (healthy)
- compose md5: 7975939c245761e451a8813852dcb9bf (unchanged 20h+, since R1088)

## 3. 6h 窗口数据 (2026-07-11 ~09:00–15:55 UTC)

### 3.1 总览
| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| OK | 12 (50.0%) |
| Fail | 12 (100% zombie) |
| ATE | 0 |
| tier_attempts | 0 |
| ms_gw | 0 traffic |

### 3.2 按模型
| 模型 | Total | OK | Fail | Zombie | ATE | Avg OK | Max |
|------|-------|-----|------|--------|-----|--------|-----|
| glm5_2_nv | 24 | 12 | 12 | 12 | 0 | 7,891ms | 38,540ms |
| dsv4p_nv | 0 | — | — | — | — | — | — |
| kimi_nv | 0 | — | — | — | — | — | — |
| minimax_m3_nv | 0 | — | — | — | — | — | — |

### 3.3 upstream 路径
| 路径 | Total | OK | Fail |
|------|-------|-----|------|
| nv_integrate | 24 | 12 | 12 |
| nvcf_pexec | 0 | — | — |

### 3.4 错误详情
- 全部 12 个失败 = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars)
- Gateway detection + error-chunk 正确: `[NV-ZOMBIE-ERROR-CHUNK] sent finish_reason=content_filter error SSE chunk to openclaw`
- 每 30min 一次 zombie (规律性), input_chars 持续增长 (165K→174K)

### 3.5 日志
- 无 ERROR/WARN (除 zombie detection 日志外)
- zombie detection 为 code-level feature, 非 config 可修

### 3.6 容器 env (关键参数)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198, MIN_OUTBOUND_INTERVAL_S=0 (floor)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor), NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15
- NVU_PEER_FALLBACK_TIMEOUT=66, NVU_CONNECT_RESERVE_S=0 (floor)
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_EMPTY_200_FASTBREAK=2, NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_SSLEOF_RETRY_DELAY_S=1.0
- KEY_AUTHFAIL_COOLDOWN_S=60
- NV_INTEGRATE_MODELS=glm5_2_nv

## 4. 候选评估

| 候选参数 | 当前值 | 评估 | 决策 |
|----------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | NVCFPexecTimeout max binding, 66 已足够 | ❌ 无需改 |
| TIER_TIMEOUT_BUDGET_S | 198 | 覆盖 ms_gw fallback 132s + UPSTREAM 66, 充足 | ❌ 无需改 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 对齐 UPSTREAM=66 | ❌ 无需改 |
| NVU_EMPTY_200_FASTBREAK | 2 | 当前 0 empty_200, dsv4p 0 traffic | ❌ 无需改 |
| TIER_COOLDOWN_S | 15 | 0 tier_attempts, 已足够 | ❌ 无需改 |
| INTEGRATE_KEY_COOLDOWN_S | 0 | floor | ❌ 无需改 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | ❌ 无需改 |
| NVU_CONNECT_RESERVE_S | 0 | floor | ❌ 无需改 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | ❌ 无需改 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | 当前 zombie 全 glm5_2_nv, 放开 peer-fb 无意义 (zombie = content-filter, 非 function 不可用) | ❌ 无需改 |

## 5. 决策

**NOP** — false trigger, 57th chain of R1133.
- 所有失败 = zombie_empty_completion (code-level, NVCF content-filter stop+12chars, 非 config 可修)
- 所有参数已 floor/optimal, compose md5 不变 20h+
- 0 tier_attempts, 0 ATE, 0 ms_gw traffic, 0 429
- Gateway detection + error-chunk 正确, zombie 机制工作正常
- dsv4p_nv/kimi_nv/minimax_m3_nv 零流量 6h

### 铁律: 只改HM1不改HM2 ✓
- 本轮零 config 变更, 零 compose 编辑, 零 container restart

## ⏳ 轮到HM1优化HM2

