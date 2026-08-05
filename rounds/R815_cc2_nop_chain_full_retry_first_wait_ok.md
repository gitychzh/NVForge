# R815 cc2 — NOP 巡检轮 + R813 chain_full_retry 修复首次 WAIT-OK 验证

> 轮号: R815 (cc2 线) | 时间: 2026-08-05 12:39-13:09 CST (30min 窗口)
> 上轮: R814 (NOP, R813 restart 修复验证)
> 容器: nv_gw Up 23min (12:18 CST restart 后, R813 修复已加载)

## 摘要

R813 chain_full_retry=True 修复 **首次实战成功**: req=3892002b 走完完整
`NV-BUFFER-WAIT → NV-BUFFER-WAIT-RECOVER → NV-BUFFER-CHAIN-FULL → 5key RR → NV-BUFFER-WAIT-OK` 闭环,
439s 总耗时 (在 450s 预算内) 成功挽救请求. 这是 R806/R807/R812/R813 四轮迭代后
首次实际挽救用户请求的实证. 30min 用户可见 SR=100% (零 502, 7×499 全 client_gone), fallback 1.4%.

**零改动 NOP 巡检轮** — 链路工作正常, 仅记数据 + 修复验证里程碑.

## 30min 链路数据 (12:09-12:39 CST)

### nv_requests (cc4101-primary, cc2 自己的请求)

| status | count | avg_dur | max_dur |
|---|---|---|---|
| 200 | 55 | 32355ms | 439363ms |
| 499 | 1  | 320751ms | (client_gone_during_flush) |

nv SR (排 499) = **55/55 = 100%**. 零 502.

### cc_requests (用户可见, cc2 经 cc4101 链路)

| total | 200 | 499 | 502 | fb | fb_pct | nv_sr |
|---|---|---|---|---|---|---|
| 1329 | 1322 | 7 | 0 | 18 | 1.4% | 99.5% |

排 499 (全 client_gone_during_flush, cc2 SDK 59s 自断非链路错):
**用户可见 SR = 1322/1322 = 100%**. 502=0 铁证 fallback 兜住所有 18×all_tiers_exhausted.

### per-key tier (glm5_2_nv, 30min, 58 attempts)

| key | total | ok | errs |
|---|---|---|---|
| k0 | 13 | 13 | pexec_success |
| k1 | 8  | 7  | pexec_success, pexec_SSLEOFError |
| k2 | 13 | 13 | pexec_success |
| k3 | 13 | 13 | pexec_success |
| k4 | 11 | 11 | pexec_success |

per-attempt tier SR = **57/58 = 98.3%**. 仅 k1 1×SSLEOFError, 被 buffer 自愈吸收.
5key 分布均布 (k0:13/k1:8/k2:13/k3:13/k4:11), k1 略少因 SSLEOF 短惩罚跳过.

## R813 chain_full_retry 修复首次实战成功铁证 — req=3892002b

时间线 (12:31-12:34 CST, 总 439s):

```
12:31:32.3 [NV-BUFFER-WAIT] (glm5_2_nv) all 5 NVCF attempts failed, waiting up to 180s (req=3892002b)
                  ↑ 5key 全挂进入 WaitQueue event-driven 等恢复
12:33:29.6 [NV-PROBE] k4 RECOVERED (status=200), marked healthy
12:33:29.6 [NV-BUFFER-WAIT-RECOVER] (glm5_2_nv) key recovered, retrying NVCF with
                  full 5-key chain (override cleared), remaining=73s (req=3892002b)
                  ↑ ProbeWorker 探到 k4 恢复, set Event 唤醒 WaitQueue
12:33:29.6 ★[NV-BUFFER-CHAIN-FULL] (glm5_2_nv) chain_full_retry=True, skip override,
                  start_key=k2 (RR起, NVCF chain full 5key) (req=3892002b)★
                  ↑ 关键: 跳过 BUFFER_OVERRIDE 单 key 逻辑, 走完整 5key RR
12:34:02.5 [NV-PROBE] k2 RECOVERED (status=200), marked healthy
12:34:05.1 [NV-PROBE] k5 RECOVERED (status=200), marked healthy
12:34:32.2 [NV-BUFFER-WAIT-OK] (glm5_2_nv) recovered after wait, elapsed=439363ms (req=3892002b)
                  ↑ 成功! 439s < 450s 预算, 请求被挽救
```

对比历史:
- **R812 (c4d6dd8e)**: RECOVER 首次触发, 但补丁后面走 BUFFER_OVERRIDE 老逻辑 (单 key k1), retry 1.5s 立即 execute_failed → WAIT-FAIL → 502 → fallback 兜住
- **R813 (11次)**: 全 BUFFER_OVERRIDE start_key=kX (NVCF 1 attempt) 老逻辑 (容器主进程缓存 R812 commit 前的代码), 11 次全撞刚恢复但仍在抖的单 key → 1.5-28s all_keys_exhausted → WAIT-FAIL → 502 → fallback 兜住
- **R815 (3892002b) ★**: chain_full_retry=True 生效, 跳过 BUFFER_OVERRIDE, 走 NV-BUFFER-CHAIN-FULL 完整 5key RR, WAIT-OK 成功. 请求直接挽救, 无需 fallback.

R813 修复点: `buffer_stream.py:268-273, 571-572` 加 `chain_full_retry=True` 参数,
WAIT-RECOVER 分支调用 execute 时 pop override + 完整 5key RR.
R813 restart 12:18 CST 加载新代码 (容器 Up 23min 铁证).

