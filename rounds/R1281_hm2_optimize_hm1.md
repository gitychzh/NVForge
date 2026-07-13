# HM2 Optimize HM1 — Round R1281

> **触发类型**: FALSE TRIGGER (double-dispatch)
> **cron 脚本输出**: "这是我提交的, 不触发"
> **最新 commit author**: opc2_uname (HM2)
> **HM1 git log**: R1206 (75 rounds behind, no new commit from HM1)
> **铁律**: 只改HM1不改HM2

## 1. 触发分析
- cron 脚本输出: "这是我提交的, 不触发" — 正确检测到自提交
- GitHub 最新 commit: f45829c (R1280, author=opc2_uname)
- HM1 本地 git log 停留在 R1206（75 轮落后），未提交任何新内容
- 脚本正确标记 "不触发" 但 cron 仍被派遣 — double-dispatch (R1280 已处理此 trigger)
- R1280 symlink 已正确指向 rounds/R1280_hm2_optimize_hm1.md，git clean

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体统计
```
 total | ok | fail
-------+----+------
    66 | 51 |   15
```
**SR = 77.3%**（与 R1280/R1279/R1278/R1277 完全一致）

### 2.2 错误分类 (6h)
| error_type               | cnt |
|---------------------------|-----|
| zombie_empty_completion   |  12 |
| all_tiers_exhausted       |   3 |

- **12 zombie**: glm5_2_nv integrate, NVCF content-filter stop+12-36chars, code-level detection working correctly (NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK in logs)
- **3 ATE**: pre-R1275 MODELMAP fix, all pre-restart (R1275 deployed by HM1 earlier)
- **0 tier_attempts** — no downstream NVCF errors

### 2.3 按路径分组 (6h)
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---------------|-----|----|----------|---------|
| nv_integrate  |  53 | 41 |    9,165 |   9,530 |
| nvcf_pexec    |  10 | 10 |   25,848 |  25,873 |
| (NULL)        |   3 |  0 |      881 |  72,019 |

- dsv4p_nv: 10/10 100% SR (pexec), avg ~25.9s (thinking requests)
- glm5_2_nv: 41/53 77.4% SR (integrate), 12 zombie
- 3 ATE = pre-R1275 server-side all_tiers_exhausted

### 2.4 容器日志 (最近 100 行 grep error/warn/zombie)
- 零 ERROR/WARN
- NV-INTEGRATE-SUCCESS: all first-attempt (k1-k5 cycling)
- NV-ZOMBIE-EMPTY: 2 occurrences (input_chars 212K-213K, content_chars=12, stop+content_filter)
- NV-ZOMBIE-ERROR-CHUNK: sent to openclaw → fallback trigger

### 2.5 当前容器配置 (nv_gw env)
```
UPSTREAM_TIMEOUT=66          (floor, R988)
TIER_TIMEOUT_BUDGET_S=210    (R1088, aligned)
TIER_COOLDOWN_S=15           (R1103, floor)
KEY_COOLDOWN_S=25            (floor)
KEY_AUTHFAIL_COOLDOWN_S=60   (R922, defensive)
NVU_TIER_BUDGET_DSV4P_NV=72  (R1116)
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_EMPTY_200_FASTBREAK=2    (R1039, code-level no-op)
NVU_PEER_FB_SKIP_MODELS=""   (R1000, peer-fallback enabled)
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
```

## 3. 决策

### 3.1 False trigger 确认
- ✅ cron 脚本输出: "这是我提交的, 不触发"
- ✅ 最新 commit author = opc2_uname (HM2)
- ✅ HM1 git log 停留在 R1206（75 轮落后），无新提交
- ✅ 数据与 R1280 完全一致（66req/51OK/15fail = 77.3% SR）
- ✅ R1280 已处理相同 trigger → double-dispatch

### 3.2 优化机会评估
- **zombie_empty_completion**: 12/15 failures — code-level (NVCF content-filter), NOT config-fixable. Gateway detection+error-chunk correct.
- **3 ATE**: pre-R1275 MODELMAP fix, 零 post-restart ATE. R1275 expected to resolve.
- **dsv4p_nv**: 10/10 100% SR, 0 issues
- **All params at floor/optimal**: zero config optimization space
- **0 tier_attempts**: no downstream NVCF errors to tune against
- **ms_gw**: 0 traffic (log-only mode)
- **No secondary optimization opportunity** → **NOP**

### 3.3 结论
**NOP — 零参数变更, 零 compose 编辑, 零容器重启**
- 所有参数已处于 floor/optimal 状态
- 唯一失败类型 zombie_empty_completion 为 code-level (NVCF content-filter)，不可通过配置修复
- 3 ATE 为 pre-R1275 历史残留
- HM1 无需任何配置修改

## ⏳ 轮到HM1优化HM2
