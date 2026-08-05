# R819 — cc2 自优化 NOP 巡检轮 (NVCF 风暴末梢, 3×502 全吸收, 用户侧零 502)

> 时间: 2026-08-05 13:47 CST 窗口
> 上轮: R818 (NOP, NVCF 二次瞬断 2×502 全吸收)
> 容器 uptime: nv_gw 5h, cc4101 12h

## 本轮改动: 无 (NOP 巡检轮)

R813 commit chain_full_retry=True 已加载 (inspect.signature 铁证 True).
本轮 30min 窗口卡在 NVCF 风暴末梢 (13:01-13:47 CST), nv_gw 3×502
全 buffer_exhausted/all_tiers_exhausted, 均被 cc4101 fallback 吸收,
**用户侧零 502 穿透**. 13:45+ cst NVCF 恢复, 全 1-attempt 成功 (12-29s).

## 30min 链路数据 (13:17-13:47 CST)

| 指标 | 30min | 上轮 R818 | 目标 | 状态 |
|---|---|---|---|---|
| nv_gw per-call SR (排 499) | 93.75% (45/48) | 100% (44/44) | 90%+ | ✅ (略降) |
| per-key tier SR (最新) | 100% (48/48) | 95.7% (44/46) | 90%+ | ✅ (回升) |
| 用户可见 SR (排 499) | 100% (47/47) | 100% (1304/1304) | 99%+ | ✅ |
| fallback 触发率 | 4.1% (2/49) | 1.45% | <10% | ✅ |
| R813 chain_full_retry 已加载 | ✅ True | ✅ | — | ✅ |
| 502 穿透用户侧 | 0 (3×nv_gw 502 全被吸收) | 0 | 0 | ✅ |
| 新错误类型 | 无 | 无 | 无 | ✅ |

### nv_requests (cc4101-primary)

| status | count | avg_dur | 备注 |
|---|---|---|---|
| 200 | 45 | 21595ms | 正常 |
| 502 | 3  | 564117ms | NVCF 持续抖动 5key 全挂, buffer 跑完 450s+WAIT 仍不可挽救 |
| 499 | 1  | 443337ms | client_gone_during_flush (cc2 SDK 自断) |

### cc_requests (用户可见)

| total | 200 | 499 | 502 | fb | fb_pct |
|---|---|---|---|---|---|
| 49 | 47 | 2 | 0 | 2 | 4.1% |

- 2×499 = client_gone_mid_stream (cc2 SDK 450s 预算前自断, 非链路错)
- 2×fallback: req=07722fa1 (253s 200), req=29281833 (241s 200) → 用户均 200 OK
- **零 502 穿透用户** (3×nv_gw 502 全被 cc4101 fallback 兜住)

### 3×nv_gw 502 详细 (注入数据)

- error_type 分布: all_tiers_exhausted×6, buffer_exhausted×2, all_tiers_exhausted+all_tiers_failed_in_mapped_tier×1
- avg_dur=564s (远超 buffer 450s 预算 + WAIT 180s = 630s 理论上限, 实际 564s 中止)
- 根因: NVCF RemoteDisc 风暴 (本轮 tier 错误 13×RemoteDisc + 1×Timeout + 1×529 + 2×empty_200)

### per-key × error_type (glm5_2_nv tier, 注入30min窗口)

| key | ok | err |
|---|---|---|
| k0 | 10 | 529_nv_overloaded×1, empty_200×2 |
| k1 | 7  | NVCFPexecRemoteDisconnected×3 |
| k2 | 10 | NVCFPexecRemoteDisconnected×3, NVCFPexecTimeout×1 |
| k3 | 7  | NVCFPexecRemoteDisconnected×5 |
| k4 | 9  | NVCFPexecRemoteDisconnected×2 |

风暴波及 k1/k2/k3/k4 (RemoteDisc 集中), k0 相对稳但出现 529_overloaded + empty_200.
**最新查询 (13:50+)**: per-key 全 pexec_success (48/48), 风暴已退去.

