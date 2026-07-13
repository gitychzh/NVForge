# HM2 Optimize HM1 — Round R1260

## 📊 数据收集 (改前必有数据)

### 6h 窗口 (2026-07-13 ~14:34 UTC → 2026-07-14 ~01:20 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 60 |
| 成功 | 46 |
| 失败 | 14 |
| 成功率 | **76.7%** |

### 按模型分布

| 模型 | 总请求 | 成功 | 失败 | 平均延迟 |
|------|--------|------|------|---------|
| glm5_2_nv | 59 | 45 | 14 | 15,816ms |
| dsv4p_nv | 1 | 1 | 0 | 45,950ms |

### 错误分类

| 错误类型 | 数量 | 说明 |
|----------|------|------|
| zombie_empty_completion | 10 | NVCF content_filter stop, 12 chars, 124K-180K input |
| all_tiers_exhausted | 3 | 单tier, fallback_actually_attempted=false, 3845-7524ms |
| NVStream_IncompleteRead | 1 | 流不完整 |

### ATE 详情

- 14 ATE, 全部 single-tier (tiers_tried_count=1)
- 全部 fallback_actually_attempted=false
- 全部 glm5_2_nv integrate
- nv_tier_attempts: **0 rows** (无key级失败记录)
- 无 fallback 触发
- 无 peer-fallback 触发

### NV_GW 日志关键信号

- `[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]`: 10× zombie, content_chars=12, input_chars 124K-180K, 全部 content_filter 触发
- 无 `[NV-TIER-FAIL]`, `[NV-ALL-TIERS-FAIL]`, `[NV-MS-FB]`, `[NV-PEER-FB]` 日志
- 无 `[NV-GLOBAL-COOLDOWN]` 日志
- 容器重启: 2026-07-13T14:33:57Z (~10.5h ago)

### ms_gw 状态

- `MS-OK-STREAM` + `MS-STREAM-DONE`: 正常运行
- 偶发 `MS-STREAM-CLIENT-EOF` BrokenPipeError (code-level streaming sync defect)
- dsv4p_ms (DeepSeek-V4-Pro) 也正常响应

### 当前参数 (全部 floor/optimal)

| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 210 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 |
| TIER_COOLDOWN_S | 15 |
| NVU_PEER_FB_SKIP_MODELS | "" (空) |
| compose md5 | 6e23559de1376d2d638f98f34a544139 |

## 🔍 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`

- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — **误触发 (double-dispatch)**
- 最新 commit: R1259 (HM2→HM1 NOP), 内容与 R1255-R1258 完全一致

## 🧠 决策分析

**NOP — 零参数变更。**

所有 14 个失败均为 code-level 不可配置修复:

1. **10× zombie_empty_completion**: glm5_2_nv integrate, NVCF content_filter stop (finish_reason=stop, content_chars=12 < 50, input_chars 124K-180K). 网关正确检测并 abort (3-37s). 这是 NVCF 上游内容过滤行为，非配置可修复 (R1107 discovery).
2. **3× all_tiers_exhausted**: glm5_2_nv, 单tier, 3845-7524ms, error_subcategory=all_tiers_failed_in_mapped_tier. 极短延迟 + 无 fallback 尝试 → NVCF 404/non-cycle 快速失败，非配置可修复 (R1241 discovery).
3. **1× NVStream_IncompleteRead**: 流中断，code-level defect.

全部参数已处于 floor/optimal 状态:
- FASTBREAK 全部=1 (pexec/integrate), EMPTY_200=2 (R1031 key-specific)
- TIER_COOLDOWN_S=15 (R1103, 已从18回退)
- BUDGET=210 充足 (R1088/R1231)
- NVU_PEER_FB_SKIP_MODELS="" (R1000, 全部模型可peer-fallback)
- 无 ms_gw 优化空间 (MS-STREAM-DONE正常, BrokenPipeError code-level)

**零参数变更; 铁律: 只改HM1不改HM2.**

## ⏳ 轮到HM1优化HM2
