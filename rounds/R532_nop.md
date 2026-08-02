# R532 — NOP 巡检轮 (2026-08-03 07:15 CST)

## 摘要
- 0 改动 0 restart. NOP 接棒巡检轮 (延续 R525-R531 间歇空闲窗口).
- cc2 (cc4101-primary) 30min 0 req (session 间歇空闲, 无 cc2 评估样本, 铁律1 cc2 视角不满足 → 不动码).
- dsv4p_nv 30min: 10 req SR=40.0% (4×200 + 5×429 + 1×502), 全 `hermes` caller (1× openclaw 200).
- 唯一错误类型 `all_tiers_exhausted` × 6 (5×429 + 1×502 peer-fb-skip), 无新错误类型.
- 502 (peer-fb-skip) 与 R530/R531 同一 53s RemoteDisconnected 请求 (07:02:22 CST, k3 NVCF pexec 挂起 53s 后断),
  dsv4p_nv 在 `NVU_PEER_FB_SKIP_MODELS` 跳过名单 → 返 local 502, cc4101 层走 ms_gw fallback.
- NV-GLOBAL-COOLDOWN tier=dsv4p_nv 每 5min 1 次 (06:45-07:10 持续), 与 R268-R531 完全一致, NVCF 侧配额波动.
- 无 stream_total_deadline, 无 zombie_empty_completion, 无 tier_attempts (KeyManager 全局冷却在前拦截), deadline 链对齐 OK.
- 配置实测与 R475-R531 完全一致, 无漂移.

## 本轮改动
- 无 (NOP). 铁律1 cc2 视角不满足 (cc2 0 流量无评估样本) → 不动码.
- dsv4p_nv 错误模式与 R268-R531 完全一致 (周期性 all_tiers_exhausted + NVCF 侧 429 配额波动),
  非 nv_gw 代码问题.

## 依据
- cc2 30min 0 req → 无 cc2 评估样本 (铁律1 cc2 视角不满足)
- dsv4p_nv 10 req: 4×200 (k3/k4, 07:01-07:04 短暂恢复窗口, 8.7s avg dur) +
  5×429 (每 5min 1 次 GLOBAL-COOLDOWN 180s) + 1×502 (k3 53s RemoteDisconnected)
- 唯一错误类型: `all_tiers_exhausted` × 6, avg_dur=9.9s
  (5×429 avg 1.3s + 1×502 avg 53.2s; 502 与 429 同型, 仅 HTTP status 映射不同)
- 502 根因链 (07:02:22 CST, 与 R530/R531 同一请求):
  1. k3 NVCF pexec 调用挂起 53s (其他 4 key 全在 GLOBAL-COOLDOWN 180s 内)
  2. 53s 后 NVCF 侧 RemoteDisconnected (传输层挂死, 非 429 配额)
  3. NV-TIER-FAIL: all 5 keys failed, elapsed=53167ms
  4. NV-PEER-FB: dsv4p_nv 在 peer-fb skip list → 返回 local 502 (不走 peer fallback)
  5. cc4101 层接收 502 → 走 `FALLBACK_UPSTREAM_URL=ms_gw` + `FALLBACK_UPSTREAM_MODEL=glm5_2_ms` 兜底
- 53s < UPSTREAM_TIMEOUT=90s: 传输挂起在超时内自己断了, 无需调整超时参数
- 全局冷却模式: 每 5min 1 次 NV-GLOBAL-COOLDOWN tier=dsv4p_nv all keys 429 (06:45:55-07:10:56 持续),
  与 R268-R531 完全一致, 是 NVCF 侧配额波动, 非 nv_gw 故障
- nv_tier_attempts 0 行 = 429/502 在 tier 层前/内被 KeyManager 全局冷却拦截, 历史一致行为
- 无新错误类型 (仅 all_tiers_exhausted), 无 stream_total_deadline, deadline 链对齐 OK
- 配置无漂移 → 无参数回退必要

## 验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv,
  nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], port=40006
- docker ps: nv_gw Up 29h, nv_gw_stable Up 29h, cc4101 Up 17h, ms_gw Up 3 weeks, logs_db Up 4 weeks
- 配置实测与 R475-R531 完全一致, 无漂移

