# R1446: HM2→HM1 — NOP (false trigger, R1445 deployed 8min ago, zero post-restart traffic)

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- R1445 刚部署 ~8min (container restart 10:49 UTC), 零 post-restart 流量
- HM1 本地 git log: R1206 (239 轮落后 HM2 R1445)
- 判定: false trigger → NOP

## 数据收集 (HM1)

### 容器状态
- nv_gw: Up 8 min (healthy), restart 2026-07-15T10:49:16 UTC (R1445 deploy)
- ms_gw: 运行中, 健康
- md5sum docker-compose: 51079b89019ddfb1a08f65e79e847b51 (R1445 deploy)

### nv_gw env (关键参数)
| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 66 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| PROXY_TIMEOUT | 360 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 280 (R1445) |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| MIN_OUTBOUND_INTERVAL_S | 0 |

### 6h DB 概况 (nv_requests)
- 55 req, 34 OK, 21 fail → 61.8% SR
- dsv4p_nv: 12 req, 2 OK, 10 fail (16.7% SR, avg 68004ms)
- glm5_2_nv: 43 req, 32 OK, 11 fail (74.4% SR, avg 17716ms)

### 6h 错误分布
| 错误类型 | 计数 | 备注 |
|---|---|---|
| zombie_empty_completion | 12 | NVCF content-filter, avg input ~210K chars, not config-fixable |
| all_tiers_exhausted | 9 | dsv4p_nv: 8 (avg 92640ms), glm5_2_nv: 13 (avg 34143ms) — ALL pre-R1445 |

### post-restart (10:49 UTC→)
- 0 req, 0 OK, 0 fail — 零流量, 无法评估 R1445 效果

### 6h fallback 健康度
- fallback_occurred=true: 12 req, 12 OK (100% SR) — ms_gw relay 全部成功 ✓
- fallback_occurred=false: 43 req, 22 OK (51.2% SR)

### ms_gw 6h
- 35 req, 31 ok, 4 error → 88.6% SR
- 1 MS-ALL-EXHAUSTED (glm5_2_ms stream_no_data_lines — 正常水平)
- 日志显示 MS-OK-STREAM relay 正常 (dsv4p_ms, glm5_2_ms)

### nv_tier_attempts 6h
- 0 rows (clean, zero key cycling)

### 每小时 SR 趋势
| 小时 (UTC) | total | ok | fail | SR% |
|---|---|---|---|---|
| 05:00 | 26 | 22 | 4 | 84.6 |
| 06:00 | 5 | 3 | 2 | 60.0 |
| 07:00 | 5 | 1 | 4 | 20.0 |
| 08:00 | 5 | 2 | 3 | 40.0 |
| 09:00 | 8 | 4 | 4 | 50.0 |
| 10:00 | 6 | 2 | 4 | 33.3 |

## 分析

### 核心判断: NOP
R1445 刚部署 8min，零 post-restart 流量。无法评估 NVU_MS_GW_FALLBACK_TIMEOUT 240→280 的效果。6h 数据全部为 pre-R1445 时期的旧数据（container restart 10:49 UTC 后无新请求）。

### dsv4p_nv ATE 持续性
8 次 dsv4p_nv ATE (avg 92640ms) — 全部为 pre-R1445 数据。R1445 的 280s timeout 旨在解决 ms_gw relay 超时问题（观测到 relay 244-250s > 240s limit），需要等待 post-restart 流量才能验证。

### zombie 持续
12 次 zombie (NVCF content-filter, avg input ~210K chars) — 不可配置修复。

### ms_gw 健康
88.6% SR, ��� 1 次 MS-ALL-EXHAUSTED (glm5_2_ms stream_no_data_lines) — 正常水平。fallback 链路 100% 成功。

### 所有参数 floor/optimal
- UPSTREAM_TIMEOUT=66 (floor)
- NVU_TIER_BUDGET_DSV4P_NV=66 (floor)
- PROXY_TIMEOUT=360 (R1442)
- NVU_MS_GW_FALLBACK_TIMEOUT=280 (R1445)
- TIER_COOLDOWN_S=15 (floor)
- MIN_OUTBOUND_INTERVAL_S=0 (floor)
- KEY_COOLDOWN_S=25 (floor+5)

## 优化决策

**NOP — 零参数变更**

理由:
1. R1445 刚部署 8min，零 post-restart 流量，无法评估
2. False trigger: HM2 自提交 (R1445)，HM1 未提交新内容
3. HM1 git 停留在 R1206 (239 轮落后)
4. 所有参数 floor/optimal，无优化空间
5. zombie 系 NVCF content-filter，不可配置修复
6. ms_gw 健康，fallback 100% 成功

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
