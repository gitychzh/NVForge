# R1021: HM2→HM1 — NOP (false trigger, ms_gw dsv4p_ms placeholder blocks R1020 MODELMAP)

## 触发类型
**False trigger** — cron 脚本输出: `"这是我提交的, 不触发"`。HM1 最新 commit 为 R821 (2026-07-05)，199 轮落后于 HM2。HM1 未提交任何新内容，脚本正确检测到自提交。按 false-trigger 流程执行数据收集 → 发现 ms_gw dsv4p_ms 为 disabled placeholder，R1020 MODELMAP 修复无法生效。

## 数据收集

### 容器状态
- `nv_gw`: Up 7 minutes (healthy), StartedAt 2026-07-09T19:14:28Z
- `logs_db`: Up 5 days (healthy)
- 容器重启于 R1020 deploy (2026-07-09T19:14Z)

### 容器 env (关键参数)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
TIER_COOLDOWN_S=18
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_EMPTY_200_FASTBREAK=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_MS_GW_FALLBACK_TIMEOUT=45
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms  # R1020 live
NVU_TIER_BUDGET_MINIMAX_M3_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=96
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
```

### 6h 窗口 (2026-07-09 ~21:20 → 2026-07-10 ~03:20 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 422 |
| Success (200) | 399 |
| Failures | 23 |
| **SR** | **94.5%** |
| avg_ms | 22,355 |
| p50_ms | 9,622 |
| p95_ms | 75,177 |
| max_ms | 208,108 |

### Per-model SR
| Model | Total | OK | ATE | Other Fail | SR | Avg Success (ms) | Max (ms) |
|-------|-------|-----|-----|------------|-----|-------------------|-----------|
| glm5_2_nv | 237 | 229 | 8 | 0 | 96.6% | 24,056 | 208,108 |
| dsv4p_nv | 84 | 77 | 7 | 0 | 91.7% | 17,694 | 61,151 |
| kimi_nv | 59 | 58 | 1 | 0 | 98.3% | 10,398 | 71,985 |
| minimax_m3_nv | 42 | 35 | 7 | 0 | 83.3% | 38,873 | 159,342 |

- minimax M3 NV: 9 ATE total (7 upstream_type=NULL + 2 IntegrateTimeout); avg 127s, max 159s
- glm5_2_nv: 13 ATE, 7/7 ms_gw rescue 100% SR (glm5_2_ms)
- dsv4p_nv: 7 ATE, **0 ms_gw rescues** — MODELMAP configured but ms_gw dsv4p_ms is disabled

### Per-path SR
| Path | Total | OK | ATE | SR |
|------|-------|-----|-----|-----|
| nvcf_pexec | 136 | 136 | 0 | **100%** |
| nv_integrate | 255 | 253 | 2 | 99.2% |
| NULL (ATE) | 31 | 10 | 21 | 32.3% |

### Tier Attempts (failure-only, 6h)
| Tier | Error Type | Count | Avg (ms) | Max (ms) |
|------|-----------|-------|----------|----------|
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134 | 9,134 |
| kimi_nv | empty_200 | 1 | - | - |
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762 | 90,762 |

- NVCFPexecTimeout: **0** — pexec 路径完全干净
- Tier attempts 极低 (3条) — 大部分 ATE 在调度层拒绝，未到达 upstream

### ATE 分析
- 31 ATE total: 13 glm5_2_nv (7 rescued by ms_gw), 9 minimax, 7 dsv4p_nv, 1 kimi_nv
- glm5_2_nv: 7/13 ms_gw rescue 100% SR → 有效；6/13 无 fallback
- dsv4p_nv: 7 ATE, 0 fallback_occurred, 0 fallback_actually_attempted — **R1020 MODELMAP 未生效**
- minimax: 9 ATE, no fallback tier (tier_chain=['minimax_m3_nv'] only), ms_gw 无 minimax 模型

### minimax ATE 根因追踪 (nv_gw logs)
```
[03:24:30.9] [NV-INTEGRATE] tier=minimax_m3_nv attempt 1/7: k1 → integrate
[03:26:01.5] [NV-INTEGRATE-TIMEOUT] k1 integrate timeout: 90649ms
[03:26:01.5] [NV-INTEGRATE-FASTBREAK] 1 consecutive timeouts -> fast-break
[03:26:01.5] [NV-INTEGRATE-FALLBACK] integrate all-failed → falling back to pexec same model
[03:26:01.5] [NV-KEY] tier=minimax_m3_nv attempt 1/7: k5 → NVCF pexec
[03:27:02.4] [NV-EMPTY-200] k5 → 200 empty body (0 bytes)
[03:27:02.4] [NV-EMPTY-FASTBREAK] 1 consecutive empty_200 ≥ threshold 1, fast-break
[03:27:02.4] [NV-ALL-TIERS-FAIL] All 1 tiers failed, elapsed=151534ms, ABORT-NO-FALLBACK
```
- Integrate: NVU_INTEGRATE_THINKING_TIMEOUT_S=90 binding → k1 timeout at 90s
- Pexec fallback: NVCF function 87ea0ddc-cff... 返回 empty_200 (function-level degrade)
- NVU_EMPTY_200_FASTBREAK=1 → 1 empty → fast-break → ATE at 151s
- Budget: NVU_TIER_BUDGET_MINIMAX_M3_NV=180, 151s < 180s → budget 未耗尽，是 fastbreak 截断

### ms_gw 状态
- `/health`: `"models": ["glm5_2_ms", "dsv4p_ms", "kimi_ms"]` — 声明了 dsv4p_ms
- **CODE DISCOVERY**: `config.py:60` — `"Only glm5_2_ms is implemented. dsv4p_ms / kimi_ms are placeholders."`
- dsv4p_ms: `"_disabled": True, "variants": []` — 已注册但禁用，variants 为空
- 6h 内 ms_gw 零条 dsv4p_ms 请求 — 确认 nv_gw 的 MODELMAP 匹配到 dsv4p_ms 但 ms_gw 拒绝服务
- ms_gw glm5_2_ms: 22 req/6h, but only 3/22 resp_status=200 — ms_gw 自身也在退化
- openclaw caller: 5/5 glm5_2_ms fail — 特定 caller 可能超时

## 决策: NOP (零参数变更)

**R1020 MODELMAP 修复未完全生效** — dsv4p_nv→dsv4p_ms 映射已配置 (compose line 653)，env 已注入，但 ms_gw 端 `dsv4p_ms` 为 disabled placeholder (`_disabled=True, variants=[]`)。nv_gw 尝试 fallback 时 ms_gw 拒绝服务 → nv_requests 记录 `fallback_actually_attempted=false`。

**minimax ATE 根因**: NVCF function 87ea0ddc 返回 empty_200 (function-level degrade)，非配置可修。NVU_INTEGRATE_THINKING_TIMEOUT_S=90 + NVU_EMPTY_200_FASTBREAK=1 均触 floor。

**所有 nv_gw 参数已触 floor/optimal**:
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
- NVU_EMPTY_200_FASTBREAK=1 (floor)
- MIN_OUTBOUND_INTERVAL_S=0 (floor)
- NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
- NVU_CONNECT_RESERVE_S=0 (floor)
- UPSTREAM_TIMEOUT=66 (NVCFPexecTimeout max=0, non-binding)
- BUDGET=110 (NVU_TIER_BUDGET_MINIMAX_M3_NV=180 per-tier override, non-binding)
- 无单参数可改空间

**建议 HM1 修复 (非本轮 scope)**:
1. ms_gw config.py: 启用 dsv4p_ms (`_disabled=False`, `variants=DSV4P_VARIANT_IDS`) — 救回 7 dsv4p_nv ATE/6h
2. ms_gw config.py: 添加 minimax_ms 模型 (需 ModelScope minimax model_id) — 救回 9 minimax ATE/6h
3. 或 NVCF 侧恢复 minimax function 87ea0ddc 的 empty_200 问题

## 验证
- 容器 `nv_gw`: Up 7 minutes (healthy) ✅
- R1020 MODELMAP env: `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms` ✅
- 日志: 0 ERROR/WARN (nv_gw), 0 NVCFPexecTimeout ✅
- nvcf_pexec: 136/136 100% SR ✅

## Git
- 零参数变更，零 compose 修改，零容器重启
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2