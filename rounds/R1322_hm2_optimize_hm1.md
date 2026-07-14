# R1322: HM2→HM1 — NOP (false trigger, HM1 internal commit, 36th consecutive post-R1286)

## 触发原因

HM1 committed `61c7745` ("Add safety infrastructure: validate_proxy.sh, blue_green_deploy.sh, self_heal.sh + systemd timer") — 这是HM1自己的内部基础设施工作，不是互优化回合。检测脚本因HM1 push到GitHub而触发，但无非优化相关的配置变更。

## 数据收集

### 6h 总体统计
- **57req / 51OK / 6fail → 89.5% SR**
- 6 zombie_empty_completion (NVCF glm5_2 content-filter, 非配置可修复)
- 0 tier_attempts, 0 ATE, 0 IncompleteRead, 0 fallback, 0 key_cycle_429s
- ms_gw: 13/13 100% (fallback未触发，ms_gw流量独立)

### 仅模型: glm5_2_nv (integrate path only)
- avg: 10,447ms, P50: 8,280ms, P95: 19,594ms, max: 50,550ms
- 成功请求: 51/51 integrate 100% SR (zombie_empty_completion 不算tier失败)

### 小时级 SR
| 小时 (UTC) | 总数 | OK | 失败 | SR |
|---|---|---|---|---|
| 22:00 | 4 | 3 | 1 | 75.0% |
| 23:00 | 6 | 5 | 1 | 83.3% |
| 00:00 | 6 | 5 | 1 | 83.3% |
| 01:00 | 29 | 28 | 1 | 96.6% |
| 02:00 | 5 | 5 | 0 | 100.0% |
| 03:00 | 5 | 3 | 2 | 60.0% |
| 04:00 | 2 | 2 | 0 | 100.0% |

### 错误分析
- zombie_empty_completion ×6: glm5_2_nv integrate, ~200K input_chars, finish_reason=stop 但 content_chars 12-46 < 50 阈值
- NVCF content-filter 行为: NVCF 检测到内容违规后返回 stop (非 content_filter stop_reason)，网关 zombie 检测正确触发 error-chunk 让 openclaw fallback
- ⚠️ 不可通过配置修复: 这是 NVCF 侧 glm5_2 函数的内容审核机制，与 HM1 配置无关

### 日志分析
- 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-GLOBAL-COOLDOWN, 0 NV-MS-FB
- 6 NV-ZOMBIE-EMPTY + 6 NV-ZOMBIE-ERROR-CHUNK (正确行为)
- 所有 integrate 请求: NV-INTEGRATE-SUCCESS on first attempt (k1-k5 轮转正常)
- 0 NV-NONCYCLE-ERR, 0 404, 0 504, 0 NVCFPexecTimeout

### 配置状态
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` — 稳定，与 R1286 基线一致
- NV_GW 启动时间: 2026-07-13T22:14:51Z (约6小时前，HM1 self_heal 基础设施重启)
- 所有关键参数 floor/optimal:
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
  - NVU_EMPTY_200_FASTBREAK=2, NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
  - NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_PEER_FB_SKIP_MODELS= (空)
  - TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
  - NV_INTEGRATE_KEY_COOLDOWN_S=0, NVU_STREAM_TOTAL_DEADLINE_S=42
  - NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_INTEGRATE_THINKING_TIMEOUT_S=90

## 决策: NOP

zombie_empty_completion = NVCF glm5_2 content-filter (NVCF侧行为，非配置可修复)。网关 zombie 检测+error-chunk 行为正确。所有参数 floor/optimal。0 tier_attempts 0 ATE 0 IncompleteRead 0 fallback 0 key_cycle。ms_gw 13/13 100%。Compose md5 6e1b58bc 稳定。NVU_PEER_FB_SKIP_MODELS 空。Zero param。铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2