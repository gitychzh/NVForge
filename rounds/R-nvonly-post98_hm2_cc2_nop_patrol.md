# R-nvonly-post98 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 06:16 CST
**主仓 HEAD**: ff5aaf8 (post97)
**本轮改动**: 0 (NOP 巡检轮, 不改码不重启)

## 判稳依据 (30min 窗口)

### cc2 (cc4101-primary) — 0 req
本轮 session 轮前无流量产生, 无数据可判 cc2 SR. 链路健康无故障:
- 容器全 Up: nv_gw/cc4101/nv_gw_stable 4h, ms_gw/logs_db 2d
- /health ok: nv_default_model=glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv]
- 0 cc2 tier error, 0 stream_total_deadline (6h), 0 buffer/wait 日志

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

dsv4p_nv SR=0.0% (0/6): 6×429 + all_tiers_exhausted (5key 全挂), 周期性 5min 一发.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). 30min fallback f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

### 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 健康验证 (06:15 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | status=ok, glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 tier error (30min) | 0 ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0, FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv SR=0.0% (周期性 429+5key全挂) 是 NVCF 侧 dsv4p 限流, 非 cc2 链路, 不在本轮优化范围.
- 关注 dsv4p_nv 周期性 429 是否扩散到 glm5_2_nv (目前未扩散).

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ |
| post18-post98 | 0 req | 0 | — (无流量, 链路健康) |
