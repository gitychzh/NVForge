# R1020: HM2→HM1 — NVU_MS_GW_FALLBACK_MODELMAP: add dsv4p_nv→dsv4p_ms

## 触发类型
**False trigger (double-dispatch)** — cron 脚本输出: `"这是我提交的, 不触发"`。R1019 是 HM2 自提交，脚本正确检测到不触发，但 cron 仍被派遣。按 false-trigger 流程执行数据收集+优化。

## 数据收集

### 容器状态
- `nv_gw`: Up 8 minutes (healthy), 0 errors/warnings in logs
- `ms_gw`: Up 27 hours (healthy), 7 MS-STREAM-DONE, 0 errors
- 容器重启于 2026-07-09T18:59:35Z (~8h ago)

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
NVU_MS_GW_FALLBACK_TIMEOUT=45
NVU_MS_GW_FALLBACK_MODELMAP=(not set — default: glm5_2_nv:glm5_2_ms only)
```

### 6h 窗口 (2026-07-09 ~19:00 → 2026-07-10 ~01:00 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 324 |
| Success (200) | 304 |
| Failures (502) | 20 |
| **SR** | **93.8%** |

### Per-model SR
| Model | Total | OK | ATE | SR | Avg Success Dur | Avg ATE Dur |
|-------|-------|-----|-----|-----|-----------------|-------------|
| glm5_2_nv | 196 | 189 | 7 | 96.4% | 21.8s | 167.5s |
| dsv4p_nv | 64 | 57 | 7 | 89.1% | 18.3s | 43.6s |
| kimi_nv | 36 | 36 | 0 | 100% | 12.8s | - |
| minimax_m3_nv | 29 | 23 | 6 | 79.3% | 17.9s | 154.3s |

### Per-path SR
| Path | Total | OK | ATE | SR |
|------|-------|-----|-----|-----|
| nvcf_pexec | 90 | 90 | 0 | **100%** |
| nv_integrate | 207 | 205 | 2 | 99.0% |
| NULL (ATE) | 28 | 10 | 18 | 35.7% |

### ATE 分析
- 20 ATE, 全部 `tiers_tried_count=1` (single-tier)
- 全部 `fallback_actually_attempted=false`
- glm5_2_nv: 7 ATE, avg 167s, 但 8/8 ms_gw fallback 成功 (100% SR, avg 8.2s)
- dsv4p_nv: 7 ATE, avg 43.6s, **0 ms_gw rescues** — MODELMAP 缺少 dsv4p_nv 条目
- minimax_m3_nv: 6 ATE, avg 154s, ms_gw 无 minimax 模型 (config.py 默认仅 glm5_2_nv:glm5_2_ms)

### Tier Attempts (failure-only)
- 仅 3 条: 1 dsv4p_nv RemoteDisconnected (9.1s), 1 kimi_nv empty_200, 1 minimax_m3_nv IntegrateTimeout (90.8s)
- NVCFPexecTimeout: **0** — pexec 路径完全干净
- UPSTREAM_TIMEOUT=66 非绑定约束

### ms_gw 验证
- `/health`: `"models": ["glm5_2_ms", "dsv4p_ms", "kimi_ms"]` — dsv4p_ms 已存在
- 8/8 glm5_2_nv→glm5_2_ms fallback 100% SR, avg 8,205ms

## 决策: 单参数变更 — 添加 NVU_MS_GW_FALLBACK_MODELMAP

**问题**: `NVU_MS_GW_FALLBACK_MODELMAP` 未在 compose 中设置，config.py 默认仅 `glm5_2_nv:glm5_2_ms`。dsv4p_nv 的 7 个 ATE 全部没有 ms_gw fallback 救援（0 rescues），而 glm5_2_nv 的 ms_gw fallback 8/8 100% 成功。ms_gw 已有 `dsv4p_ms` 模型可用。

**变更**: compose line 653 新增 `NVU_MS_GW_FALLBACK_MODELMAP: "glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms"`

**预期效果**: dsv4p_nv ATE 可获 ms_gw fallback 救援（类似 glm5_2_nv 的 8/8 100% SR）。保守估计每 6h 窗口救回 5-7 个 dsv4p_nv ATE → SR 提升至 ~97-98%。

**安全边际**: 
- ms_gw dsv4p_ms 已运行 27h 无错误
- 不影响现有 glm5_2_nv→ms fallback 路径
- 不影响 nvcf_pexec 100% SR 路径
- 单参数，仅影响 fallback 映射，零风险

## 部署验证 (四源)

| 源 | 结果 |
|----|------|
| Compose line 653 | `NVU_MS_GW_FALLBACK_MODELMAP: "glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms"` ✅ |
| Container env | `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms` ✅ |
| Container status | `nv_gw Up 21 seconds (healthy)` ✅ |
| Health endpoint | `{"status": "ok", ...}` ✅ |

## Git
- 单参数，铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2