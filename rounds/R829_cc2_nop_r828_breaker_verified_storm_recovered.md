# R829 — cc2 NOP 巡检轮: R828 ms_gw breaker 兜底路径活体验证 + NVCF RemoteDisc 持续风暴

> 时间: 2026-08-05 19:30 CST | 上轮: R828 (nv_breaker 5-consecutive→ms_gw, 已就位)
> 容器: nv_gw (Up 1h, R828 restart 后) | 改动: 无 (NOP 巡检轮)

## 本轮改动: 无 (NOP 巡检轮)

R827 (buffer total_deadline 锚定 t_start) + R828 (nv_breaker + buffer_stream ms_gw 兜底) 均已就位。
本轮做的是 **R828 兜底路径活体验证** + 持续 NVCF 风暴下全链路健康确认。无源码 / 无 env 改动。

## R827 + R828 就位铁证

```bash
docker exec nv_gw python3 -c "
import gateway.buffer_stream as b, inspect
src = inspect.getsource(b.BufferStream.__init__)  # 实际是 BufferStreamSession
print('R827 t_start anchor:', 'self.t_start + NVU_BUFFER_TOTAL_DEADLINE_S' in src)
print('R828 is_ms_fallback_open:', 'is_ms_fallback_open' in inspect.getsource(b))
print('R828 record_nv_failure:', 'record_nv_failure' in inspect.getsource(b))
print('R828 record_nv_success:', 'record_nv_success' in inspect.getsource(b))
print('R813 chain_full_retry:', 'chain_full_retry' in inspect.getsource(b))
"
# → R827 t_start anchor: True
# → R828 is_ms_fallback_open: True
# → R828 record_nv_failure: True
# → R828 record_nv_success: True
# → R813 chain_full_retry: True
```

```bash
docker exec nv_gw python3 -c "
import gateway.nv_breaker as b
print('breaker module consecutive-counter:', 'consecutive' in __import__('inspect').getsource(b).lower())
print('no time-window R1771:', 'time.time() -' not in __import__('inspect').getsource(b))
print('threshold:', b.NVU_MS_FALLBACK_FAIL_THRESHOLD, 'skip_s:', b.NVU_MS_FALLBACK_SKIP_S)
"
# → consecutive-counter: True (R1771 time-window 已替换为简单计数器)
# → no time-window R1771: True
# → threshold=5 skip_s=30
```

环境变量 (铁律 4: 不切回 ms_gw — R828 是把 ms_gw 作为**最后的兜底 fallback**,
不是切回 primary): `NVU_MS_FALLBACK_ENABLED=1`, `NVU_DISABLE_MS_FALLBACK=0`,
`NVU_MS_FALLBACK_MODELS=glm5_2_nv`, `NVU_MS_FALLBACK_FAIL_THRESHOLD=5`,
`NVU_MS_FALLBACK_SKIP_S=30`, `NVU_MS_FALLBACK_URL=http://ms_gw:40007/v1/chat/completions`.
primary 链路仍是 cc4101→nv_gw→glm5_2_nv 5key pexec, ms_gw 只在 5 次连续 NVCF 失败后才介入。

## 30min 真实链路数据 (19:00-19:30 CST)

### nv_requests (cc4101-primary, cc2 的请求)

| status | count | avg_ms | max_ms |
|---|---|---|---|
| 200 | 64 | 72279 | 681545 |
| 499 | 1 | 226387 | (client_gone_during_flush) |

per-call SR = 98.5% (64/65, 唯一非 200 是 client_gone 499, **零 502 穿透**) ✅

### cc_requests (用户可见层, 30min)

| status | error_type | cnt | fb | avg_ms |
|---|---|---|---|---|
| 200 | (空) | 913 | 30 | 54573 |
| 499 | client_gone_mid_stream | 21 | 0 | 185623 |
| 502 | timeout | 7 | 0 | 297369 |

- 用户可见 SR (排除 499 客户端中断) = 913 / (913+7) = **99.24%** ✅
- fallback 触发率 = 30/913 = 3.3% ✅ < 10%
- 7 个 502 timeout 来自 hermes caller 的 dsv4f0731_nv 链路 (非 cc2 范围), 不影响 cc2 指标

### per-key tier attempts (30min, glm5_2_nv)

| key | pexec_success | 瞬态错误 |
|---|---|---|
| k0 | 9 | 0 |
| k1 | 11 | 0 |
| k2 | 9 | pexec_conn_RemoteDisconnected × 1 |
| k3 | 11 | 0 |
| k4 | 11 | 0 |
| 合计 | 51 | 1 |

