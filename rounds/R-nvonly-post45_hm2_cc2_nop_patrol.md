# R-nvonly-post45 — hm2_cc2 NOP 巡检轮

**日期**: 2026-08-02 03:42 CST
**轮次**: R-nvonly-post45 (NOP 巡检, 0 改动, 0 重启)
**接棒**: post44 round 已 commit+push (HEAD=7958310). 本轮延续 NOP 巡检.

## 数据 (30min 窗口, 2026-08-02 03:12~03:42 CST)

### 1. cc2 (cc4101-primary) — 0 req
本轮 30min cc2 无请求产生 (session 轮前无流量). 无数据可判 cc2 SR.
链路健康无故障: 容器全 Up, /health ok, 0 tier error, 0 buffer/wait/error 日志.

### 2. 其他 caller (非 cc2 链路)
| caller | model | status | error_type | count |
|--------|-------|--------|------------|-------|
| hermes | dsv4p_nv | 429 | all_tiers_exhausted | 6 |

dsv4p_nv SR=0% (0/6), 全 429. **与 cc2 无关** (cc2 走 glm5_2_nv).
日志铁证: dsv4p_nv 5key (k1-k5) 全 429, TIER_COOLDOWN=180s, ALL-TIERS-FAIL abort-no-fallback.
NVCF 侧 dsv4p 持续限流 (03:40 一波 5key 全挂).

### 3. tier 错误
nv_tier_attempts 30min: 0 rows (cc2 0 req, 无 cc2 流量进入 tier).
注: hermes 打 dsv4p 的 429 走 nv_gw 内部 KeyManager, 不一定记入 nv_tier_attempts (caller 非 cc4101-primary buffer caller).

### 4. buffer/wait 日志
30min 无 BUFFER-/WAIT-/ERROR 日志 (cc2 0 req, 无流量触发 buffer).

## 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw Up 2h, nv_gw_stable Up 2h, ms_gw/logs_db Up 2d ✓ |
| 配置 (实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |
| buffer/wait/keymanager 日志 | 30min 仅 hermes/dsv4p 的 KeyManager 429, 无 cc2 相关 ✅ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (cc2 无 tier error, 无 buffer/wait) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 决策依据
- cc2 0 req = session 轮前无流量, 非链路故障 (容器全 Up, /health ok).
- hermes/dsv4p_nv 全 429 是 NVCF 侧限流, 与 cc2 (glm5_2_nv) 无关.
- post17~post27 连续满分 11 连庄保持; post28-post45 均 0 req 不计入连庄也不打断.
- 符合铁律"改前有数据": 本轮 cc2 无数据 = 不动, 链路健康 = NOP.

## cc2 SR 走势 (延续)
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17~post27 | 100% (各轮) | 0 | ✅ 11 连庄 |
| post28-post44 | 0 req | 0 | — (无流量, 不打断) |
| **post45** | **0 req** | **0** | — (无流量, 链路健康, 不打断) |

## 参数快照 (实测 2026-08-02 03:36 注入)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `MIN_OUTBOUND_INTERVAL_S=10`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`, `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`, `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM=ms_gw:40007`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM=nv_gw:40006`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
- ms_gw fallback 已恢复, 不主动禁用.

## 本轮动作
- 0 改动, 0 重启, 0 验证 (NOP).
- round 文件 + STATE.md 覆写 + commit + push origin main.
