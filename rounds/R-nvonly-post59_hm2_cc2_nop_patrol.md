# R-nvonly-post59 — hm2_cc2 NOP 巡检轮 (2026-08-02 04:30 CST)

## 基线
- 主仓 git HEAD: 81d2331 (post57 已 push; post58 本仓 commit 未走主仓 round, 内容等同 post59)
- 容器: nv_gw/cc4101 Up 2 hours, 全栈 Up
- 本轮: NOP 巡检轮, 0 改动 0 重启

## 轮前链路分析 (30min 窗口, 04:24 CST)
### cc2 (cc4101-primary) — 0 req
session 轮前无流量产生, 无数据可判 cc2 SR. 链路健康无故障.
- 0 cc2 tier error
- 0 cc2 buffer/wait/error 日志

### hermes caller (非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

- dsv4p_nv SR=0% (0/6), 6×all_tiers_exhausted (5key 全挂)
- 按分钟趋势: 19:55~20:20 每 5min 1×429, 稳定限流
- **NVCF 侧 dsv4p 持续限流, 与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p)
- fallback 发生率: f|6 (hermes→dsv4p 路径, 非 cc2→glm5_2_nv)

## 健康验证 (04:30 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up ✓ |
| git pull (cc2 master) | Already up to date ✓ |
| DB 复核 | cc2 30min 0 req (cc4101-primary), 0 tier error ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 配置实测 (注入)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_TIMEOUT_BUDGET_S=180, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: FALLBACK_UPSTREAM=ms_gw:40007, FALLBACK_UPSTREAM_MODEL=glm5_2_ms, PRIMARY_UPSTREAM=nv_gw:40006, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30, UPSTREAM_IDLE_TIMEOUT=150

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
