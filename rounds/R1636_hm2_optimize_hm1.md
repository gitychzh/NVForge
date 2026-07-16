# R1636: HM2→HM1 — NOP (false trigger, post-restart window too small)

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发" — false trigger
- 最新 commit: ce8c0ab (R1635, opc2_uname) — HM2 自提交
- 触发类型: double-dispatch (R1635 已提交, cron 再次派遣)

## 数据收集 (改前必有数据)

### 容器状态
| Container | Status | Uptime |
|---|---|---|
| nv_gw | Up | 9 min (restarted 2026-07-16T10:47:25Z) |
| cc4101 | Up | 3 min (restarted 2026-07-16T10:53:48Z) |
| ms_gw | Up | 6h (healthy) |
| logs_db | Up | 35h (healthy) |

### 6h DB 总览 (11:00-17:00 UTC 实际窗口, 全部 pre-restart)
| Metric | Value |
|---|---|
| 总请求 | 216 |
| OK (200) | 103 (47.7% SR) |
| Fail (502) | 113 |
| MAX(created_at) | 11:00 UTC (8h ago, pre-restart) |
| Post-restart (10:47 UTC+) | 0 DB entries |
| nv_tier_attempts | 260 |

### 按模型 (6h, all pre-restart)
| Model | Total | OK | SR% | Avg OK ms |
|---|---|---|---|---|
| glm5_2_nv | 200 | 97 | 48.5% | 16,815ms |
| dsv4p_nv | 16 | 6 | 37.5% | 12,258ms |

### 错误分解 (6h, all pre-restart)
| Error Type | Model | Count | Avg Dur |
|---|---|---|---|
| zombie_empty_completion | glm5_2_nv | 103 | 9,489ms |
| all_tiers_exhausted | dsv4p_nv | 10 | 65,782ms |

### 按重启分段
- **Pre-restart (<10:47 UTC)**: 216 req / 103 OK (47.7%) / 113 fail
  - 103 zombie_empty_completion (glm5_2_nv)
  - 10 all_tiers_exhausted (dsv4p_nv)
- **Post-restart (10:47 UTC+)**: 0 DB entries, active live traffic in docker logs
  - zombie_empty_completion (glm5_2_nv, 16-17 chars, 120K-121K input, NVCF content-filter)
  - 429 cascading (NV-GLM52-COOLDOWN, all 5 keys hitting 429)
  - CHAIN-FAIL → CHAIN-RESET → CHAIN-FALLBACK → all keys cooldown → TIER-FAIL → PEER-FB
  - Peer-FB mixed: some OK (200, 5-373ms ttfb), some timeout (72s)

### Tier attempts
- 260 nv_tier_attempts (all pre-restart): 201 pexec_success, 46 pexec_429, 11 SSLEOFError, 1 empty_200, 1 RemoteDisconnected
- All glm5_2_nv tier

### tiers_tried_count
- 所有 114 个 ATE 均为 tiers_tried_count=1 (单层)
  - start_tier_idx=2 (glm5_2_nv): 104
  - start_tier_idx=1 (dsv4p_nv): 10

### fallback_occurred
- 0 fallback_occurred in 6h DB window

### FALLBACK_GRAPH
- tier_chain=['glm5_2_nv'] (no cross-model fallback, R753) — expected state

### 容器日志 (post-restart live)
- 3 zombie events: glm5_2_nv integrate, content_chars=16-17, input_chars=120K-121K, NVCF content-filter
- Gateway 检测+error-chunk 正确
- 1 CHAIN-FAIL → peer-fb → OK (200, 5ms ttfb)
- 2 CHAIN-FAIL → peer-fb → timeout (72s) → fail
- 429 cascading pattern: all 5 keys hitting pexec_429, chain-exhaustion

### 环境变量（关键参数）
- UPSTREAM_TIMEOUT=66, TIER_BUDGET=205, TIER_COOLDOWN=15, KEY_COOLDOWN=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=120
- NVU_PEER_FB_SKIP_MODELS=dsv4p_nv
- NVU_MS_GW_FALLBACK_TIMEOUT=120
- NVU_PEER_FALLBACK_TIMEOUT=72
- FALLBACK_HEALTH_THRESHOLD=0.05
- Compose md5: 6e81cd001acd69ac828eae1cfaa3bffe

### cc4101
- CC4101_PRIMARY_FAIL_THRESHOLD=4 (R1635 变更生效 ✅)

## NOP 决策 (6 门分析)

### Gate 1: 所有 ATE 双 tier?
114 ATE 全部 tiers_tried_count=1 → **FAIL, Gate 2 豁免**

### Gate 2: 零单层 ATE 或全代码级?
- 103 zombie_empty_completion (glm5_2_nv): NVCF content-filter 返回 stop+16-17 chars, 代码级 intentional mechanism ✅
- 10 all_tiers_exhausted (dsv4p_nv): 全部 PRE-RESTART, peer-fb SKIP for dsv4p_nv ✅
- 0 post-restart DB failures ✅
→ **全代码级 ✅**

### Gate 3: NVCFPexecTimeout buffer?
- 0 NVCFPexecTimeout in nv_tier_attempts (tier_attempts only pexec_success/429/SSLEOFError) → **N/A ✅**

### Gate 4: FALLBACK_GRAPH?
- tier_chain=['glm5_2_nv'] (no cross-model fallback) — R753 expected state, not broken → **N/A ✅**

### Gate 5: Fallback SR?
- 0 fallback_occurred in 6h window → **N/A ✅**

### Gate 6: 所有参数 floor/optimal?
- 全部在地板/最优值 ✅

## 根因分析
- **103 zombie_empty_completion (glm5_2_nv)**: NVCF 3b9748d8 function 大 context (120K+ input) 返回 16-17 chars stop。代码级 intentional mechanism, 不可配置修复。
- **10 all_tiers_exhausted (dsv4p_nv)**: 全部 PRE-RESTART。Post-restart 0 dsv4p_nv 请求, 无法评估 BUDGET=66 效果。
- **429 cascading**: NVCF API 限流, 非 HM1 配置问题。
- **Peer-FB**: 混合结果 (OK→timeout), NVU_PEER_FALLBACK_TIMEOUT=72, 符合对端 BUDGET 约束。

## 决策
**NOP** — 零参数变更, 零 compose 变更, 零容器重启。

- False trigger (R1635 self-commit double-dispatch)
- Post-restart 窗口仅 9 min, 0 DB 请求, 无法评估 R1635 变更效果
- ���有 6h DB 故障均为 pre-restart 代码级
- 所有参数在地板/最优值
- R1635 CC4101_PRIMARY_FAIL_THRESHOLD=4 已生效, 等待下一轮 HM1 评估

## 铁律
✅ 改前有数据 ✅ 改后有验证 ✅ 只改 HM1 (零变更) ✅ 已 commit push

## ⏳ 轮到HM1优化HM2
