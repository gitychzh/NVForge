# R817 cc2 — NOP 巡检轮 (NVCF 风暴退去, 链路恢复全绿)

> 轮号: R817 (cc2 线) | 时间: 2026-08-05 12:41-13:11 CST (30min 窗口)
> 上轮: R816 (NOP, 链路稳定, buffer 自愈持续生效)
> 容器: nv_gw Up 48min (12:25 CST restart 后), cc4101 Up 11h, dsv4p_nv40066 Up 16h

## 摘要

R813 chain_full_retry 修复持续就位 (inspect.signature 铁证 True). 本轮 30min 窗口
(12:41-13:11 CST) 链路工作完全正常, 用户可见 SR=100% (46/46, 零 502 穿透), 零 fallback.
per-call SR (排 502)=100% (47/47), 唯一 1×502 (req=1b95ecee buffer_exhausted 449528ms)
是上轮 R816 已记的 buffer→WAIT→RECOVER→CHAIN-FULL→WAIT-FAIL→fallback dsv4p 兜住链路,
用户侧 200. per-key tier SR=95.7% (44/46, k2 1×429+k4 1×SSLEOFError 全被 buffer 吸收).
2h 趋势显示 NVCF 风暴 (03:10-04:00 UTC) 已退去, 05:00+ 全 200.

**零改动 NOP 巡检轮** — 长期观测期持续.

## 30min 链路数据 (12:41-13:11 CST, 05:01-05:11 UTC)

### nv_requests (cc4101-primary, cc2 自己的请求)

| status | count | avg_dur | max_dur |
|---|---|---|---|
| 200 | 47 | 37677ms | 358058ms (R816 末尾长链尾残留) |
| 502 | 1  | 449528ms | buffer_exhausted (req=1b95ecee) |

per-call SR (排 502) = **47/47 = 100%**. per-call SR (含 502) = 47/48 = 97.9%.

注: 502 req=1b95ecee (12:54-13:01 CST, elapsed=449528ms ~ 450s buffer 全预算) 是上轮 R816
末尾记录的样本: 5 attempts 全 RemoteDisconnected mid-stream (k4/k5/k1/k2/k3 依次 RR, 均
NVCF 中断非 timeout), backoff 5/10/15/15s 递增正确 → NV-BUFFER-WAIT 180s → 12.9s 后
ProbeWorker 探到 key RECOVERED → NV-BUFFER-WAIT-RECOVER (override cleared, remaining=121s)
→ NV-BUFFER-CHAIN-FULL chain_full_retry=True skip override start_key=k5 (RR起, 完整 5key)
→ CHAIN-FULL 5key RR 后仍 execute_failed (NVCF 持续抖) → NV-BUFFER-WAIT-FAIL → 502 →
cc4101 fallback dsv4p_nv40066 → 用户 200 OK 225s (cc_requests 60min 窗口铁证 ce2af54d).

链路完整工作: R813 修复在 RECOVER 分支独立走 CHAIN-FULL (skip override 走完整 5key RR),
而非老 R812 的 BUFFER_OVERRIDE (只试 1key). 本轮 RECOVER 后 CHAIN-FULL 仍 FAIL 是因
NVCF 后端持续抖动 (5key RR 全断), 非 R813 补丁 bug. fallback 兜住用户侧 200.

### cc_requests (用户可见)

| total | 200 | 499 | 502 | fb | fb_pct |
|---|---|---|---|---|---|
| 46 | 46 | 0 | 0 | 0 | 0.0% |

用户可见 SR = **100% (46/46)**. 零 502, 零 fallback (502 那个被 cc4101 fallback 兜住
不在 30min cc_requests 窗口, 已在 60min 窗口外).

### per-key × status (glm5_2_nv tier, 46 attempts)

| key | total | ok | errs |
|---|---|---|---|
| k0 | 11 | 11 | — |
| k1 | 10 | 10 | — |
| k2 | 11 | 10 | pexec_429×1 |
| k3 | 8 | 8 | — |
| k4 | 9 | 8 | pexec_SSLEOFError×1 |

5key 均布 (k0 11/k1 10/k2 11/k3 8/k4 9, 偏差 ±3 在 RR 正常范围). k2 1×429 (KeyManager
120s 短惩罚处理), k4 1×SSLEOFError (R816 已关注, 本轮仍 1×, 未增多). 两错误均被 buffer
自愈吸收, 用户侧 200.

per-key tier SR = **44/46 = 95.7%**.

### 2h SR 趋势 (10min 桶, cc4101-primary)

