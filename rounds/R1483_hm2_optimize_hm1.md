# R1483: HM2→HM1 — NOP (post-restart 12min, 4req/2OK, insufficient data)

## 数据收集

- **容器状态**: nv_gw Up 12 minutes (healthy), ms_gw Up 17 hours, logs_db Up 17 hours
- **重启时间**: 2026-07-15T16:58:09Z
- **compose md5**: 089a818e37299c1632ce56e44b326090

## 6h 全局 (pre+post-restart 混合)

| metric | value |
|--------|-------|
| total | 45 |
| OK | 22 |
| fail | 23 |
| SR | 48.9% |

## 6h 错误分布

| error_type | cnt |
|-----------|-----|
| zombie_empty_completion | 16 |
| all_tiers_exhausted | 7 |

## Post-restart 窗口 (12min)

| model | total | OK | fail | SR |
|-------|-------|-----|------|-----|
| dsv4p_nv | 2 | 1 | 1 | 50.0% |
| glm5_2_nv | 2 | 1 | 1 | 50.0% |
| **total** | **4** | **2** | **2** | **50.0%** |

## Post-restart 失败详情

1. **glm5_2_nv zombie_empty_completion** (8,345ms): NVCF content-filter 返回 close-but-empty stream (content_chars=12 < 50, input_chars=221,556). 网关正确检测 zombie 并快速中止 → 触发 openclaw fallback. R1107 确认: code-level feature, faster abort 优于旧 96s 超时. 不可配置修复.

2. **dsv4p_nv all_tiers_exhausted** (64,263ms):
   - k1 → 504_nv_gateway_timeout → NVU_TIER_BUDGET_DSV4P_NV=66 触发 budget break (remaining 1.7s < 5s)
   - ms_gw fallback 触发: `[NV-MS-FB]` → dsv4p_ms
   - ms_gw 成功处理: `[MS-OK-STREAM]` + `[MS-STREAM-DONE]` at 01:07:55-56 (0.7s)
   - nv_gw relay 超时: `[NV-MS-FB] ms_gw relay failed after 123623ms: TimeoutError`
   - **R1103 streaming sync defect**: ms_gw 完成 relay 但 nv_gw 未收到完成信号, OS-level TCP timeout 覆盖 NVU_MS_GW_FALLBACK_TIMEOUT=120. 不可配置修复.

## 环境参数 (全部 floor/optimal)

| param | value | status |
|-------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | safe |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | =UPSTREAM (BUDGET floor) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | sufficient |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal (function-level) |
| NVU_EMPTY_200_FASTBREAK | 2 | set (R1039: no-op in pexec) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal (function-level) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | sufficient |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | =UPSTREAM |
| NVU_PEER_FB_SKIP_MODELS | (empty) | peer-fb enabled for all |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |

## ms_gw 信号

- 6h: 21 req, 18 OK = 85.7% SR
- Post-restart: 2/2 OK (100%)
- ms_gw dsv4p_ms 成功处理但 nv_gw relay 超时 → streaming sync defect 而非 ms_gw 故障

## 评判

- **NOP 是唯一正确决策。** 4 条 post-restart 请求 (12min 窗口) 无法支撑任何参数优化判断
- 2 条 post-restart 失败均为 code-level 缺陷:
  - zombie → NVCF content-filter, R1107 确认 code-level feature
  - dsv4p_nv ATE → R1103 streaming sync defect (ms_gw 完成但 nv_gw 未感知)
- 所有参数已在 floor/optimal 状态
- 铁律: 只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2