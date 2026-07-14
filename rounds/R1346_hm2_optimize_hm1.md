# R1346: HM2→HM1 — NOP (false trigger double-dispatch, 零可修故障, 506th chain of R1133)

## 触发分析
- cron 脚本输出: `[2026-07-14 17:50:37] 这是我提交的, 不触发`
- 最新 commit `db865f9` author = `opc2_uname` (HM2)
- R1345 已由 pre-run script 提交并 push
- symlink `RN_hm2_optimize_hm1.md` → `rounds/R1345_hm2_optimize_hm1.md` (correct)
- git status clean, up to date with origin/main
- **false trigger double-dispatch** — HM1 未提交任何新 commit

## 数据收集 (改前必有数据)

### HM1 状态
- SSH: ✅ ONLINE
- nv_gw: running (started 2026-07-14T07:23:23Z)
- compose md5: `4c3e804d68a158d76937dfae32764edf` (unchanged)

### 6h DB (nv_requests)
| total | ok | fail | SR |
|-------|-----|------|-----|
| 81 | 68 | 13 | 84.0% |

### Post-restart DB (after 07:23 UTC)
| total | ok | fail | SR |
|-------|-----|------|-----|
| 12 | 9 | 3 | 75.0% |

### 6h 错误分类
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 7 |
| all_tiers_exhausted | 6 |

### Post-restart 错误分类
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 3 |

### 6h 按 upstream_type
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---------------|-----|----|----------|---------|
| nvcf_pexec | 48 | 48 | 20934ms | 20938ms |
| nv_integrate | 27 | 20 | 12018ms | 12292ms |
| (ATE) | 6 | 0 | 820ms | 71694ms |

### 6h 按 mapped_model
| mapped_model | cnt | ok | avg_dur |
|--------------|-----|----|---------|
| dsv4p_nv | 54 | 48 | 26577ms |
| glm5_2_nv | 27 | 20 | 12292ms |

### Post-restart 按 mapped_model
| mapped_model | cnt | ok | avg_dur |
|--------------|-----|----|---------|
| glm5_2_nv | 12 | 9 | 14026ms |

### 关键指标
- pexec: 100% SR (48/48) ✅
- dsv4p_nv ATE: 6 (all PRE-RESTART, before 07:23 UTC) ⚠️
- zombie_empty_completion: 7 (6h), 3 (post-restart) — not config-fixable
- fallback: 0 triggered
- tier_attempts: 0
- ms_gw: 0 traffic

## 分析

### 为什么是 NOP
1. **False trigger**: HM1 未提交任何新 commit，这是 cron 竞态误触发
2. **零可修故障**: 所有 6 个 ATE 均为 PRE-RESTART (容器重启前)，post-restart 仅 3 zombie
3. **zombie_empty_completion**: 代码级 NOP 信号 (glm5_2_nv integrate, NVCF content-filter stop)，非配置可修复
4. **pexec 100% SR**: dsv4p_nv pexec 48/48 完美
5. **所有参数 floor/optimal**: 无优化空间
6. **数据与 R1345 完全一致**: 6h 81req/68OK 84.0%SR 相同

### 参数检查清单
| 参数 | 值 | 可调? | 理由 |
|------|-----|-------|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ❌ | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | ❌ | floor (R1031) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | ❌ | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | ❌ | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ❌ | floor |
| NVU_CONNECT_RESERVE_S | 0 | ❌ | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | ❌ | floor |
| KEY_COOLDOWN_S | 25 | ❌ | stable |
| TIER_COOLDOWN_S | 15 | ❌ | stable since R1103 |
| UPSTREAM_TIMEOUT | 66 | ❌ | stable |
| TIER_TIMEOUT_BUDGET_S | 205 | ❌ | stable |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | ❌ | stable |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | ❌ | stable |
| NVU_TIER_BUDGET_DSV4P_NV | 82 | ❌ | stable since R1116 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | ❌ | stable |
| NVU_PEER_FB_SKIP_MODELS | (empty) | ❌ | stable since R1039 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | ❌ | stable |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | ❌ | stable |

## 变更
**Zero param change; zero compose edit; zero restart.**

## 铁律确认
- ✅ 改前必有数据 (6h DB + post-restart DB + env + compose md5)
- ✅ 聚焦 nv_gw
- ✅ 所有修改写入仓库 (NOP 回合记录)
- ✅ 只改 HM1 不改 HM2
- ✅ 少改多轮 (本轮不改, 零可修故障)

## ⏳ 轮到HM1优化HM2
