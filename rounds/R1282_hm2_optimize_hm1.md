# HM2 Optimize HM1 — Round R1282

> **触发类型**: FALSE TRIGGER (double-dispatch)
> **cron 脚本输出**: "这是我提交的, 不触发"
> **最新 commit author**: opc2_uname (HM2)
> **HM1 git log**: R1206 (76 rounds behind, no new commit from HM1)
> **铁律**: 只改HM1不改HM2

## 1. 触发分析
- cron 脚本输出: "这是我提交的, 不触发" — 正确检测到自提交
- GitHub 最新 commit: 59c8f39 (R1281, author=opc2_uname)
- HM1 本地 git log 停留在 R1206（76 轮落后），未提交任何新内容
- 脚本正确标记 "不触发" 但 cron 仍被派遣 — double-dispatch (R1280→R1281→R1282 连续 3 轮 false trigger)
- R1281 symlink 已正确指向 rounds/R1281_hm2_optimize_hm1.md

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体统计
```
 total | ok | fail | sr_pct
-------+----+------+--------
    66 | 51 |   15 |   77.3
```
**SR = 77.3%**（与 R1281/R1280/R1279 完全一致）

### 2.2 错误分类 (6h)
| error_type               | cnt | avg_dur |
|---------------------------|-----|---------|
| zombie_empty_completion   |  12 |   9,108 |
| all_tiers_exhausted       |   3 |  72,019 |

- **12 zombie**: glm5_2_nv integrate, NVCF content-filter stop+12chars, avg input_chars=195K, output_tokens=6-12. Code-level detection working correctly (NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK in logs)
- **3 ATE**: dsv4p_nv, pre-R1275 MODELMAP fix, all pre-restart (R1275 deployed by HM1)
- **0 tier_attempts** — no downstream NVCF errors

### 2.3 按路径分组 (6h)
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|----------|---------|---------|
| nv_integrate  |  53 | 41 |    9,165 |   9,530 |  44,489 |
| nvcf_pexec    |  10 | 10 |   25,848 |  25,873 |  54,918 |
| (NULL)        |   3 |  0 |      881 |  72,019 |  72,023 |

- dsv4p_nv: 10/10 100% SR (pexec), avg ~25.9s (thinking requests)
- glm5_2_nv: 41/53 77.4% SR (integrate), 12 zombie
- 3 ATE = pre-R1275 server-side all_tiers_exhausted

### 2.4 按模型分组 (6h)
| mapped_model | cnt | ok | fail |  sr_pct | avg_dur | max_dur |
|--------------|-----|----|------|---------|---------|---------|
| glm5_2_nv    |  53 | 41 |   12 |    77.4 |   9,530 |  44,489 |
| dsv4p_nv     |  13 | 10 |    3 |    76.9 |  36,522 |  72,023 |

### 2.5 小时趋势 (6h)
| hour UTC | total | ok | fail | sr_pct |
|----------|-------|----|------|--------|
| 15:00 | 3 | 2 | 1 | 66.7 |
| 16:00 | 6 | 4 | 2 | 66.7 |
| 17:00 | 6 | 4 | 2 | 66.7 |
| 18:00 | 36 | 31 | 5 | 86.1 |
| 19:00 | 6 | 4 | 2 | 66.7 |
| 20:00 | 6 | 4 | 2 | 66.7 |
| 21:00 | 3 | 2 | 1 | 66.7 |

### 2.6 最近 10 条请求
| ts | model | status | dur_ms | error_type | upstream | input_chars | out_tokens |
|----|-------|--------|--------|------------|----------|-------------|------------|
| 21:03:32 | glm5_2_nv | 502 | 5,366 | zombie_empty_completion | integrate | 213,750 | 6 |
| 21:03:26 | glm5_2_nv | 200 | 5,533 | — | integrate | 213,095 | 123 |
| 21:03:21 | glm5_2_nv | 200 | 4,262 | — | integrate | 212,376 | 31 |
| 20:33:37 | glm5_2_nv | 502 | 4,821 | zombie_empty_completion | integrate | 212,319 | 6 |
| 20:33:30 | glm5_2_nv | 200 | 6,220 | — | integrate | 211,561 | 134 |
| 20:33:21 | glm5_2_nv | 200 | 8,292 | — | integrate | 210,842 | 31 |
| 20:03:33 | glm5_2_nv | 502 | 4,614 | zombie_empty_completion | integrate | 210,725 | 6 |
| 20:03:27 | glm5_2_nv | 200 | 6,292 | — | integrate | 209,997 | 134 |
| 20:03:21 | glm5_2_nv | 200 | 4,894 | — | integrate | 209,278 | 31 |
| 19:33:33 | glm5_2_nv | 502 | 5,580 | zombie_empty_completion | integrate | 209,185 | 6 |

**Pattern**: 每 3 请求→1 zombie (~195K input chars, NVCF content-filter 6-token response), 2 success (31/123/134 tokens)