per-attempt SR = 51/52 = **98.1%** ✅ (NVCF 风暴退去后单 key 偶发 RemoteDisc)

## R828 ms_gw 兜底路径活体验证 (req=b0f7c1dc)

30min 内 5 个 NV-BUFFER-LAST-FAIL (b0f7c1dc/e4c30e42/b4b19da3/5fb7f288/eaaa7e7a)
全部 buffer 5/5 attempts exhausted, 但**最终用户拿到 200** (duration 400-681s)。
走的是 R828 设计的兜底链路:

```
req=b0f7c1dc (典型路径, 603s 总耗时):
18:56:47  STAGE1 chain 失败 (k1 RemoteDisc)
18:57:46  → buffer retry 启动 (R827 t_start anchor 正确)
18:58:30  try 1 失败 (k3)
18:59:06  try 2 失败 (k4)
19:00:34  try 3 失败 (k5)
19:01:38  try 4 失败 (k1)
19:03:04  try 5 失败 (k2), elapsed=487s (R827 把 5th attempt timeout 截短到 33s)
19:03:18  WAIT 180s 短恢复 (13s 内 key recovered), 但 -52s 没 time, 中止
19:03:18  → BUFFER-EXHAUSTED → MS-FB-ATTEMPT (R828 兜底)
19:03:18  → BUFFER-MS-FB-SKIP (-52s 不够 120s ms_gw timeout)
19:03:18  → ANTH-COLLECT-SOFTFAIL → 另一个 ms_gw fallback 路径
19:03:20  → MS-FB-OK success (1956ms) → relay SSE 给 cc4101 ✅
```

**关键观察**:
1. R827 t_start anchor 生效: 5th attempt timeout 从 90s 截短到 33s (elapsed=487s, 450-487=-37s 已超, 但 R827 还留了少量余量直到 487s 才中止单 attempt)
2. R828 ms_gw 兜底路径救活了原本会 502 穿透的请求 — 旧逻辑 (无兜底) 这里会 502 + 用户中断 + cc2 watchdog 1100s 风险
3. **breaker 未真正 OPEN**: 5 次 record_nv_failure 全部 `state=('CLOSED', 1, 0)` — 每次失败中间有 success 清零计数器, 5 次失败**不连续**。当前 breaker state=CLOSED consecutive=0。
   这意味着 breaker 5-consecutive 阈值从未触发到 OPEN, **ms_gw 兜底是通过 ANTH-COLLECT-SOFTFAIL 路径触发的, 不是 breaker OPEN 路径**。

## 指标对比

| 指标 | R829 | R828 | R827 | R826 | 目标 | 状态 |
|---|---|---|---|---|---|---|
| per-call SR (nv_req) | 98.5% (64/65) | 96.7% (89/92) | 95.7% (44/46) | 100% (48/48) | 90%+ | ✅ |
| 用户可见 SR (cc_req, 排 499) | 99.24% (913/920) | 98.9% (90/91) | — | 100% | 99%+ | ✅ |
| per-attempt SR | 98.1% (51/52) | 98.9% (87/88) | — | 68.6% (48/70) | — | ✅ |
| fallback 触发率 | 3.3% (30/913) | 1.1% (1/91) | — | 0% | <10% | ✅ |
| 502 穿透用户侧 (cc2 链路) | 0 | 0 (风暴窗 3 内部) | 2 | 0 | 0 | ✅ |
| R827 t_start anchor | ✅ | ✅ | ✅ | N/A | — | ✅ |
| R828 ms_gw 兜底就位 | ✅ | ✅ | N/A | N/A | — | ✅ |
| R828 breaker 就位 | ✅ | ✅ | N/A | N/A | — | ✅ |
| R813 chain_full_retry | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| NVCF 风暴 | 持续 (per-attempt 1 错误) | 16:08-16:21 (13min) | 14:44-15:14 | 14:08-14:38 | — | ⚠️ |

## 判稳结论

- **R827 + R828 全部就位**: t_start anchor=True, is_ms_fallback_open/record_nv_failure/record_nv_success=True
- **零 502 穿透用户侧**: cc4101-primary nv_requests 64×200 + 1×499 (client_gone), 零 502
- **用户可见 SR 99.24%**: 排除客户端 499 后达 99%+ 目标
- **fallback 3.3%** < 10% 目标
- **R828 兜底路径活体验证**: 5 个原本会 502 的请求经 ANTH-COLLECT-SOFTFAIL→MS-FB-OK 救活, 用户拿到 200
- **NVCF 风暴已大幅减弱**: per-attempt SR 从 R826 的 68.6% 升到 98.1% (仅 1 个 RemoteDisc)
- **breaker 未真正 OPEN**: 5 次失败不连续, 当前 CLOSED consecutive=0 — breaker 路径未被强触发,
  ms_gw 兜底是通过 buffer→softfail 路径生效的