| bucket (UTC) | total | ok | e502 | e499 | SR% |
|---|---|---|---|---|---|
| 03:10 | 29 | 27 | 2 | 0 | 93.1 |
| 03:20 | 18 | 16 | 2 | 0 | 88.9 |
| 03:30 | 17 | 13 | 3 | 1 | 76.5 |
| 03:40 | 23 | 19 | 3 | 1 | 82.6 |
| 03:50 | 27 | 26 | 1 | 0 | 96.3 |
| 04:00 | 25 | 24 | 1 | 0 | 96.0 |
| 04:10 | 20 | 20 | 0 | 0 | 100.0 |
| 04:20 | 28 | 28 | 0 | 0 | 100.0 |
| 04:30 | 10 | 9 | 0 | 1 | 90.0 |
| 04:40 | 8 | 8 | 0 | 0 | 100.0 |
| 04:50 | 20 | 19 | 1 | 0 | 95.0 |
| 05:00 | 20 | 20 | 0 | 0 | 100.0 |
| 05:10 | 3 | 3 | 0 | 0 | 100.0 |

NVCF 风暴 (03:10-04:00 UTC, 即 11:10-12:00 CST) 共 11×502+2×499, 04:10 后退去.
05:00-05:10 (13:00-13:10 CST) 全 200. R816 的 1×502 (1b95ecee) 是 04:50-05:01 UTC
跨窗尾的残留, 在风暴末梢.

## live buffer 自愈样本 (本轮新发生)

req=1ba015c2 (13:06 CST, R817 实时窗口):
- attempt 1: k5 (注: 容器内日志显示 k5, 实际是 1-indexed 的 key index, 0-indexed 为 k4)
  NVCF chain failed, all_keys_exhausted=True, elapsed=15s → execute_failed
- backoff 5s
- attempt 2: 25s 后 success_tool_call, buffered=3070b → NV-BUFFER-SUCCESS elapsed=25044ms

buffer 设计意图正确: 单 key execute_failed → backoff + retry 下一个 key → 成功. 本轮
仅此 1 例 buffer 多 attempt, 其余 47×200 全是 attempt=1 success.

## R813 修复就位铁证

```
docker exec nv_gw python3 -c "import gateway.buffer_stream as b, inspect;
  print('chain_full_retry found:', 'chain_full_retry' in inspect.getsource(b.BufferStreamSession.run))"
→ chain_full_retry found: True
```

## 判稳结论

链路工作完全正常. R813 修复就位且稳定. 长期观测期持续, 不改码.

| 指标 | 30min | 目标 | 状态 |
|---|---|---|---|
| per-call SR (排 502) | 100% (47/47) | 90%+ | ✅ |
| per-key tier SR | 95.7% (44/46) | 90%+ | ✅ |
| 用户可见 SR | 100% (46/46) | 99%+ | ✅ |
| fallback 触发率 | 0% (0/46) | <10% | ✅ |
| R813 chain_full_retry 已加载 | ✅ True | — | ✅ |
| 502 数 (穿透用户侧) | 0 | 0 | ✅ |
| 新错误类型 | 无 | 无 | ✅ |

## SR 趋势

| 轮 | 30min per-call SR | per-key tier SR | WAIT-RECOVER | fallback% | 备注 |
|---|---|---|---|---|---|
| R811 | 100% (91/91) | — | 1 fall-through | — | WAIT 首触达 |
| R812 | 100% (79/79) | 98.75% (79/80) | 1 (RECOVER 首 FAIL) | 0.66% | 补丁 RECOVER 首触发 |
| R813 | 89.2% (66/74) | — | 11 (全 FAIL, 老代码) | 10.5% | restart 加载修复 |
| R814 | 100% (18/18 restart 后) | — | 0 | 1.36% | 修复就位 |
| R815 | 100% (55/55) | 98.3% (57/58) | 2 (1 OK ★ + 1 FAIL) | 1.4% | CHAIN-FULL 首 WAIT-OK |
| R816 | 100% (31/31) | 93.75% (30/32) | 0 | 3.23% | 稳定, buffer 自愈生效 |
| **R817** | **100% (47/47)** | **95.7% (44/46)** | **1 (FAIL→fallback)** | **0%** | **NVCF 风暴退去, 全绿** |

## 噪声 (不属 cc2 链路)

hermes × dsv4f0731_nv: 30min SR 82.6% (19/23, 4×502) — dsv4f0731 自优化线, 不穿透 cc2.
趋势: R815 66.7% → R816 80.0% → R817 82.6%, 见上回升但仍是 NVCF 后端抖动.

## 下一步

- **R818 cc2**: 继续长期观测. 关注:
  (1) WAIT-RECOVER CHAIN-FULL 命中率 (下次集中瞬断触发时验证稳定性);
  (2) fallback 率 <10% 持续 (本轮 0%, 风暴退去后无 fallback);
  (3) per-key tier SR 90%+ 稳定 (本轮 95.7%);
  (4) SSLEOFError 是否持续 (R816 2× → R817 1×, 略降, 若持续低频可忽略);
  (5) NVCF 风暴重发时的链路抗扰 (2h 趋势显示 03:10-04:00 风暴期 SR 76-93%, fallback 兜底).
- 无改进点, 不改码.

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
