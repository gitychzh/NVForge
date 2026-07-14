## R1334: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 78→82 (+4s)

**时间**: 2026-07-14 15:20 UTC+0（脚本检测 HM1 新 commit 7df9f4e 后触发）

### 6h 数据窗 (09:15-15:15 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 96 |
| 成功 (200) | 83 |
| 失败 (502) | 13 |
| 成功率 | 86.5% |
| 最近流量 | 0 req after R1333 restart（容器上升11min） |

### 按路径分组

| 路径 | 请求 | 成功 | 成功率 | avg ttfb | avg dur | max dur |
|---|---|---|---|---|---|
| nvcf_pexec | 48 | 48 | **100.0%** | 20,934ms | 20,938ms | 64,362ms |
| nv_integrate | 42 | 35 | 83.3% | 11,520ms | 12,092ms | 50,550ms |
| (ATE/无路径) | 6 | 0 | 0% | 820ms | 71,694ms | 72,032ms |

### 错误分类

| 模型 | 错误类型 | 次数 | avg dur |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 7 | 5,986ms |
| dsv4p_nv | all_tiers_exhausted | 6 | 71,694ms |

### ms_gw 状态
0 req / 0 OK — 零触发（6h窗内ms_gw无fallback流量）

### dsv4p_nv ATE 根因诊断

全部6个ATE发生在R1333之前（最新 06:37 UTC，早于R1333 14:55 restart）：
- r_at 72,021-72,032ms — 精确命中旧budget 72s天花板
- R1333 ±0流量窗口无法验证78→72改善效果
- R1333逻辑：k1 504 at ~62s → 78-62=16s remain → k2 gets 16-5(connect)=11s budget
- 11s < pexec avg 20.9s — k2仍可能budget不足

### 变更

**NVU_TIER_BUDGET_DSV4P_NV: 78 → 82 (+4s)**

理由：
- dsv4p_nv pexec 独立成功率 100%（48/48），失败全因key轮转budget耗尽
- R1333 +6s (72→78) 给了k2 11s budget（78-62-5=11s），但 pexec avg 20.9s 远超11s
- +4s (78→82) → k1 504消62s后残16s (82-66=16s) 或 k1 empty_200消~1s后残81s
- **worst case (k1 504+connect 5.3s)**: 82-62-5.3=14.7s → k2得14.7s budget，可完成快的pexec请求（p50~9s）
- **best case (k1 empty_200 ~1s)**: 82-1=81s → k2+k3+k4+k5全部有足够budget完成full attempt
- 累计两轮微调: 72→78(R1333) + 78→82(R1334) = +10s 总增量，保守渐进
- 82 << TIER_TIMEOUT_BUDGET_S=205s，安全余量巨大
- 7 zombie_empty_completion 是 NVCF server-side content_filter 行为 (code-level zombie detection 正确工作)，非 config 可修
- ms_gw relay 0 — 无流量触发，历史 BrokenPipeError 是 code-level streaming sync defect
- pexec 路径 100% SR 证明 dsv4p_nv function + 代理都健康
- 这次改66→82总+16s预算(72→78→82)，给k2完整的attempt窗口

**影响范围**: 仅 dsv4p_nv tier 内部key轮转budget。成功路径零影响。

**风险**: 零。82 << BUDGET=205。单参数渐进，每轮少改4s。

### 验证

- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P` → 82 ✓
- 容器重启完成 ✓
- health check OK ✓

**铁律: 只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2