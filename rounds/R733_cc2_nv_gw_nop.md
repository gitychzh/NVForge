# R733: cc2 nv_gw NOP 巡检 (2026-08-04 ~09:04 CST)

## 改动
不改码 (NOP)。

## 依据 (实测 30min 窗口, created_at 字段)

### 实测数据 (docker exec logs_db, ~01:04 UTC = 09:04 CST)

**nv_gw 层 (cc4101-primary caller)**
| status | count |
|--------|-------|
| 200    | 32    |

SR = 100.0% (32/32), 0 错误。

**per-key tier (glm5_2_nv, nv_tier_attempts)**
| error_type       | count |
|-------------------|-------|
| pexec_success     | 19    |
| integrate_success | 13    |

32 attempts 全 success (pexec 19 + integrate 13)。混合链路全 healthy。

**cc4101 层 (cc_requests, created_at 30min)**
| status | error_type             | count |
|--------|-------------------------|-------|
| 200    | -                       | 32    |
| 499    | client_gone_mid_stream  | 1     |

SR = 97.0% (32/33)。1×499 client_gone_mid_stream = cc2 SDK 侧主动断连, 非链路故障。nv_gw 层全 200。

注入轮前分析的 `cc4101-primary|glm5_2_nv|200|28` 与本轮实测 32 一致 (窗口滚动 +少量新请求)。

**fallback 触发率**: 0% (0/33) — 远超 < 10% 目标。

**buffer 日志 (nv_gw --since 30m)**: 全 NV-BUFFER-SUCCESS。
- 多数 1 attempt 即成功 (elapsed ~22-30s)
- 1 个 e24a6812 attempt=4/5 仍 success_tool_call, elapsed 167s — buffer retry 机制有效吸收抖动
- 无 WAIT/KEYMGR/breaker/cooling 事件

### 健康检查
- `/health`: nv_gw ok(5keys, glm5_2_nv default) + cc4101 ok(primary=glm5_2_nv) + dsv4p_nv40066 ok(5keys)
- `docker ps`: nv_gw Up 7h, cc4101 Up 11h, dsv4p_nv40066 Up 7h, nv_gw_stable Up 2days, logs_db Up 4days — 全 Up
- env 零漂移 (沿 R-glm52split 架构)

### 注入轮前分析 vs 实测
- 注入: `cc4101-primary|glm5_2_nv|200|28`, per-key 8+5+7+7+1=28, `f|28` (0 fb)
- 实测 (晚 ~90s): 32×200, per-key 19+13=32, 0 fb
- 一致, 数据真实

## 验证 (NOP 无需 restart)
- 沿用 R732 参数, 无改动
- 链路全顺, 无新错误类型

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- 当前 nv_gw SR 100%, cc4101 SR 97.0% (1 client_gone 非 nv_gw), fb 0% — 远超目标
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730/R732 已实证)

## 参数快照 (无变化, 沿用 R-glm52split)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: 0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: 0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
  - NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066
  - STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
