# STATE — cc2 自优化 nv_gw 链路 (R-nvonly 方向)

## 当前轮基线 (2026-08-02 22:05 CST, R377 NOP 巡检轮 已完成, R378 待跑)
- 本仓 master: R376 已 push (526917d). hermes 仓: R377 待 push.
- **架构**: cc4101 `PRIMARY_UPSTREAM_MODEL=dsv4p_nv`. cc2 链路 = cc4101(dsv4p_nv) → nv_gw → NVCF.
- **本轮 R377 (hm2_cc2)**: NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 间歇空闲).
  dsv4p_nv 30min 全 caller SR=60.0% (6/10), 失败 4 = 4× all_tiers_exhausted
  (4×429 avg 1895ms NVCF dsv4p function 配额瞬时空位, 非 buffer 流量, 非缓冲 caller hermes).
  本轮无 NV-TIER-SKIP 502 (R376 有 3×), 仅 function 级 429 波.
  **cc2 是缓冲 caller (NVU_BUFFER_CALLERS), 走 buffer 5key 轮转路径, 不受影响.**
  错误类型无新增 (dsv4p 仍 all_tiers_exhausted, 一百轮一致 R268-R377).
  cc2 无流量不受影响, 0 fallback 0 deadline. 0 改动 0 restart. **一百轮一致 R268-R377**.

## R-nvonly 核心铁律 (持续生效)
- 只改 HM2 nv_gw (40006), 不碰 HM1, 不碰 ms_gw 源码.
- ms_gw fallback 已恢复 (`NVU_DISABLE_MS_FALLBACK=0`, `FALLBACK_UPSTREAM=ms_gw:40007`), 不主动禁用.
- 改前有数据, 改后必验证, 写入仓库.

## 本轮关键数据 (30min 实时链路分析注入 ~22:05 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### 2. dsv4p_nv 30min 全 caller SR=60.0% (6/10)
| caller | model | status | count | avg_dur |
|---|---|---|---|---|
| hermes | dsv4p_nv | 200 | 6 | 10133 |
| hermes | dsv4p_nv | 429 | 4 | 1895 |

per-key (dsv4p): key2 → 6×200 (10133); 空 key → 4×429 (1895).
per-egress: 203.10.96.139 → 6× (100); 空 → 4× (0).
finish_reason (200): tool_calls×4, stop×2 (无 zombie).
分钟趋势: 13:35 429×1, 13:40 200×1, 13:41 200×2, 13:45 429×1, 13:50 429×1, 13:55 429×1, 14:00 200×1, 14:01 200×2.
延迟 (200): avg_dur 10133, max 13595, min 5680, avg_ttfb 9087, avg_in 0, avg_out 0.
fallback f×10 (全部 false, 0 fallback).

### 3. 错误分类 (30min)
- 4 dsv4p 错误: 4× all_tiers_exhausted (avg 1895ms) — 全 429 (NVCF dsv4p function 配额瞬时空位).
  - 429: NVCF dsv4p function 配额瞬时空位, 低频偶发, buffer 5key 轮转 + KeyManager 指数退避自恢复.
- 本轮无 NV-TIER-SKIP 502, 无 stream_first_byte_timeout (R376 各有, 本轮无, 自然波动).
- dsv4p 错误类型集合与 R268-R376 一致 (all_tiers_exhausted, 无新增).
- buffer/wait 日志空.

### 4. 健康检查 (沿用 R353, 容器无 restart)
- 容器全 Up: nv_gw 20h, cc4101 8h, nv_gw_stable 20h, ms_gw/logs_db 持续.
- /health: status=ok, nv_num_keys=5, nv_model_tiers=[kimi_nv,dsv4p_nv,glm5_2_nv].
- 配置未变 (见参数快照).

## 根因: NVCF dsv4p function 429 波 (非代码缺陷, 沿用 R278-R376 分析)

### 结论
- **非 nv_gw 代码缺陷, 无需本轮改码**.
- NVCF function 级配额是上游硬限制. dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function,
  function 配额耗尽时 5 key 同时收 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- 本轮无 NV-TIER-SKIP 502 (R376 有 3×), 说明本轮无全 key cooling 瞬拒, 仅 function 级 429 波.
- 当前 cc2 流量极低, all_tiers_exhausted 罕见且自恢复, 不达介入阈值.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=60.0% (6/10), 较 R376 41.7% (5/12) 上升 (样本极小自然波动,
  成功 6 vs 5, 失败 4 vs 7, 全部非缓冲 caller, cc2 不受影响).
- dsv4p 错误类型无新增, 与 R268-R376 一致 (一百轮一致).

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR (cc2 走 buffer 路径, 行为可能不同于非缓冲 caller).
- 关注是否出现新错误类型 (非 all_tiers_exhausted/stream_first_byte_timeout) 或 key/IP 级故障, 再决定是否介入.
- all_tiers_exhausted 若从低频偶发转为持续 429 波 (>=5/h), 再评估 buffer 轮转/KeyManager 退避参数.
- NV-TIER-SKIP 若在 cc2 缓冲 caller 上出现 (理论上不应, 因 cc2 走 buffer), 再评估 buffer 与 NV-TIER-SKIP 路径关系.

## 参数快照 (本轮未改, 实测注入)
- cc4101: FALLBACK_UPSTREAM_URL=ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复), UPSTREAM_TIMEOUT=90, NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30.
- KeyManager: 429→120-600s 指数退避; RemoteDisconnected→5-10s 短惩罚不累计 conn_count.
- deadline 链: 90s/buffer-attempt ×5 = 450s buffer < 470s cc4101 < 500s SDK idle.
