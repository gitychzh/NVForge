# R1503: HM2→HM1 — NOP (zero ATE in 3h post-restart, zombie-only, all params floor/optimal)

## 触发
- 脚本: `"这是我提交的, 不触发"` — 误触发 (R1502 HM2 self-commit NOP)
- Commit: `a96cda0` — R1502 HM2→HM1 NOP

## 数据采集

**容器状态**: 重启于 2026-07-15T18:15:54Z (3h), compose md5 `ba4f2871` 未变, container env 与 compose 一致

### 6h 全局
| 指标 | 数值 |
|------|------|
| 总请求 | 60 (与 R1502 完全相同) |
| 成功 | 37 (61.7%) |
| 失败 | 23 |
| zombie | 19 (12 glm5_2_nv, 7 dsv4p_nv) |
| ATE | 7 dsv4p_nv (全部 pre-restart, 4×502 + 3×200 rescued) |
| tier_attempts | 2 (glm5_2_nv 429_integrate_rate_limit) |
| ms_gw | 19/15 (78.9%) |
| peer-fb | 0 |

### 重启后 (18:15:54Z → 当前)
| 指标 | 数值 |
|------|------|
| 总请求 | 23 |
| 成功 | 14 (60.9%) |
| 失败 | 9 (ALL zombie) |
| ATE | **0** |
| zombie | 9 (4 dsv4p_nv avg 4,333ms, 5 glm5_2_nv avg 10,166ms) |
| ms_gw | 5/5 (100%) |
| peer-fb | 0 |
| tier cycling | 0 |

### 每小时趋势 (重启后)
| 小时 | 请求 | 成功 | 失败 | SR |
|------|------|------|------|-----|
| 18:00 (45min) | 4 | 3 | 1 | 75.0% |
| 19:00 | 9 | 5 | 4 | 55.6% |
| 20:00 | 10 | 6 | 4 | 60.0% |

### 成功请求延迟分布
| 延迟 | 计数 |
|------|------|
| <5s | 1 |
| 5-15s | 18 |
| 15-30s | 9 |
| 30-60s | 8 |
| >60s | 1 |

### 容器 env (关键参数)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_PEER_FB_SKIP_MODELS= (空)
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 分析

### 零可配置修复项
- **zombie_empty_completion (100% of failures)**: NVCF content-filter 行为 — input_chars ~220K, content_chars 0-12, finish_reason=stop。网关正确检测 (NV-ZOMBIE-EMPTY) + 快速 abort (NV-ZOMBIE-ERROR-CHUNK)。代码级，不可配置修复。
- **零 ATE 重启后**: BUDGET=205, UPSTREAM=66, 各 tier budget 地板。重启后 3h 零 ATE，零 tier-fail，零 FASTBREAK 触发，零 peer-fb/ms-fb。BUDGET 地板模式有效。
- **零 tier cycling**: 仅 2 个 tier_attempts (glm5_2_nv 429 integrate rate limit)，无需调 COOLDOWN。
- **零 peer-fb/ms-fb**: 无需调 fallback 参数。
- **ms_gw 健康**: 重启后 5/5 100% SR，日志 clean (MS-OK-STREAM → MS-STREAM-DONE)。
- **所有 FASTBREAK/Cooldown/Timeout/Budget 地板/最优**: 无下调空间。
- **compose md5 未变，container env 一致**: 无需重启。

### 与 R1502 对比
完全相同的 NOP 模式 — 同一数据集 (60 req, 37 OK, 61.7%)，同样 zombie 主导，同样全部参数触底。重启后 3h 零 ATE 进一步确认 BUDGET 地板模式有效。连续 5 轮 (R1499-R1503) 零可配置问题。

### dsv4p_nv ms_gw 模型映射评估
当前 `NVU_MS_GW_FALLBACK_MODELMAP` 不含 dsv4p_nv。dsv4p_nv ATE 仅靠 peer-fb (HM2) 救援。但重启后零 ATE → 无需添加。若后续出现 dsv4p_nv ATE，可考虑添加 `dsv4p_nv:dsv4p_ms` 作为第二救援路径。

## 决策: NOP (零变更)

零可配置优化。所有错误为 code-level (NVCF content-filter zombie)。重启后 3h 零 ATE 验证系统稳定。所有参数触底无下调空间。

## 铁律
- ✅ 只改HM1不改HM2 — 本轮无配置修改
- ✅ compose md5 ba4f2871 未变
- ✅ container env 与 compose 一致
- ✅ 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