### 2.7 容器日志 (最近 100 行 grep error/warn/zombie)
- 零 ERROR/WARN
- 6× NV-INTEGRATE-SUCCESS (first-attempt, k1-k5 cycling)
- 4× NV-ZOMBIE-EMPTY: glm5_2_nv content_chars=12 < 50, input_chars=212K+/213K+ ≥ 5000
- NV-ZOMBIE-ERROR-CHUNK: sent to openclaw → fallback trigger
- 0× NVCFPexecTimeout, 0× SSLEOF, 0× 429, 0× empty_200, 0× NV-TIER-FAIL
- 0× NV-PEXEC-SUCCESS in tail (no dsv4p_nv traffic recently)

### 2.8 当前容器配置 (nv_gw env)
```
UPSTREAM_TIMEOUT=66          (floor, R988)
TIER_TIMEOUT_BUDGET_S=210    (R1088, aligned)
TIER_COOLDOWN_S=15           (R1103, floor)
KEY_COOLDOWN_S=25            (floor)
KEY_AUTHFAIL_COOLDOWN_S=60   (R922, defensive)
NVU_TIER_BUDGET_DSV4P_NV=72  (R1116)
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
NVU_EMPTY_200_FASTBREAK=2    (R1039, code-level no-op)
NVU_PEER_FB_SKIP_MODELS=""   (R1000, peer-fallback enabled)
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
MIN_OUTBOUND_INTERVAL_S=0    (floor)
NVU_CONNECT_RESERVE_S=0      (floor)
NVU_FORCE_STREAM_UPGRADE=0   (floor)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_MS_GW_FALLBACK_TIMEOUT=200
NVU_PEER_FALLBACK_TIMEOUT=66
```
Container StartedAt: 2026-07-13T20:23:46Z (R1265 deploy, 无新重启)

### 2.9 ms_gw 信号
- ms_requests 6h: 4 total, 0 ok — ms_gw log-only mode, not actively serving

## 3. 决策

### 3.1 False trigger 确认
- ✅ cron 脚本输出: "这是我提交的, 不触发"
- ✅ 最新 commit author = opc2_uname (HM2)
- ✅ HM1 git log 停留在 R1206（76 轮落后），无新提交
- ✅ 数据与 R1281/R1280/R1279 完全一致（66req/51OK/15fail = 77.3% SR）
- ✅ R1281 已处理相同 trigger → double-dispatch

### 3.2 优化机会评估
- **zombie_empty_completion**: 12/15 failures — code-level (NVCF content-filter), NOT config-fixable. Gateway detection+error-chunk correct. Pattern: NVCF returns stop+content_filter on ~195K input char requests, giving 6-12 token response. Detection: content_chars<50, input_chars≥5000 → zombie classification → error-chunk to openclaw → fallback to ms_gw.
- **3 ATE**: pre-R1275 MODELMAP fix, 零 post-restart ATE. R1275 expected to resolve.
- **dsv4p_nv**: 10/10 100% SR pexec, 0 issues
- **All params at floor/optimal**: zero config optimization space
- **0 tier_attempts**: no downstream NVCF errors to tune against
- **ms_gw**: 0 traffic (log-only mode)
- **No secondary optimization opportunity** → **NOP**

### 3.3 候选参数评估
| 参数 | 当前值 | 候选 | 评估 | 决策 |
|------|--------|------|------|------|
| UPSTREAM_TIMEOUT | 66 | 64(-2s) | floor已达; max_ok=54,918ms margin 11s; 但 0 pexec post-deploy 无数据 | ❌ 无数据 |
| TIER_TIMEOUT_BUDGET_S | 210 | 200(-10s) | max_ok=54,918ms << 210s; 但降低不影响 zombie 路径 | ❌ 无收益 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 40(-2s) | 提前断流让 fallback 更快; 但 zombie 已触发 fallback | ❌ 无收益 |
| TIER_COOLDOWN_S | 15 | 13(-2s) | 0 tier_attempts, 无多 tier 尝试 | ❌ 无收益 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | 70(-2s) | 0 dsv4p_nv pexec traffic recently | ❌ 无数据 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 94(-2s) | glm5_2 走 integrate 非 pexec, 此参数仅影响 pexec 路径 | ❌ 不适用 |
| NVU_EMPTY_200_FASTBREAK | 2 | 1(-1) | 1=floor; 0 empty_200 post-deploy | ❌ floor已达 |

### 3.4 结论
**NOP — 零参数变更, 零 compose 编辑, 零容器重启**
- 所有参数已处于 floor/optimal 状态
- 唯一失败类型 zombie_empty_completion 为 code-level (NVCF content-filter)，不可通过配置修复
- 3 ATE 为 pre-R1275 历史残留
- HM1 无需任何配置修改
- 连续 3 轮 false trigger (R1280→R1281→R1282)，HM1 侧无活动

## ⏳ 轮到HM1优化HM2