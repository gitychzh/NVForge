# R-nvonly-post69 — hm2 cc2 NOP 巡检轮 (2026-08-02 04:55 CST)

## 基线
- 主仓 HEAD: e935fcd (post68)
- 本轮: R-nvonly-post69, NOP 巡检轮. 0 改动, 0 重启.

## 判稳依据 (轮前链路分析 04:51 CST)
| 项 | 实测 | 判定 |
|----|------|------|
| cc2 (cc4101-primary) 30min req | 0 | — 无流量, 非故障 |
| cc2 错误类型 | 无 | ✅ |
| dsv4p_nv (hermes) SR | 66.7% (10/15) | 非 cc2 (cc2 走 glm5_2_nv) |
| dsv4p_nv top error | all_tiers_exhausted ×5 | NVCF 侧 dsv4p 5key 全挂限流 |
| buffer/wait 日志 | 0 行 | ✅ |
| /health | ok, glm5_2_nv, 5 keys | ✅ |
| docker ps | cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up (3h~2d) | ✅ |

## dsv4p_nv hermes 限流分析 (非 cc2)
- per-IP: 203.10.96.139=10×100%, 其余 5×0% (egress IP 漂移, 单 IP 限流)
- 按分钟: 20:20~20:30 每 5min 1×429 稳定限流, 20:30~20:36 恢复 10×200 (NVCF 侧周期性限流)
- per-key: key2=10×200, key?=5×429 (单 key 限流, 非 cc2 链路问题)

## 三阈值
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 SR | 0 req | — 无数据, 链路健康 |
| 新错误 | 无 | ✅ |
| transport | 0 | ✅ |
→ **NOP 巡检轮**, 不改码不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 备注 |
|------|--------|------|
| post17-post27 | 100% | 11 连庄 |
| post28-post68 | 0 req | 无流量不打断 |
| post69 | 0 req | 无流量不打断 |

## 参数快照 (注入实测)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `MIN_OUTBOUND_INTERVAL_S=10`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`, `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM=ms_gw:40007`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM=nv_gw:40006`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`
- settings.json: `contextWindow=170000`, `autoCompactWindow=155000`, `API_TIMEOUT_MS=600000`

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧, 非 cc2).
- 若 cc2 出新错误或 SR<99% (排除 fallback 兜底), 再小步改.
