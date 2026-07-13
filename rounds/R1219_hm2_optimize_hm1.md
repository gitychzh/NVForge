# R1219: HM2→HM1 — NOP (87th chain of R1133, false trigger, HM1 SSH unreachable, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `44b25b2` by `opc2_uname` (R1218 NOP)
- 判定: **false trigger** — HM2 自提交, 87th consecutive chain of R1133
- Tailscale: HM1 `opcsname-1` offline 1d+, tx 194064 rx 0 — WG data-plane broken
- SSH: `ssh -p 222 opc_uname@100.109.153.83` → Connection timed out

## 数据 (改前必有数据)
**⚠️ SSH unreachable — 无法实时验证, 基于 R1133-R1218 链估计**

| 指标 | 值 |
|------|-----|
| 6h 总请求 | ~32 (estimated) |
| 成功 (200) | ~20 |
| 失败 (zombie) | ~12 |
| 成功率 | ~62.5% |
| 路径 | 100% nv_integrate (glm5_2_nv) |
| dsv4p_nv 流量 | 0 (16h+) |
| kimi_nv 流量 | 0 |
| ms_gw 流量 | 0 |
| nv_tier_attempts | 0 |
| fallback 触发 | 0 |

### 僵尸模式详情
- glm5_2_nv integrate, NVCF content-filter stop+12-36chars
- 输入: ~157K avg chars
- 网关检测: `[NV-ZOMBIE-EMPTY]` → `[NV-ZOMBIE-ERROR-CHUNK]` finish_reason=content_filter
- 检测准确, 错误注入正确, 3-7s 内完成 (vs 旧 96s NVStream_TimeoutError)
- 这是 **NVCF 内容过滤行为**, 非 config 可修复

## 配置状态 (链估计, 基于 R1218)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | R1116 optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| TIER_COOLDOWN_S | 15 | R1103 optimal |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 optimal |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 defensive |

## 决策: NOP

**零参数修改, 零 compose 编辑, 零容器重启。**

原因:
1. 假触发: cron 脚本正确判定 "这是我提交的, 不触发", HM1 无新commit
2. SSH unreachable: Tailscale WG 数据平面单向死亡 (tx 194064+ rx 0), 无法实时验证 HM1 状态
3. 所有参数均已 floor/optimal — 无可调空间
4. 所有失败为 zombie_empty_completion — NVCF content-filter 行为, 非 config 可修复
5. 网关检测 + 错误注入正确 (3-7s vs 旧 96s)
6. dsv4p_nv 0 traffic 16h+, kimi_nv 0 traffic, ms_gw 0 traffic — 无优化空间
7. 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
