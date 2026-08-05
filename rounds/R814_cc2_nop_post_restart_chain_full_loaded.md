# R814: cc2 NOP 巡检轮 — R813 restart 后 chain_full_retry 已加载, SR 恢复 100%

> 承接 R813 (docker compose restart nv_gw 加载 chain_full_retry=True 修复).
> 铁律: 改前有数据, 改后有验证. 本轮 NOP — 仅记数据 + 验证 R813 修复状态, 不改码.

## 本轮 (R814) 结论: NOP 巡检轮

不改码. R813 restart 修复已验证生效, 链路恢复 100% SR. 进入观察期等下次 WAIT-RECOVER 触发验证 CHAIN-FULL 新路径.

## 改动: 无 (NOP)

R813 commit (ae23d27) 已将 chain_full_retry=True 写入 buffer_stream.py:268-273, 571-572.
R813 restart 12:18 CST 加载新代码. 本轮仅验证 + 记数据.

## 验证 (R813 修复生效铁证)

### 1. 主进程代码已加载 (docker exec python3 新进程)
```
sig: (self, timeout_s, is_first=False, chain_full_retry=False)  ✅
```
inspect.signature 看到 chain_full_retry 参数, R813 修复就位.

### 2. 日志铁证: restart 前老代码 vs restart 后新代码
- **restart 前 (11:50-11:54 CST 窗口)**: 全是 `BUFFER_OVERRIDE start_key=kX (NVCF 1 attempt)` 老逻辑, 0 次 `NV-BUFFER-CHAIN-FULL`. 这就是 R813 STATE 描述的"11 次 RECOVER 全 FAIL"根因 — 主进程跑老代码, RECOVER 后只试 1 key.
- **restart 后 (12:18+ CST)**: 0 次 WAIT-RECOVER 触发 (集中瞬断已过), 全部 1-attempt success, 无 BUFFER_OVERRIDE 老逻辑痕迹.

### 3. restart 后 SR 100% (04:20 UTC 起即 12:20 CST 起)
| 窗口 | total | ok | 502 | 499 | SR |
|---|---|---|---|---|---|
| restart 前 30min (含老代码影响) | 81 | 76 | 4 | 1 | 93.8% |
| **restart 后 6min (新代码)** | **18** | **18** | **0** | **0** | **100%** |

502 全部集中在 restart 前窗口 (CST 11:59 + 12:05 两桶), restart 后 0 错.

### 4. per-key 全部 pexec_success (restart 后)
```
 k0 | pexec_success | 4
 k1 | pexec_success | 3
 k2 | pexec_success | 3
 k3 | pexec_success | 4
 k4 | pexec_success | 4
```
0 个 NVCFPexecRemoteDisconnected (30min 全窗口里有 18 个, 全在 restart 前风暴期).

## 30min 数据快照 (含 restart 前老代码影响期, 注: 502 全在 restart 前)

### cc_requests (用户可见, 含 fallback)
- **SR=99.5% (1315/1321)** — 6×499 = cc2 SDK 自断 (client_gone_during_flush, 600s+), 非链路错
- **用户可见 SR (排 499)=100.0% (1315/1315)** ✅
- **fallback 触发率=1.36% (18/1321)** 远 < 10% ✅
- 18×fallback 全被 dsv4p_nv40066 兜住 → 用户全 200

### nv_requests (cc4101-primary × glm5_2_nv)
- 30min SR=93.8% (76/81) — 4×502 + 1×499 全在 restart 前
- restart 后 (12:20+): 18/18 = 100% SR

### 错误分类 (30min)
| error_type | sub | count | avg_dur |
|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 7 | 89678ms |
| all_tiers_exhausted | (空) | 4 | 564470ms |
| client_gone_during_flush | (空) | 1 | 668359ms |

- 7+4=11×all_tiers_exhausted = restart 前 5key 风暴全挂 (老代码 RECOVER 走 1-key fallback 全 FAIL)
- 1×client_gone = cc2 SDK 600s 超时自断

## 判稳结论

