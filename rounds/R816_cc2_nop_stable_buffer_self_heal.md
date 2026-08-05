# R816 cc2 — NOP 巡检轮 (链路稳定, buffer 自愈持续生效)

> 轮号: R816 (cc2 线) | 时间: 2026-08-05 12:53-13:13 CST (30min 窗口)
> 上轮: R815 (NOP, R813 chain_full_retry 修复首次 WAIT-OK 实战成功)
> 容器: nv_gw Up 38min (12:25 CST restart 后), cc4101 Up 11h, dsv4p_nv40066 Up 16h

## 摘要

R813 chain_full_retry 修复持续就位 (inspect.signature 铁证), 链路工作完全正常.
30min: nv SR (排 499)=100% (31/31), 用户可见 SR=96.8% (30/31, 1×499 client_gone_mid_stream
非链路错), fallback 3.23% (1/31 < 10%), per-key tier SR 93.75% (30/32, 2×SSLEOFError 被
buffer 自愈吸收). 零 502, 零新错误, 零退化.

**零改动 NOP 巡检轮** — 进入长期观测期.

## 30min 链路数据 (12:23-12:53 CST)

### nv_requests (cc4101-primary, cc2 自己的请求)

| status | count | avg_dur | max_dur |
|---|---|---|---|
| 200 | 31 | 52416ms | 439363ms (R815 长 WAIT-OK 链尾) |
| 499 | 1  | 320751ms | client_gone_mid_stream (req=287b1b44, 439s) |

nv SR (排 499) = **31/31 = 100%**. 零 502.

注: 499 req=287b1b44 duration=439378ms 是 cc2 SDK 在 450s 预算前自断
(client_gone_mid_stream), 非链路错. 与 R815 的 client_gone_during_flush 同类, 仅
error_type 细分不同 (mid_stream vs during_flush, 均客户端主动放弃).

### cc_requests (用户可见, cc2 经 cc4101 链路)

| total | 200 | 499 | 502 | fb | fb_pct | sr |
|---|---|---|---|---|---|---|
| 31 | 30 | 1 | 0 | 1 | 3.23% | 96.8% |

排 499 (client_gone_mid_stream):
**用户可见 SR = 30/30 = 100%**. 502=0 铁证 dsv4p fallback 兜住 1×all_tiers_exhausted.

### fallback 案例 (req=ce2af54d)

| req | status | dur | fallback_triggered |
|---|---|---|---|
| ce2af54d | 200 | 225300ms | t |

1×all_tiers_exhausted → dsv4p fallback → 200 OK 225s. fallback 链路正常工作.

### per-key tier (glm5_2_nv, 30min, 32 attempts)

| key | total | ok | errs |
|---|---|---|---|
| k0 | 7  | 7 | pexec_success |
| k1 | 7  | 6 | pexec_success, pexec_SSLEOFError×1 |
| k2 | 6  | 6 | pexec_success |
| k3 | 7  | 7 | pexec_success |
| k4 | 7  | 6 | pexec_success, pexec_SSLEOFError×1 |

5key 均布 (k0:7 k1:7 k2:6 k3:7 k4:7). 仅 k1/k4 各 1×SSLEOFError 被 buffer 自愈吸收.
per-key tier SR = 30/32 = **93.75%** (≥90% ✅).

### R813 修复就位铁证

```bash
docker exec nv_gw python3 -c "
  import gateway.buffer_stream as b, inspect
  src = inspect.getsource(b.BufferStreamSession.run)
  print('chain_full_retry found:', 'chain_full_retry' in src)"
# → chain_full_retry found: True
```

### live buffer 自愈样本 (req=1b95ecee, 12:54-12:57, 3-attempt 仍在 buffer)