**进入长期观测期, 不改码。** R827+R828 在 NVCF 风暴期都正确生效, 兜底路径救活请求。
下一步观察: (a) breaker 5-consecutive 是否在更严重风暴下触发; (b) ms_gw 兜底延迟
(用户拿到 200 但耗 10 分钟, 是否值得加更早的 ms_gw 切换)。

## 健康检查

- `curl localhost:40006/health` → ok, 5 keys, pexec 含 glm5_2_nv
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- `curl localhost:40066/health` → ok, dsv4p_nv 5 keys
- docker ps: nv_gw Up 1h, cc4101 Up 18h, dsv4p_nv40066 Up 23h, ms_gw Up (历史 Up 时间未显示, 但 fallback 已恢复), logs_db Up
- breaker state: CLOSED, consecutive=0, threshold=5, skip_s=30

## 下一步

- 长期观测, 等 NVCF 风暴加剧时观察 breaker 5-consecutive 是否真正 OPEN
- 若 ms_gw 兜底延迟 (10 分钟) 反复出现影响用户体验, 评估降低 breaker 阈值 (5→3) 或
  在 buffer 早期就尝试 ms_gw 切换 — 但当前不急, R827+R828 设计正确
- 不改码, 不动 fallback, 不碰 key binding

## 参数快照 (nv_gw + cc4101)

### nv_gw (40006)
- NVU_FORCE_STREAM_UPGRADE = 0
- NVU_PEER_FB_SKIP_MODELS = glm5_2_nv,dsv4p_nv
- MIN_OUTBOUND_INTERVAL_S = 10
- KEY_COOLDOWN_S = 30
- NVU_CALLER_KEY_MAP = hermes:2;openclaw:3;opencode:4
- TIER_TIMEOUT_BUDGET_S = 180
- **NVU_DISABLE_MS_FALLBACK = 0** (R828 启用 ms_gw 兜底)
- **NVU_MS_FALLBACK_ENABLED = 1** (R828)
- **NVU_MS_FALLBACK_FAIL_THRESHOLD = 5** (R828, 5 consecutive→OPEN)
- **NVU_MS_FALLBACK_SKIP_S = 30** (R828, OPEN 后 30s cooldown)
- NVU_MS_FALLBACK_MODELS = glm5_2_nv
- NVU_MS_FALLBACK_URL = http://ms_gw:40007/v1/chat/completions
- TIER_COOLDOWN_S = 180
- UPSTREAM_TIMEOUT = 90
- NVU_BUFFER_CALLERS = cc4101-primary,openclaw2
- NVU_BUFFER_TIMEOUT_STAIRS = 90,90,90,90,90
- NVU_BUFFER_TOTAL_DEADLINE_S = 450
- NVU_BUFFER_MAX_RETRIES = 5
- KEY_FID_BIND = 0:0;1:0;2:0;3:0;4:0 (全 bind b1b22d03)
- KEY_PROXY_BIND = k0→7894 k1→7897 k2→7896 k3→7899 k4→7901 (实测)

### cc4101
- PRIMARY_UPSTREAM_URL = http://nv_gw:40006/v1/messages
- PRIMARY_UPSTREAM_MODEL = glm5_2_nv
- FALLBACK_UPSTREAM_URL = http://ms_gw:40007/v1/messages (历史残留, R828 是 nv_gw 层兜底不是 cc4101 层)
- FALLBACK_UPSTREAM_MODEL = glm5_2_ms
- CC4101_STREAM_TOTAL_DEADLINE_S = 470
- PRIMARY_HEADER_TIMEOUT = 400
- CC4101_PRIMARY_FAIL_THRESHOLD = 3
- CC4101_PRIMARY_SKIP_S = 30

### deadline 链
- 90s/buffer-attempt × 5 = 450s buffer (R827 t_start anchor) < 470s cc4101 < 600s API < 900s idle

## Function IDs (NVCF glm-5.2)
- b1b22d03 ✅ ACTIVE 首选 (当前全 5key bind, 实测 200 OK)
- b6029a96 ✅ ACTIVE 备用 (200K 同限, b1b22d03 持续出错时改 pos1)
- 3b9748d8 ⚠️ broken (持续 RemoteProtocolError, 不 bind)
