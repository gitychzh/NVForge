# R810 — NOP 巡检轮 (BUFFER 3-attempt 自愈实战样本, R806 WAIT-RECOVER 仍 0 触发)

> 时间: 2026-08-05 11:11 CST
> 上轮: R809 (NOP — BUFFER 自愈实战观测 req=bb5a29b6 2-attempt 35s 成功)
> 容器: nv_gw StartedAt=2026-08-05T02:32:28Z (10:32:28 CST, 已运行 39min, R806 补丁在容器内)

## 本轮改动

**NOP — 无源码 / 无 env / 无容器重启**

本轮工作: 接棒 + 拉数据 + 交叉核实 + BUFFER 3-attempt 自愈路径实战观测 (req=4892ea40).

## 数据 (30min, 2026-08-05 11:10 CST)

### cc2 自己链路 (cc4101-primary × glm5_2_nv)

| 指标 | 实测 | 目标 | 状态 |
|---|---|---|---|
| nv_requests SR | 100% (88/88) | 90%+ | ✅ |
| cc4101 cc_requests SR | 100% (88/88 全 200) | 99%+ | ✅ |
| fallback 触发率 | 1.0% (1/98, f\|98 → fb=1) | <10% | ✅ |
| cc4101 499 | 0 | - | ✅ |
| 容器健康 | nv_gw=ok, cc4101=ok, dsv4p=ok | - | ✅ |

### 30min per-attempt tier 错误分布 (nv_tier_attempts, glm5_2_nv)

| k | pexec_success | RemoteDisconnected | empty_200 | 529_overloaded | NVCFPexecTimeout |
|---|---|---|---|---|---|
| k0 | 20 | 2 | 0 | 0 | 0 |
| k1 | 19 | 1 | 2 | 1 | 0 |
| k2 | 17 | 1 | 2 | 0 | 0 |
| k3 | 18 | 4 | 1 | 0 | 0 |
| k4 | 14 | 3 | 0 | 0 | 1 |

总计: 88 pexec_success + 11 RemoteDisconnected + 5 empty_200 + 1 529_overloaded + 1 NVCFPexecTimeout = 106 tier attempts.
per-attempt SR = 88/106 = 83.0% (NVCF 单 key 配额/RemoteDisconnected 噪声被 buffer retry 全吸收).
5 key 分布基本均布 (k0:22 / k1:23 / k2:20 / k3:23 / k4:18 attempts, fid=b1b22d03).

### 30min error_type 分类 (nv_requests)

- all_tiers_exhausted × 6 (avg_dur=122065ms) — "5key 全挂瞬间" tag, 实质是 buffer 重试期间 attempt 级 all_keys_exhausted 信号, 不等价于 WAIT-RECOVER 触发
- NVStream_IncompleteRead × 1 (avg_dur=35764ms)

### BUFFER 3-attempt 自愈实战样本 (req=4892ea40, 11:09:47-11:11:29)

```
[11:10:21.4] NV-KEYMGR transport_err tier=glm5_2_nv k3 type=RemoteDisconnected penalty=5s (no conn_count)
[11:10:21.4] NV-BUFFER-EXEC-FAIL attempt 1 key=k3 all_keys_exhausted=True (4892ea40)
[11:10:21.4] NV-BUFFER-VERDICT attempt=1 verdict=None reason=execute_failed elapsed=34s
[11:10:21.4] NV-BUFFER-RETRY attempt=1 failed (execute_failed), resetting for retry
[11:10:21.4] NV-BUFFER-BACKOFF backing off 5s before attempt 2
[11:10:26.4] NV-BUFFER-ATTEMPT attempt=2/5 timeout=90s
[11:10:32.9] NV-KEYMGR transport_err tier=glm5_2_nv k4 type=SSLEOFError penalty=10s (no conn_count)
[11:10:32.9] NV-BUFFER-EXEC-FAIL attempt 2 key=k4 all_keys_exhausted=True (4892ea40)
[11:10:32.9] NV-BUFFER-VERDICT attempt=2 verdict=None reason=execute_failed elapsed=46s
[11:10:32.9] NV-BUFFER-RETRY attempt=2 failed (execute_failed), resetting for retry
[11:10:32.9] NV-BUFFER-BACKOFF backing off 10s before attempt 3
[11:10:42.9] NV-BUFFER-ATTEMPT attempt=3/5 timeout=90s
[11:11:29.6] NV-BUFFER-VERDICT attempt=3 verdict=success_tool_call content=0c tool(id=True,args=True) fr=tool_calls done=True elapsed=102s
[11:11:29.6] NV-BUFFER-FLUSH flushing 4320b verdict=success_tool_call
[11:11:29.6] NV-BUFFER-SUCCESS flushed 4320b after 3 attempt(s), elapsed=102666ms
```

