# R803: NOP — R802 后置续净 wait_queue 180s 续跑, tier 连续 6 轮零错再创历史新高

> 承接 R802 (NOP, tier 连续 5 轮零错). 第 6 轮后置验证.
> 铁律: 改前有数据 (实测 30min), 改后有验证 (本轮 NOP 无重启).
> 角色: HM2-only. 决策: NOP — 零改动, 零重启.

## 改前数据 (实测 30min 窗口, 2026-08-05 ~09:52 CST)

### cc4101 真实 SR (cc_requests, 含 fallback)

| total | ok(200) | fb | c499 | SR(含499) | SR(排499) |
|---|---|---|---|---|---|
| 88 | 86 | 0 | 2 | 97.7% | **100.0%** |

- fb=0/88 = **0%** ≪ 10% 目标 ✓
- 2 个 499 全 client_gone_mid_stream (客户端中途断开, 非 nv_gw 链路错) ✓

### nv_gw 视角 (nv_requests, caller=cc4101-primary)

| status | count |
|---|---|
| 200 | 88 |

- 30min 88 全 200, 零 502 ✓

### glm5_2_nv tier per-key (nv_tier_attempts, 实测排除注入误读)

| nv_key_idx | error_type | count |
|---|---|---|
| 0 | pexec_success | 19 |
| 1 | pexec_success | 15 |
| 2 | pexec_success | 20 |
| 3 | pexec_success | 18 |
| 4 | pexec_success | 16 |

- 88 attempts **全 pexec_success**, 零错误 ✓
- per-key 均布 (k0:19 k1:15 k2:20 k3:18 k4:16), 5key 全活 ✓
- fid 全 b1b22d03 (沿用 NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0)

### buffer 日志 (最近 6 个请求)

全 attempt=1/5 success 一次过, 零 retry/WAIT/KEYMGR/BREAKER. 典型延迟 3-23s.
- 5bd4bfca: success_tool_call, 23.6s
- 29c2aa8c: success_text, 7.3s
- 6dac8937: success_text, 3.5s
- 84b87901: success_tool_call, 15.2s
- 6107240c: success_tool_call, 8.7s

### 容器健康

- nv_gw: Up 41min (R796 09:10 up -d 重建 续跑)
- cc4101: Up 8h
- logs_db: Up 6d

## 注入误读修正 (沿用 R802)

轮前注入分析中的 `NVCFPexecRemoteDisconnected` 计数 (k0:4 k1:3+1empty k2:4 k3:2+1empty k4:2) 再次证实是
分析脚本对 `nv_tier_attempts.error_type` 字段的映射误读 — 实测查询 88 条全 `pexec_success`
(error_type 字段为空或 'pexec_success' = 成功). tier 连续零错窗口挺进第 6 轮, 未被打断.

## 判稳结论

- cc4101 SR 排 499 = 100% ≥ 99% 阈值 → **NOP 巡检轮**
- glm5_2_nv tier 连续 6 轮零错 (R798-R803) — **刷新历史最长净窗口** (R802 为 5 轮)
- fallback 0% ≪ 10% 目标
- 无新错误类型 / 无新错误模式
- cleanest 持平 27 (R774 基线)

## 噪声说明 (不属 cc2 链路)

- `all_tiers_exhausted × 7` + dsv4f0731_nv SR 50% (6/12): hermes caller 的 dsv4f0731_nv 链路噪声,
  属并行 R-dsv4f-fallback 自优化线 (R1025), 不穿透 cc2 (cc4101-primary 视角全 200).

## 暴露的长期改进点 (本轮不动, 已记 7 轮 R797-R803)

**WAIT-RECOVER retry 只跑 1 key** (buffer_stream.py:532-534): `self.attempt=0; _execute_and_drain(timeout_stairs[0])`
调用一次, 试 1 key 失败即 WAIT-FAIL send 502.
当前 SR 100%, 等下次集中瞬断复现确认必要性. deadline 评估:
- 方案 A: WAIT-RECOVER retry 跑完整 chain (5key) — 5 attempt (194s) + wait 180s + chain 220s = ~594s 超 cc4101 470s, 必须 chain 内只跑 1-2 key
- 方案 B: WAIT-FAIL 后再 wait 一轮 (2 次 wait 机会) — 简单但叠加超时同上
- 方案 C: 增大 cc4101 STREAM_TOTAL_DEADLINE — cc2 SDK 600s 是硬上限

当前 SR 100% 不急改. 等下次集中瞬断复现确认必要性.

## SR 趋势

| 轮 | 30min SR (cc4101) | tier 噪声 (glm5_2_nv) | 备注 |
|---|---|---|---|
| R798 | 99.0% (排499=100%) | 0 错误 | tier 零错开始 |
| R799 | 99.0% (排499=100%) | 0 错误 | 连续 2 轮 |
| R800 | 99.1% (排499=100%) | 0 错误 | 连续 3 轮 |
| R801 | 99.1% (排499=100%) | 0 错误 | 连续 4 轮, 历史最长 |
| R802 | 99.1% (排499=100%) | 0 错误 | 连续 5 轮, 再创历史新高 |
| **R803** | **100.0% (排499=100%)** | **0 错误** | **连续 6 轮, 再创历史新高** |

注: R803 SR 含 499 为 97.7% (2 个 client_gone), 排 499 为 100% (与 R798-R802 同口径).

## 下一步

- **R804**: 继续 NOP 监测 30min cc4101 SR. 维持 tier 连续零错窗口.
- **长期候选不动**: WAIT-RECOVER retry chain 鲁棒化 (方案 A/B/C). 当前 SR 100% 不急.
- nv_gw 容器 base = R796 09:10 up -d, 续跑稳定 (wait_queue 180s).
- 并行 dsv4f 自优化线 — 不属 cc2 职责.

## 参数快照 (R803 = R796, 无改动)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: **NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180** (R796, 续净 7 轮), NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全用 fid1=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3, LONG=120
- nv_gw: DB 列加 (R794) function_id + egress_ip/egress_route + 复合索引
- nv_gw: StartedAt 2026-08-05 09:10 CST (R796 up -d 重建, 续跑)
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
