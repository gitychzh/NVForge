# HM2 Optimize HM1 — Round R1208

## ⚠️ 触发分析
- 预运行脚本输出: `这是我提交的, 不触发`
- 最新 commit author: `opc_uname` (HM1)
- 判定: NOP — 76th chain of R1133, zombie-only, all params floor/optimal

## 数据收集 (改前必有数据)
```
6h_overall:      32req/20OK(62.5%)/12fail
6h_hourly:       05:2/1, 06:4/2, 07:4/2, 08:4/2, 09:11/9, 10:5/3, 11:2/1
6h_by_upstream:  nv_integrate 32/20OK/12err, avg_ttfb=7223ms, avg_dur=8422ms, max_dur=38540ms
6h_error_type:   zombie_empty_completion x12
6h_by_model:     glm5_2_nv 32/20OK(62.5%), avg_dur=8422ms
6h_tier_attempts: 0 rows
6h_fallback:     0 fallback triggers
6h_ate_tiers:    tiers_tried=1 x12, avg_dur=5267ms
ms_6h:           0 traffic
container:       Up 16h+ since 2026-07-10T19:03:27Z
compose_md5:     7975939c245761e451a8813852dcb9bf (unchanged 16h+)
```

## 日志分析
- 所有 12 个失败均为 `[NV-ZOMBIE-EMPTY]` (glm5_2_nv integrate, R1107 code-level)
- 特征: finish_reason=stop, content_chars=12-36 < 50, input_chars=106K-178K >= 5000
- `[NV-ZOMBIE-ERROR-CHUNK]` 正确发送 content_filter error SSE chunk
- 持续时间: 3.4-4.8s (fast abort)
- 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 tier_attempts
- 所有参数在 floor/optimal 状态:
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198
  - MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15
  - CONNECT_RESERVE_S=0, SSLEOF_RETRY_DELAY_S=1.0
  - INTEGRATE_KEY_COOLDOWN_S=0, INTEGRATE_TIMEOUT_FASTBREAK=1
  - PEXEC_TIMEOUT_FASTBREAK=1, EMPTY_200_FASTBREAK=2
  - NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
  - PEER_FALLBACK_TIMEOUT=66, PEER_FB_SKIP_MODELS=glm5_2_nv
- dsv4p_nv 0 traffic 16h+, kimi_nv 0 traffic
- ms_gw 0 traffic
- 0 tier_attempts — 无 per-key 错误可优化

## 决策: NOP
- 所有失败均为 zombie_empty_completion (code-level, NVCF content-filter, 不可配置修复)
- 0 tier_attempts — 无 per-key 错误可优化
- 所有参数 floor/optimal, compose md5 不变
- dsv4p_nv 0 traffic, kimi_nv 0 traffic, ms_gw 0 traffic
- 铁律: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2