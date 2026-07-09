# HM2 Optimize HM1 — Round R1015

## ⚠️ 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author: opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 / double-dispatch (R1014 已处理此 commit)
- 数据与 R1014 完全一致

## 1. 数据快照 (改前必有数据)

### 6h 总体
- 241 req, 220 OK (91.3% SR), 21 ATE
- 与 R1014 完全相同 (241/220/91.3%/21)

### 6h 按 tier
| tier_model | total | ok | err | sr_pct |
|---|---|---|---|---|
| glm5_2_nv | 132 | 126 | 6 | 95.5% |
| dsv4p_nv | 66 | 57 | 9 | 86.4% |
| kimi_nv | 24 | 24 | 0 | 100.0% |
| minimax_m3_nv | 19 | 13 | 6 | 68.4% |

### 6h 延迟 (成功请求)
| tier_model | avg_ttfb | avg_dur | cnt |
|---|---|---|---|
| kimi_nv | 15,568ms | 15,586ms | 24 |
| minimax_m3_nv | 10,810ms | 16,911ms | 13 |
| glm5_2_nv | 22,623ms | 25,989ms | 126 |
| dsv4p_nv | 38,522ms | 38,522ms | 57 |

### 6h ATE 分析
- 21 ATE, 全部 tiers_tried_count=1 (单 tier 耗尽, 无 fallback)
- dsv4p_nv: 9 ATE avg 106,374ms
- glm5_2_nv: 6 ATE avg 168,641ms
- minimax_m3_nv: 6 ATE avg 154,330ms
- 错误类型: 全部 `all_tiers_exhausted` (21), 无 NVCFPexecTimeout

### 6h nv_tier_attempts
- dsv4p_nv IntegrateTimeout: 14, avg 56,021ms, max 67,086ms
- dsv4p_nv NVCFPexecRemoteDisconnected: 1, 9,134ms
- kimi_nv empty_200: 1
- 无 NVCFPexecTimeout 出现 → UPSTREAM=66 非绑定

### 6h fallback
- fallback_occurred=false: 233
- fallback_occurred=true: 8 (仅 3.3%)

### 1h 总体
- 66 req, 59 OK (89.4%), 7 ATE

### ms_gw 状态
- BrokenPipe 持续: 3 次 nonstream relay BrokenPipe (MS 后端成功但 relay 到客户端断开)
- EMPTY_200_FASTBREAK_THRESHOLD=3 (可优化到 1 但 BrokenPipe 是 code-level 缺陷)
- KEY_COOLDOWN_S=60, MIN_OUTBOUND_INTERVAL_S=1.0

## 2. HM1 当前参数 (nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=112
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
FALLBACK_HEALTH_THRESHOLD=0.05 (dead param)
NVU_FORCE_STREAM_UPGRADE=0
MIN_OUTBOUND_INTERVAL_S=0
```

## 3. 根因分析
- 所有 FASTBREAK 已在地板值 (1)
- UPSTREAM=66 非绑定 (无 NVCFPexecTimeout)
- TIER_TIMEOUT_BUDGET_S=112 充足
- minimax_m3_nv SR 68.4% — NVCF degraded, 无 secondary provider (ms_gw 无 minimax model)
- ms_gw BrokenPipe 是 code-level 缺陷 (relay 成功获取 MS 后端数据但 relay 到客户端时 BrokenPipe)
- 21 个 ATE 全为单 tier 无 fallback — FALLBACK_GRAPH 为空 (R832 设计), ms_gw 同模型 fallback 无法覆盖所有场景
- 所有参数已最优, 无可优化空间

## 4. 决策: NOP
- nv_gw: 所有参数在 floor/optimal, 无调整空间
- ms_gw: EMPTY_200_FASTBREAK_THRESHOLD=3 可降到 1, 但 BrokenPipe 是 code-level 缺陷, 降低 FASTBREAK 不会修复 relay 问题
- 数据与 R1014 完全一致, 无新事件
- 铁律: 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2
