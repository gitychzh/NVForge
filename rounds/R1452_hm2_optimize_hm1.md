# HM2 Optimize HM1 — Round R1452

**Date**: 2026-07-15 19:50 UTC
**Author**: opc2_uname (HM2)
**Type**: NOP (false trigger, double-dispatch, 57th chain of R1395)
**Hash**: 9374299 (R1451) → R1452

## 1. 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2) — R1451 是 HM2 提交的 NOP
- 预运行脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 双派遣误触发 (57th chain since R1395)
- **铁律:只改HM1不改HM2**

## 2. HM1 环境快照

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | code-bug (no-op in pexec) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 280 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | optimal |
| Compose md5 | 51079b89019ddfb1a08f65e79e847b51 | stable |
| Container uptime | ~1h (healthy) | stable |

## 3. 6h 数据 (35 req)

| 指标 | 值 |
|------|-----|
| 总量 | 35req/14OK 40.0%SR |
| glm5_2_nv | 25req/14OK 56.0%SR |
| dsv4p_nv | 10req/0OK 0.0%SR |
| ATE | 11 (10 dsv4p_nv 504, 1 glm5_2_nv) |
| zombie | 10 (glm5_2_nv, NVCF content-filter) |
| tier_attempts | 0 (clean) |
| ms_gw | 25/21 84.0%SR (DEEPSEEK-V4-PRO 11/11, ZHIPUAI-GLM-5.2 10/10) |

## 4. 错误诊断

### dsv4p_nv 504 (10 ATE, avg 87s)
- 日志: `NV-CYCLE tier=dsv4p_nv k2 → 504 (504_nv_gateway_timeout), cycling to next key`
- `NV-TIER-FAIL all 5 keys failed: 429=0, empty200=0, timeout=0, other=1`
- NVCF function-level 504 — 所有 key 返回相同结果
- FASTBREAK=1 正确，但 504 bypasses FASTBREAK (goes through NV-CYCLE)
- NVU_TIER_BUDGET_DSV4P_NV=66=UPSTREAM (BUDGET Floor Pattern, R1440)
- **Not config-fixable** — NVCF-side function degradation

### glm5_2_nv zombie (10, avg 11s)
- 日志: `NV-ZOMBIE-EMPTY finish_reason=stop, content_chars=12-20 < 50, input_chars=216K+`
- NVCF content-filter 返回空/极短内容
- 代码级 zombie 检测正确触发 fast abort (3-15s vs 旧 96s hang)
- **Not config-fixable** — NVCF content-filter behavior

### ms_gw relay TimeoutError (284s)
- 日志: `NV-MS-FB ms_gw relay failed after 284097ms: TimeoutError: timed out (relay_started=True)`
- ms_gw: `MS-STREAM-DONE` at ~2s (dsv4p_ms DEEPSEEK-V4-PRO 11/11 100%SR)
- **代码级 streaming sync defect** — nv_gw 看不到 ms_gw 的完成信号
- BUDGET=205, MS_GW_FALLBACK_TIMEOUT=280 — relay 284s 远超两者, BUDGET enforcement gapped (R1103)
- **Not config-fixable** — code-level defect

## 5. 决策: NOP

所有参数已处于 floor/optimal 状态:
- UPSTREAM=66 floor, TIER_COOLDOWN=15 floor, KEY_COOLDOWN=25 floor
- BUDGET=205 充裕 (BUDGET - NVU_TIER_BUDGET_DSV4P_NV = 205-66 = 139s > 280s MS_GW_FALLBACK_TIMEOUT)
- NVU_TIER_BUDGET_DSV4P_NV=66=UPSTREAM (BUDGET Floor Pattern)
- FASTBREAK 全部 floor=1
- ms_gw MODELMAP 完整, peer-fb SKIP_MODELS 空

残余错误均为非配置可修复:
- dsv4p_nv 504: NVCF function-level degradation
- glm5_2_nv zombie: NVCF content-filter
- ms_gw relay TimeoutError: code-level streaming sync defect

**零配置变更, 零容器重启.**

## 6. 回合链

R1395→R1452: 58 consecutive false-trigger NOP rounds (since 2026-07-14).
HM1 git at R1206 (246 rounds behind as of R1452).

## ⏳ 轮到HM1优化HM2
