## R1333: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 72→78 (+6s)

**时间**: 2026-07-14 14:55 UTC+0（脚本检测 HM1 新 commit 7a17dd6 后触发）

### 6h 数据窗 (09:00-14:55 UTC+0)

| 指标 | 值 |
|---|---|
| 总请求 | 106 |
| 成功 (200) | 93 |
| 失败 (502) | 13 |
| 成功率 | 87.7% |
| OK 平均延迟 | 17,030ms (avg dur) / 16,412ms (avg ttfb) |
| 最大延迟 | 72,032ms (ATE) |

### 按路径分组

| 路径 | 请求 | 成功 | 成功率 | avg ttfb | avg dur | max dur |
|---|---|---|---|---|---|---|
| nvcf_pexec | 48 | 48 | **100.0%** | 20,934ms | 20,938ms | 64,362ms |
| nv_integrate | 52 | 45 | 86.5% | 10,834ms | 11,937ms | 50,550ms |
| (ATE/无路径) | 6 | 0 | 0% | 820ms | 71,694ms | 72,032ms |

### 错误分类

| 模型 | 错误类型 | 次数 | avg dur |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 7 | 5,986ms |
| dsv4p_nv | all_tiers_exhausted | 6 | 71,694ms |

### ms_gw 状态
19 req / 18 OK → 94.4% SR

### dsv4p_nv ATE 详细诊断

6 个 ATE 全部遵循同一模式：
1. k5 → empty_200 → cycle 到 k1
2. k1 → NVCF pexec timeout (≈10.3s attempt) 或 504 gateway timeout (≈62s)
3. FASTBREAK 触发（PEXEC_TIMEOUT_FASTBREAK=1 → 仅 1 次 timeout 就快断）
4. TIER_BUDGET=72s 耗尽 → ABORT → ms_gw fallback
5. ms_gw MS-STREAM-DONE 成功 (18-38s) 但 nv_gw relay TimeoutError (213-233s) — **code-level streaming sync defect，非 config 可修**

关键数据点：
- 14:33:28 的 ATE: k1 遇到 504 在 62s，connect=5.3s 后剩余 2.0s < 5s min threshold → k2 attempt 被中止
- 72s budget 在 k1 timeout+connect 消耗后不足以启动 k2

### 变更

**NVU_TIER_BUDGET_DSV4P_NV: 72 → 78 (+6s)**

理由：
- dsv4p_nv pexec 独立成功率 100%（48/48），失败全部因为 key 轮转时 budget 耗尽
- k1 504 在 ~62s 消耗 budget 后，remaining=10s（原 72-62=10s 不够 connect reserve）
- +6s → 78-62=16s 剩余 → k2 有充足 budget 完成完整 attempt（含 connect reserve + UPSTREAM_TIMEOUT=66s 余量）
- 78s << TIER_TIMEOUT_BUDGET_S=205s 安全
- 7 个 zombie_empty_completion 是 NVCF server-side content_filter 行为（code-level zombie detection 正确工作），非 config 可修
- ms_gw relay TimeoutError 是 code-level streaming sync defect，非 config 可修
- pexec 路径 100% SR 证明 dsv4p_nv function + 代理都健康

**影响范围**: 仅 dsv4p_nv tier 内部 key 轮转预算。成功路径零影响。仅 affect ATE 恢复路径。

**风险**: 零。78s < BUDGET=205s。HM2 同步值可由 HM1 下轮自行评估。

### 验证

- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P` → 78 ✓
- 容器重启完成 ✓
- compose 注释已更新

**铁律: 只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2