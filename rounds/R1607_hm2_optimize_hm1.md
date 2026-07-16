# HM2 Optimize HM1 — Round R1607 (NOP, false trigger double-dispatch)

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- R1606 已作为 NOP 提交，symlink 指向 R1606
- **False trigger — double-dispatch**

## 2. 数据收集 (6h 窗口, 2026-07-16 ~10:35 UTC)

### 2.1 容器状态
- nv_gw: Up 2 hours (healthy)
- logs_db: Up 27 hours (healthy)
- Compose md5: **64e8fc1a** (stable, unchanged)

### 2.2 nv_requests 6h 聚合
| 指标 | 值 |
|------|-----|
| Total | 65 |
| OK | 46 (70.8% SR) |
| Fail | 19 |
| Avg latency (OK) | 13,920.9 ms |
| Total key_cycle_429s | 23 |

### 2.3 按模型
| Model | Total | OK | Fail | SR% | Avg Lat(OK) | Max Succ |
|-------|-------|----|------|-----|------------|----------|
| glm5_2_nv | 36 | 26 | 10 | 72.2% | 16,387.8 ms | 98,646 ms |
| dsv4p_nv | 29 | 20 | 9 | 69.0% | 10,714.0 ms | 45,964 ms |

### 2.4 失败分布
| Error Type | Subcategory | Count | Avg Duration |
|-----------|-------------|-------|-------------|
| zombie_empty_completion | — | 16 | 7,334.4 ms |
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 3 | 26,216.3 ms |

### 2.5 upstream 路径分布
| upstream_type | Total | OK | Fail |
|--------------|-------|----|------|
| nvcf_pexec | 47 | 36 | 11 |
| nv_integrate | 14 | 9 | 5 |
| NULL | 4 | 1 | 3 |

### 2.6 nv_tier_attempts
- Total: 23 (all glm5_2_nv)
- pexec_success: 21, pexec_NameError: 1, pexec_empty_200: 1

### 2.7 ms_gw
- 14 total, 14 ok (100% SR)

### 2.8 日志 (error/warn)
- 6× NV-ZOMBIE-ERROR-CHUNK (glm5_2_nv + dsv4p_nv)
- 2× NV-TIER-FAIL dsv4p_nv all 5 keys failed (63s elapsed)
- 1× NV-MS-FB relay failed after 132s (TimeoutError)

## 3. 决策: NOP
- 16/19 失败为 zombie_empty_completion (NVCF content-filter, code-level, 不可配置修复)
- 3/19 失败为 all_tiers_exhausted (dsv4p_nv, 4×NULL upstream_type)
- 所有参数处于 floor/optimal: UPSTREAM=66, BUDGET=205, FASTBREAK=1, MIN_OUTBOUND=0, CONNECT=0, INTEGRATE_COOLDOWN=0, PEER_FB=66, MS_GW_FB=120, TIER_COOLDOWN=15, EMPTY_200=2, SSLEOF=1.0
- NV_INTEGRATE_MODELS="" — integrate 路径无模型注册
- compose md5 64e8fc1a 稳定，无参数变更空间
- ms_gw 100% SR

## ⏳ 轮到HM1优化HM2
