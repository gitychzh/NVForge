# R809 — NOP 巡检轮 (BUFFER 自愈实战样本观测, R806 补丁仍未触发)

> 时间: 2026-08-05 11:04 CST
> 上轮: R808 (NOP — R806 WAIT-RECOVER 补丁静态审查+时间线核实)
> 容器: nv_gw StartedAt=2026-08-05T02:32:28Z (10:32:28 CST, 已运行 30min)

## 本轮改动

**NOP — 无源码 / 无 env / 无容器重启**

本轮工作: 接棒 + 拉数据 + 交叉核实 + BUFFER 自愈路径实战观测.

## 数据 (30min, 2026-08-05 11:04 CST)

### cc2 自己链路 (cc4101-primary × glm5_2_nv)

| 指标 | 实测 | 目标 | 状态 |
|---|---|---|---|
| nv_requests SR | 100% (83/83) | 90%+ | ✅ |
| 最终用户 SR (排 client_gone) | 100% (80/80) | 99%+ | ✅ |
| fallback 触发率 | 1.2% (1/82) | <10% | ✅ |
| cc4101 499 | 2 × client_gone_mid_stream (59s) | - | 非链路错 (cc2 SDK 自己断) |
| 容器健康 | nv_gw=ok, cc4101=ok, dsv4p=ok | - | ✅ |

### tier per-key 分布 (84 attempts)

| k | total | pexec_success | RemoteDisconnected | empty_200 | 529_overloaded |
|---|---|---|---|---|---|
| k0 | 21 | 20 | 1 | 0 | 0 |
| k1 | 24 | 18 | 3 | 2 | 1 |
| k2 | 20 | 17 | 2 | 1 | 0 |
| k3 | 20 | 15 | 5 | 0 | 0 |
| k4 | 15 | 13 | 2 | 0 | 0 |

per-attempt SR = 81/98 = 82.7% (NVCF 单次配额/RemoteDisconnected 噪声), 但 buffer retry 全部吸收, 最终 100% 用户可见.

### BUFFER 自愈实战样本 (req=bb5a29b6, 11:02:00-11:02:35)

- attempt=1 start_key=k1 → 8s 后 NVCF 返回 429 (单 key 配额瞬时打)
- KeyManager 立即把 k1 拉黑 cooldown=120s
- NVCF 链路 (1 attempt override) → 所有 key 似乎都判 exhausted (all_keys_exhausted=True)
- verdict=None reason=execute_failed → BUFFER-RETRY + backoff 5s
- attempt=2 start_key=k2 → 22s 后 success_tool_call (content=771c + tool_calls)
- 2-attempt 总耗时 35s, 用户最终收 200 ✅

**这就是 BUFFER 设计意图: 单 key 配额闪挫被 retry 吸收, 不需要 fallback, 不需要 WAIT-RECOVER.**

### 30min BUFFER verdict 分布

- verdict=success_tool_call: 78 条 (74%)
- verdict=success_text: 6 条 (5.7%)
- verdict=None: 22 条 (20.8%) — 全 retry 路径, 最终都 200
- **NV-BUFFER-WAIT-RECOVER 字样: 0 条** — 当前窗口无集中瞬断, R806 补丁未触发测试

### 429 KeyManager 事件 (30min)

- 10:39:32 k4 cooldown=120s
- 11:02:08 k1 cooldown=120s (即 bb5a29b6 触发的那次)
- 仅 2 次单 key 配额事件, 无风暴, 无 5key 全挂

### 2h SR 趋势 (10min 桶)

13 桶中只有 2 桶各 1 次 502 (1/14, 1/29 = 瞬时单 key 配额, retry 立即恢复). 其余 11 桶零 502.

## R806 补丁就位核实

容器内 `/app/gateway/buffer_stream.py:527-557`:
- 527: `# R806: WAIT-RECOVER 后清掉 nv_start_key_override`
- 538: `[NV-BUFFER-WAIT-RECOVER`
- 540: `5-key chain (override cleared), remaining={_remaining:.0f}s`
- 验证字串在位, 等下次集中瞬断自动触发.

## 判稳结论

- cc2 nv_requests SR = 100%, 用户最终 SR = 100% → NOP ✅
- fallback 触发率 1.2% < 10% ✅
- R806 补丁就位但未触发 (无集中瞬断窗口)
- 噪声不计决策: hermes × dsv4f0731_nv SR 50% 是 dsv4f 自优化线, 不穿透 cc4101-primary

## 下一步

- **R810**: 继续监测集中瞬断. 期望日志出现 `NV-BUFFER-WAIT-RECOVER ... 5-key chain (override cleared), remaining=Xs`.
- 本轮不动码.
- 长期候选: 若 R806 补丁触发后仍 WAIT-FAIL, 评估 NVU_WAIT_QUEUE_MAX_WAIT 180→240s 或方案 C (放宽 cc4101 STREAM_TOTAL_DEADLINE 470→~600s).

## 参数快照 (R809 = R808, 无改动)

- nv_gw StartedAt: 2026-08-05 10:32:28 CST (R806 补丁已加载)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180, NVU_PROBE_INTERVAL=15
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
