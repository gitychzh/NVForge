# HM2 Optimize HM1 — Round R1357

## 触发分析
- **cron脚本输出**: "这是我提交的, 不触发"
- **最新commit author**: opc2_uname (HM2), commit 52ba7fc (R1356)
- **判定**: FALSE TRIGGER — 双派发 (double-dispatch), 517th chain of R1133
- HM1无新commit, 自派发误触发

## 数据采集 (改前必有数据)

### 容器状态
- nv_gw: Up ~1h (healthy), restarted 2026-07-14T11:29:07Z
- compose md5: b367c647a8d42d9d86ed8814234a1d19 (changed from R1356's 28795fbe — outside-loop rewrite, env vars identical)

### 6h 请求统计 (nv_requests)
| 指标 | 数值 |
|------|------|
| 总请求 | 29 |
| 成功 | 20 (69.0% SR) |
| 失败 | 9 |

### 按模型
| 模型 | 请求 | 成功 | 失败 | SR |
|------|------|------|------|-----|
| glm5_2_nv | 27 | 20 | 7 | 74.1% |
| dsv4p_nv | 2 | 0 | 2 | 0.0% |

### 错误类型
| 错误类型 | 次数 | 说明 |
|----------|------|------|
| zombie_empty_completion | 7 | code-level, glm5_2_nv integrate, ~187K input, ~10s avg |
| all_tiers_exhausted | 2 | dsv4p_nv, 70-72s, 全部 PRE-RESTART (06:32-06:37 UTC) |

### Pre/Post restart 分割
| 时期 | 请求 | 成功 | 失败 | SR |
|------|------|------|------|-----|
| pre-restart | 24 | 16 | 8 | 66.7% |
| post-restart | 5 | 4 | 1 | 80.0% |

- Post-restart: 5 glm5_2_nv (4 OK, 1 zombie), 0 dsv4p_nv traffic

### 其他
- tier_attempts: 0
- fallback: 0 triggered
- ms_gw: 3/3 OK (100% SR)
- ms_gw EMPTY_200_FASTBREAK_THRESHOLD=3, UPSTREAM_TIMEOUT=300, KEY_COOLDOWN_S=60

### 关键参数 (docker exec nv_gw env)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=94, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS= (empty), NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_SSLEOF_RETRY_DELAY_S=1.0

## 决策: NOP

**零可修故障**: 
- 7/9 失败 = zombie_empty_completion (code-level, NVCF content-filter, 不可配置修复)
- 2/9 失败 = pre-restart dsv4p_nv ATE (容器重启前数据, 已失效)
- Post-restart: 4/5 OK (80% SR), 仅1次zombie
- 0 tier_attempts, 0 fallback — 系统无参数级故障
- All params floor/optimal, 无优化空间
- ms_gw 100% SR, 无优化空间

**变更**: 无 (零参数, 零compose, 零容器重启)

**铁律**: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2
