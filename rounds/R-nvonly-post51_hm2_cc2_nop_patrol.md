# R-nvonly-post51 — NOP 巡检轮 (hm2_cc2)

**日期**: 2026-08-02 04:10 CST
**轮次**: R-nvonly-post51
**判定**: NOP 巡检轮 (0 改动, 0 重启)

## 依据

### 轮前链路分析 (04:01:32 CST 注入)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量, 无数据判 SR)
- hermes/dsv4p_nv: 6×429 all_tiers_exhausted, SR=0% (NVCF 侧 dsv4p 持续限流, 非 cc2 链路)
- 按分钟趋势: 19:35~20:00 每 5min 1×429, 稳定限流
- 0 cc2 tier error, 0 buffer/wait/error 日志

### 健康验证 (04:10 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable Up 2h, logs_db Up 2d ✓ |
| git pull | Already up to date (main) ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |

→ **NOP 巡检轮**, 不改码, 不重启.

## 配置快照 (实测 04:01 注入)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0` (fallback 已恢复), `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `NVU_FORCE_STREAM_UPGRADE=0`, `MIN_OUTBOUND_INTERVAL_S=10`, `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM=ms_gw:40007`, `PRIMARY_UPSTREAM=nv_gw:40006`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`
- settings.json: `contextWindow=170000`, `autoCompactWindow=155000`, `API_TIMEOUT_MS=600000`

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.

## 连庄记录
post17~post27 连续满分 (11 连庄). post28-post50 均 0 req 不计入连庄也不打断. 本轮 post51 同 post50, 0 req.
