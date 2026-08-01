# R-nvonly-post62 — hm2_cc2 NOP 巡检轮 (2026-08-02 04:33 CST)

## 轮前数据 (注入, 30min 窗口)
- **cc2 (cc4101-primary) 30min: 0 req** — session 轮前无流量产生, 无数据可判 cc2 SR.
  链路健康无故障: 容器全 Up, /health ok (glm5_2_nv, 5 keys), 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
- **其他 caller (hermes, 非 cc2 链路)**: hermes|dsv4p_nv SR=44.4% (4/9), 5×429, 5×all_tiers_exhausted.
  按 5min 1×429 稳定限流 (NVCF 侧 dsv4p 持续限流, 非 cc2 链路 — cc2 走 glm5_2_nv).
- **配置实测 (注入)**: `NVU_DISABLE_MS_FALLBACK=0` (fallback 已恢复), `FALLBACK_UPSTREAM=ms_gw:40007`, `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=90/130`.

## 健康验证 (04:33 CST)
| 项 | 结果 |
|----|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up ✓ |
| git pull (hermes main) | Already up to date, HEAD=ea08db7 ✓ |

## 判稳
- cc2 SR: 0 req (无流量, 链路健康无故障) → —
- 新错误类型: 无 (0 cc2 tier error) → ✅
- transport 层: 0 错误 → ✅
- buffer 触发: 无 → ✅
→ **NOP 巡检轮**, 0 改动, 0 重启.

## 本轮改动
无 (NOP).

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
