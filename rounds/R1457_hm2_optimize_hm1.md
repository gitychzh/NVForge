# HM2 Optimize HM1 — Round R1457

## 触发分析

cron 脚本输出: "这是我提交的, 不触发" ← FALSE TRIGGER / DOUBLE-DISPATCH
- 最新 commit author = opc2_uname (HM2)
- HM1 未提交新内容，R1456 为 HM2 NOP 轮
- 此轮为 double-dispatch 继续链（R1395 链的第 63 轮）

## 数据 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 35 |
| 成功 | 14 (40.0%) |
| 失败 | 21 (60.0%) |

### 错误分类
| 错误类型 | 数量 | 模型 |
|----------|------|------|
| all_tiers_exhausted | 11 | 10 dsv4p_nv + 1 glm5_2_nv |
| zombie_empty_completion | 10 | glm5_2_nv (NVCF content-filter) |

### 模型维度
| 模型 | 请求 | 成功 | SR% | 平均延迟 |
|------|------|------|-----|----------|
| glm5_2_nv | 25 | 14 | 56.0% | 18.6s |
| dsv4p_nv | 10 | 0 | 0.0% | 82.1s |

### 路径维度
| 路径 | 请求 | 成功 | 失败 |
|------|------|------|------|
| nv_integrate | 24 | 14 | 10 |
| (NULL/pexec) | 11 | 0 | 11 |

### zombie 详情
- glm5_2_nv: 10 zombie, avg input_chars=214,919, avg dur=11.4s
- NVCF content-filter stop, output=6-32 chars, gateway detection+error-chunk 正确

### ATE 详情
- dsv4p_nv: 10 ATE, avg dur=82.1s (NVCF pexec 504, 5 keys cycling per request, ~64s waste)
- ATE 日志: `[NV-CYCLE] tier=dsv4p_nv → 504 (504_nv_gateway_timeout), cycling to next key`
- dsv4p_nv tier_chain=['dsv4p_nv'] (no fallback, 3model) — FALLBACK_GRAPH={} is expected
- ms_gw fallback: TimeoutError 284s (code-level streaming sync defect — MS-STREAM-DONE at 2-5s not seen by nv_gw)
- glm5_2_nv: 1 ATE, dur=187.2s (isolated, not a pattern)

### ms_gw
- 25/21 84.0% SR
- glm5_2_ms: MS-OK-STREAM + MS-STREAM-DONE at ~1s — healthy
- dsv4p_ms: MS-OK-STREAM + MS-STREAM-DONE at ~2-5s — healthy, but nv_gw relay times out

### 其他
- tier_attempts: 0
- fallback: 0
- IncompleteRead: 0
- key_cycle_429s: 0

### 每小时 SR
| 小时 (UTC) | 总请求 | 成功 | 失败 | SR% |
|------------|--------|------|------|-----|
| 06:00 | 2 | 2 | 0 | 100.0 |
| 07:00 | 5 | 1 | 4 | 20.0 |
| 08:00 | 5 | 2 | 3 | 40.0 |
| 09:00 | 8 | 4 | 4 | 50.0 |
| 10:00 | 6 | 2 | 4 | 33.3 |
| 11:00 | 6 | 2 | 4 | 33.3 |
| 12:00 | 3 | 1 | 2 | 33.3 |

## 容器状态
- 重启时间: 2026-07-15T10:49:16Z (unchanged, ~2h 前)
- 状态: Up 2 hours (healthy)
- Compose md5: 51079b89019ddfb1a08f65e79e847b51 (unchanged from R1456)

## 当前参数 (all floor/optimal)
- UPSTREAM_TIMEOUT=66
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_TIER_BUDGET_DSV4P_NV=66 (BUDGET=UPSTREAM floor, R1440 pattern)
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- NVU_PEER_FALLBACK_ENABLED=1
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS="" (peer open)
- NV_INTEGRATE_KEY_COOLDOWN_S=0

## 判定

**NOP** — 数据与 R1456 完全一致，所有参数已在地板/最优值，无配置空间可优化。
- zombie=10 (NVCF content-filter，非配置可修复)
- ATE=11 (dsv4p_nv NVCF 504 function-level degradation，非配置可修复；ms_gw relay TimeoutError 284s 为代码级 streaming sync 缺陷)
- 0 tier_attempts, 0 key_cycle_429s, 0 IncompleteRead
- HM1 git at R1206 (250 rounds behind)
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
