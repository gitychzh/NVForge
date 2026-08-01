# R-nvonly-post91 — hm2 cc2 NOP 巡检轮 (2026-08-02 05:57 CST)

## 结论: NOP 巡检轮, 0 改动 0 重启

cc2 (cc4101-primary) 30min 窗口 0 req (session 轮前无流量产生), 无数据可判 cc2 SR.
链路健康无故障: 容器全 Up, /health ok, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
与 post90 基线完全一致, 无新错误, 无需改码.

## 健康验证 (05:57 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min nv_requests | 0 req (cc4101-primary) — |
| cc2 30min tier errors | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓ |
| hermes HEAD | bc80549 (post90), Already up to date ✓ |

## 其他 caller (非 cc2 链路)
hermes 打 dsv4p_nv SR=37.5% (3/8): 5×429 + all_tiers_exhausted, 周期性 5min 一发 429,
NVCF 侧 dsv4p 限流模式. **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback 发生率 f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR 是 NVCF 侧限流, 非 cc2 链路, 不在本轮优化范围.

## 参数快照 (2026-08-02 05:56 CST 实测注入)
| 参数 | 值 |
|------|-----|
| nv_gw.UPSTREAM_TIMEOUT | 90 |
| nv_gw.TIER_COOLDOWN_S | 180 |
| nv_gw.KEY_COOLDOWN_S | 30 |
| nv_gw.NVU_DISABLE_MS_FALLBACK | 0 (fallback 已恢复) |
| nv_gw.NVU_BUFFER_CALLERS | cc4101-primary,openclaw2 |
| nv_gw.NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |
| nv_gw.NVU_CALLER_KEY_MAP | hermes:2;openclaw:3;opencode:4 |
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.UPSTREAM_TIMEOUT | 130 |
| cc4101.PRIMARY_UPSTREAM_MODEL | glm5_2_nv |
| cc4101.FALLBACK_UPSTREAM_URL | http://ms_gw:40007/v1/chat/completions |
| cc4101.PRIMARY_UPSTREAM_URL | http://nv_gw:40006/v1/messages |
