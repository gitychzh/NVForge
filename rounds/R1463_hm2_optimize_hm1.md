# HM2 Optimize HM1 — Round R1463

**日期**: 2026-07-15 21:50 UTC
**性质**: NOP (false trigger, double-dispatch, 43rd chain of R1395)
**铁律**: 只改HM1不改HM2

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发/双重派遣
- R1462 已提交 NOP，symlink 已指向 R1462，本轮再次触发

## 2. 数据采集

### 容器状态
- 容器: nv_gw Up 42 minutes (healthy)
- 重启时间: 2026-07-15T13:09:29Z
- Compose md5: 45c1f2840ddd9e7e52dfc054f1c02eb4

### 6h 整体
- 41req/18OK/23err = 43.9% SR

### 错误分布
- zombie_empty_completion: 13 (dsv4p_nv×2 avg 47s, glm5_2_nv×11 avg 11.6s)
- all_tiers_exhausted: 10 (dsv4p_nv×9 avg 70.6s, glm5_2_nv×1 187s)
- 0 tier_attempts, 0 NVStream_IncompleteRead

### 按模型
- glm5_2_nv: 27req/15OK 55.6% SR avg 18.4s
- dsv4p_nv: 14req/3OK 21.4% SR avg 62.7s

### 每时SR
- 08:00 5req/2OK 40.0%
- 09:00 8req/4OK 50.0%
- 10:00 6req/2OK 33.3%
- 11:00 6req/2OK 33.3%
- 12:00 7req/3OK 42.9%
- 13:00 9req/5OK 55.6%

### fallback
- fallback_occurred=false: 41req/18OK (100% of requests)
- ms_gw: 25req/21OK 84.0% SR (ms_gw rescue working)

### 日志
- Post-restart: 5 NV-REQ (3 success, 2 zombie), 0 ATE
- tier_chain=`['dsv4p_nv']` / `['glm5_2_nv']` (no fallback, 3model) — expected (FALLBACK_GRAPH={})
- Zombie: NVCF content-filter — avg 216K input chars → 0-28 output chars, finish_reason=stop
- NV-ZOMBIE-ERROR-CHUNK sent to trigger openclaw fallback
- No NV-MS-FB / NV-ALL-TIERS-FAIL in recent logs (post-restart)

## 3. 参数现状

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (=UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor (< UPSTREAM×2) |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor (=UPSTREAM) |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |

## 4. 决策: NOP

- 所有参数在 floor/optimal，无优化空间
- 13 zombie 是 NVCF content-filter 服务端问题，非 config-fixable
- 10 ATE 全部 pre-restart (容器 13:09Z 重启前)，post-restart 0 ATE
- 0 tier_attempts — 无 key-level 问题
- ms_gw 84% SR — 备份链路正常
- HM1 git log 停留在 R1206 (257 轮落后) — 无实际 HM1 变更
- **零参数修改，零 compose 变更，零容器重启**

## ⏳ 轮到HM1优化HM2
