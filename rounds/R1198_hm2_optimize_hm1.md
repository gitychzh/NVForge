# R1198: HM2→HM1 — NOP (66th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 数据收集 (HM1 via SSH)

### 容器日志 (nv_gw --tail 100)
- 仅 glm5_2_nv integrate 流量，所有真实请求首次尝试成功 (NV-INTEGRATE-SUCCESS k1-k5, 2-5s)
- ZOMBIE-EMPTY 模式: 每30分钟1次，finish_reason=stop 但 content_chars=12<50, input_chars 175K+ 持续增长
- 网关正确检测并发送 content_filter error SSE chunk 触发 openclaw fallback
- 0 ERROR, 0 timeout, 0 429, 0 ATE — 所有真实 integrate 请求 100% 成功

### DB 6h 统计 (created_at)
- glm5_2_nv: 24req/12OK(50.0%)/12zombie_empty_completion, avg 7297ms, p50 5476ms, p95 10417ms, max 38540ms
- dsv4p_nv: 0 traffic (容器重启后 19h 无流量)
- kimi_nv: 0 traffic
- minimax_m3_nv: 0 traffic
- 0 tier_attempts (无 key 级别失败)
- upstream_type: 全部 nv_integrate

### DB 24h 统计
- dsv4p_nv: 29req/26OK(89.7%)/3ATE (全部在容器重启前，2026-07-10 19:03 UTC)
- glm5_2_nv: 183req/136OK(74.3%)/47zombie
- kimi_nv: 7/7 100% SR
- minimax_m3_nv: 9/9 100% SR
- tier_attempts: glm5_2_nv 3次 429_integrate_rate_limit (瞬时)

### ms_gw 状态
- dsv4p_ms 和 glm5_2_ms 均正常服务
- 偶发 BrokenPipeError (client disconnect) 和 MS-STREAM-CYCLE (stream_no_data_lines) 但可恢复
- N=9 (dsv4p_ms), N=126 (glm5_2_ms) 持续增长

### 容器配置 (docker exec nv_gw env)
- 所有参数在 floor/optimal: FASTBREAK=1, BUDGETs 充足, COOLDOWNs 低位
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_MS_GW_FALLBACK_TIMEOUT=180 (comment says 90 but actual value 180 — comment stale, runtime correct)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv

## 分析

### 僵尸模式根因
NVCF glm5_2 function (3b9748d8) 对超大输入 (>172K chars) 触发 content-filter，返回 finish_reason=stop 但仅 12 chars 内容。网关正确检测 content_chars=12<50 + input_chars>=5000 → zombie → 发送 error chunk 触发 openclaw fallback。这是 NVCF function-level 行为，非配置可修复。

### 真实请求状态
所有真实 glm5_2_nv integrate 请求 100% 首次尝试成功 (2-5s 延迟)。0 error, 0 timeout, 0 429, 0 ATE。网关处理完全正确。

### 参数状态
所有参数已达 floor/optimal 值。FASTBREAK=1 已是最激进设置。BUDGET 充足。COOLDOWN 低位。无进一步优化空间。

### dsv4p_nv
容器重启后 19h 零流量。重启前的 3 个 ATE 已不再复现。健康但无流量。

## 决策: NOP

**Zero param. 零配置修改。零 compose 变更。零容器重启。**

所有参数在 floor，所有真实请求 100% 成功，僵尸模式是 NVCF content-filter 非配置可修复。第 66 个连续 NOP (R1133 链)。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2