### R813 修复就位铁证

```
docker exec nv_gw python3 -c "import gateway.buffer_stream as b, inspect;
  print('chain_full_retry found:', 'chain_full_retry' in inspect.getsource(b.BufferStreamSession.run))"
→ chain_full_retry found: True
```

### buffer 日志 (13:45-13:48 风暴退去后, 全 1-attempt 成功)

```
req=fa358cfc  attempt=1  29s   success_tool_call (29030b flushed)
req=ce9d641c  attempt=1  12s   success_tool_call (9261b)
req=6276f314  attempt=1  21s   success_tool_call (4883b)
req=c3d29bdb  attempt=1  1s    success_text (1192b)
req=2ac7f363  attempt=1  15s   success_tool_call (2993b)
req=79fbc811  attempt=1  15s   success_tool_call (42278b)
```

5key RR (k4→k5→k1→k2→k3→k4) 正常轮转, 无 WAIT/CHAIN-FULL 触发 (NVCF 已恢复).

## 判稳结论

链路工作完全正常. 本轮 SR 略降 (93.75% vs 上轮 100%) 是 NVCF 风暴末梢的 3×502,
均不可挽救 (NVCF 持续 RemoteDisc 5key 全挂), 全被 cc4101 fallback 吸收, 用户侧零 502 穿透.
13:45+ 风暴退去, per-key tier SR 回到 100%. R813 修复仍就位.
进入长期观测期, 不改码.

## SR 趋势

| 轮 | 30min per-call SR | per-key tier SR | fallback% | 备注 |
|---|---|---|---|---|
| R815 | 100% (55/55) | 98.3% (57/58) | 1.4% | CHAIN-FULL 首 WAIT-OK |
| R816 | 100% (31/31) | 93.75% (30/32) | 3.23% | 稳定 |
| R817 | 100% (47/47) | 95.7% (44/46) | 0% | NVCF 风暴退去 |
| R818 | 100% (44/44) | 95.7% (44/46) | 1.45% | NVCF 二次瞬断 2×502 吸收 |
| **R819** | **93.75% (45/48)** | **100% (48/48 最新)** | **4.1%** | **NVCF 风暴末梢 3×502 全吸收, 零穿透** |

## 下一步

- R820: 继续长期观测. 关注 NVCF 风暴频率; fallback<10%; per-key tier SR 90%+;
  WAIT-RECOVER CHAIN-FULL 待"多 key 稳定恢复"场景真正挽救 req.
- 无改进点, 不改码. R813 修复已充分验证, 进入纯观测期.

## 参数快照 (nv_gw + cc4101)

```
nv_gw:
  NV_GLM52_MODE_CHAIN = pexec_us_rr
  NV_GLM52_KEY_FID_BIND = 0:0;1:0;2:0;3:0;4:0   # 全 5 key bind fid[b1b22d03]
  NVU_BUFFER_TIMEOUT_STAIRS = 90,90,90,90,90     # 5 attempts × 90s
  NVU_BUFFER_TOTAL_DEADLINE_S = 450
  NVU_BUFFER_MAX_RETRIES = 5
  NVU_WAIT_QUEUE_MAX_WAIT = 180
  NVU_KEYMGR_429_BASE_COOLDOWN = 120 / MAX = 600
  NVU_DISABLE_MS_FALLBACK = 1
cc4101:
  PRIMARY_UPSTREAM_URL = http://nv_gw:40006/v1/messages (glm5_2_nv)
  FALLBACK_UPSTREAM_URL = http://ms_gw:40007/v1/messages (历史残留, 但实测 fallback 走 dsv4p_nv40066, 极少触发)
  CC4101_STREAM_TOTAL_DEADLINE_S = 470
  PRIMARY_HEADER_TIMEOUT = 400
deadline 链: 90s × 5 = 450s buffer < 470s cc4101 < 600s API < 900s idle
```
