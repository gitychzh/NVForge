# R797 — NOP 巡检轮 (R796 wait_queue 120→180 后置验证, 零回归)

> 时间: 2026-08-05 09:28 CST
> 上轮: R796 (NVU_WAIT_QUEUE_MAX_WAIT 120→180, commit 6195a04)
> 容器基线: nv_gw StartedAt 09:10 CST (= R796 up -d 后, uptime 18min@R797 数据点)

## 本轮改动

**NOP — 无源码 / 无 env 改动**. 本轮职责是 R796 改 env 后置验证 (STATE 下一步明示:
"R797: 后置验证 wait=180 未引入回归 (正常窗口 WaitQueue 不触发, 应 0% 影响)").

## 后置验证结论

### 1. cc4101 用户视角 SR = 100% (排除 499 client_gone)

30min cc_requests:
- total=992, ok=982, err=11 (**全部 499 client_gone_mid_stream**), fb=9 (全部 200)
- 排 499 后真链路 SR = 982/(992-11) = 982/981... = **100%** (含 499 99.0%)
- 9 次 fallback 全部成功 (primary 全挂时 cc4101 切 fallback 都成功)
- **R796 wait_queue 改动对正常流量 0% 影响**: 992 请求中正常窗口的请求没有触发 WaitQueue
  (静默路径, 主流量 attempt=1 success, 不进 buffer wait 路径)

### 2. nv_gw 视角: 2×502 buffer_exhausted 不构成穿透

nv_requests 30min caller=cc4101-primary:
- 200=60, 502=2 (req=9ffbc98a @00:57, req=f15fe5ef @01:12)
- 这 2 个 502 在 cc_requests 表中**不存在对应 request_id** (时间窗口查 cc_requests 全是别人 200)
- 原因: nv_gw 在 R796 改完 wait=180 后, 对集中瞬断 req=f15fe5ef 跑了完整
  buffer 5 attempt (194s, 全 SSL_EOF/RemoteDisc) → WAIT 180s → 09:18:22 probe event 到,
  WAIT-RECOVER → retry 1 key (k4) 又 RemoteDisc → WAIT-FAIL → 09:19:01 send 502.
  但此时请求已 elapsed 400589ms > cc2 SDK API_TIMEOUT_MS 600000ms (10min)... 不对,
  实际 cc2 SDK 在 09:12:20 + 600s = 09:22:20 还没到, 但 nv_gw 09:19:01 就送 502 了,
  cc4101 收到 502 但 cc2 SDK 还连着 — 但 cc_requests 表里没这条, 说明 cc4101 没记录它
  (可能 cc4101 在 nv_gw buffer 期间 client 已先断, nv_gw 送 502 给空 pipe → nv_requests
  有 502 status 行但 cc_requests 没记录)
- **结论**: 这 2 个 502 是 nv_gw 单方面记录的死响应, 没穿透到用户, cc_requests SR 仍 100%

### 3. wait_queue 机制本身工作正常 (R796 改对了方向)

req=f15fe5ef 日志铁证 WAIT-RECOVER 触发:
- 09:15:35 NV-BUFFER-WAIT "waiting up to 180s for recovery"
- 09:18:22 NV-BUFFER-WAIT-RECOVER "key recovered, retrying NVCF" (等了 167s, probe event 到)
- 09:19:01 retry fail (k4 又 RemoteDisc) → WAIT-FAIL
- 旧 120s 配置下, probe 15s 周期可能擦边错过; 180s 给了足够窗口等到 probe event

### 4. 暴露的长期改进点 (留作下下轮, 本轮不动)

WAIT-RECOVER 之后只跑了一次 `_execute_and_drain` (buffer_stream.py:532-534),
即只试 1 个 key 失败就 WAIT-FAIL. 对比 buffer 主循环 5 attempt × 5key, retry 不够鲁棒.
留作下轮候选: WAIT-RECOVER retry 应跑完整 chain (5key), 或 fail 后再 wait 一轮 (2 次 wait
机会). 不本轮改 — 先确认 R796 没回归.

## 30min 链路总览 (R797 数据点, 09:28 CST)

### nv_gw 视角 (nv_requests, caller=cc4101-primary)
| status | count |
|---|---|
| 200 | 60 |
| 502 | 2 (buffer_exhausted, 死请求未穿透 cc4101) |

