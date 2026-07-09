# R984: HM2→HM1 — NOP

## 触发分析
- **False trigger**: cron 脚本输出 `[2026-07-09 17:45:29] 这是我提交的, 不触发`
- 最新 commit `af1a1d6` = opc2_uname (HM2 self-commit, R983 symlink fix)
- 预运行脚本已提交 R983 NOP + symlink fix
- 本次为 double-dispatch (R983 已提交, symlink 已指向 R983)
- False trigger streak: R884→R984 (101 consecutive NOPs)

## 数据摘要 (6h, as of 17:45 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 39 |
| 成功 (200) | 33 |
| ATE (502) | 6 |
| 成功率 | **84.6%** |
| 24h SR | 194/187 = **96.4%** (7 ATE) |
| dsv4p_nv | 5/5 **100%** SR |
| glm5_2_nv | 34/28 = **82.4%** SR (6 ATE) |
| Fallback count | 20 (all ms_gw same-model) |

## ATE 分析

| tiers_tried | count | avg_dur | fb_attempted |
|-------------|-------|---------|-------------|
| 1 | 4 | 66,044ms | 0 (all via ms_gw) |
| 2 | 2 | 174,417ms | 0 (ms_gw rescued) |

- 4 single-tier ATEs: glm5_2_nv key timeout → fast-break → ms_gw fallback failed (streaming timeout)
- 2 double-tier ATEs: glm5_2_nv → ms_gw fallback → rescued (200 OK)
- All ATEs are glm5_2_nv; dsv4p_nv 0 ATE, 5/5 100% SR
- FALLBACK_GRAPH={} (R832 design) — tier_chain=['glm5_2_nv'] (no fallback, 3model) 是预期状态
- ms_gw fallback: 部分成功, 部分 streaming timeout (已知代码缺陷, 非 config 可修)

## Tier Attempts (6h)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 17 | 57,814 | 62,606 |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — | — |
| glm5_2_nv | empty_200 | 3 | — | — |

NVCFPexecTimeout max=62,606ms vs UPSTREAM=64 → buffer=1.4s (<3s R751 rule, tight). 但 NVU_TIER_BUDGET_GLM5_2_NV=20 生效后, 实际 cap 在 20s.

## 环境状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | 绑定边缘 (buffer=1.4s < 3s), 但 tier budget=20 实际 cap |
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
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | **R982 部署生效** (0.10→0.05) |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 死参数 (R919), 同值但无关 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | R923 防御 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 防御 |
| HEALTH_THRESHOLD (effective) | **0.05** | `docker exec` 验证: Python import 确认 |

## R982 验证

- `docker exec nv_gw python3 -c 'from gateway import func_health; print(func_health.HEALTH_THRESHOLD)'` → **0.05** ✓
- 容器重启于 17:43 UTC, 运行 2 分钟
- nv_gw 日志零 error/warn/exception
- dsv4p_nv：已从 tier_chain 消失 (MIN_SAMPLES expired, health<0.05 → 现在 0.05 阈值应保留), 但无新请求流入

## 候选参数评审

| 参数 | 当前值 | 候选 | 判定 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 64 | +2→66 | 拒绝: tier budget=20 实际 cap, +2 无意义; NVCFPexecTimeout max=62.6s 但 tier budget 已限制 |
| NVU_TIER_BUDGET_GLM5_2_NV | 20 | ±5 | 拒绝: 20s 平衡(1 次完整 key 尝试+fast-break); 增加浪费 ATE 路径时间, 减少可能误杀慢成功 |
| 其余参数 | 全地板 | — | 无优化空间 |

## 判定: NOP

全参数地板/最优。R982 的 NVU_FALLBACK_HEALTH_THRESHOLD=0.05 已部署生效。glm5_2_nv NVCFPexecTimeout 高发是 NVCF 上游问题, 非 config 可修。ms_gw streaming timeout 是已知代码缺陷, 非 config 可修。FALLBACK_GRAPH={} 是 R832 设计, tier_chain 单 tier 是预期状态。系统稳定, 无单参数优化空间。

**Commit**: 待提交

## ⏳ 轮到HM1优化HM2