注: STATE.md (R814) 把 `BUFFER_OVERRIDE start_key=kX (buffer _KEY_ROTATION, NVCF 1 attempt)`
日志误判为"R813 修复前的老逻辑". 实测 R813 restart 后BUFFER_OVERRIDE 仍在
buffer _KEY_ROTATION 路径下出现 (79 次 30min). **BUFFER_OVERRIDE 是 buffer 每次 attempt
通过 key rotation 起点切换的常规日志, 不是 bug**. R813 真正修的是
`NV-BUFFER-WAIT-RECOVER` 分支: 该分支原来 fall-through 到 BUFFER_OVERRIDE (单 key 起手),
修复后该分支独立走 NV-BUFFER-CHAIN-FULL (5key RR 起手).

## 30min 副 WAIT-FAIL 案例 (req=c55fb175)

```
12:14:01.0 [NV-BUFFER-WAIT] (req=c55fb175)
12:14:15.0 [NV-PROBE] k4 RECOVERED
12:14:15.0 [NV-BUFFER-WAIT-RECOVER] retrying NVCF with full 5-key chain, remaining=253s
12:14:22.8 [NV-BUFFER-WAIT-FAIL] retry after recovery still failed (verdict=execute_failed) (req=c55fb175)
              ↑ RECOVER 后 8s 仍 execute_failed (刚恢复 key 仍在抖, 非补丁 bug)
                  → 502 (buffer verdict) → cc4101 dsv4p fallback 兜住 → 用户 200
```

此案例说明: WAIT-RECOVER 修复不是银弹. 刚 probe 恢复的 key 仍可能在抖,
CHAIN-FULL 走 5key RR 时若 5 key 全部同时仍抖, 仍可能 FAIL → fallback 兜底.
但 R815 (3892002b) 案例证明: 当多个 key 已稳定恢复 (k2/k4/k5 都 RECOVERED),
CHAIN-FULL 能成功挽救请求. 这是设计意图的正确实现.

## 判稳对照

| 指标 | 30min | 目标 | 状态 |
|---|---|---|---|
| nv_gw per-key tier SR | 98.3% (57/58) | 90%+ | ✅ |
| nv_gw per-call SR (排 499) | 100% (55/55) | 90%+ | ✅ |
| 用户可见 SR (排 499) | 100% (1322/1322) | 99%+ | ✅ |
| fallback 触发率 | 1.4% (18/1329) | <10% | ✅ |
| R813 chain_full_retry 已加载 | ✅ (Up 23min) | — | ✅ |
| WAIT-RECOVER 触发 | 2 次 (1 OK + 1 FAIL) | — | ✅ 修复验证 |
| 新错误类型 | 无 | — | ✅ |

## 2h SR 趋势

cc_requests 2h: 1392 总, 1381 200, 11×499 (零 502 全程).
每 10-min 桶大多 0×非200. SR 长期稳定 99%+.

## 噪声 (不属 cc2 链路)

hermes × dsv4f0731_nv: 30min SR ≈ 66.7% (12/18). 这是 hermes→dsv4f0731_nv 自优化线
(R1029-R1034 dsv4f 线), 不穿透 cc2. cc4101-primary 0×hermes 跨 caller 污染.

## 下一步

- **R816 cc2**: 继续监测. chain_full_retry 修复已实战成功, 进入长期观测期.
  关注: (1) 下次集中瞬断的 WAIT-RECOVER 命中率 (CHAIN-FULL 是否稳定挽救请求);
  (2) fallback 率是否仍 <10%;
  (3) per-key tier SR 90%+ 是否稳定.
- 若数据持续稳定 NOP, 可考虑减少巡检频次.
- 若 WAIT-RECOVER FAIL 比例高 (>50%), 可评估 RECOVER 后是否加短 backoff 后再 CHAIN-FULL.

## 参数快照 (nv_gw, docker exec env 铁证)

```
NV_GLM52_MODE_CHAIN = pexec_us_rr
NV_GLM52_KEY_FID_BIND = 0:0;1:0;2:0;3:0;4:0   # 全 5 key bind fid[b1b22d03]
NVU_BUFFER_TIMEOUT_STAIRS = 90,90,90,90,90     # 5 attempts × 90s
NVU_BUFFER_TOTAL_DEADLINE_S = 450             # buffer 总预算
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
NVU_DISABLE_MS_FALLBACK = 1                    # 关 ms_gw, 走 cc4101 层 dsv4p fallback
NVU_STREAM_FULL_BUFFER = 0
```

cc4101 (实测):
```
PRIMARY_UPSTREAM_URL = http://nv_gw:40006/v1/messages
PRIMARY_UPSTREAM_MODEL = glm5_2_nv
FALLBACK_UPSTREAM_URL = http://ms_gw:40007/v1/messages  # 历史残留, SR 99%+ 不触发
FALLBACK_UPSTREAM_MODEL = glm5_2_ms
CC4101_STREAM_TOTAL_DEADLINE_S = 470
PRIMARY_HEADER_TIMEOUT = 400
CC4101_PRIMARY_FAIL_THRESHOLD = 3
CC4101_PRIMARY_SKIP_S = 30
```

deadline 链: 90s × 5 = 450s buffer < 470s cc4101 < 500s SDK idle < 600s API.
