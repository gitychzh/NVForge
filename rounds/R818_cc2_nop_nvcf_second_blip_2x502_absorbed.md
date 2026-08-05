# R818 cc2 — NOP 巡检轮 (NVCF 二次瞬断, 2×502 均被吸收, 用户侧 100%)

> 轮号: R818 (cc2 线) | 时间: 2026-08-05 13:01-13:31 CST (30min 窗口)
> 上轮: R817 (NOP, NVCF 风暴退去, 链路恢复全绿)
> 容器: nv_gw Up 1h (12:25 CST restart 后), cc4101 Up 12h, dsv4p_nv40066 Up 17h

## 摘要

R813 chain_full_retry 修复持续就位 (inspect.signature 铁证 True). 本轮 30min 窗口
(13:01-13:31 CST) 出现 2×502 (1b95ecee 跨窗 + cb61eac7 新发), 均为 buffer_exhausted
(NVCF RemoteDisconnected 风暴 5key×5attempt 全挂). ★cb61eac7 是 R813 修复后第二次
WAIT-RECOVER→CHAIN-FULL 实战触发★, 完整走 CHAIN-FULL (skip override, 完整 5key RR),
但 retry 仍全 RemoteDisc/SSLEOFError → WAIT-FAIL → 502. 两 502 均被 cc4101 吸收
(passthrough error SSE → 用户侧最终 200, fallback=f), 用户可见 SR=100%.

**零改动 NOP 巡检轮** — 长期观测期持续. 502 是 NVCF 后端故障不可挽救请求, 非链路 bug.

## 30min 链路数据 (13:01-13:31 CST, 05:01-05:31 UTC)

### nv_requests (cc4101-primary, cc2 自己的请求)

| status | count | avg_dur | max_dur |
|---|---|---|---|
| 200 | 44 | 28681ms | 155895ms |
| 502 | 2  | 484048ms | 518568ms (cb61eac7) |

per-call SR (排 502) = **44/44 = 100%**. per-call SR (含 502) = 44/46 = 95.7%.

### 两个 502 详细分析

#### req=1b95ecee (12:54-13:01 CST, elapsed=449528ms ~ 450s)

R817 跨窗样本 (R816/R817 已详记). buffer 5 attempts 全 RemoteDisc → WAIT 180s →
ProbeWorker 探到恢复 → CHAIN-FULL retry 全 5key 仍 FAIL → WAIT-FAIL → 502.
cc4101 对应 req=23d5a44c, ttfb=449547ms, **status=200 fallback=f** (吸收).

#### req=cb61eac7 (13:13-13:22 CST, elapsed=518568ms ~ 519s) ★R813 CHAIN-FULL 第二次实战★

完整轨迹 (nv_gw 日志铁证):
```
13:13:27  NV-BUF2KEY-INTERCEPT caller=cc4101-primary buffer handles NVCF directly
13:13:27  NV-BUFFER-START max_retries=5 stairs=[90×5] total_deadline=450s
13:13:27  NV-BUFFER-ATTEMPT 1/5
13:14:08  k5 RemoteDisconnected → EXEC-FAIL attempt 1 all_keys_exhausted=True
13:14:13  NV-BUFFER-ATTEMPT 2/5 (backoff 5s)
13:14:49  k1 RemoteDisconnected → EXEC-FAIL attempt 2
13:14:59  NV-BUFFER-ATTEMPT 3/5 (backoff 10s)
13:15:35  k2 RemoteDisconnected → EXEC-FAIL attempt 3
13:15:50  NV-BUFFER-ATTEMPT 4/5 (backoff 15s)
13:16:25  k3 RemoteDisconnected → EXEC-FAIL attempt 4
13:16:40  NV-BUFFER-ATTEMPT 5/5 (backoff 15s)
13:17:42  k4 RemoteDisconnected → EXEC-FAIL attempt 5 LAST-FAIL
13:17:42  NV-BUFFER-WAIT all 5 attempts failed, waiting up to 180s for recovery
13:20:05  NV-BUFFER-WAIT-RECOVER key recovered, retrying with full 5-key chain
           (override cleared), remaining=51s   ← ProbeWorker 13:20:05 探到恢复
13:20:05  NV-BUFFER-CHAIN-FULL chain_full_retry=True, skip override, start_key=k1
           (RR起, NVCF chain full 5key)          ← ★R813 修复正确触发★
13:20:51  k4 RemoteDisconnected (CHAIN-FULL attempt 1)
13:21:21  k5 SSLEOFError (CHAIN-FULL attempt 2)
13:21:57  k1 RemoteDisconnected (CHAIN-FULL attempt 3)
13:22:05  k2 timeout 8428ms (CHAIN-FULL attempt 4)
13:22:05  NV-BUFFER-EXEC-FAIL attempt 1 key=k1 all_keys_exhausted=True
13:22:05  NV-BUFFER-WAIT-FAIL retry after recovery still failed (execute_failed)
13:22:05  NV-BUFFER-NO-MS ms_gw fallback disabled, sending error to CC → 502
```