- 3-attempt 总耗时 102.7s (远 < buffer 450s 总预算)
- attempt=1 k3 RemoteDisconnected → attempt=2 k4 SSLEOFError → attempt=3 k0/k1/k2 任一成功
- KeyManager 拉黑 k3 5s, k4 10s (短惩罚, 不累计 conn_count — 设计意图)
- **这正是 buffer 多层 retry 的设计意图: 单 key 配额/transport 闪挫被吸收, 不需要 fallback, 不需要 WAIT-RECOVER**

### R806 WAIT-RECOVER 补丁就位核实

- `docker logs nv_gw --since 30m | grep -c "NV-BUFFER-WAIT-RECOVER"` = **0**
- 30min 窗口无集中瞬断, WAIT-RECOVER 路径仍 0 触发
- 补丁字串仍在容器内 buffer_stream.py:527-557 (R808 已静态审查)

## 判稳结论

| 指标 | 实测 | 目标 | 状态 |
|---|---|---|---|
| nv_gw per-key SR | 100% (88/88) | 90%+ | ✅ |
| 用户可见 SR | 100% (88/88) | 99%+ | ✅ |
| fallback 触发率 | 1.0% (1/98) | <10% | ✅ |
| 容器健康 | nv_gw/cc4101/dsv4p 全 ok | - | ✅ |
| R806 补丁就位 | ✅ 字串在容器内 | - | 待实测 |
| 全挂场景 (WAIT-RECOVER) | 0 (未触发) | - | 补丁未测 |

**NOP 巡检轮** — R806 补丁继续待测.

## 噪声说明 (不属 cc2 链路, 不计入决策)

- hermes × dsv4f0731_nv: 30min SR 30% (3/10, 7×502) — dsv4f 自优化线持续不稳 (R1029-R1030 RemoteDisconnected storm), 不穿透 cc4101-primary
- 进程类信号: `all_tiers_exhausted × 6` 是 buffer attempt 级 all_keys_exhausted tag, 已被 buffer retry 在 3-attempt 内吸收至 200, **不触发** WAIT-RECOVER (因为 `_remaining` 余额充足)

## SR 趋势

| 轮 | 30min SR (cc4101-primary) | per-attempt tier SR | 备注 |
|---|---|---|---|
| R807 | 98.9% (91/92) | 98.9% | WAIT-RECOVER 1-key 弱点 (上轮容器实例, R806 补丁未加载) |
| R808 | 100% (78/78) | 100% (87/87) | R806 补丁已加载, 当前窗口无集中瞬断 |
| R809 | 100% (83/83) | 82.7% (81/98) | BUFFER 自愈实战 (bb5a29b6 2-attempt 35s) |
| **R810** | **100% (88/88)** | **83.0% (88/106)** | BUFFER 3-attempt 自愈实战 (4892ea40 102.7s) |

注: per-attempt tier SR 持续 ~82-83% 反映 NVCF 单 key 配额/transport 噪声, 由 buffer retry 性能吸收为 100% 用户可见.

## 下一步

- **R811**: 继续监测集中瞬断. 期望日志出现 `NV-BUFFER-WAIT-RECOVER ... 5-key chain (override cleared), remaining=Xs`.
- 本轮不动码, 等数据.
- 长期候选 (R806 补丁触发后仍 WAIT-FAIL 时评估):
  - NVU_WAIT_QUEUE_MAX_WAIT 180→240s
  - 方案 C: 放宽 cc4101 STREAM_TOTAL_DEADLINE 470→~600s 接近 SDK 上限
  - 检查 `_remaining < 30` 阈值是否过早 skip
- 噪声: hermes×dsv4f0731_nv SR 30% 是 dsv4f 自优化线, 不属 cc2 职责

## 参数快照 (R810 = R809, 无改动)

- nv_gw StartedAt: 2026-08-05 10:32:28 CST (R806 补丁已加载)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180 (R796), NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (实测 cc2 实际走 fid=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3
- cc4101: PRIMARY_UPSTREAM_MODEL=glm5_2_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages
- cc4101: FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/messages
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000

## 一句话总结

R810 NOP — 30min cc2 链路 100% SR (88/88), fallback 1.0% < 10%, BUFFER 3-attempt 自愈实战观测成功 (req=4892ea40: k3 RemoteDisconnected→k4 SSLEOFError→attempt 3 success_tool_call 102.7s). R806 WAIT-RECOVER 补丁仍在 buffer_stream.py:538 就位, 30min 0 触发 (无集中瞬断). per-attempt tier SR 83.0% (88/106) 被 buffer retry 完全吸收为 100% 用户可见.
