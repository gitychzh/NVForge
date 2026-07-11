# HM2 Optimize HM1 — Round R1202 (NOP)

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author: `opc2_uname` (HM2)
- 脚本正确检测到自提交 — false trigger / double-dispatch
- R1201 已提交，symlink 已指向 R1201
- 70th chain of R1133 zombie-only

## 数据收集 (改前必有数据)

### 6h 窗口 (now-6h → now)
| Metric | Value |
|--------|-------|
| Total | 32 req |
| OK | 20 (62.5% SR) |
| Error | 12 zombie_empty_completion |
| Models | glm5_2_nv integrate only |
| dsv4p_nv | 0 traffic |
| kimi_nv | 0 traffic |
| Fallback | 0 (all "no fallback, 3model") |
| tier_attempts | 0 |
| ms_gw 6h | 0 traffic |

### 错误分析
全部 12 个错误 = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, input 176K avg)
- 日志: `[NV-ZOMBIE-EMPTY] finish_reason=stop content_chars<50, input_chars>=5000, no tool_calls`
- gateway detection+error-chunk: correct (sent finish_reason=content_filter SSE chunk)
- NVCF content-filter: not config-fixable (code-level zombie detection correct)

### 容器状态
- Container restart: 2026-07-10T19:03:27Z (unchanged 22h+)
- Compose MD5: `7975939c245761e451a8813852dcb9bf` (unchanged since R1133)

### 参数状态
| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | Bug confirmed (R1039) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |

## 决策: NOP
- 所有错误 = zombie_empty_completion (NVCF content-filter, not config-fixable)
- 0 tier_attempts (no NVCF-level errors, no timeouts, no 429s, no SSEOF)
- 0 fallback triggers (zombie fast-break within tier, no tier exhaustion)
- dsv4p_nv 0 traffic 22h+ (no ATE risk)
- ms_gw 0 traffic 6h (no ms_gw fallback, no BrokenPipeError risk)
- All params at floor/optimal
- compose md5 unchanged 22h+
- 70th chain of R1133 zombie-only

**Zero param changes.**
**Iron rule: only change HM1 never HM2.**
**70th chain of R1133 zombie-only.**

## ⏳ 轮到HM1优化HM2
