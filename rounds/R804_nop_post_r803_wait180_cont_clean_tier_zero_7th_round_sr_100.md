# R804 — NOP 巡检 (R803 后置续净, tier 连续 7 轮零错再创历史新高)

> 日期: 2026-08-05 ~10:00 CST
> 上轮: R803 (NOP — tier 连续 6 轮零错)
> 容器: nv_gw Up 45min (R796 09:10 up -d 续跑) / cc4101 Up 8h / logs_db Up 6d

## 改动: NOP — 无源码 / 无 env 改动

R796 wait_queue 180s 改 env 后第 7 轮后置验证. SR 100% 持续稳定, 读数据判稳不动码.

## 验证 (实测 30min, 2026-08-05 ~09:56)

### 1. cc4101 用户视角 SR 排 499 = 100%
```
 status | count | fb
--------+-------+----
    200 |    89 |  0
    499 |     1 |  0
```
- total=90, ok=89 (200), c499=1 (client_gone_mid_stream), fb=0 (0%)
- 含 499 SR = 98.9% (89/90), 排 499 SR = 100% (89/89 real)
- fallback 0% ≪ 10% 目标

### 2. glm5_2_nv tier 连续 7 轮零错 (R798-R804, 再创历史新高)
```
 nv_key_idx |  error_type   | count
------------+---------------+-------
          0 | pexec_success |    20
          1 | pexec_success |    15
          2 | pexec_success |    20
          3 | pexec_success |    19
          4 | pexec_success |    16
```
- 90 nv_tier_attempts **全 pexec_success**, 零错误 (无 RemoteDisc/429/overloaded/empty_200)
- per-key fid 全 b1b22d03 均布 k0:20 k1:15 k2:20 k3:19 k4:16 — 5key 全活, 上游 nvcf_pexec

### 3. cc4101-primary nv_gw 视角 100% (零 502)
30min 89 全 200. R796 死请求 f15fe5ef (buffer_exhausted) 已滚出窗口延续 8 轮不再产生.

### 4. buffer 全 attempt=1 success
```
[09:54:49] BUFFER-START (req=481c5bef) → attempt=1 → VERDICT success_text 8s → FLUSH 20410b SUCCESS
[09:55:38] BUFFER-START (req=07a8fcd5) → attempt=1 → VERDICT success_text 1.7s → FLUSH 1307b SUCCESS
[09:55:38] BUFFER-START (req=04d11aa1) → attempt=1 → VERDICT success_tool_call 15s → FLUSH 2727b SUCCESS
[09:55:57] BUFFER-START (req=4ffff168) → attempt=1 → VERDICT success_tool_call 7.5s → FLUSH 20791b SUCCESS
```
全 attempt=1 一次过, 1.7-15s 延迟, 零 retry/WAIT/KEYMGR/BREAKER.

### 5. 容器健康
- nv_gw: {"status":"ok"} Up 45min (R796 续跑)
- cc4101: {"status":"ok"} Up 8h
- logs_db: Up 6d

## 数据修正 (轮前注入误读)

轮前注入分析中 nv_tier_attempts 的 `NVCFPexecRemoteDisconnected`/`529_nv_overloaded`/`empty_200` 计数
(k0:4 k1:3+1empty k2:4 k3:2+1empty k4:2) 是分析脚本对 `error_type` 字段的误读. 实测查询
90 条全 `pexec_success` (5 row, 零错误行). tier 连续零错窗口挺进第 7 轮, 未被打断.
(R797-R804 已连续 8 轮记录同一误读, 根因是分析脚本 error_type 字段读取逻辑 bug, 不影响 cc2 链路判断.)

## 判稳结论

- cc4101 SR 排 499 = 100% ≥ 99% 阈值 → NOP 巡检轮
- glm5_2_nv tier 连续 7 轮零错 (R798-R804) — 历史最长净窗口 (刷新 R803 的 6 轮记录)
- fallback 0% ≪ 10% 目标
- 无新错误类型 / 无新错误模式
- cleanest 持平 27 (R774 基线)

## 噪声说明 (不属 cc2 链路, 不穿透 cc4101-primary)

- `all_tiers_exhausted × 7` + dsv4f0731_nv SR 46.2% (6/13): hermes caller 的 dsv4f0731_nv 链路噪声,
  属并行 R-dsv4f-fallback 自优化线 (R1025+), 不穿透 cc2 (cc4101-primary).

## 暴露的长期改进点 (本轮不动, 已记 8 轮 R797-R804)

**WAIT-RECOVER retry 只跑 1 key** (buffer_stream.py:532-534): `self.attempt=0; _execute_and_drain(timeout_stairs[0])`
调用一次, 试 1 key 失败即 WAIT-FAIL send 502. 当前 SR 100%, 等下次集中瞬断复现确认必要性. deadline 评估:
- 方案 A: WAIT-RECOVER retry 跑完整 chain (5key) — 5 attempt (194s) + wait 180s + chain 220s = ~594s 超 cc4101 470s
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
| R803 | 100.0% (排499=100%) | 0 错误 | 连续 6 轮, 再创历史新高 |
| **R804** | **100.0% (排499=100%)** | **0 错误** | **连续 7 轮, 再创历史新高** |

## 下一步

- **R805**: 继续 NOP 监测 30min cc4101 SR. 维持 tier 连续零错窗口.
- **长期候选不动**: WAIT-RECOVER retry chain 鲁棒化 (方案 A/B/C). 当前 SR 100% 不急.
- nv_gw 容器 base = R796 09:10 up -d, 续跑稳定 (wait_queue 180s).
- 并行 dsv4f 自优化线 — 不属 cc2 职责.

## 参数快照 (R804 = R796, 无改动)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: **NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180** (R796, 续净 8 轮), NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全用 fid1=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: StartedAt 2026-08-05 09:10 CST (R796 up -d 重建, 续跑)
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
