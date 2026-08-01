# R-nvonly-post25 — hm2_cc2 NOP 巡检轮

- 轮次: R-nvonly-post25
- 主机: HM2 (cc2)
- 时间: 2026-08-02 02:30 CST
- 类型: NOP 巡检轮 (0 改动, 0 重启)
- 上轮: R-nvonly-post24 (8 连庄)

## 本轮数据 (30min 窗口, caller=cc4101-primary 即 cc2)

| request_model | status | fallback_occurred | fallback_to | count | avg_ms |
|---------------|--------|-------------------|-------------|-------|--------|
| glm5_2_nv     | 200    | f                 |             | 1     | 85680  |
| glm5_2_nv     | 200    | t                 | ms_gw       | 1     | (含 fallback) |

cc2 30min 2/2 = SR 100%.
- 1 次 glm5_2_nv 直接成功 (85680ms, 慢路径, 可能含 buffer 重试但最终 200).
- 1 次 nv 侧失败 → fallback 到 ms_gw 兜底成功 (符合"fallback 已恢复"指令).
- 无 transport 错误, 无 RemoteDisconnected/SSL EOF.

## 其他 caller (非 cc2 流量, 仅记录不优化)

| caller | model | SR |
|--------|-------|-----|
| hermes | dsv4p_nv | 14×200 / (14+3+3=20) = 70% (3×429 + 3×502) |
| openclaw | dsv4p_nv | 5/5 = 100% |
| other | dsv4p_nv | 3×200 / (3+2=5) = 60% (2×502) |
| other | glm5_2_nv | 1/1 = 100% |

dsv4p_nv 整体 SR=73.3% (22/30) 是 NVCF 侧限流 (8× all_tiers_exhausted avg 5037ms + 3×429 + 5×502).
与 cc2 无关 (cc2 已切 glm5_2_nv 主链, SR 100%).

## tier 错误 (30min)

| key | error_type | count |
|-----|-----------|-------|
| 2 | 429_nv_rate_limit | 1 |

仅 1 次 dsv4p_nv 429 (key2). 无 transport 错误, 无 RemoteDisconnected/SSL EOF.
R-nvonly 短惩罚分类 (5-10s 不累计 conn_count) 持续生效.

## fallback 发生率

| fallback | count |
|----------|-------|
| f (无) | 32 |
| t (有) | 1 |

1 次 fallback 到 ms_gw (glm5_2_ms), 符合"ms_gw fallback 已恢复"指令, 非 nv_gw 故障.

## 健康验证

| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | `nv_default_model: glm5_2_nv`, `nv_num_keys: 5`, status=ok ✓ |
| nv_gw `NVU_DISABLE_MS_FALLBACK` | `0` (fallback 已恢复) ✓ |
| docker ps | cc4101 Up 27m, nv_gw Up 27m, nv_gw_stable Up 31m, ms_gw Up 2d, logs_db Up 2d ✓ |

## 三阈值判稳

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 2/2 = 100% | ✅ glm5_2_nv 健康 tier |
| 新错误类型 | 无 (仅 1×429 dsv4p_nv, 非 cc2) | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 (2 req 直接成功/1 fallback) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

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
| **post25** | **2/2=100%** | **0** | ✅ 9 连庄 (含 1 次 ms_gw fallback 兜底) |

## 参数快照 (实测 2026-08-02 02:30)

- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`
- settings.json: `contextWindow=170000`, `autoCompactWindow=155000`, `API_TIMEOUT_MS=600000`

## 下一步

- 继续 NOP 巡检, 维持 9 连庄.
- 关注 dsv4p_nv SR (hermes/openclaw caller, 非 cc2 链路), 若 NVCF 侧恢复则整体 SR 上升.
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改.
