# HM2 Optimize HM1 — Round R1458 (NOP)

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `e4c8523` (R1457, author=opc2_uname), 64th chain of R1395
- HM1 compose md5: `51079b89` (stable since container restart, unchanged from R1455-R1457)
- 判定: FALSE TRIGGER — 本轮无HM1变更

## 2. 数据收集 (改前必有数据)

### 容器状态
- nv_gw: `Up 2 hours (healthy)`, restart 2026-07-15T10:49:16Z
- ms_gw: running

### nv_gw 6h 统计 (2026-07-15 14:40 UTC ≈)
| 指标 | 值 |
|------|-----|
| 总请求 | 36 |
| 成功 (200) | 14 |
| 失败 (502) | 22 |
| 成功率 | 38.9% |

### 6h 错误分类
| 错误类型 | 数量 | 说明 |
|---------|------|------|
| zombie_empty_completion | 11 | glm5_2_nv, NVCF content-filter, avg 215K输入→12字符 |
| all_tiers_exhausted | 11 | 10 dsv4p_nv (NVCF 504), 1 glm5_2_nv |

### 按模型
| 模型 | 总数 | 成功 | 失败 | SR | avg_dur |
|------|------|------|------|-----|---------|
| glm5_2_nv | 25 | 13 | 12 | 52.0% | 18679ms |
| dsv4p_nv | 11 | 1 | 10 | 9.1% | 79795ms |

### 按上游
| upstream_type | 总数 | 成功 | 失败 | avg_dur |
|--------------|------|------|------|---------|
| nv_integrate | 24 | 13 | 11 | 11658ms |
| NULL (ATE) | 11 | 0 | 11 | 91627ms |
| nvcf_pexec | 1 | 1 | 0 | 57012ms |

### 6h 按小时
| 小时 | 总数 | 成功 | 失败 | SR |
|------|------|------|------|-----|
| 07:00 | 5 | 1 | 4 | 20.0% |
| 08:00 | 5 | 2 | 3 | 40.0% |
| 09:00 | 8 | 4 | 4 | 50.0% |
| 10:00 | 6 | 2 | 4 | 33.3% |
| 11:00 | 6 | 2 | 4 | 33.3% |
| 12:00 | 6 | 3 | 3 | 50.0% |

### ms_gw 6h: 27/23 85.2% SR — healthy
- ms_gw logs: MS-OK-STREAM + MS-STREAM-DONE for both dsv4p_ms (deepseek-ai/Deepseek-v4-Pro) and glm5_2_ms (ZHIPUAI/glm-5.2)
- ms_gw status values: 'ok', 'error'

### Other
- tier_attempts: 0 (no key cycling)
- NVStream_IncompleteRead: 0
- fallback_occurred: 0
- nv_gw logs: NV-EMPTY-200 k1 dsv4p_nv → 200 Content-Length:0; NV-TIER-FAIL dsv4p_nv all 5 keys: empty200=1, other=1; NV-MS-FB relay failed TimeoutError 284s; NV-ZOMBIE-EMPTY glm5_2_nv 12 chars from 217K input

## 3. 当前配置
```
UPSTREAM_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```
Compose md5: `51079b89`
All params at floor/optimal.

## 4. ms_gw 配置
```
EMPTY_200_FASTBREAK_THRESHOLD=3
KEY_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=1.0
UPSTREAM_TIMEOUT=300
```
ms_gw also at floor/optimal.

## 5. 决策: NOP
- 64th chain false trigger of R1395 sequence
- 数据与 R1457 几乎一致 (36req/14OK vs 35req/14OK)
- zombie = NVCF content-filter (avg 215K input → 12 chars, not config-fixable)
- ATE = NVCF 504 (not config-fixable)
- 0 tier_attempts (no key cycling)
- All nv_gw params at floor/optimal
- ms_gw at floor/optimal
- 无参数可调, 无重启理由
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