## 链路数据 (07:15:10 CST 实时复核)
### 30min 窗口
- cc4101-primary (cc2): 0 req (session 间歇空闲)
- hermes caller, dsv4p_nv: 9 req (3×200 + 5×429 + 1×502), SR=33.3%
- openclaw caller, dsv4p_nv: 1 req (1×200), SR=100%
- 200 finish_reason: tool_calls × 3, stop × 1 (无 zombie)
- fallback_occurred=f × 10 (nv_gw 层 dsv4p_nv 不 fallback, cc4101 层兜底)

### 30min 错误分类
| error_type | sub | count | avg_dur_s | HTTP status |
|------------|-----|-------|-----------|-------------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | 1.3 | 429 |
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 1 | 53.2 | 502 (peer-fb-skip) |

### KeyManager 行为 (持续)
- 全 5 key 429 → NV-GLOBAL-COOLDOWN tier=dsv4p_nv, Marking all cooling 180s
- 每 5min 1 次 (06:45:55 / 06:50:55 / 06:55:55 / 07:05:56 / 07:10:56 CST)
- 全局冷却 180s 后 ProbeWorker 探测恢复, 周期性与 R268-R531 一致
- 07:01 CST 短暂恢复窗口: k3 连续 3 次成功 (NV-SUCCESS on first attempt)
- 07:04:59 k4 1×200 (单次成功)
- 07:02:22 k3 53s RemoteDisconnected → 502 (peer-fb-skip)

### 502 请求路径 (07:02:22 CST, 与 R530/R531 同一请求)
- 07:01:29 NV-REQ mapped=dsv4p_nv start_tier=dsv4p_nv stream=True
- 07:01:29 NV-TIER Starting tier=dsv4p_nv model=deepseek-v4-pro func=12acbc62
- 07:01:29 NV-KEY attempt 1/7: k3 → NVCF pexec via socks5h://172.18.0.1:7902
- 07:02:22 NV-CONN k3 connection error: Remote end closed connection without response (53s 挂起后断)
- 07:02:22 NV-TIER-FAIL all 5 keys failed: other=1, elapsed=53167ms
- 07:02:22 NV-ALL-TIERS-FAIL ABORT-NO-FALLBACK, elapsed=53170ms
- 07:02:22 NV-PEER-FB model=dsv4p_nv in skip list → returning local 502 for agent ms_gw fallback

### Fallback 配置实测 (持续)
- `NVU_DISABLE_MS_FALLBACK=0` (ms fallback 启用, 但只覆盖 glm5_2_nv)
- `NVU_MS_FALLBACK_MODELS=glm5_2_nv` (ms fallback 不含 dsv4p_nv)
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv` (dsv4p_nv 跳过 peer fallback)
- → dsv4p_nv 全挂时 nv_gw 层裸返 429/502, 不走 ms/peer fallback
- cc4101 层 `FALLBACK_UPSTREAM_URL=ms_gw` + `FALLBACK_UPSTREAM_MODEL=glm5_2_ms` 兜底 cc2/hermes 请求

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为 (当前 0 cc2 buffer 样本)
- 关注新错误类型 (非 all_tiers_exhausted/zombie) 或 key/IP 级故障, 再决定是否介入
- 502 (peer-fb-skip) 频次 >=3/h 再评估 dsv4p_nv fallback 策略 (当前 1/30min, 偶发可接受)
- k3 53s RemoteDisconnected 传输挂死若频次上升再评估 (当前 1 次, 偶发, UPSTREAM_TIMEOUT=90s 已能容纳)
- dsv4p_nv 小时级 SR 持续 <60% + cc2 缓冲流量恢复后再评估:
  (a) 将 dsv4p_nv 加入 `NVU_MS_FALLBACK_MODELS` 让 nv_gw 层也兜底, 或
  (b) 切换 `PRIMARY_UPSTREAM_MODEL` 回 glm5_2_nv, 或
  (c) 增加 ring fallback
- all_tiers_exhausted 持续 >=5/h 且中段不恢复 再评估 buffer/KeyManager 参数 (TIER_COOLDOWN_S 180s 是否过激)

## 参数快照 (本轮未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_MS_FALLBACK_MODELS=glm5_2_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, PRIMARY_UPSTREAM_MODEL=dsv4p_nv,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
