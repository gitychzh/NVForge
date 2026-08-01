# R-nvonly-post26 — hm2_cc2 NOP 巡检轮 (10 连庄)

> 日期: 2026-08-02 02:34 CST
> 上轮: R-nvonly-post25 (NOP 巡检, 9 连庄)
> 本轮判定: **NOP 巡检轮**, 0 改动, 0 重启, 0 buffer 触发.

## 判稳三阈值

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 1/1 = 100% | ✅ glm5_2_nv 健康 tier |
| 新错误类型 | 无 (all_tiers_exhausted ×5 全是 dsv4p_nv/hermes+openclaw, 非 cc2) | ✅ |
| transport 层 | 0 错误 (仅 1×429 dsv4p_nv key2) | ✅ |
| buffer 触发 | 无 (1 req 直接 fallback ms 兜底) | ✅ |

→ **NOP 巡检轮**, 不改码, 不重启.

## 本轮关键数据

### 1. cc4101-primary (cc2) 30min 窗口 — 1 req, SR 100%

| caller | model | status | fallback | count | avg_ms |
|--------|-------|--------|----------|-------|--------|
| cc4101-primary | glm5_2_ms | 200 | t | 1 | 166464 |

cc2 本轮 30min 仅 1 个请求:
- nv 侧 (glm5_2_nv) 失败 → fallback 到 ms_gw (glm5_2_ms) 兜底成功, 全链路 166464ms.
- 符合"ms_gw fallback 已恢复"指令, 非 nv_gw 故障.
无 transport 错误, 无 buffer 触发.

### 2. 其他 caller (hermes/openclaw/other, 非 cc2 流量)

| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 14 |
| hermes | dsv4p_nv | 429 | 2 |
| hermes | dsv4p_nv | 502 | 2 |
| openclaw | dsv4p_nv | 200 | 1 |
| other | dsv4p_nv | 200 | 2 |
| other | dsv4p_nv | 502 | 1 |
| other | glm5_2_nv | 200 | 1 |

dsv4p_nv SR=77.3% (17/22): 5× all_tiers_exhausted (5key 全挂, avg 7153ms) + 3×502 + 2×429.
NVCF 侧 dsv4p_nv 持续限流, **与 cc2 无关** (cc2 走 glm5_2_nv).

### 3. tier 错误明细

| key | error_type | count |
|-----|-----------|-------|
| 2 | 429_nv_rate_limit | 1 |

仅 1 次 dsv4p_nv 429 (key2), 无 RemoteDisconnected/SSL EOF. R-nvonly 短惩罚分类持续生效.

### 4. fallback 发生率

| fallback | count |
|----------|-------|
| f (无) | 23 |
| t (有) | 1 |

1 次 fallback 到 ms_gw (glm5_2_ms), 符合"ms_gw fallback 已恢复"指令.

### 5. 健康验证

| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | `nv_default_model: glm5_2_nv`, `nv_num_keys: 5`, status=ok ✓ |
| docker ps | cc4101 Up 31m, nv_gw Up 31m, nv_gw_stable Up 35m, ms_gw Up 2d, logs_db Up 2d ✓ |

## cc2 SR 走势

| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康, 满分 |
| post18 | 1/1=100% | 0 | ✅ 连续满分 |
| post19 | 2/2=100% | 0 | ✅ 连续满分 |
| post20 | 2/2=100% | 0 | ✅ 连续满分 |
| post21 | 2/2=100% | 0 | ✅ 5 连庄 |
| post22 | 3/3=100% | 0 | ✅ 6 连庄 (含 1 次 ms_gw fallback) |
| post23 | 2/2=100% | 0 | ✅ 7 连庄 (含 1 次 ms_gw fallback) |
| post24 | 2/2=100% | 0 | ✅ 8 连庄 (含 1 次 ms_gw fallback) |
| post25 | 2/2=100% | 0 | ✅ 9 连庄 (含 1 次 ms_gw fallback) |
| **post26** | **1/1=100%** | **0** | ✅ 10 连庄 (1 次 ms_gw fallback 兜底) |

## 参数快照 (实测 2026-08-02 02:34)

- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `MIN_OUTBOUND_INTERVAL_S=10`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`
- settings.json: `contextWindow=170000`, `autoCompactWindow=155000`, `API_TIMEOUT_MS=600000`

## 下一步

- 继续 NOP 巡检, 维持 10 连庄.
- 关注 dsv4p_nv SR (hermes/openclaw caller, 非 cc2 链路), 若 NVCF 侧恢复则整体 SR 上升.
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改.
