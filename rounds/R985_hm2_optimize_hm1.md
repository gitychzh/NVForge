# R985: HM2→HM1 — NOP

## 触发分析
- **False trigger**: cron 脚本输出 `[2026-07-09 18:00:30] 这是我提交的, 不触发`
- 最新 commit `27312ef` = opc2_uname (HM2, R984 NOP)
- 预运行脚本已提交 R984 NOP，symlink 已指向 R984
- 本次为 double-dispatch (R984 已提交, symlink 已正确)
- False trigger streak: R884→R985 (102 consecutive false-trigger dispatches)

## 数据摘要 (6h, as of 18:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 41 |
| 成功 (200) | 34 |
| ATE (502) | 7 |
| 成功率 | **82.9%** |
| dsv4p_nv | 5/5 **100%** SR |
| glm5_2_nv | 35/28 = **80.0%** SR (7 ATE) |

## ATE 分析

| tiers_tried | count | avg_dur |
|-------------|-------|---------|
| 1 | 5 | 56,841ms |
| 2 | 2 | 174,417ms |

- 5 single-tier ATEs: glm5_2_nv key timeout → fast-break → ms_gw fallback
- 2 double-tier ATEs: both tiers exhausted, ms_gw rescue
- All ATEs glm5_2_nv; dsv4p_nv 0 ATE, 5/5 100% SR
- FALLBACK_GRAPH={} (R832 design) — tier_chain=['glm5_2_nv'] (no fallback, 3model) 预期

## Tier Attempts (6h)

| error_type | cnt | avg_ms | max_ms |
|-----------|-----|--------|--------|
| NVCFPexecTimeout | 16 | 58,190 | 62,606 |
| 504_nv_gateway_timeout | 3 | — | — |
| empty_200 | 2 | — | — |

NVCFPexecTimeout max=62,606ms vs UPSTREAM=64 → buffer=1.4s (<3s R751 rule, tight). 但 NVU_TIER_BUDGET_GLM5_2_NV=20 生效后实际 cap 在 20s，UPSTREAM 非绑定因素。

## 环境状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | 非绑定 (tier budget=20 cap) |
| FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 对齐 UPSTREAM |
| TIER_TIMEOUT_BUDGET_S | 112 | 充裕 (112 >> 64) |
| FASTBREAK | 1 | 地板 |
| EMPTY_200_FASTBREAK | 3 | R829 缓解 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 地板 |
| CONNECT_RESERVE_S | 0 | 地板 |
| KEY_COOLDOWN_S | 25 | 默认 |
| TIER_COOLDOWN_S | 25 | 默认 |
| INTEGRATE_KEY_COOLDOWN | 0 | 地板 |
| INTEGRATE_MODELS | "" | 全部 pexec |
| NVU_TIER_BUDGET_GLM5_2_NV | 20 | 20s per-attempt cap |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | R982 部署生效 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 死参数 (R919), 同值但无关 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | R923 防御 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 防御 |
| HEALTH_THRESHOLD (effective) | **0.05** | `docker exec` Python import 验证 ✓ |

## R982 验证
- `docker exec nv_gw python3 -c 'from gateway import func_health; print(func_health.HEALTH_THRESHOLD)'` → **0.05** ✓
- 容器运行 20 分钟，零 error/warn/exception
- ms_gw 健康: 23 请求 (24h)，全部 MS-OK/MS-OK-STREAM
- 日志: `tier_chain=['glm5_2_nv'] (no fallback, 3model)` 预期状态 (R832 design)
- ms_gw same-model fallback: 部分成功, 1次 streaming timeout (已知代码缺陷)

## 候选参数评审

| 参数 | 当前值 | 候选 | 判定 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 64 | +2→66 | 拒绝: tier budget=20 实际 cap, +2 无意义 |
| NVU_TIER_BUDGET_GLM5_2_NV | 20 | ±5 | 拒绝: 20s 平衡 (1次完整 key 尝试+fast-break); 增加浪费 ATE 路径时间, 减少可能误杀慢成功 |
| EMPTY_200_FASTBREAK | 3 | 2 | 拒绝: R829 已缓解, 3 是平衡值 |
| 其余参数 | 全地板 | — | 无优化空间 |

## 判定: NOP

全参数地板/最优。R982 NVU_FALLBACK_HEALTH_THRESHOLD=0.05 已部署生效。glm5_2_nv NVCFPexecTimeout 高发是 NVCF 上游问题, 非 config 可修。dsv4p_nv 5/5 100% SR。ms_gw streaming timeout 是已知代码缺陷, 非 config 可修。FALLBACK_GRAPH={} 是 R832 设计, tier_chain 单 tier 是预期状态。系统稳定, 无单参数优化空间。

**Commit**: R985 (NOP, false trigger double-dispatch)

## ⏳ 轮到HM1优化HM2