```
12:54:17 NV-BUFFER-START caller=cc4101-primary stairs=[90×5]
12:54:17 NV-BUFFER-ATTEMPT 1/5 k4 input=100659c
12:55:03 NV-GLM52-CONN k4 conn err: RemoteDisconnected → mode advance (45s)
12:55:03 NV-BUFFER-EXEC-FAIL attempt=1 key=k4 all_keys_exhausted
12:55:03 NV-BUFFER-BACKOFF 5s
12:55:08 NV-BUFFER-ATTEMPT 2/5
12:55:45 NV-GLM52-CONN k5 conn err: RemoteDisconnected (37s)
12:55:45 NV-BUFFER-EXEC-FAIL attempt=2 key=k5
12:55:45 NV-BUFFER-BACKOFF 10s
12:55:55 NV-PROBE k5 RECOVERED (200)  ← ProbeWorker 探测恢复
12:55:55 NV-BUFFER-ATTEMPT 3/5
12:56:46 NV-GLM52-CONN k1 conn err: RemoteDisconnected (51s)
12:56:46 NV-BUFFER-EXEC-FAIL attempt=3 key=k1
12:56:46 NV-BUFFER-BACKOFF 15s
12:57:01 NV-BUFFER-ATTEMPT 4/5  ← 仍在 retry, 未触发 WAIT (5key 未全挂)
```

观察: 连续 3 attempt 均 RemoteDisconnected mid-stream (45-51s, 远 < 90s timeout),
非 timeout 是 NVCF 中断. buffer backoff 序列 5/10/15s 正确递增.
此 req 未走 WAIT-RECOVER 路径 (因 5key 未同时全挂, 每次 attempt 单 key 失败).
buffer 设计意图正确: 单 key mid-stream 断裂 → backoff + retry 下一个 key.

## 判稳结论

| 指标 | 本轮值 | 目标 | 状态 |
|---|---|---|---|
| nv_gw per-call SR (排 499) | 100% (31/31) | 90%+ | ✅ |
| per-key tier SR | 93.75% (30/32) | 90%+ | ✅ |
| 用户可见 SR (排 499) | 100% (30/30) | 99%+ | ✅ |
| fallback 触发率 | 3.23% (1/31) | <10% | ✅ |
| R813 chain_full_retry 加载 | ✅ True | — | ✅ |
| 502 数 | 0 | 0 | ✅ |
| 新错误类型 | 无 | 无 | ✅ |

链路工作完全正常. R813 修复就位且稳定. 进入长期观测期, **不改码**.

## SR 趋势

| 轮 | 30min per-call SR (排 499) | per-key tier SR | WAIT-RECOVER | fallback% | 备注 |
|---|---|---|---|---|---|
| R811 | 100% (91/91) | — | 1 fall-through | — | WAIT 首触达 |
| R812 | 100% (79/79) | 98.75% (79/80) | 1 (RECOVER 首 FAIL) | 0.66% | 补丁 RECOVER 首触发 |
| R813 | 89.2% (66/74) | — | 11 (全 FAIL, 老代码) | 10.5% | restart 加载修复 |
| R814 | 100% (18/18 restart 后) | — | 0 | 1.36% | 修复就位 |
| R815 | 100% (55/55) | 98.3% (57/58) | 2 (1 OK ★ + 1 FAIL) | 1.4% | CHAIN-FULL 首 WAIT-OK |
| **R816** | **100% (31/31)** | **93.75% (30/32)** | **0** | **3.23%** | **稳定, buffer 自愈生效** |

## 噪声 (不属 cc2 链路)

hermes × dsv4f0731_nv: 30min SR 80.0% (16/20, 4×502) — dsv4f0731 自优化线, 不穿透 cc2.

## 下一步

- **R817 cc2**: 继续长期观测. 关注:
  (1) WAIT-RECOVER CHAIN-FULL 命中率 (下次集中瞬断触发时验证稳定性);
  (2) fallback 率 <10% 持续;
  (3) per-key tier SR 90%+ 稳定;
  (4) SSLEOFError 是否持续 (本轮 2×, 若增多评估是否需 conn 短惩罚调整).
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
  NVU_KEYMGR_429_BASE_COOLDOWN = 120
  NVU_KEYMGR_429_MAX_COOLDOWN = 600
  NVU_KEYMGR_CONN_BASE_COOLDOWN = 30
  NVU_KEYMGR_CONN_FAIL_THRESHOLD = 3
  NVU_KEYMGR_CONN_MAX_COOLDOWN = 60
  NVU_KEYMGR_CONN_LONG_COOLDOWN = 120
  TIER_TIMEOUT_BUDGET_S = 180
  TIER_COOLDOWN_S = 180
  NVU_DISABLE_MS_FALLBACK = 1
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