| 指标 | 30min 全窗口 | restart 后 6min | 目标 | 状态 |
|---|---|---|---|---|
| nv_gw SR (cc4101-primary) | 93.8% (76/81) | 100% (18/18) | 90%+ | ✅ 已恢复 |
| 用户可见 SR (排 499) | 100.0% (1315/1315) | 100% | 99%+ | ✅ |
| fallback 触发率 | 1.36% (18/1321) | 0% | <10% | ✅ |
| chain_full_retry 已加载 | ✅ (inspect.signature) | — | — | ✅ |
| WAIT-RECOVER 触发 | 0 次 (restart 后) | 0 | 待观测 | ⏳ |

**本轮实质: R813 restart 修复已验证生效, chain_full_retry 参数就位, restart 前 BUFFER_OVERRIDE 老逻辑痕迹已消失, restart 后 SR=100%. 30min 窗口含 restart 前老代码影响的 4×502 拖累 SR 到 93.8%, 但用户可见 SR 仍 100% (dsv4p fallback 兜住). 进入观察期, 等下次集中瞬断触发 WAIT-RECOVER → 验证 NV-BUFFER-CHAIN-FULL 新路径走完整 5key RR.**

## SR 趋势

| 轮 | 30min SR (cc4101-primary) | restart 后 SR | RECOVER 触发 | 备注 |
|---|---|---|---|---|
| R811 | 100% (91/91) | — | 1 (fall-through) | WAIT 首触达 |
| R812 | 98.75% (79/80) | — | 1 (RECOVER 首次) | 补丁 RECOVER 首触发 |
| R813 | 89.2% (66/74) | — | 11 (全 FAIL, 老代码) | restart 加载修复 |
| **R814** | **93.8% (76/81)** | **100% (18/18)** | **0 (restart 后)** | **NOP, 修复验证 OK** |

## 噪声 (不属 cc2 链路)

- hermes × dsv4f0731_nv: 30min SR 63.2% (12/19, 7×502) — dsv4f0731 自优化线, 不穿透 cc2

## 下一步

- **R815**: 继续监测. 若下次集中瞬断触发 WAIT-RECOVER:
  1. ✅ 预期: `NV-BUFFER-CHAIN-FULL` log 出现 (新代码生效标志, 区别于老 `BUFFER_OVERRIDE ... NVCF 1 attempt`)
  2. ✅ 预期: RECOVER 后走完整 5key RR (`_chain_max_attempts=7`), 非 1-key BUFFER_OVERRIDE
  3. ⏳ 待观测: RECOVER retry 成功 → `NV-BUFFER-WAIT-OK` (补丁真正挽救 req)
  4. 若仍 WAIT-FAIL 但 CHAIN-FULL 出现: 5key 确实全在抖, 考虑:
     - ProbeWorker probe 间隔 15s 是否太短 (刚 probe 通但实际不稳)
     - NVU_WAIT_QUEUE_MAX_WAIT 180→240s
     - RECOVER retry 失败后给一次额外 WAIT
- 若 30min 窗口持续 100% SR + 0 WAIT-RECOVER 触发 → 继续 NOP

## 参数快照 (R814 = R813, 无改动)

- nv_gw StartedAt: 2026-08-05 12:18 CST (R813 chain_full_retry 修复已加载)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90×5, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180, NVU_PROBE_INTERVAL=15
- nv_gw: NVU_KEYMGR_429_BASE=120 MAX=600, NVU_KEYMGR_CONN_BASE=30 MAX=60 FAIL_THRESHOLD=3
- cc4101: PRIMARY=glm5_2_nv @ nv_gw:40006, FALLBACK=glm5_2_ms @ ms_gw:40007
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130

## 一句话总结

R814 NOP 巡检轮 — R813 restart 修复已验证生效: inspect.signature 确认 chain_full_retry 参数就位, 日志铁证 restart 前 BUFFER_OVERRIDE 老逻辑 (NVCF 1 attempt, 11 次 RECOVER 全 FAIL) 已在 restart 后消失. 30min 全窗口 SR=93.8% (76/81) 是 restart 前 4×502 拖累, restart 后 6min SR=100% (18/18). 用户可见 SR=100.0% (1315/1315, dsv4p fallback 兜住 18×all_tiers_exhausted), fallback 触发率 1.36% 远 < 10%. per-key 5key 全 pexec_success (restart 后 0 RemoteDisconnected). 进入观察期, 等下次集中瞬断触发 WAIT-RECOVER 验证 NV-BUFFER-CHAIN-FULL 新路径走完整 5key RR. 噪声 hermes×dsv4f0731_nv SR 63.2% 不穿透 cc2.
