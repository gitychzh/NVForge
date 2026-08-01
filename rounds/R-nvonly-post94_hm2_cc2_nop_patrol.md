# R-nvonly-post94 — hm2 cc2 NOP 巡检轮 (2026-08-02 06:05 CST)

## 本轮结论: NOP 巡检轮, 0 改动, 0 重启

## 链路数据 (30min 窗口, 注入数据)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量产生, 无数据判 SR)
- 其他 caller: hermes 打 dsv4p_nv SR=37.5% (3/8, 5×429+all_tiers_exhausted)
  - 周期性 5min 一发 429 (21:35/45/50/55/22:00), NVCF 侧 dsv4p 限流
  - **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- 30min fallback 发生率 f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复工作正常)

## 健康验证 (06:05 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | status=ok, glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 tier error (30min) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0, FALLBACK=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 SR | 0 req (无流量) | — (链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 依据
- cc2 30min 0 req 无流量, 链路健康无故障, 无数据可改 → NOP.
- dsv4p_nv 低 SR 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路 (cc2 走 glm5_2_nv), 不在本轮优化范围.
- ms_gw fallback 已恢复 (`NVU_DISABLE_MS_FALLBACK=0`), dsv4p 全挂时正常 fallback 到 ms, 不主动禁用.

## 验证
- 无码改动 → 无需 restart/py_compile.
- /health + docker ps 通过.

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- 关注 dsv4p_nv 周期性 429 是否扩散到 glm5_2_nv (目前未扩散).

## 参数快照 (06:05 CST 实测注入)
| 参数 | 值 |
|------|-----|
| nv_gw.UPSTREAM_TIMEOUT | 90 |
| nv_gw.TIER_COOLDOWN_S | 180 |
| nv_gw.TIER_TIMEOUT_BUDGET_S | 180 |
| nv_gw.KEY_COOLDOWN_S | 30 |
| nv_gw.NV_INTEGRATE_KEY_COOLDOWN_S | 90 |
| nv_gw.MIN_OUTBOUND_INTERVAL_S | 10 |
| nv_gw.NVU_DISABLE_MS_FALLBACK | 0 (fallback 已恢复) |
| nv_gw.NVU_BUFFER_CALLERS | cc4101-primary,openclaw2 |
| nv_gw.NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |
| nv_gw.NVU_CALLER_KEY_MAP | hermes:2;openclaw:3;opencode:4 |
| nv_gw.NVU_FORCE_STREAM_UPGRADE | 0 |
| nv_gw.NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 150 |
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.UPSTREAM_TIMEOUT | 130 |
| cc4101.UPSTREAM_IDLE_TIMEOUT | 150 |
| cc4101.CC4101_PRIMARY_FAIL_THRESHOLD | 3 |
| cc4101.CC4101_PRIMARY_SKIP_S | 30 |
| cc4101.PRIMARY_UPSTREAM_MODEL | glm5_2_nv |
| cc4101.FALLBACK_UPSTREAM_MODEL | glm5_2_ms |
| cc4101.FALLBACK_UPSTREAM_URL | http://ms_gw:40007/v1/chat/completions |
| cc4101.PRIMARY_UPSTREAM_URL | http://nv_gw:40006/v1/messages |
