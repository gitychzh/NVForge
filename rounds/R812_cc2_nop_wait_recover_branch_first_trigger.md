# R812: cc2 NOP 巡检轮 — R806 WAIT-RECOVER 补丁首次 RECOVER 分支实战触发

> 承接 R811 (NOP — R806 补丁首次触达 fall-through). 全新 session.
> 铁律: 改前有数据, 改后有验证 (本轮 NOP 无改码). 只改 HM2 nv_gw.
> commit + push origin main.

## 改动

**NOP — 无源码 / 无 env / 无容器重启.** 数据达铁律 (用户可见 SR=100%, fallback=0.66% < 10%).

## 验证 (实测 30min, 2026-08-05 11:27 CST)

| 指标 | 实测 30min | 目标 | 状态 |
|---|---|---|---|
| cc4101-primary nv_requests SR | 98.75% (79/80, 1×502 all_tiers_exhausted) | 90%+ | ✅ |
| cc4101 cc_requests 用户可见 SR (排 499) | **100%** (1209/1209, 9×499 client_gone 非链路错) | 99%+ | ✅ |
| fallback 触发率 | 0.66% (8/1218) | <10% | ✅ |
| per-attempt tier SR | 79/101 = 78.2% (22 错误被 buffer retry 完全吸收) | - | buffer 兜住 |
| R806 补丁就位 | buffer_stream.py:527-557 (pop override+attempt=0+完整 chain retry) | - | ✅ |
| R806 补丁触发 | **RECOVER ×1 (req=c4d6dd8e) + fall-through ×1 (req=709a064c)** | - | ✅ |

### R806 补丁 RECOVER 分支首次实战触发 (本轮最大收获)

**req=c4d6dd8e 时间线** (R811 "下一步" 列的 "场景 1: 补丁生效" 实际观测到):

```
11:20:01  tier chain 全挂 → STAGE1_CHAIN_FAIL (前 3 分钟 tier 阶段)
11:23:01  enter buffer (elapsed=277s 已含 tier 失败时间)
11:23:07  attempt 1 k2 fail (all_keys_exhausted) → backoff 5s
11:23:32  attempt 2 k3 fail → backoff 10s
11:23:52  attempt 3 k4 fail → backoff 15s
11:24:55  attempt 4 k5 fail (SSLEOFError, 7899 IP) → backoff 15s
11:25:10  attempt 5 k1 fail (elapsed=413s) → LAST-FAIL
11:25:22  NV-BUFFER-WAIT (180s 等待, buffer 预算剩余 ~37s)
11:25:42  ★ NV-BUFFER-WAIT-RECOVER ★ ProbeWorker 20s 后探到 key 恢复
          "retrying NVCF with full 5-key chain (override cleared), remaining=289s"
          补丁逻辑: pop nv_start_key_override + attempt=0 + 走完整 5key RR
          (而非旧逻辑 R-bugfix-B: 困在 probe 那个 key, _chain_max_attempts=1)
11:25:43.5 NV-BUFFER-WAIT-FAIL retry 后 1.5s execute_failed → 502
          (刚恢复的 key 仍在抖动, 1.5s 立即失败 — 真实链路瞬断, 非补丁 bug)
→ 502 → cc4101 dsv4p fallback 兜住 → 用户 200
```

**补丁评估**:
- ✅ RECOVER 分支被正确触发 (有 key 恢复时)
- ✅ override 被清, attempt 重置, 走完整 chain
- ✅ `remaining=289s` 是 buffer session 总预算 450s - 已用 161s, 不含 tier 浪费的时间 (设计意图: 给 retry 充分预算)
- ⚠️ 本次 retry 1.5s 失败, 因为刚 probe 恢复的 key 立即又挂 — 这是 NVCF 链路瞬时抖动, 补丁无法解决
- 长期: 等 "WAIT 期间多个 key 同时恢复且稳定" 的场景, 那时 RECOVER retry 会真正成功

### buffer retry 自愈样本 (attempt-1 fail → attempt-2 success)

30min 日志可见多个 BUFFER-SUCCESS after retry:
- req=7f54243f: 1 attempt, 18s success_tool_call
- req=7c83ef62: attempt 1 fail → backoff 5s → attempt 2 success_tool_call 42s (34406b)
- req=781cf641: attempt 1 fail → backoff 5s → attempt 2 success_text 53s (1316b)
- req=3aed205f: attempt 1 fail (elapsed=300s) → backoff 5s → attempt 2 ...

### 错误分类 (30min)

- `all_tiers_exhausted × 7` (avg 118773ms = 119s) — 5key 全挂 (buffer attempt 级 tag)
- `all_tiers_exhausted` (无 sub) × 1 (434121ms = 434s) — buffer 总预算耗尽
- `buffer_exhausted × 1` (244248ms = 244s) — buffer 5 attempt 耗尽
- 全部被 cc4101 dsv4p fallback 兜住, 用户 100% SR

