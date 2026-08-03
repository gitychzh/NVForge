# R732: cc2 nv_gw NOP 巡检 (2026-08-04 ~08:00 CST)

## 改动
不改码 (NOP)。

## 依据 (实测 30min 窗口, created_at 字段)

### 实测数据 (docker exec logs_db, ~23:41 UTC = 07:41 CST)

**nv_gw 层 (cc4101-primary caller)**
| status | count |
|--------|-------|
| 200    | 58    |

SR = 100.0% (58/58), 0 错误。

**per-key tier (glm5_2_nv, nv_tier_attempts)**
| nv_key_idx | error_type       | count |
|------------|-------------------|-------|
| 0          | pexec_success     | 13    |
| 1          | integrate_success | 11    |
| 2          | pexec_success     | 12    |
| 3          | integrate_success | 11    |
| 4          | pexec_success     | 11    |

58 attempts 全 success。pexec (k0/k2/k4) + integrate (k1/k3) 混合链路全 healthy。

**cc4101 层 (cc_requests, created_at 30min)**
| upstream_used | status | count |
|---------------|--------|-------|
| primary       | 200    | 60    |
| primary       | 499    | 2     |

SR = 96.7% (60/62)。2×499 client_gone_mid_stream (非 nv_gw 问题):
- abc9e430: 135K input, 17 msgs, 27 tools, 9s 后客户端断
- b2be545f: 202K input, 81 msgs, 27 tools, 36s 后断

均为 cc2 SDK 侧主动断连 (用户取消/超时),非链路故障。avg_dur 25s, max_dur 169s。

**fallback 触发率**: 0% (0/62) — 远超 < 10% 目标。

**buffer 日志**: 全 NV-BUFFER-SUCCESS, 1 attempt 即成功, 无 WAIT/KEYMGR 事件。

### 关键发现: cc_requests.ts 时区 bug 实证 (再次确认)

R730 已识别 `cc_requests.ts` 时区 bug: 部分记录 ts 用 CST 写入但带 +00 timezone 标记,
导致 `ts > now()-interval '30 min'` 实际抓 8 小时数据。

本轮实证:
- `ts` 30min 窗口: 1459 req, 88.8% SR, 503 fallback (含历史集中 502 错误 00:54-02:07 UTC)
- `created_at` 30min 窗口: 62 req, 96.7% SR, 0 fallback (真实当前状态)

**结论**: 分析 cc_requests 必须用 `created_at` 而非 `ts`。nv_requests/nv_tier_attempts 用 `created_at` 也已验证正确。

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok(5keys, glm5_2_nv default) + cc4101 ok(primary=glm5_2_nv) + dsv4p_nv40066 ok(5keys)
- `docker ps`: nv_gw/cc4101/dsv4p_nv40066/logs_db 全 Up
- env 零漂移 (沿 R-glm52split 架构)

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- 当前 nv_gw SR 100%, fb 0% — 远超目标
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 记录已确认, 分析时用 created_at

## 参数快照 (无变化, 沿用 R-glm52split)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: 0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: 0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
  - NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066
  - STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
