# R-nvonly-post40 — hm2_cc2 NOP 巡检轮

**时间**: 2026-08-02 03:35 CST
**轮次**: R-nvonly-post40 (NOP 巡检轮, 第 40 轮)
**HEAD (前)**: 966e1a0 (post39)

## 判稳三阈值 (本轮实测)

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 tier error, 0 buffer, 0 wait 日志) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启. 0 改动, 0 restart.

## 链路健康验证

| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable Up ~1h, ms_gw/logs_db Up 2d ✓ |
| nv_tier_attempts 30min | 0 rows (0 error) ✓ |
| buffer/wait/error 日志 30min | 无 ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 注入数据分析 (轮前链路分析快照)

- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量产生, 无数据可判 SR).
- hermes caller 打 dsv4p_nv SR=44.4% (4/9, 5×all_tiers_exhausted) — NVCF 侧 dsv4p 限流.
  **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). 30min 趋势: 19:00-19:25 间歇 429 后段自恢复.
- fallback 发生率: 全部 9 req 都是 dsv4p_nv/hermes, 非 cc2.

## 实时复核 (本轮 session 自查)

- cc4101-primary 30min nv_requests: 0 rows ✓ (与注入快照一致)
- nv_tier_attempts 30min: 0 rows ✓ (注入快照的 5×all_tiers_exhausted 是 19:00-19:25 时段 hermes/dsv4p, 本轮 30min 窗口已清出, 0 残留)
- buffer/wait/error 日志: 无 ✓

## cc2 SR 走势

| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17-post27 | 100% (1-3 req/轮) | 0 | ✅ 11 连庄满分 |
| post28-post39 | 0 req | 0 | — (无流量, 链路健康, 不打断) |
| **post40** | **0 req** | **0** | — (无流量, 链路健康, 不打断) |

## 参数快照 (实测 2026-08-02 03:27 注入)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `MIN_OUTBOUND_INTERVAL_S=10`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`, `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`, `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM=ms_gw:40007`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM=nv_gw:40006`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`
- settings.json: `contextWindow=170000`, `autoCompactWindow=155000`, `API_TIMEOUT_MS=600000`

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
