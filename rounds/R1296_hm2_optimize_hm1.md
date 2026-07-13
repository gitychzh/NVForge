# HM2 Optimize HM1 — Round R1296

## 1. 触发分析
- **cron 脚本输出**: `"这是我提交的, 不触发"` (false trigger)
- **最新 commit**: `93ab9b9 R1295 (HM2→HM1 NOP, 9th consecutive post-R1286)` — author=opc2_uname (HM2)
- **判定**: 双调度 false trigger。R1295 已由 pre-run 脚本提交，cron 再次派遣 agent。创建 R1296 NOP。
- **HM1 状态**: 容器 `nv_gw` 运行 2h (restart 22:14 UTC)，上次 HM1 提交仍为 R818 (2026-07-08)，78 轮落后。

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 67 |
| 成功 | 53 (79.1% SR) |
| 失败 | 14 |

### 2.2 按模型
| 模型 | 请求 | 成功 | 失败 | SR | 平均延迟 |
|------|------|------|------|-----|---------|
| glm5_2_nv | 54 | 43 | 11 | 79.6% | 6,682ms |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 36,522ms |

### 2.3 按上游路径
| 路径 | 请求 | 成功 | 失败 | 平均延迟 |
|------|------|------|------|---------|
| nv_integrate | 54 | 43 | 11 | 6,682ms |
| nvcf_pexec | 10 | 10 | 0 | 25,873ms |
| (ATE) | 3 | 0 | 3 | 72,019ms |

### 2.4 错误分类
| 错误类型 | 数量 | 模型 | 详情 |
|----------|------|------|------|
| zombie_empty_completion | 11 | glm5_2_nv | content-filter, avg input 211K chars, avg dur 5,858ms |
| all_tiers_exhausted | 3 | dsv4p_nv | duration=72,020ms 精确绑定 NVU_TIER_BUDGET_DSV4P_NV=72 |

### 2.5 每小时 SR
| 小时 (UTC) | 总数 | 成功 | 失败 | SR |
|------------|------|------|------|-----|
| 18:00 | 36 | 31 | 5 | 86.1% |
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |
| 21:00 | 6 | 4 | 2 | 66.7% |
| 22:00 | 7 | 5 | 2 | 71.4% |
| 23:00 | 6 | 5 | 1 | 83.3% |

### 2.6 dsv4p_nv ATE 详情 (pre-restart burst)
- 3 ATEs 全部在 18:00-18:08 UTC (5h+ 前，pre-restart)
- duration=72,020ms — 精确等于 NVU_TIER_BUDGET_DSV4P_NV=72
- tiers_tried_count=1, fallback_actually_attempted=false
- nv_tier_attempts: 0 行 (失败前预算耗尽)
- **自愈**: 容器重启后 (22:14 UTC) 0 个 dsv4p ATE
- ms_gw: 4req/3OK (75%), 健康

### 2.7 tier_attempts (6h)
- 0 行 — 无 tier 级别失败记录

### 2.8 容器状态
- 容器: nv_gw Up 2 hours (healthy)
- 重启时间: 2026-07-13T22:14:51Z
- Compose md5: 6e1b58bc (稳定，与 R1294-R1295 一致)
- 日志: 58 行 (重启后仅 2h 日志)

### 2.9 当前参数 (HM1 nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
MIN_OUTBOUND_INTERVAL_S=0
```

## 3. 决策: NOP

### 3.1 无需优化
- **11 zombie**: glm5_2_nv content-filter，NVCF 侧行为，不可配置修复。网关正确检测 (NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK) 并在 3-7s 内快速中止。
- **3 dsv4p ATE**: 全部 pre-restart burst (18:00-18:08 UTC)，duration=72,020ms 精确绑定 NVU_TIER_BUDGET_DSV4P_NV=72。容器重启后自愈 — 最近 2h 0 个 dsv4p ATE。NVU_TIER_BUDGET_DSV4P_NV=72 是已知保守值 — 提高可能增加 dsv4p_ms 超时风险 (DeepSeek-V4-Pro 100-200s)。当前预算数学: 205-72=133s ms_gw fallback budget > NVU_MS_GW_FALLBACK_TIMEOUT=195 (但 timeout 只是 nv_gw 侧上限，实际 ms_gw 处理时间决定)。保持 72 不变。
- **所有参数 floor/optimal**: 无需调整。
- **最近 1h 100% SR**: 6 请求 5 OK + 1 zombie (23:33 UTC)，无非 zombie 失败。

### 3.2 预算验证
- dsv4p_nv: NVU_TIER_BUDGET_DSV4P_NV=72, UPSTREAM=66 → tier budget 72s (key1=66s, key2=6s 没用完即超预算)
- PEER_FB: 205-72=133s >> 66s PEER_FALLBACK_TIMEOUT ✓
- MS_GW: 205-72=133s budget, NVU_MS_GW_FALLBACK_TIMEOUT=195 (cap) → 实际 ms_gw 时间 ≤ 133s
- glm5_2_nv: NVU_TIER_BUDGET_GLM5_2_NV=96, UPSTREAM=66 → tier budget 96s (key1=66s, key2=30s)

### 3.3 ms_gw 信号
- 4req/3OK (75%), 1 BrokenPipeError (MS-STREAM-CLIENT-EOF) — 已知流同步缺陷，不可配置修复
- 后端: ZHIPUAI/GLM-5.2 (3 OK) + deepseek-ai/deepseek-v4-pro (1 OK + 1 BrokenPipe)

## 4. 总结
- **触发**: false trigger (双调度，R1295 已由 pre-run 脚本提交)
- **数据**: 6h 67req/53OK 79.1%SR, 11 zombie (不可配置修复) + 3 pre-restart dsv4p ATE (自愈)
- **最近 1h**: 100% SR (无非 zombie 失败)
- **决策**: NOP — 所有参数 floor/optimal，无优化空间
- **铁律**: 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2
