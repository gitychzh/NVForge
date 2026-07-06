## R789 (HM2→HM1) — NOP — 95.5% SR, 双向fallback 100%, 全参数floor, 零单tier ATE

HM1上一次commit: d90552f (R788 NOP)。HM1本轮未提交新commit，检测脚本判定由HM2执行优化。但收集数据后进行NOP Gate全检查，所有6个Gate通过，零变更需求。

### 诊断数据

| 指标 | 值 |
|------|-----|
| 6h总请求 | 202 |
| 6h OK | 193 (95.5%) |
| 6h Fail | 9 (4.5%, 均为 `all_tiers_exhausted`) |

### 按模型 SR

| 模型 | 请求数 | OK | SR |
|------|--------|----|------|
| dsv4p_nv | 114 | 106 | 93.0% |
| glm5_2_nv | 86 | 85 | 98.8% |
| kimi_nv | 2 | 2 | 100.0% (peer fallback rescued) |

### 按路径

| 路径 | 请求数 | OK | avg TTFB | avg Dur | max Dur |
|------|--------|----|-----------|----------|---------|
| nvcf_pexec | 188 | 188 | 41,688ms | 41,706ms | 184,737ms |
| (ATE) | 14 | 5 | 9ms | 114,577ms | 228,616ms |

注：14条 `upstream_type=NULL` 中，5条为 peer-fallback 成功（status=200，kimi_nv×2 + dsv4p_nv×3），9条为HM1本地ATE（status=502）。

### ATE 分析

| tiers_tried_count | cnt | avg_dur |
|---|---|---|
| 2 | 9 | 175,392ms |

零单tier ATE。全部9个ATE均为 `all_tiers_exhausted`，`tiers_tried_count=2`，NVCF上游双tier真实耗尽，非配置可修复。

**注：** 另外3条 dsv4p_nv `all_tiers_exhausted`但status=200的记录：
- 均为 `tiers_tried_count=2`, `fallback_occurred=false`，duration 2,772~10,110ms
- 日志确认：本地双tier失败后 `[NV-PEER-FB]` 转发到HM2，peer fallback 成功 → 标记status=200
- 这3条 + 2条 kimi_nv peer-fallback = 5条被peer rescued

### Fallback 统计

| fallback_occurred | cnt | OK | SR |
|---|---|---|---|
| false | 160 | 151 | 94.4% |
| true | 42 | 42 | 100.0% |

Fallback 42/42全部成功 — fallback链路100%可靠。

### NVCFPexecTimeout（非绑定诊断）

| Tier | max(ms) | UPSTREAM | gap | 判定 |
|------|---------|----------|-----|------|
| dsv4p_nv | 53,194 | 66 | 12.8s | 非绑定 ✓ |
| glm5_2_nv | 51,597 | 66 | 14.4s | 非绑定 ✓ |

NVCFPexecTimeout 分布均匀跨key（dsv4p_nv: 8次跨4个key, glm5_2_nv: 3次跨2个key），非函数级集中。

### Tier Attempts 错误分类

| Tier | Error | 次数 |
|------|-------|------|
| dsv4p_nv | empty_200 | 23 |
| dsv4p_nv | 504_nv_gateway_timeout | 11 |
| dsv4p_nv | NVCFPexecTimeout | 8 |
| dsv4p_nv | 500_nv_error | 1 |
| dsv4p_nv | 429_nv_rate_limit | 1 |
| glm5_2_nv | 504_nv_gateway_timeout | 15 |
| glm5_2_nv | empty_200 | 12 |
| glm5_2_nv | NVCFPexecTimeout | 3 |

### 函数健康度（日志确认）

- dsv4p_nv (`74f02205`): 0.6→0.65 — 稳定健康
- glm5_2_nv (`3b9748d8`): 0.5→0.55→0.6 — 稳定回升
- kimi_nv (`f966661c`): 0.0 — NVCF函数死亡，单tier无fallback
- 双向fallback正常: `tier_chain=['dsv4p_nv', 'glm5_2_nv']` 和 `['glm5_2_nv', 'dsv4p_nv']` 均存在，动态fallback
- kimi_nv: `tier_chain=['kimi_nv'] (no fallback, 3model)` — NVCF函数 `f966661c` 健康度=0.0，无本地fallback，但 `[NV-PEER-FB]` 到HM2成功

### 逐小时 SR

| 小时 (UTC) | 请求 | OK | ATE | SR |
|-----------|------|-----|-----|------|
| 04:00 | 1 | 1 | 0 | 100.0% |
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
| 16:00 | 12 | 10 | 2 | 83.3% |
| 17:00 | 21 | 19 | 2 | 90.5% |
| 18:00 | 20 | 19 | 1 | 95.0% |

SR总体稳定。16:00-17:00的两波ATE（各2次）均为NVCF双tier耗尽，非配置修复。

### dsv4p_nv 成功请求 duration 分布

| Bucket | cnt | ok | 其中fallback |
|--------|-----|----|-------------|
| <5s | 6 | 6 | 0 |
| 5-10s | 5 | 5 | 0 |
| 10-20s | 12 | 12 | 0 |
| 20-30s | 9 | 9 | 0 |
| 30-40s | 11 | 11 | 0 |
| 40-50s | 11 | 11 | 0 |
| 50-60s | 16 | 16 | 0 |
| 60-70s | 3 | 3 | 2 |
| 70-90s | 14 | 14 | 9 |
| 90-120s | 10 | 10 | 7 |
| >120s | 17 | 9 | 9 |

50-60s bucket 16次100%直接成功，60-70s仅3次（2次fallback）。UPSTREAM=66 覆盖 50-60s 全部直接成功，安全边际充足。

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
| Gate 1 | 所有ATE tiers_tried_count=2 | ✓ 9/9 |
| Gate 2 | 零单tier ATE | ✓ 0 |
| Gate 3 | NVCFPexecTimeout buffer≥3s | ✓ dsv4p+12.8s, glm5_2+14.4s |
| Gate 4 | 双向fallback | ✓ 两方向均存在，动态fallback正常 |
| Gate 5 | Fallback SR=100% | ✓ 42/42 |
| Gate 6 | 所有参数floor | ✓ |
| Bonus | 函数健康度稳定 | ✓ dsv4p 0.6-0.65, glm5_2 0.5-0.6 |

### kimi_nv 说明

kimi_nv函数 `f966661c` 在HM1上健康度=0.0，导致 `tier_chain=['kimi_nv'] (no fallback, 3model)`。但本地失败后 `[NV-PEER-FB]` 转发到HM2成功（2/2）。这不是config问题——NVCF函数死亡是上游问题。HM2上的kimi_nv可能有不同的函数ID或更健康的NVCF实例。

### 决策：NOP（零变更）

**不调整任何参数，不重启容器。**

理由：
1. SR 95.5%，系统健康稳定
2. 零单tier ATE — 全部9个ATE均为NVCF双tier真实耗尽
3. NVCFPexecTimeout双函数非绑定（gap均≥12.8s），UPSTREAM不变
4. FASTBREAK=1已最优：429仅1次（dsv4p_nv），不足以构成调整触发
5. 50-60s bucket 16次100%直接成功，UPSTREAM=66覆盖充足
6. Fallback链路100%可靠（42/42），双向fallback正常
7. 所有参数已在floor最优值，无进一步下调空间
8. dsv4p_nv健康度稳定（0.6-0.65），glm5_2_nv健康度稳定（0.5-0.6）

## ⏳ 轮到HM1优化HM2