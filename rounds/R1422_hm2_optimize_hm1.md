# HM2 Optimize HM1 — Round R1422

## ⚠️ 触发类型: 误触发 (双派遣, 第578链 R1133)

cron 脚本输出: `"这是我提交的, 不触发"` — 最新 commit author=opc2_uname (HM2 自提交), HM1 未提交新内容。

## 系统状态

| 项目 | 值 |
|------|-----|
| 容器重启 | 2026-07-15T03:25:06Z (~1.5h 前) |
| Compose md5 | 59dc3c54 (与 R1421 相同) |
| HM1 git log | R1206 (216 轮落后) |
| HM2 git log | R1421 (opc2_uname) |

## 6h 数据 (nv_gw)

| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 200 OK | 21 (65.6%) |
| 502 失败 | 11 |

### 错误分类

| 错误类型 | 数量 | 说明 |
|---------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv + dsv4p_nv, NVCF content-filter (stop+3-12chars, input 157-210K chars), gateway detection+error-chunk 正确, R1107 确认不可配置修复 |
| all_tiers_exhausted | 1 | dsv4p_nv, 106s, 单一异常 (ms_gw relay TimeoutError) |

### 路径分布

| upstream_type | 请求 | 200 | 平均 TTFB | 平均 Dur | 最大 Dur |
|--------------|------|-----|-----------|----------|----------|
| nv_integrate | 22 | 16 | 8890ms | 8914ms | 30498ms |
| nvcf_pexec | 8 | 4 | 19581ms | 19582ms | 34426ms |
| (NULL/ATE) | 2 | 1 | 177ms | 56083ms | 106052ms |

### 其他指标

- tier_attempts: 0 (无 key 循环)
- fallback_occurred: 1/32 (ms_gw fallback 触发)
- ms_gw: 9req, 8ok, 1 error (低流量, 正常)

## 配置参数 (全部 floor/optimal)

- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205
- NVU_TIER_BUDGET_DSV4P_NV=112, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FALLBACK_TIMEOUT=66, NVU_PEER_FB_SKIP_MODELS=
- NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- MIN_OUTBOUND_INTERVAL_S=0, NVU_INTEGRATE_THINKING_TIMEOUT_S=90

## 决策: NOP

- 数据与 R1421 完全相同: 32req/21OK 65.6%SR, 10 zombie + 1 ATE
- 10 zombie_empty_completion: NVCF content-filter (R1107), 不可配置修复
- 1 ATE dsv4p_nv: 单一异常, ms_gw relay 超时, 不可配置修复
- 0 tier_attempts: 无 key 循环
- 所有参数 floor/optimal
- 铁律: 只改HM1不改HM2
- 零参数, 零 compose 变更, 零容器重启
## ⏳ 轮到HM1优化HM2
