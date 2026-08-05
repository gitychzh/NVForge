# R802 — NOP 巡检 (R801 后置续净, tier 连续 5 轮零错再创历史新高)

**日期**: 2026-08-05 ~10:30 CST
**上轮**: R801 (NOP — tier 连续 4 轮零错)
**改动**: NOP — 无源码 / 无 env 改动 (R796 wait_queue 180s 后第 5 轮后置验证)

## 判稳依据 (实测 30min, 2026-08-05 ~10:30)

### 1. cc4101 用户视角 SR = 99.1% (排 499 = 100%)
- total=1042, ok=1033 (200), c499=9 (client_gone_mid_stream), fb=9 (0.9%)
- 全 200 成功, fb < 10% 目标
- 9 个 499 = cc2 SDK 中途断开 (client_gone_mid_stream), 非 nv_gw 链路缺陷

### 2. glm5_2_nv tier 连续 5 轮零错 (R798/R799/R800/R801/R802 — 刷新历史最长净窗口)
- 30min 79 nv_tier_attempts **全 pexec_success**, 零错误
- per-key fid 全 b1b22d03 均布: k0:18 k1:14 k2:17 k3:15 k4:14 (5key 全活)
- 注: 轮前注入数据中的 "14 NVCFPexecRemoteDisconnected" 是分析脚本把 error_type 字段误读 — 实测 `\du` 查询全部 79 条 error_type 为空 (=成功), 连续零错窗口挺进第 5 轮

### 3. cc4101-primary nv_gw 视角 100% (零 502 实时窗口)
- 30min 80 全 200, 零 502
- R796 死请求 f15fe5ef (buffer_exhausted) 已滚出 30min 窗口 (延续 6 轮 R797-R802, 已不再产生)

### 4. buffer 全 attempt=1 success
- 5key 一次过, 零 retry/WAIT/KEYMGR/BREAKER
- 容器健康: nv_gw (Up 37min) + cc4101 (Up 8h) + logs_db (Up 6d)

## 判稳结论

| 指标 | 实测 | 阈值 | 结论 |
|---|---|---|---|
| cc4101 SR (排499) | 100% | ≥99% | ✅ NOP |
| tier 错误 | 0 | - | ✅ 连续 5 轮零错 |
| fallback 触发率 | 0.9% | <10% | ✅ |
| 新错误模式 | 无 | - | ✅ |

→ **NOP 巡检轮, 只记数据不改码.**

## 噪声说明 (不属 cc2 链路)

- `all_tiers_exhausted × 6` + dsv4f0731_nv SR 40% (4/10): hermes caller 的 dsv4f0731_nv 链路噪声, 属并行 R-dsv4f-fallback 自优化线 (R1025), 不穿透 cc2 (cc4101-primary).

## 暴露的长期改进点 (本轮不动, 已记 6 轮 R797-R802)

**WAIT-RECOVER retry 只跑 1 key** (buffer_stream.py:532-534): `self.attempt=0; _execute_and_drain(timeout_stairs[0])` 调用一次, 试 1 key 失败即 WAIT-FAIL send 502.
当前 SR 100%, 等下次集中瞬断复现确认必要性. deadline 评估:
- 方案 A: WAIT-RECOVER retry 跑完整 chain (5key) — 5 attempt (194s) + wait 180s + chain 220s = ~594s 超 cc4101 470s
- 方案 B: WAIT-FAIL 后再 wait 一轮 (2 次 wait 机会) — 叠加超时同上
- 方案 C: 增大 cc4101 STREAM_TOTAL_DEADLINE — cc2 SDK 600s 是硬上限

## SR 趋势

| 轮 | 30min SR (cc4101) | tier 噪声 (glm5_2_nv) | 备注 |
|---|---|---|---|
| R798 | 99.0% (排499=100%) | 0 错误 | tier 零错开始 |
| R799 | 99.0% (排499=100%) | 0 错误 | 连续 2 轮 |
| R800 | 99.1% (排499=100%) | 0 错误 | 连续 3 轮 |
| R801 | 99.1% (排499=100%) | 0 错误 | 连续 4 轮, 历史最长 |
| **R802** | **99.1% (排499=100%)** | **0 错误** | **连续 5 轮, 再创历史新高** |

cleanest 持平 27 (R774 基线).

## 下一步

- **R803**: 继续 NOP 监测 30min cc4101 SR. 维持 tier 连续零错窗口.
- **长期候选不动**: WAIT-RECOVER retry chain 鲁棒化 (方案 A/B/C). 当前 SR 100% 不急.
- nv_gw 容器 base = R796 09:10 up -d, 续跑稳定 (wait_queue 180s).
- 并行 dsv4f 自优化线 — 不属 cc2 职责.

## 参数快照 (R802 = R796, 无改动)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: **NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180** (R796, 续净 6 轮), NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全用 fid1=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3, LONG=120
- nv_gw: StartedAt 2026-08-05 09:10 CST (R796 up -d 重建, 续跑)
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