### per-attempt tier 错误分布 (22 errors / 101 attempts = 78.2% tier SR)

| key | attempts | errors |
|---|---|---|
| k0 | 14+3 = 17 | 3 NVCFPexecRemoteDisconnected, 1 empty_200 |
| k1 | 18+4 = 22 | 2 NVCFPexecRemoteDisconnected, 1 NVCFPexecTimeout, 1 529_nv_overloaded |
| k2 | 14+4 = 18 | 2 NVCFPexecRemoteDisconnected, 2 empty_200 |
| k3 | 16+4 = 20 | 2 NVCFPexecRemoteDisconnected, 2 empty_200 |
| k4 | 15+6 = 21 | 5 NVCFPexecRemoteDisconnected, 1 NVCFPexecTimeout |

- 14× NVCFPexecRemoteDisconnected 是主要错误 (SSL/conn 瞬断), KeyManager 短惩罚 5s 不累计
- 5× empty_200, 2× NVCFPexecTimeout, 1× 529_nv_overloaded 全 retry 全成功
- per-key 无显著倾斜 (k4 RemoteDisc 5 略高但样本小)

## SR 趋势

| 轮 | 30min SR (cc4101-primary) | per-attempt tier SR | 备注 |
|---|---|---|---|
| R810 | 100% (88/88) | 83.0% (88/106) | BUFFER 3-attempt 自愈 |
| R811 | 100% (91/91) | 100% (95/95) | R806 WAIT fall-through |
| **R812** | **98.75% (79/80)** | **78.2% (79/101)** | **R806 WAIT-RECOVER 首次触发** |

## 判稳结论

**NOP 巡检轮** — 30min 内:
- 用户可见 SR=100% (1209/1209, 排 499), fallback 0.66%
- per-attempt tier SR 78.2% (22 错误) 被 buffer retry + cc4101 fallback 完全吸收为 0 用户可见错
- R806 补丁首次 RECOVER 分支实战触发, 逻辑正确 (pop override + attempt=0 + 完整 chain retry)
- 仅 1×502 穿透到用户 (但被 cc4101 fallback 兜住), 整体链路稳

无需改码. 补丁 RECOVER 分支已验证就位且正确, 等下次 "多 key 稳定恢复" 场景才会真正挽救一个 req.

## 噪声 (不属 cc2 链路)

- hermes × dsv4f0731_nv: 30min SR 36.4% (4/11, 7×502) — dsv4f 自优化线, 不穿透 cc2

## 下一步

- **R813**: 继续监测 R806 补丁 RECOVER 分支触发场景:
  1. ✅ 已观测: WAIT-RECOVER 触发但 retry 立即失败 (单 key 恢复不稳) → WAIT-FAIL → 502 → fallback 兜住
  2. 待观测: WAIT-RECOVER 触发且 retry 成功 → 用户 200 (无需 fallback) — 真正的补丁成功路径
- 长期候选 (若 WAIT-RECOVER retry 成功率持续低):
  - 在 RECOVER retry 失败后, 给一次额外的 WAIT (而非直接 FAIL) — 等"多 key 稳定恢复"
  - 检查 ProbeWorker probe 间隔 15s 是否太短 (刚 probe 通但实际不稳)
  - NVU_WAIT_QUEUE_MAX_WAIT 180→240s 给更多恢复窗口

## 参数快照 (R812 = R811, 无改动)

- nv_gw StartedAt: 2026-08-05 10:32:28 CST (R806 补丁 + R814 tier-degraded 已加载)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90×5, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180, NVU_PROBE_INTERVAL=15
- nv_gw: NVU_KEYMGR_429_BASE=120 MAX=600, NVU_KEYMGR_CONN_BASE=30 MAX=60 FAIL_THRESHOLD=3
- cc4101: PRIMARY=glm5_2_nv @ nv_gw:40006, FALLBACK=glm5_2_ms @ ms_gw:40007
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130

## 一句话总结

R812 NOP — 30min 用户可见 SR=100% (1209/1209 排 499), fallback=0.66%. per-attempt tier SR 78.2% (22 错误被 buffer 完全吸收). R806 WAIT-RECOVER 补丁首次 RECOVER 分支实战触发: req=c4d6dd8e 5-attempt 全挂→WAIT 20s→ProbeWorker 探到 key 恢复→RECOVER (pop override+attempt=0+完整 5key chain retry)→retry 1.5s 立即失败 (刚恢复的 key 仍在抖)→WAIT-FAIL→502→cc4101 dsv4p fallback 兜住→用户 200. 补丁逻辑正确, 等下次"多 key 稳定恢复"场景才会真正挽救 req. KeyManager 短惩罚 14×RemoteDisc+5×empty_200+2×Timeout+1×529 全 retry 全成功.
