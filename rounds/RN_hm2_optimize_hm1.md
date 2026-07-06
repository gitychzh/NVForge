## R788 (HM2→HM1) — NOP — 97.8% SR, 双向fallback 100%, 全参数floor, 零单tier ATE

### 诊断数据

| 指标 | 值 |
|------|-----|
| 6h总请求 | 184 |
| 6h OK | 180 (97.8%) |
| 6h Fail | 4 (2.2%, 均为ATE) |

### 按路径

| 路径 | 请求数 | OK | avg TTFB | avg Dur | max Dur |
|------|--------|----|-----------|----------|---------|
| nvcf_pexec | 180 | 180 | 33,740ms | 33,754ms | 159,885ms |
| (ATE) | 4 | 0 | — | 148,860ms | 175,499ms |

### ATE 分析

| tiers_tried_count | cnt | avg_dur |
|---|---|---|
| 2 | 4 | 148,860ms |

零单tier ATE。全部4个ATE均为 `all_tiers_exhausted`，`tiers_tried_count=2`，NVCF上游双tier真实耗尽，非配置可修复。

### Fallback 统计

| fallback_occurred | cnt | OK | SR |
|---|---|---|---|
| false | 153 | 149 | 97.4% |
| true | 31 | 31 | 100.0% |

Fallback 31/31全部成功 — fallback链路100%可靠。

### NVCFPexecTimeout（非绑定诊断）

| Tier | max(ms) | UPSTREAM | gap | 判定 |
|------|---------|----------|-----|------|
| dsv4p_nv | 53,194 | 66 | 12.8s | 非绑定 ✓ |
| glm5_2_nv | 51,597 | 66 | 14.4s | 非绑定 ✓ |

### Tier Attempts 错误分类

| Tier | Error | ���数 |
|------|-------|------|
| dsv4p_nv | empty_200 | 24 |
| dsv4p_nv | 429_nv_rate_limit | 6 |
| dsv4p_nv | NVCFPexecTimeout | 2 |
| glm5_2_nv | 504_nv_gateway_timeout | 11 |
| glm5_2_nv | empty_200 | 9 |
| glm5_2_nv | NVCFPexecTimeout | 3 |

### 函数健康度（日志，最近100行）

- dsv4p_nv: 0.7→0.75→0.8→0.85→0.9（持续回升中）
- glm5_2_nv: 0.579→0.6→0.65→0.7→0.75（持续回升中）
- 双向fallback正常: `tier_chain=['dsv4p_nv', 'glm5_2_nv']` 和 `['glm5_2_nv', 'dsv4p_nv']` 均存在
- 日志确认 fallback 成功: `[NV-FALLBACK] ... → [NV-FALLBACK-SUCCESS]`

### 逐小时 SR

| 小时 (UTC) | 请求 | OK | ATE | SR |
|-----------|------|-----|-----|------|
| 02:00 | 1 | 1 | 0 | 100.0% |
| 03:00 | 6 | 6 | 0 | 100.0% |
| 04:00 | 18 | 18 | 0 | 100.0% |
| 05:00 | 8 | 8 | 0 | 100.0% |
| 06:00 | 5 | 5 | 0 | 100.0% |
| 07:00 | 11 | 11 | 0 | 100.0% |
| 08:00 | 17 | 17 | 0 | 100.0% |
| 09:00 | 11 | 11 | 0 | 100.0% |
| 10:00 | 20 | 18 | 2 | 90.0% |
| 11:00 | 11 | 11 | 0 | 100.0% |
| 12:00 | 21 | 20 | 1 | 95.2% |
| 13:00 | 17 | 16 | 1 | 94.1% |
| 14:00 | 14 | 14 | 0 | 100.0% |
| 15:00 | 13 | 13 | 0 | 100.0% |
| 16:00 | 10 | 10 | 0 | 100.0% |

8小时连续100% SR（02:00-09:00），10:00/12:00/13:00出现零星ATE后恢复，14:00起重回100%。后段SR受前段NVCF函数死亡影响已完全恢复。

### 当前配置（全部floor值，无变更）

| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 1 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 (=UPSTREAM) |

### NOP Gate 全通过

| Gate | 条件 | 结果 |
|------|------|------|
| Gate 1 | 所有ATE tiers_tried_count=2 | ✓ 4/4 |
| Gate 2 | 零单tier ATE | ✓ 0 |
| Gate 3 | NVCFPexecTimeout buffer≥3s | ✓ dsv4p+12.8s, glm5_2+14.4s |
| Gate 4 | 双向fallback | ✓ 两方向均存在，动态fallback正常 |
| Gate 5 | Fallback SR=100% | ✓ 31/31 |
| Gate 6 | 所有参数floor | ✓ |
| Bonus | 函数健康度回升 | ✓ dsv4p 0.7→0.9, glm5_2 0.58→0.75 |

### 决策：NOP（零变更）

**不调整任何参数，不重启容器。**

理由：
1. SR 97.8%，系统稳定
2. 所有参数已在floor最优值，无进一步下调空间
3. NVCFPexecTimeout双函数非绑定（gap均>12s），UPSTREAM不变
4. FASTBREAK=1已最优：429仅6次（dsv4p_nv），不足以构成调整触发
5. 4个ATE均为NVCF上游双tier真实耗尽，不可配置修复
6. Fallback链路100%可靠（31/31），双向fallback正常
7. 双函数健康度持续回升，系统自行修复中

## ⏳ 轮到HM1优化HM2