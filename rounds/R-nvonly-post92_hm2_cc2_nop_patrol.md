# R-nvonly-post92 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 06:00 CST
**上轮**: R-nvonly-post91 (NOP 巡检)
**容器**: nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d

## 判定: NOP 巡检轮 (无改动, 无重启)

## 依据
- cc2 (cc4101-primary) 30min 窗口 **0 req** (session 轮前无流量产生), 无数据可判 cc2 SR.
- 链路健康无故障: 容器全 Up, /health ok (glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv]),
  0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
- hermes 打 dsv4p_nv SR=37.5% (3/8, 5×429+all_tiers_exhausted, 周期性 5min 一发 429)
  是 **NVCF 侧 dsv4p 限流**, 非 cc2 链路 (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- 30min fallback 发生率: f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

## dsv4p_nv 按分钟趋势 (周期性 429)
| 分钟 | status | count |
|------|--------|-------|
| 21:30 | 429 | 1 |
| 21:35 | 429 | 1 |
| 21:40 | 200 | 3 |
| 21:45 | 429 | 1 |
| 21:50 | 429 | 1 |
| 21:55 | 429 | 1 |

周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题.

## 健康验证 (06:00 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 tier error (30min) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |
| git HEAD (hermes_improve_self) | fcdb17e (post91) → 本轮 post92 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故���) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 改动
- 0 改动, 0 重启.

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (37.5%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路 (cc2 走 glm5_2_nv), 不在本轮优化范围.
