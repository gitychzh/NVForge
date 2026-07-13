# HM2 Optimize HM1 — Round R1261

## 🔍 触发分析

- **cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit author**: opc2_uname (HM2)
- **HM1 git log**: 停留在 R1206 (55 轮落后)
- **判定**: 误触发, double-dispatch. R1260 已提交且 symlink 已更新.

## 📊 数据收集 (改前必有数据)

### 6h 总体 (2026-07-13 ~12:00 → 18:00 UTC)

| 指标 | 数值 |
|------|------|
| 总请求 | 59 |
| 成功 (200) | 45 |
| 失败 | 14 |
| 成功率 | **76.3%** |

### 按模型

| 模型 | 请求 | 成功 | 失败 | SR | 平均延迟 |
|------|------|------|------|------|------|
| glm5_2_nv | 58 | 44 | 14 | 75.9% | 15,739ms |
| dsv4p_nv | 1 | 1 | 0 | 100% | 45,950ms |

### 按 upstream

| upstream | 请求 | 成功 | 失败 | 平均TTFB | 平均延迟 |
|----------|------|------|------|----------|---------|
| nv_integrate | 52 | 41 | 11 | 14,696ms | 16,207ms |
| nvcf_pexec | 4 | 4 | 0 | 24,938ms | 24,939ms |
| (empty) | 3 | 0 | 3 | 767ms | 5,449ms |

### 错误分类

| 错误类型 | 数量 | 分析 |
|----------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv integrate, NVCF content-filter stop+12chars, 168,886 avg input, 15,494ms avg dur |
| all_tiers_exhausted | 3 | glm5_2_nv, avg 5,449ms, 1.0 avg tiers, 快速 ATE, 单tier 无 fallback |
| NVStream_IncompleteRead | 1 | 代码级流中断 |

### 每小时 SR

| 小时 | 总请求 | 成功 | 失败 | SR |
|------|--------|------|------|------|
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |
| 15:00 | 6 | 4 | 2 | 66.7% |
| 16:00 | 6 | 4 | 2 | 66.7% |
| 17:00 | 6 | 4 | 2 | 66.7% |

### 容器状态

- **nv_gw**: Up 3 hours (healthy)
- **compose md5**: 6e23559de1376d2d638f98f34a544139 (unchanged)
- **FALLBACK_GRAPH**: {} (no fallback, 3model — R832 预期)
- **0 tier_attempts** (无 key 级失败)
- **0 fallback_occurred** (无 fallback 触发)
- **ms_gw**: MS-STREAM-DONE 正常, 5 req in 6h, 全部成功

### nv_gw 日志关键信号

- `[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]`: 12× zombie (last 200 lines), content_chars=12, input_chars 177K-182K, 全部 content_filter 触发
- `[NV-REQ]` tier_chain=['glm5_2_nv'] (no fallback, 3model) — 正常
- 无 `[NV-TIER-FAIL]`, `[NV-ALL-TIERS-FAIL]`, `[NV-MS-FB]`, `[NV-PEER-FB]`
- 无 `[NV-GLOBAL-COOLDOWN]`

### 当前参数 (全部 floor/optimal)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=210
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=200
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_FORCE_STREAM_UPGRADE=0
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
```

## 🧠 决策分析

**NOP — 零参数, 零 compose 改动, 零容器重启.**

所有 14 个失败均为 code-level，不可配置修复:

1. **10× zombie_empty_completion**: glm5_2_nv integrate, NVCF content_filter stop (finish_reason=stop, content_chars=12 < 50, input_chars 168K avg). 网关正确检测并 abort (5-15s). NVCF 上游内容过滤行为，非配置可修复 (R1107 discovery).
2. **3× all_tiers_exhausted**: glm5_2_nv, 单tier, 3,849-7,276ms, 快速 ATE. NVCF 404/non-cycle 快速失败，非配置可修复 (R1241 discovery).
3. **1× NVStream_IncompleteRead**: 流中断，code-level defect.

全部参数处于 floor/optimal:
- FASTBREAK 全部=1 (pexec/integrate), EMPTY_200=2 (R1031 key-specific)
- TIER_COOLDOWN_S=15 (R1103, 已从18回退)
- BUDGET=210 充足 (R1088/R1231)
- NVU_PEER_FB_SKIP_MODELS="" (R1000, 全部模型可peer-fallback)
- UPSTREAM_TIMEOUT=66 (floor)
- ms_gw MS-STREAM-DONE 正常, 无优化空间

**本轮: 零参数, 零 compose 改动, 零容器重启**

## ⏳ 轮到HM1优化HM2
