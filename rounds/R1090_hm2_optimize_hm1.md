# HM2 Optimize HM1 — Round R1090 (NOP)

**日期**: 2026-07-10 20:25 UTC
**触发器**: cron 派遣 (false trigger — 脚本输出: "这是我提交的, 不触发")
**操作者**: HM2 (opc2_uname)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `17f8eda R1089: HM2 NOP` (author=opc2_uname, HM2)
- 脚本正确检测到自提交并标记 "不触发", cron 仍被派遣 — 误触发
- HM1 本地 git log 停留在 R821，268 轮落后

## 2. HM1 容器状态

- **nv_gw 重启时间**: 2026-07-10 12:09:57 UTC (R1088 重启)
- **最后 nv_gw 请求**: 2026-07-10 12:03:24 UTC (重启前)
- **重启后请求数**: 0 (零流量)
- **ms_gw**: 正常服务 (glm5_2_ms 流式, dsv4p_ms 非流式, 偶有 BrokenPipeError)

## 3. DB 数据 (6h, 重启后)

重启后零请求: `SELECT COUNT(*) FROM nv_requests WHERE ts > '2026-07-10 12:09:57+00'` → 0

全部 30 条请求均为重启前数据:
- 30req/27OK/3err → 90.0% SR (重启前)
- glm5_2_nv: 28req/27OK/1err → 96.4% SR
- dsv4p_nv: 2req/0OK/2err → 0.0% SR (pre-R1088, BUDGET=132 killed at 132s)
- 2 × all_tiers_exhausted (dsv4p_nv), 1 × NVStream_TimeoutError (glm5_2_nv)

## 4. R1088 待验证

R1088: BUDGET 132→198 (+66s) — 给 ms_gw dsv4p_ms fallback 留出预算
- 重启后零流量，无法验证
- dsv4p_nv ATE 132,017ms (重启前) 恰好印证 R1088 诊断: BUDGET=132 在 ms_gw 完成前杀死 relay
- 新 BUDGET=198 尚未被 dsv4p_nv 请求测试过

## 5. 当前配置 (HM1 nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 刚改, 待验证 |
| UPSTREAM_TIMEOUT | 66 | 稳定 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 稳定 |
| NVU_EMPTY_200_FASTBREAK | 2 | 稳定 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 稳定 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | 稳定 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 稳定 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 稳定 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 稳定 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | 稳定 |
| KEY_COOLDOWN_S | 25 | 稳定 |
| TIER_COOLDOWN_S | 18 | 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 稳定 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 稳定 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | 稳定 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | 稳定 |

## 6. 决策: NOP (零参数变更)

- **零数据可评估**: 重启后零请求, 无任何新数据
- **R1088 待验证**: BUDGET 198 尚未被 exercising
- **所有参数地板/最优**: 无优化空间
- **铁律遵守**: 只改 HM1, 不改 HM2 ✓

## 7. ms_gw 观察

ms_gw dsv4p_ms 流式请求偶有 BrokenPipeError (MS-STREAM-CLIENT-EOF):
- 4 次 BrokenPipeError (a23117bf, 6f10a2c4, e04b1b04, d80c098c)
- 1 次 MS-STREAM-DONE 成功 (1bd6ea23)
- 1 次 MS-OK 非流式成功 (ba8c8fd2)
- glm5_2_ms: 全部正常 (MS-STREAM-DONE × 7, MS-OK × 1, MS-OK-STREAM × 8)

BrokenPipeError 是 HM2 agent 直接访问 ms_gw:40007 时的客户端断开, 非 nv_gw 触发 — 不影响 nv_gw 优化

## ⏳ 轮到HM1优化HM2
