# R-nvonly-post27 — hm2_cc2 NOP 巡检轮 (11 连庄)

> 日期: 2026-08-02 02:41 CST
> 上轮: R-nvonly-post26 (NOP 巡检, 10 连庄)
> 本轮判定: **NOP 巡检轮**, 0 改动, 0 重启.

## 判稳三阈值

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 1/1 = 100% | ✅ (经 ms_gw fallback 兜底) |
| 新错误类型 | 无 (all_tiers_exhausted ×5 全是 dsv4p_nv/hermes, 非 cc2) | ✅ |
| transport 层 | 0 错误 (nv_tier_attempts 空, 无 RemoteDisconnected/SSL) | ✅ |
| buffer 触发 | 1 req 经 5key buffer 全 execute_failed → ms_gw fallback 兜底成功 | ✅ (fallback 已恢复) |

## 本轮 cc2 链路数据 (cc4101-primary, 30min)

| request_model | status | fallback_occurred | fallback_to | count | avg_ms |
|---------------|--------|-------------------|-------------|-------|--------|
| glm5_2_ms     | 200    | t                 | ms_gw       | 1     | 166464 |

cc2 本轮 1 个请求 (req=eda169d4) 完整链路 (docker logs nv_gw 实证):
1. 5 次 buffer attempt (k1→k5) 全 `execute_failed` (NVCF chain failed, all_keys_exhausted=True)
   - 每次 attempt 90s timeout, 15s backoff 间隔
2. WaitQueue `NV-BUFFER-WAIT` 等 120s 未恢复
3. `NV-BUFFER-EXHAUSTED` → `NV-BUFFER-MS-FB-ATTEMPT` (ms_gw fallback)
4. `NV-BUFFER-MS-FB-OK` ms_gw 兜底成功, elapsed=166464ms, 最终 200

→ NVCF 侧 glm5_2_nv 短时全挂 (5key 全 execute_failed), 经 ms_gw fallback 兜底, 全链路 200.
符合"ms_gw fallback 已恢复"指令 (`NVU_DISABLE_MS_FALLBACK=0`), 非 nv_gw 故障.

## 其他 caller (非 cc2 流量)

| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 9 |
| hermes | dsv4p_nv | 429 | 4 |
| hermes | dsv4p_nv | 502 | 1 |

dsv4p_nv SR=64.3% (9/14), 5× all_tiers_exhausted (5key 全挂, avg 7925ms) + 4×429 + 1×502.
NVCF 侧 dsv4p_nv 限流持续, **与 cc2 无关** (cc2 已切 glm5_2_nv).

## fallback 发生率

| fallback | count |
|----------|-------|
| f (无) | 14 |
| t (有) | 1 |

1 次 fallback 到 ms_gw (glm5_2_ms), 符合"fallback 已恢复"指令.

## 健康验证

| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | `nv_default_model: glm5_2_nv`, `nv_num_keys: 5`, status=ok ✓ |
| nv_gw `NVU_DISABLE_MS_FALLBACK` | `0` (fallback 已恢复) ✓ |
| cc4101 `FALLBACK_UPSTREAM_URL` | `http://ms_gw:40007/v1/chat/completions` ✓ |
| cc4101 `CC4101_STREAM_TOTAL_DEADLINE_S` | `470` ✓ |
| docker ps | cc4101 Up 38m, nv_gw Up 38m, nv_gw_stable Up 42m, ms_gw Up 2d, logs_db Up 2d ✓ |

## cc2 SR 走势

| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康, 满分 |
| post18 | 1/1=100% | 0 | ✅ 连续满分 |
| post19 | 2/2=100% | 0 | ✅ 连续满分 |
| post20 | 2/2=100% | 0 | ✅ 连续满分 |
| post21 | 2/2=100% | 0 | ✅ 5 连庄 |
| post22 | 3/3=100% | 0 | ✅ 6 连庄 (含 1 次 ms_gw fallback 兜底) |
| post23 | 2/2=100% | 0 | ✅ 7 连庄 (含 1 次 ms_gw fallback 兜底) |
| post24 | 2/2=100% | 0 | ✅ 8 连庄 (含 1 次 ms_gw fallback 兜底) |
| post25 | 2/2=100% | 0 | ✅ 9 连庄 (含 1 次 ms_gw fallback 兜底) |
| post26 | 1/1=100% | 0 | ✅ 10 连庄 (1 次 ms_gw fallback 兜底) |
| **post27** | **1/1=100%** | **0** | ✅ 11 连庄 (1 次 ms_gw fallback 兜底, NVCF glm5_2_nv 短时全挂经 fallback 兜底) |

## 参数快照 (实测 2026-08-02 02:41)

- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `MIN_OUTBOUND_INTERVAL_S=10`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`, `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`
- settings.json: `contextWindow=170000`, `autoCompactWindow=155000`, `API_TIMEOUT_MS=600000`

## 下一步

- 继续 NOP 巡检, 维持 11 连庄.
- 关注 dsv4p_nv SR (hermes caller, 非 cc2 链路), 若 NVCF 侧恢复则整体 SR 上升.
- 关注 glm5_2_nv 是否频繁出现 5key 全 execute_failed (本轮 1 次, 经 fallback 兜底); 若频率上升, 排查 NVCF 侧配额/限流.
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底成功的请求), 再找根因小步改.
