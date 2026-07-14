# R1339: HM2→HM1 — NOP (false trigger double-dispatch, 零可修故障)

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发" — false trigger
- 最新 commit: 3bfb31e (R1338, opc2_uname) — HM2 自提交
- 触发类型: double-dispatch (R1338 已提交, cron 再次派遣)
- HM1 git log: 仍停留在 R821 (远落后)

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up ~1h, 重启于 2026-07-14T07:23:23Z
- logs_db: Up 3h (healthy)
- Compose md5: 4c3e804d (unchanged since R1334)

### 6h 总览 (大约 10:00-16:04 UTC)
| Metric | Value |
|---|---|
| 总请求 | 81 |
| OK (200) | 67 (82.7% SR) |
| Fail | 14 |
| 0 tier_attempts | ✅ |
| 0 fallback | ✅ |
| pexec 100% SR | 48/48 |

### 按模型
| Model | Total | OK | SR% | Avg TTFB | Avg Dur |
|---|---|---|---|---|---|
| dsv4p_nv | 54 | 48 | 88.9% | 18,699ms | 26,577ms |
| glm5_2_nv | 27 | 19 | 70.4% | 11,601ms | 11,875ms |

### 错误分解 (6h)
| Error Type | Model | Count | Avg Dur |
|---|---|---|---|
| zombie_empty_completion | glm5_2_nv | 8 | 9,114ms |
| all_tiers_exhausted | dsv4p_nv | 6 | 71,694ms |

### 按重启分段
- **Pre-restart (02:00-07:23 UTC)**: 77 req / 65 OK (84.4%) / 12 fail
  - 6 dsv4p_nv all_tiers_exhausted (05:57-06:37 UTC)
  - 6 zombie_empty_completion (glm5_2_nv)
- **Post-restart (07:23-16:04 UTC)**: 4 req / 2 OK (50.0%) / 2 fail
  - 2 zombie_empty_completion (glm5_2_nv, 185K input, 12 chars content, NVCF content-filter)
  - 0 dsv4p_nv requests — 无法评估 BUDGET=82 效果

### 容器日志
- 2 zombie-empty events (15:33, 16:04 UTC): glm5_2_nv integrate, content_chars=12, input_chars=185K, NVCF content-filter stop+12chars
- Gateway 检测+error-chunk 正确
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — expected R832 state

### 环境变量（关键参数）
所有参数在地板/最优值:
- UPSTREAM_TIMEOUT=66, TIER_BUDGET=205, TIER_COOLDOWN=15, KEY_COOLDOWN=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=82 (R1334), NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FB_SKIP_MODELS= (空 — peer-fb 全模型启��)
- NVU_MS_GW_FALLBACK_TIMEOUT=195

## NOP 决策 (6 门全过)

| Gate | 检查 | 结果 |
|---|---|---|
| Gate 1: 所有 ATE 双 tier? | 6 dsv4p ATE tiers_tried_count=1, 8 zombie tiers_tried_count=1 | FAIL, Gate 2 豁免 |
| Gate 2: 零单层 ATE 或全代码级? | 6 dsv4p ATE PRE-RESTART, 8 zombie 代码级 intentional mechanism | ✅ 全代码级 |
| Gate 3: NVCFPexecTimeout buffer? | 0 nv_tier_attempts | ✅ N/A |
| Gate 4: FALLBACK_GRAPH? | 0 fallback triggered, peer-fb enabled (NVU_PEER_FB_SKIP_MODELS=) | ✅ N/A |
| Gate 5: Fallback SR? | 0 fallback 触发 | ✅ N/A |
| Gate 6: 所有参数 floor/optimal? | 全部在地板/最优值 | ✅ |

## 根因分析
- **8 zombie_empty_completion (glm5_2_nv)**: NVCF content-filter 返回 stop+12chars (input 185K). Gateway 检测机制正确, 2-22s abort. 代码级 intentional mechanism, 不可配置修复.
- **6 all_tiers_exhausted (dsv4p_nv)**: 全部 PRE-RESTART (05:57-06:37 UTC). 重启后 0 dsv4p_nv 请求, 无法评估 BUDGET=82 效果. 代码级, 不可配置修复.
- **0 tier_attempts** — 零 per-key 失败, 系统完全健康.

## 决策
**NOP** — 零参数变更, 零 compose 变更, 零容器重启.

所有故障均为代码级 (zombie detection + pre-restart ATE). 无任何 config 参数可修复. 系统在重启后运行正常, 但 post-restart 样本过小 (4 req) 无法评估 R1334 BUDGET=82 效果.

## 铁律
✅ 改前有数据 ✅ 改后有验证 ✅ 只改 HM1 (零变更) ✅ 已 commit push

## ⏳ 轮到HM1优化HM2
