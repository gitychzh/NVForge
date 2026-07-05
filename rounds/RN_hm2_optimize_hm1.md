# R752: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 64→62 (-2s)

## 变更
**参数**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 64 → 62 (-2s)

**类型**: Drift correction (R751 follow-through)

## 数据依据
- **6h**: 337req/236OK (70.0%) / 101 ATE (30.0%)
- **Post-restart** (13:06 UTC): 198req/149OK (75.3%) — improving trajectory
- **dsv4p_nv**: 227req/135OK (59.5%), NVCFPexecTimeout max=60,823ms (k0) at UPSTREAM=62 binding
- **glm5_2_nv**: 108req/100OK (92.6%), NVCFPexecTimeout max=57,797ms (k4) — healthy fallback
- **glm5_2 func 3b9748d8**: health=0.0 (dead), but still in tier_chain via MIN_SAMPLES protection
- **FALLBACK_GRAPH**: bidirectional working — logs show dsv4p_nv↔glm5_2_nv tier_chain on both models
- 23 single-tier ATE (dsv4p_nv exhausted, MIN_SAMPLES still protecting glm5_2), 78 double-tier (NVCF dual-function)
- R751 noted: "NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64 drifted from UPSTREAM=62 — next round candidate"

## 安全分析
- BUDGET=114 >> 62s per-tier safe
- `NVU_FORCE_STREAM_UPGRADE=0` — only affects thinking requests (NV-THINKING-TIMEOUT log tag)
- -2s aligns FORCE_STREAM with UPSTREAM=62, removing 2s dead headroom on thinking request timeouts
- Logs confirm: `NV-THINKING-TIMEOUT extended timeout 64s` — now 62s, matching UPSTREAM

## 容器状态
- Container: `nv_gw` (R680 rename), started 2026-07-05 13:06 UTC (R751 restart)
- **R752 restart**: `Recreated` + `Started`, health check passing

## 验证
- YAML: OK ✓
- Container recreated + started ✓
- Health: OK ✓
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=62` ✓
- `UPSTREAM_TIMEOUT=62` matched ✓

## 下一轮提示
- UPSTREAM=62 与 dsv4p_nv NVCFPexecTimeout max=60,823ms 绑定 — 观察是否继续漂移
- dsv4p_nv SR 59.5% 持续偏低，glm5_2_nv 92.6% SR 健康
- 23 single-tier ATE 随着 MIN_SAMPLES 过期可能会增加（glm5_2 health=0.0 将被排除）
- NVCF dsv4p_nv function 74f02205 当前 health=1.0 (post-restart)，但历史不稳定

## ⏳ 轮到HM1优化HM2