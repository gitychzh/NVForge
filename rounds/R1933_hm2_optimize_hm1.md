# R1933 (HM2→HM1): NOP — false trigger, R1931 just deployed 8min, stale symlink fix

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `b898dbe R1931 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 32→30 (-2s)`
- 最新 commit author = `opc2_uname` (HM2自提交)
- 脚本正确检测到自提交并标记"不触发"
- cron 仍被派遣 — 误触发 / double-dispatch
- ⚠️ **symlink 过期**: `RN_hm2_optimize_hm1.md -> rounds/R1905_hm2_optimize_hm1.md` (R1931/HM2→HM1 未更新)
- R1931 容器 `nv_gw` StartedAt: 2026-07-19T13:33:40Z (仅 8 分钟前)

## 数据 (6h window, ~08:00-14:00 UTC)

### nv_gw SR
| 指标 | 值 |
|------|-----|
| 总请求 | 41 |
| 成功 (200) | 29 |
| 失败 (502) | 12 |
| SR | **70.7%** |

### 502 错误分类
| 模型 | 错误类型 | 数量 | 平均耗时 |
|------|---------|------|---------|
| glm5_2_nv | zombie_empty_completion | 10 | 9,226ms |
| dsv4p_nv | all_tiers_exhausted | 2 | 3ms |

- **10 zombie glm5_2**: 全部 big_input (avg 136,501 chars, >115K threshold) — NVCF content-filter 平台行为，非 nv_gw 配置可修复
- **2 dsv4p phantom ATE**: 3ms duration, 明显 phantom (status=502 但 duration=3ms) — 非配置可修复

### 成功请求
| 模型 | 数量 | 平均耗时 | 最小 | 最大 |
|------|------|---------|------|------|
| glm5_2_nv | 25 | 8,870ms | 2,333ms | 27,809ms |
| dsv4p_nv | 4 | 16,485ms | 1,963ms | 43,081ms |

### 按时段 SR
| 时段 | 总量 | OK | 失败 | SR% |
|------|------|-----|------|-----|
| 08:00 | 10 | 6 | 4 | 60.0 |
| 09:00 | 6 | 5 | 1 | 83.3 |
| 10:00 | 6 | 4 | 2 | 66.7 |
| 11:00 | 7 | 5 | 2 | 71.4 |
| 12:00 | 5 | 3 | 2 | 60.0 |
| 13:00 | 7 | 6 | 1 | 85.7 |

### tier_attempts
| 错误类型 | 数量 |
|---------|------|
| pexec_success | 25 |
| pexec_timeout | 1 |

### ms_gw
- 6h: 3 req, 0 OK, 3 fail — ModelScope 上游问题，非 HM1 配置可修复

## HM1 环境 (container env)
```
NVU_TIER_BUDGET_GLM5_2_NV=30     # R1931: 32→30
NVU_TIER_BUDGET_DSV4P_NV=25      # R1928: 30→25
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_TIMEOUT_BUDGET_S=153
UPSTREAM_TIMEOUT=30
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_MS_GW_FALLBACK_TIMEOUT=120
PROXY_TIMEOUT=360
NVU_BIG_INPUT_COOLDOWN_S=21600
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_THRESHOLD=115000
NVU_PEER_FB_SKIP_MODELS=kimi_nv
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=25
```

## 决策: NOP

### 原因
1. **False trigger**: 脚本正确标记"不触发"，R1931 由 HM2 自提交
2. **R1931 刚部署 8 分钟**: 容器 StartedAt 13:33:40Z，零有效 post-R1931 数据
3. **BUDGET_GLM5_2_NV=30 已 tight**: glm5_2 OK max=27,809ms, margin=2,191ms (30,000-27,809)。进一步减至 28 仅留 191ms margin — 风险过高
4. **10 zombie 非配置可修复**: 全部 big_input >115K，NVCF content-filter 上游行为
5. **2 dsv4p phantom ATE (3ms)**: 非配置可修复，BUDGET_DSV4P=25 已至 floor
6. **symlink 过期**: `RN_hm2_optimize_hm1.md -> rounds/R1905` 需修正为 R1933

### 参数变更: 无 (NOP)
### compose 变更: 无
### 容器重启: 无

## 验证
- 无需验证 (NOP)

## 铁律遵守
- ✅ 改前必有数据: SSH 到 HM1 收集 docker logs + env + DB 6h 数据
- ✅ 改后必有验证: N/A (NOP)
- ✅ 聚焦 nv_gw: 仅检查 nv_gw + ms_gw
- ✅ 所有修改写入仓库: 本回合记录写入 R1933
- ✅ 只改 HM1 不改 HM2: 本回合无任何修改

## ⏳ 轮到HM1优化HM2
