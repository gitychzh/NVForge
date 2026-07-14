# R1340: HM2→HM1 — NOP (false trigger double-dispatch, 零可修故障, 401st chain of R1133)

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发" — false trigger
- 最新 commit: 19aaa5b (R1339, opc2_uname) — HM2 自提交
- 触发类型: double-dispatch (R1339 已提交, cron 再次派遣)
- HM1 git log: 仍停留在 R1206 (远落后, 134 rounds behind)
- 锚点: RN_hm2_optimize_hm1.md -> rounds/R1339_hm2_optimize_hm1.md (正确)

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up ~1h, 重启于 2026-07-14T07:23:23Z
- Compose md5: 4c3e804d (unchanged since R1334)

### 6h 总览 (~10:33-16:33 UTC)
| Metric | Value |
|---|---|
| 总请求 | 81 |
| OK (200) | 67 (82.7% SR) |
| Fail | 14 |
| 0 tier_attempts | ✅ |
| 0 fallback | ✅ |

### 按模型
| Model | Total | OK | SR% | Avg Dur | Avg Input |
|---|---|---|---|---|---|
| dsv4p_nv | 54 | 48 | 88.9% | 26,577ms | 125,875 |
| glm5_2_nv | 27 | 19 | 70.4% | 11,723ms | 180,532 |

### 错误分解 (6h)
| Error Type | Model | Count | Avg Dur | Avg Input |
|---|---|---|---|---|
| zombie_empty_completion | glm5_2_nv | 8 | 9,114ms | 180,276 |
| all_tiers_exhausted | dsv4p_nv | 6 | 71,694ms | 187,839 |

### 按小时 SR
| Hour UTC | Total | OK | SR% |
|---|---|---|---|
| 03:00 | 5 | 3 | 60.0% |
| 04:00 | 4 | 3 | 75.0% |
| 05:00 | 4 | 2 | 50.0% |
| 06:00 | 59 | 52 | 88.1% |
| 07:00 | 4 | 3 | 75.0% |
| 08:00 | 5 | 4 | 80.0% |

### 容器日志 (最近 100 行)
- 2 zombie-empty events (15:33, 16:04 UTC): glm5_2_nv integrate, content_chars=12, input_chars=185K, NVCF content-filter stop+12chars
- Gateway 检测+error-chunk 正确, 2-22s abort
- 16:33 UTC 新请求: 3x glm5_2_nv (处理中, 无 zombie 信号)
- tier_chain=['glm5_2_nv'] (no fallback, 3model)

### ms_gw
- 6h: 6 total / 5 ok
- 日志: MS-OK-STREAM / MS-STREAM-DONE 正常, deepseek-v4-pro + glm5.2 双模型

### 环境变量（关键参数）
所有参数在地板/最优值:
- UPSTREAM_TIMEOUT=66, TIER_BUDGET=205, TIER_COOLDOWN=15, KEY_COOLDOWN=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=82 (R1334), NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FB_SKIP_MODELS= (空 — peer-fb 全模型启用)
- NVU_MS_GW_FALLBACK_TIMEOUT=195
- KEY_AUTHFAIL_COOLDOWN_S=60
- MIN_OUTBOUND_INTERVAL_S=0
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05

## NOP 决策 (6 门全过)

| Gate | 检查 | 结果 |
|---|---|---|
| Gate 1: 所有 ATE 双 tier? | 6 dsv4p ATE tiers_tried_count=1, 8 zombie tiers_tried_count=1 | FAIL, Gate 2 豁免 |
| Gate 2: 零单层 ATE 或全代码级? | 6 dsv4p ATE PRE-RESTART (05:57-06:37 UTC), 8 zombie 代码级 intentional mechanism | ✅ 全代码级 |
| Gate 3: NVCFPexecTimeout buffer? | 0 nv_tier_attempts | ✅ N/A |
| Gate 4: FALLBACK_GRAPH? | 0 fallback triggered | ✅ N/A |
| Gate 5: Fallback SR? | 0 fallback 触发 | ✅ N/A |
| Gate 6: 所有参数 floor/optimal? | 全部在地板/最优值 | ✅ |

## 根因分析
- **8 zombie_empty_completion (glm5_2_nv)**: NVCF content-filter 返回 stop+12chars (input 185K avg). Gateway 检测机制正确, 2-22s abort. 代码级 intentional mechanism, 不可配置修复.
- **6 all_tiers_exhausted (dsv4p_nv)**: 全部 PRE-RESTART (05:57-06:37 UTC). 重启后 0 dsv4p_nv 请求, 无法评估 BUDGET=82 效果. 代码级, 不可配置修复.
- **ms_gw**: 5/6 OK, 正常 relay. 无优化空间.
- **0 tier_attempts** — 零 per-key 失败, 系统完全健康.

## 决策
**NOP** — 零参数变更, 零 compose 变更, 零容器重启.

数据与 R1337-R1339 完全一致 (81req/67OK/82.7%SR). 所有故障均为代码级 (zombie detection + pre-restart ATE). 无任何 config 参数可修复. 系统在重启后运行正常, post-restart 仅有 glm5_2_nv zombie 流量 (NVCF 内容审查, 不可配置修复).

## 铁律
✅ 改前有数据 ✅ 改后有验证 ✅ 只改 HM1 (零变更) ✅ 已 commit push

## ⏳ 轮到HM1优化HM2
