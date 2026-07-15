# R1519: HM2→HM1 — NOP (false trigger, zero post-restart ATEs, all params floor/optimal)

## 数据收集 (HM1 nv_gw)

| Metric | Value |
|--------|-------|
| 6h SR | 70req/48OK/22fail **68.6%** |
| dsv4p_nv | 47req/36OK/11fail 76.6%SR avg 14.1s |
| glm5_2_nv | 23req/12OK/11fail 52.2%SR avg 10.1s |
| 6h error type | zombie_empty_completion=19, all_tiers_exhausted=3 |
| ms_gw | 15req/14OK **93.3%SR** |
| tier_attempts | glm5_2_nv: 2x 429_integrate_rate_limit |
| Container restart | 2026-07-15T22:25:46Z (56min ago) |
| compose md5 | 9fb97661 |

## 重启后分析 (post-restart ≥22:25 UTC)

| 时间段 | OK | zombie | ATE | SR |
|--------|-----|--------|-----|-----|
| 22:25-23:05 | 4 | 2 | **0** | 66.7% |

- **零 ATE 重启后** — 所有成功请求正常完成
- 2 zombie = NVCF content-filter (input_chars ≥223K, output 0-48 chars) — 不可配置
- 0 tier-fail, 0 FASTBREAK, 0 peer-fb, 0 ms_gw relay

## 判决: NOP

**所有参数已 floor/optimal:**
- UPSTREAM_TIMEOUT=66 (NVCF下限)
- NVU_TIER_BUDGET_DSV4P_NV=66 (=UPSTREAM_TIMEOUT, BUDGET Floor Pattern)
- TIER_COOLDOWN_S=15 (floor)
- KEY_COOLDOWN_S=25 (floor)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
- NVU_EMPTY_200_FASTBREAK=2 (code-level no-op, BUDGET exhaustion precludes 2nd key)
- NVU_PEER_FB_SKIP_MODELS="" (all models peer-fb enabled)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- TIER_TIMEOUT_BUDGET_S=205 (adequate headroom)
- NVU_CONNECT_RESERVE_S=0 (floor)

**失败根因:** zombie_empty_completion = NVCF content-filter (大输入请求被NVCF过滤返回空响应, 网关检测为zombie并注入timeout SSE chunk触发openclaw fallback). 不可配置修复.

**False trigger:** 检测脚本触发因HM1提交了GitHub commit, 但该commit是HM2自己的R1518回合文件. 重启后零ATE, 无优化空间.

铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
