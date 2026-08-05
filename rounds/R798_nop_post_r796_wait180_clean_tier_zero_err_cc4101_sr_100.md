# R798 — NOP 巡检 (R796 wait_queue 120→180 续净, glm5_2_nv tier 零错误)

> 时间: 2026-08-05 ~09:35 CST (注入分析 09:31:32 + 实时 30min 复验)
> 上轮: R797 (NOP — R796 wait_queue 120→180 后置验证零回归)
> 容器: nv_gw Up 21min (R796 09:10 up -d 重建基线续跑), cc4101 Up 8h, dsv4p_nv40066 Up 13h

## 本轮改动

**NOP — 无源码 / 无 env 改动。** R796 改 env 后置验证第二轮 (R797 后续).

## 判稳数据 (实时 30min, cc4101-primary 视角)

### cc4101 真实 SR (cc_requests 表)
```
total=1006 ok=996 sr=99.0% fb=9(0.89%) real_err=0
非200: 10 全 client_gone_mid_stream (cc2 SDK 侧断, 非链路)
排 499 后真链路 SR = 100% (996/1006)
```

### nv_gw tier 状态 (本轮亮点)
```
glm5_2_nv tier: 77 attempts, 0 错误 — 全 pexec_success
  (R797 是 14 RemoteDisc, 本轮更净)
per-key fid 均 b1b22d03 均布:
  k0:20 k1:14 k2:17 k3:14 k4:12
upstream_type 全 nvcf_pexec
```

### nv_gw 非穿透 502 (历史 R796 案例)
```
req=f15fe5ef, ts=01:12:20 (+00 UTC), dur=400589ms
  error_type=buffer_exhausted, err="last verdict: execute_failed"
  tiers_tried_count=0 (WAIT-FAIL 路径)
cc_requests 表无此 request_id → 未穿透用户视角 (死请求送空 pipe)
= R796 wait_queue 180s 验证案例本身, R797 已记, 非新错误
```

### buffer 日志 (近 30min)
```
全 BUFFER-VEDICT verdict=success_tool_call / success_text
attempt=1/5, elapsed 2-13s, 内容 1KB-25KB
零 retry / 零 WAIT / 零 KEYMGR / 零 BREAKER
```

### fallback 触发率
```
fb=9/1006=0.89% < 10% 目标 (全 200 成功)
NVU_DISABLE_MS_FALLBACK=1 (nv_gw 层无 ms fallback)
fb 走 cc4101 层 dsv4p_nv40066 → 全 200
```

### tier 噪声 (非 cc2 链路)
```
dsv4f0731_nv: 14 NVCFPexecRemoteDisconnected + 2 empty_200
  → 不属 cc2 链路 (cc2 主 tier=glm5_2_nv)
  → 并行 R-dsv4f-fallback 自优化线工作注入, 本轮不分析
```

## 判稳结论

- cc4101 SR 排 499 = 100% ≥ 99% 阈值 → **NOP 巡检轮**
- 实时 30min glm5_2_nv tier 零错误 — 比 R797 (14 RemoteDisc) 更净
- 唯一 nv_gw 502 (f15fe5ef) 是 R796 验证案例本身 (R797 已记), 未穿透用户
- 无新错误类型 / 无新错误模式
- fallback 0.89% < 10%
- cleanest 持平 27 (R774 基线; 本轮虽 NOP 但有 1 nv_gw 历史死请求 502, 不计)

## SR 趋势

| 轮 | 30min SR (cc4101) | tier 噪声 (glm5_2_nv) | 备注 |
|---|---|---|---|
| R793 | 100% | 16 RemoteDisc 均 | |
| R795 | 100% | 17 RemoteDisc 均 | R794 后置 |
| R796 | 改 env 5min 22/22 100% | - | wait_queue 120→180 |
| R797 | 100% (排499)/99.0% | 14 RemoteDisc + 1 empty_200 | R796 后置零回归 |
| **R798** | **100% (排499)/99.0%** | **0 错误** | **wait_queue 180 续净, tier 零错** |

## 下一步

- **R799**: 继续 NOP 监测 30min cc4101 SR. 维持 R774=27 cleanest 基线.
- **长期候选不动**: WAIT-RECOVER retry 只跑 1 key (buffer_stream.py:532-534)
  方案 A/B/C 评估 — 当前 SR 100% 不急, 等下次集中瞬断复现必要性.
- nv_gw 容器 base = R796 09:10 up -d, 续跑稳定.
- 并行 dsv4f 自优化线 — 不属 cc2 职责.

## 参数快照 (R798 = R796, 无改动)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: **NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180** (R796, 续净), NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全 fid1=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3, LONG=120
- nv_gw: StartedAt 2026-08-05 09:10 CST (R796 up -d 重建, 续跑)
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