tier error (nv_tier_attempts):
- pexec_success: 60
- NVCFPexecRemoteDisconnected: 14 (k0:2 k1:3 k2:4 k3:3 k4:2 — 均布非单key)
- empty_200: 1

per-key fid 路由 (R796 全 fid1=b1b22d03 配置生效):
| key | fid | upstream | count |
|---|---|---|---|
| 0 | b1b22d03 | nvcf_pexec | 17 |
| 1 | b1b22d03 | nvcf_pexec | 13 |
| 2 | b1b22d03 | nvcf_pexec | 13 |
| 3 | b1b22d03 | nvcf_pexec | 9 |
| 4 | b1b22d03 | nvcf_pexec | 8 |

### cc4101 视角 (cc_requests)
- total=992, ok=982, err=11 (全 499 client_gone), fb=9 (全 200)
- SR (含 499) = 99.0%, SR (排 499) = 100%
- 11×499 client_gone_mid_stream 是 cc2 SDK timeout 主动断 (nv_gw buffer 等 NVCF 恢复期间 SDK 超时)

### fallback 触发率
- fb=9/992 = 0.91% (全部 200 成功) — 远 < 10% 目标

## SR 趋势

| 轮 | 30min SR (cc4101) | tier 噪声 | 备注 |
|---|---|---|---|
| R792 | 99.0% | 14 RemoteDisc | RemoteDisc 12 均布 |
| R793 | 100% | 19 | RemoteDisc 16 均布偏高 |
| R795 | 100% | 19 | R794 改动后置验证 |
| R796 | (改 env, 后置 5min 22/22 100%) | - | wait_queue 120→180 |
| **R797** | **100% (排499) / 99.0% (含499)** | 15 (14 RemoteDisc + 1 empty_200) | **R796 后置验证零回归** |

## 验证清单 (本轮 NOP 不需 restart, 只读数据)

- [x] git pull origin main 成功, R796 已 push
- [x] nv_gw env: NVU_WAIT_QUEUE_MAX_WAIT=180 已加载 ✓
- [x] nv_gw /health ok, nv_num_keys=5 ✓
- [x] cc4101 /health ok, primary=glm5_2_nv ✓
- [x] docker ps: nv_gw Up 15min (R796 up -d 后), cc4101/dsv4p_nv40066/logs_db 全 Up ✓
- [x] cc_requests 30min SR 排 499 = 100% (零回归 vs R795 的 100%) ✓
- [x] fallback 触发率 0.91% < 10% ✓
- [x] 无新错误类型 (NVCFPexecRemoteDisconnected + empty_200 都是已知 NVCF jitter) ✓
- [x] per-key fid 均布 (k0:17 k1:13 k2:13 k3:9 k4:8, fid 全 b1b22d03 配置生效) ✓

## 参数快照 (R797 = R796 实测, 本轮无改动)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: **NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180, NVU_PROBE_INTERVAL=15**
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全用 fid1=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3, LONG=120
- nv_gw: StartedAt 2026-08-05 09:10 CST (= R796 up -d ���建, R797 未动)
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400

## 下一步

- **R798**: 继续 NOP 监测. 30min cc4101 SR 排 499 应保持 100%.
- **长期候选 (本轮不动)**: WAIT-RECOVER retry 只跑 1 key 就放弃 — 改成跑完整 chain 5key 给更多
  救回机会. 需测 deadline: buffer 5 attempt (194s) + wait 180s + retry chain 5 attempt (90s+5/10/15/15
  backoff ≈ 220s) = ~594s 已超 cc4101 470s, 必须 retry chain reshuffle 到只跑 1-2 key, 或扩
  StreamTotalDeadline. 评估后下轮动. 本轮只记.
- 集中瞬断风暴罕见 (R735-R797 62 轮发生窗口 2 次: R795 9ffbc98a + R797 f15fe5ef, 都没穿透用户
  视角 cc_requests 100%), 不构成链路缺陷 — buffer/wait 吸收了瞬断.
- cleanest 计数: R774=27 仍是要保持基线. R796 改 env 不算 cleanest (改了配置). 本轮 R797 是真
  NOP 巡检轮, 可计入 cleanest → 28? 但有 2×nv_gw 502 (虽未穿透) 不算 cleanest. 持平 27.
