# R-nvonly-post63 — hm2_cc2 NOP 巡检轮

- 轮次: R-nvonly-post63 (2026-08-02 04:37 CST)
- 类型: NOP 巡检轮 (无流量, 链路健康, 0 改动 0 重启)
- 主仓 HEAD: e778c31 (post62, 已 pull 已 up-to-date)

## 判稳数据 (30min 窗口)

### cc4101-primary (cc2) — 0 req
本轮 session 轮前无流量产生, 30min cc4101-primary 0 req. 无数据可判 cc2 SR.
DB 复核确认 0 rows. 链路健康无故障.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 6 |
| hermes | dsv4p_nv | 429 | 4 |

hermes 打 dsv4p_nv SR=60.0% (6/10), 4×all_tiers_exhausted (5key 全挂, NVCF 侧 dsv4p 限流).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
按分钟趋势: 20:10~20:25 每 5min 1×429 稳定限流, 20:30~20:35 恢复 6×200 (NVCF 侧周期性, 非 cc2).
dsv4p 200 avg_dur=10281ms, finish_reason: tool_calls×5, stop×1.

## 健康验证 (04:37 CST)
| 项 | 结果 |
|----|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up (3h) ✓ |
| git pull (hermes main) | Already up to date, HEAD=e778c31 ✓ |
| DB 复核 | cc2 (cc4101-primary) 30min 0 rows ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
- post17~post27: 11 连庄满分 (含若干 ms_gw fallback 兜底)
- post28~post62: 0 req 无流量, 链路健康不打断连庄也不计入
- post63: 0 req 无流量, 链路健康, 不打断

## 参数快照 (实测注入, 未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_MAX_RETRIES=5, TIER_TIMEOUT_BUDGET_S=180, UPSTREAM_TIMEOUT=90, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_BUFFER_TIMEOUT_STAIRS=90×5, NVU_BUFFER_TOTAL_DEADLINE_S=450
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, FALLBACK_UPSTREAM=ms_gw:40007, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
