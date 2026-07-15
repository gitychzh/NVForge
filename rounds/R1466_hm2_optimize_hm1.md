# HM2 Optimize HM1 — Round R1466

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit ce44f0c author = opc2_uname (HM2)
- ⚠️ 脚本正确检测到自提交 → 误触发 double-dispatch (46th chain of R1395)
- HM1 无新提交; 数据与 R1465 完全一致

## 2. 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up About an hour (healthy)
- 重启时间: 2026-07-15T13:09:29Z (HM1 outside-loop restart)
- compose md5: 45c1f284

### 6h 概要
| metric | value |
|--------|-------|
| total | 42 |
| OK | 19 (45.2%) |
| fail | 23 |
| zombie_empty_completion | 14 |
| all_tiers_exhausted | 9 |

### 按模型分布
| model | total | OK | err | SR% | avg_dur |
|-------|-------|----|-----|-----|---------|
| glm5_2_nv | 27 | 15 | 12 | 55.6% | 18,712ms |
| dsv4p_nv | 15 | 4 | 11 | 26.7% | 57,563ms |

### 按上游类型
| upstream_type | total | OK | err | avg_dur |
|---------------|-------|----|-----|---------|
| nv_integrate | 26 | 15 | 11 | 12,233ms |
| (null) | 9 | 0 | 9 | 77,567ms |
| nvcf_pexec | 7 | 4 | 3 | 50,359ms |

### Zombie 明细
| model | cnt | avg_input_chars | avg_dur |
|-------|-----|-----------------|---------|
| glm5_2_nv | 11 | 216,664 | 12,083ms |
| dsv4p_nv | 3 | 218,535 | 49,159ms |

### ATE 明细
| model | cnt | avg_dur |
|-------|-----|---------|
| dsv4p_nv | 8 | 63,867ms |
| glm5_2_nv | 1 | 187,171ms |

### ms_gw
- 24req/20OK (83.3% SR)
- status values: ok, error

### 关键参数 (docker exec nv_gw env)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=205
- NVU_TIER_BUDGET_DSV4P_NV=66
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_MS_GW_FALLBACK_TIMEOUT=120
- KEY_COOLDOWN_S=25
- TIER_COOLDOWN_S=15
- NVU_PEER_FB_SKIP_MODELS= (empty)
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- tier_attempts: 0

## 3. 决策: NOP

### 原因
- 所有参数已在地板/最优值
- 14 zombie = NVCF content-filter (avg input ~217K chars, output 0-21 tokens), 代码级功能不可配置
- 9 ATE = all_tiers_exhausted (8 dsv4p_nv + 1 glm5_2_nv), NVCF upstream degradation
- 0 tier_attempts = 无 key cycling, 密钥池清洁
- ms_gw 24/20 OK = fallback 可靠
- BUDGET=205, UPSTREAM=66, per-model budgets at floor
- 容器已重启 (13:09Z), 窗口内无可配置优化空间
- 铁律:只改HM1不改HM2

### 修改: 无 (零参数, 零 compose 变更, 零容器重启)
## ⏳ 轮到HM1优化HM2
