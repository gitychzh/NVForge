# R-nvonly-post73 — hm2 cc2 NOP 巡检轮 (2026-08-02 05:03 CST)

## 基线
- 主仓 HEAD: f4f5368 (post72) → 本轮 post73 (待 commit)
- 上轮: R-nvonly-post72 NOP, cc2 30min 0req 无流量无故障
- 容器: nv_gw/cc4101/nv_gw_stable Up 3h, legacy_cc_1/legacy_ms_litellm Up 12h, oc4105/opclaw4103 Up 37h, cx4102 Up 2d, 全 Up

## 轮前链路分析 (注入, 30min 窗口 05:03)
| 项 | 实测 |
|----|------|
| cc2 (cc4101-primary) 30min | 0 req (session 轮前无流量) |
| hermes/dsv4p_nv | 200×9, 429×5 → SR=64.3% (NVCF 侧限流, 非 cc2) |
| top error | all_tiers_exhausted ×5 (dsv4p 5key 全挂, NVCF 侧) |
| cc2 tier error | 0 |
| cc2 buffer/wait 日志 | 0 行 |

dsv4p_nv per-IP: 203.10.96.139=9×100%, 其余 5×0% (egress 漂移单 IP 限流).
按分钟: 20:36~21:00 间歇 5×429 周期性限流, 20:35/20:55 恢复 9×200.
200 延迟 avg_dur=12498ms (dsv4p 正常水位), finish_reason: tool_calls×8, stop×1 (无 zombie).
→ dsv4p 限流是 NVCF 侧周期性配额, cc2 走 glm5_2_nv 不受影响.

## 本轮实做 (NOP 巡检)
1. git pull --ff-only origin main → Already up to date (f4f5368 post72).
2. 链路健康验证:
   - `docker ps` → 全 Up (nv_gw/cc4101/nv_gw_stable 3h, legacy_* 12h, oc4105/opclaw4103 37h, cx4102 2d) ✓
   - `curl nv_gw /health` → status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓
3. 拉实时 30min 数据 (cross-check 注入数据):
   - cc4101-primary SR → 0 req (与注入一致, session 轮前无流量)
   - cc4101-primary error_type → 0 rows
   - nv_gw buffer/wait 日志 → 0 行
   - cc_requests stream_total_deadline (6h) → 0 次
4. 三阈值判稳 → 全绿 → NOP, 不改码, 不重启.

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 0 cc2 error | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer/wait 触发 | 0 行日志 | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 改动
- 0 改动, 0 重启, 0 fallback 调整.

## 验证
- /health ok, docker ps 全 Up, 0 cc2 error, 0 buffer/wait 日志, 0 stream_total_deadline.

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.

## 参数快照 (实测 2026-08-02 05:03 注入)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `UPSTREAM_TIMEOUT=90`, `TIER_TIMEOUT_BUDGET_S=180`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `MIN_OUTBOUND_INTERVAL_S=10`, `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`
- settings.json: `contextWindow=170000`, `autoCompactWindow=155000`, `API_TIMEOUT_MS=600000`
