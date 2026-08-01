# R-nvonly-post126 — NOP 巡检轮 (2026-08-02 07:39 CST)

## 本轮结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 窗口 0 req (session 轮前无流量产生, 无数据可判 cc2 SR).
链路健康无故障: 容器全 Up (nv_gw/cc4101/nv_gw_stable 6h, ms_gw/logs_db 2d), env 配置正确
(NVU_DISABLE_MS_FALLBACK=0 fallback 已恢复, buffer 5×90s=450s, cc4101 deadline 470s).
0 改动, 0 重启.

## 本轮数据 (轮前链路分析注入)

### cc2 (cc4101-primary) 30min — 0 req
无流量, 无数据可判 cc2 SR. 链路健康无故障, 0 cc2 tier error, 0 buffer/wait 日志, 0 stream_total_deadline (6h).
注: 直接裸探 cc4101/nv_gw 入口返回 401 (caller token 鉴权), 本 session 工具调用本身经 cc4101→nv_gw 链路.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |

dsv4p_nv SR=37.5% (3/8): 3×200 + 5×429 (all_tiers_exhausted, 5key 全挂), 周期性 5min 一发 429.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback 发生率: f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

### dsv4p_nv 按分钟趋势 (周期性 429, UTC)
23:10 429×1 | 23:15 200×2 | 23:16 200×1 | 23:20 429×1 | 23:25 429×1 | 23:30 429×1 | 23:35 429×1
周期性 5min 一发 429, 间夹 200, NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题.
与 post125 对比: 窗口一致 (37.5%), 仍局限 hermes+dsv4p, 未扩散到 glm5_2_nv.

## 健康验证 (07:39 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), buffer 5×90s=450s, cc4101 deadline 470s ✓ |

## 改动
0 改动, 0 重启 (NOP 巡检轮).

## 依据
cc2 (cc4101-primary) 30min 0 req, 无流量无故障, SR 无数据可判, 但链路健康指标全绿
(容器全 Up, env 正确, 0 stream_total_deadline, 0 cc2 error). dsv4p_nv 限流属 NVCF 侧 +
hermes caller, 非 cc2 职责 (只改 HM2 nv_gw, 不碰 caller). 符合 NOP 巡检判稳标准.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责.
- glm5_2_nv 链路连续 27 轮稳定, 无需调整.

## 参数快照 (2026-08-02 07:39 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90,
  BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据, 改后必验证