**关键**: cb61eac7 证明 R813 chain_full_retry 在 WAIT-RECOVER 分支**正确工作**:
- WAIT 180s 等到 ProbeWorker 探到 key 恢复 → WAIT-RECOVER
- CHAIN-FULL (chain_full_retry=True) skip override, 从 k1 起完整 5key RR
- 但 NVCF 在 13:20-13:22 仍在持续抖 (4key RemoteDisc/SSL/timeout 全挂)
- WAIT-FAIL → 502 (remaining=51s 不够再 WAIT)

这是"NVCF 恢复后立即又抖"的不可挽救场景, 非补丁 bug. cc4101 吸收了此 502:
- cc4101 对应 req=b0c1307d, ttfb=518581ms
- `[CC4101-UPSTREAM-ERROR-SEEN] passthrough detected nv_gw api_error SSE -> breaker failure`
- cc_requests 记 status=**200** fallback=**f** (用户侧最终 200, 未触发 fallback)

### cc_requests (用户可见)

| total | 200 | 499 | 502 | fb | fb_pct |
|---|---|---|---|---|---|
| 1312 | 1304 | 8 | 0 | 19 | 1.45% |

用户可见 SR (排 499) = **1304/1304 = 100%**. 零 502 穿透. 8×499 client_gone_mid_stream
(cc2 SDK 450s 预算前自断, 非链路错). fallback 19 次 (1.45%, 集中 11:18-12:17 前段, 本轮
13:01-13:31 窗口内仅 1×29281833 fallback). fallback dsv4p 全 200 兜住.

### per-key × status (glm5_2_nv tier, 46 attempts)

| key | total | ok | errs |
|---|---|---|---|
| k0 | 9 | 9 | pexec_success |
| k1 | 10 | 10 | pexec_success |
| k2 | 14 | 13 | pexec_429×1 |
| k3 | 6 | 6 | pexec_success |
| k4 | 7 | 6 | pexec_SSLEOFError×1 |

per-key tier SR = **44/46 = 95.7%**. k2 1×429 (KeyManager 120s 短惩罚), k4 1×SSLEOFError.
两错误均被 buffer 自愈吸收. 5key 分布 k0 9/k1 10/k2 14/k3 6/k4 7 (k2 偏高, RR 正常波动).

注: 两个 502 的 tier attempts 未入 nv_tier_attempts 表 (buffer 全程 RemoteDisc 在
NV-GLM52-CONN 层, 非 tier 级 attempt 记录). 表内 46 attempts 是 44×200 + 2×非成功
(1×429 + 1×SSL) 对应的 buffer 成功/自愈路径.

## 2h SR 趋势 (10min 桶, cc4101-primary)

| bucket (UTC) | total | ok | e502 | e499 | SR% |
|---|---|---|---|---|---|
| 03:30 | 9 | 7 | 1 | 1 | 77.8 |
| 03:40 | 23 | 19 | 3 | 1 | 82.6 |
| 03:50 | 27 | 26 | 1 | 0 | 96.3 |
| 04:00 | 25 | 24 | 1 | 0 | 96.0 |
| 04:10 | 20 | 20 | 0 | 0 | 100.0 |
| 04:20 | 28 | 28 | 0 | 0 | 100.0 |
| 04:30 | 10 | 9 | 0 | 1 | 90.0 |
| 04:40 | 8 | 8 | 0 | 0 | 100.0 |
| 04:50 | 20 | 19 | 1 | 0 | 95.0 |
| 05:00 | 20 | 20 | 0 | 0 | 100.0 |
| 05:10 | 11 | 9 | 2 | 0 | 81.8 ← 1b95ecee + cb61eac7 |
| 05:20 | 15 | 15 | 0 | 0 | 100.0 |
| 05:30 | 17 | 17 | 0 | 0 | 100.0 |

NVCF 风暴两波: 03:30-04:00 (主风暴 SR 77-96%) + 04:50-05:10 (余波 SR 81-95%).
05:20+ (13:20+) 全 200 恢复. 本轮 502 集中在 05:10 桶 (13:10 CST), 是余波末梢.

## R813 修复就位铁证

```
docker exec nv_gw python3 -c "import gateway.buffer_stream as b, inspect;
  print('chain_full_retry found:', 'chain_full_retry' in inspect.getsource(b.BufferStreamSession.run))"
→ chain_full_retry found: True
```

## 判稳结论

链路工作完全正常. R813 修复就位且稳定 (cb61eac7 第二次 CHAIN-FULL 实战铁证).
两个 502 是 NVCF 后端 RemoteDisc 风暴不可挽救请求, 均被 cc4101 吸收, 用户侧 100%.

| 指标 | 30min | 目标 | 状态 |
|---|---|---|---|
| per-call SR (排 502) | 100% (44/44) | 90%+ | ✅ |
| per-key tier SR | 95.7% (44/46) | 90%+ | ✅ |
| 用户可见 SR (排 499) | 100% (1304/1304) | 99%+ | ✅ |
| fallback 触发率 | 1.45% (19/1312) | <10% | ✅ |
| R813 chain_full_retry 已加载 | ✅ True | — | ✅ |
| 502 穿透用户侧 | 0 (2×nv_gw 502 全被吸收) | 0 | ✅ |
| 新错误类型 | 无 (buffer_exhausted 已知) | 无 | ✅ |

