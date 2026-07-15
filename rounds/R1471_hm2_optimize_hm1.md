# R1471: HM2→HM1 — NOP (false trigger, double-dispatch, chain of R1395)

> **触发分析**: cron脚本输出 `"这是我提交的, 不触发"` — 误触发(double-dispatch).
> 最新commit author = opc2_uname (HM2), R1470已由pre-run脚本提交.
> HM1 git log 落后(空输出), 无新提交. 本轮为false trigger NOP.

## 改前数据 (6h window, 2026-07-15 15:07 UTC, nv_gw StartedAt 2026-07-15T13:09:29Z)

### DB 6h 聚合
- **总请求**: 41 req / 17 OK / 24 fail
- **SR**: 41.5% (17/41)
- **dsv4p_nv**: 16 req / 4 OK (25.0%), avg=58,011ms, max=66,074ms
- **glm5_2_nv**: 25 req / 13 OK (52.0%), avg=22,154ms, max=187,171ms
- **nv_tier_attempts**: 0 (零tier尝试失败 — 全部first-attempt成功或直接ATE)

### 错误分布
- **zombie_empty_completion**: 14 (NVCF content-filter stop+12chars, code-level, 不可配置修复)
- **all_tiers_exhausted**: 10 (NVCF 504/pexec timeout, 上游不可用)
- **upstream NULL**: 10 ATE (调度层直接拒绝, 非integrate/pexec可修)
- **nv_integrate**: 24 req (13 OK, 11 zombie)
- **nvcf_pexec**: 7 req (4 OK, 3 zombie)

### ms_gw
- **26 req / 19 OK / 7 fail (503)** — 26.9% fail rate, 全为503错误
- **backend_model**: deepseek-ai/DeepSeek-V4-Pro (OK), ZHIPUAI/GLM-5.2 (OK), 空backend_model (503 fail)
- **error_type**: 全部NULL (纯503, 无明确error_type)

### docker logs (最近100行)
- 12条 error/warn: 5× NV-ZOMBIE-ERROR-CHUNK (glm5_2_nv+dsv4p_nv), 2× NV-TIER-FAIL/NV-ALL-TIERS-FAIL (dsv4p_nv, elapsed=64s), 1× NV-MS-FB ms_gw relay failed timeout=124s
- 容器无重启, 零ERROR/WARN, 当前uptime

### 当前配置 (env snapshot)
```
UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15
NVU_PEER_FALLBACK_TIMEOUT=66, NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NV_INTEGRATE_KEY_COOLDOWN_S=0, NV_INTEGRATE_MODELS=glm5_2_nv
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FB_SKIP_MODELS=(空)
NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
Compose md5: 45c1f2840ddd9e7e52dfc054f1c02eb4 (stable)
```

## 决策: NOP

### 候选参数评估
| 参数 | 当前值 | 状态 | 评估 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | floor | 66s已对齐NVCFPexecTimeout max; 不改 |
| TIER_TIMEOUT_BUDGET_S | 205 | 充足 | armoring dsv4p_nv ATE 64s; 不改 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | 1为绝对floor; 不改 |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal | 2为最佳值; 不改 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | 0为绝对floor; 不改 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | 0为绝对floor; 不改 |
| NVU_CONNECT_RESERVE_S | 0 | floor | 0为绝对floor; 不改 |
| KEY_COOLDOWN_S | 25 | stable | 长期稳定值; 不改 |
| TIER_COOLDOWN_S | 15 | stable | R1103锁定; 不改 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal | 对齐UPSTREAM=66; 不改 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | adequate | ms_gw relay timeout 124s; 120s略紧但ms_gw rescue已工作中; 不改 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor | 66s caps futile 504 key cycling; 不改 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | stable | HM1-HM2对称; 不改 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | stable | < openclaw 45s; 不改 |

**结论**: 所有参数均在floor/optimal状态. 14 zombie (NVCF content-filter, code-level不可配置修复), 10 ATE (NVCF 504/pexec timeout, 上游不可用). ms_gw 26req中7次503(26.9%), 但ms_gw rescue已在工作. 零tier_attempts表明所有失败发生在first-attempt后直接ATE, 无key retry. NVCF上游持续不可用非网关参数可修. **NOP**.

## 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
