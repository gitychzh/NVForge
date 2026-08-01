# R-nvonly-post96 (hm2 cc2) — NOP 巡检轮

**日期**: 2026-08-02 06:14 CST
**轮次**: post96 (NOP, 无改动无重启)
**前轮**: post95 (020bfd2)

## 数据 (30min 窗口, 轮前链路分析注入 + 本轮验证)

### cc2 (cc4101-primary) — 0 req
| 验证项 | 结果 |
|--------|------|
| nv_requests 30min cc4101-primary | 0 rows (无流量) |
| cc_requests 6h stream_total_deadline | 0 rows |
| nv_gw /health | status=ok, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |

session 轮前无 cc2 流量产生, 无数据可判 SR. 链路健康无故障: 容器全 Up, /health ok,
0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |

dsv4p_nv SR=37.5% (3/8): 5×429 (all_tiers_exhausted, 5key 全挂), 周期性 5min 一发 429.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). NVCF 侧 dsv4p 限流模式.
30min fallback 发生率: f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 本轮改动
- 无 (NOP)

## 验证
- /health ok, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps 全 Up, 无 restart
- 0 cc2 tier error, 0 stream_total_deadline

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (37.5%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路,
  不在本轮优化范围. 关注是否扩散到 glm5_2_nv (目前未扩散).

## 参数快照 (未变化, 沿用 post95)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, UPSTREAM_TIMEOUT=90
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM=ms_gw:40007
- 5key(k0-k4)×5美国IP(hysteria2代理), KeyManager: 429→指数退避, RemoteDisconnected→5-10s短惩罚
- buffer: 5 attempts × 90s = 450s, deadline链: 90s×5=450s buffer < 470s cc4101 < 500s SDK idle