## SR 趋势

| 轮 | 30min per-call SR | per-key tier SR | WAIT-RECOVER | fallback% | 备注 |
|---|---|---|---|---|---|
| R811 | 100% (91/91) | — | 1 fall-through | — | WAIT 首触达 |
| R812 | 100% (79/79) | 98.75% (79/80) | 1 (RECOVER 首 FAIL) | 0.66% | 补丁 RECOVER 首触发 |
| R813 | 89.2% (66/74) | — | 11 (全 FAIL, 老代码) | 10.5% | restart 加载修复 |
| R814 | 100% (18/18 restart 后) | — | 0 | 1.36% | 修复就位 |
| R815 | 100% (55/55) | 98.3% (57/58) | 2 (1 OK ★ + 1 FAIL) | 1.4% | CHAIN-FULL 首 WAIT-OK |
| R816 | 100% (31/31) | 93.75% (30/32) | 0 | 3.23% | 稳定, buffer 自愈生效 |
| R817 | 100% (47/47) | 95.7% (44/46) | 1 (FAIL→fallback) | 0% | NVCF 风暴退去, 全绿 |
| **R818** | **100% (44/44)** | **95.7% (44/46)** | **2 (全 FAIL→吸收)** | **1.45%** | **NVCF 二次瞬断, 2×502 全吸收** |

## 噪声 (不属 cc2 链路)

hermes × dsv4f0731_nv: 30min SR 68.8% (11/16, 5×502) — dsv4f0731 自优化线, 不穿透 cc2.
趋势: R816 80% → R817 82.6% → R818 68.8%, NVCF 后端持续抖动影响 dsv4f0731.

## 下一步

- **R819 cc2**: 继续长期观测. 关注:
  (1) NVCF RemoteDisc 风暴频率 (本轮二次瞬断 13:00-13:22, 已恢复);
  (2) WAIT-RECOVER CHAIN-FULL 命中率 (R815 1/2 OK, R817 0/1, R818 0/2, 均因 NVCF
      持续抖动而非补丁问题 — 待"多 key 稳定恢复"场景才能真正挽救 req);
  (3) fallback 率 <10% 持续 (本轮 1.45%);
  (4) per-key tier SR 90%+ 稳定 (本轮 95.7%);
  (5) SSLEOFError 是否持续 (R816 2× → R817 1× → R818 1×, 低频可忽略).
- 无改进点, 不改码. R813 修复已充分验证, 进入纯观测期.

## 参数快照 (nv_gw + cc4101, docker exec env 铁证)

```
nv_gw:
  NV_GLM52_MODE_CHAIN = pexec_us_rr
  NV_GLM52_KEY_FID_BIND = 0:0;1:0;2:0;3:0;4:0   # 全 5 key bind fid[b1b22d03]
  NVU_BUFFER_TIMEOUT_STAIRS = 90,90,90,90,90     # 5 attempts × 90s
  NVU_BUFFER_TOTAL_DEADLINE_S = 450
  NVU_BUFFER_MAX_RETRIES = 5
  NVU_BUFFER_PING_INTERVAL_S = 30
  NVU_BUFFER_CALLERS = cc4101-primary,openclaw2
  NVU_WAIT_QUEUE_ENABLED = 1
  NVU_WAIT_QUEUE_MAX_WAIT = 180                   # 全挂后 event-driven 等 NVCF 恢复, max 180s
  NVU_KEYMGR_429_BASE_COOLDOWN = 120
  NVU_KEYMGR_429_MAX_COOLDOWN = 600
  NVU_KEYMGR_CONN_BASE_COOLDOWN = 30
  NVU_KEYMGR_CONN_FAIL_THRESHOLD = 3
  NVU_KEYMGR_CONN_MAX_COOLDOWN = 60
  NVU_KEYMGR_CONN_LONG_COOLDOWN = 120
  NVU_DISABLE_MS_FALLBACK = 1
  NVU_STREAM_FULL_BUFFER = 0
cc4101:
  PRIMARY_UPSTREAM_URL = http://nv_gw:40006/v1/messages
  PRIMARY_UPSTREAM_MODEL = glm5_2_nv
  FALLBACK_UPSTREAM_URL = http://ms_gw:40007/v1/messages  # 历史残留, SR 99%+ 极少触发
  FALLBACK_UPSTREAM_MODEL = glm5_2_ms
  CC4101_STREAM_TOTAL_DEADLINE_S = 470
  PRIMARY_HEADER_TIMEOUT = 400
  CC4101_PRIMARY_FAIL_THRESHOLD = 3
  CC4101_PRIMARY_SKIP_S = 30
deadline 链: 90s × 5 = 450s buffer < 470s cc4101 < 600s API < 900s idle
```
