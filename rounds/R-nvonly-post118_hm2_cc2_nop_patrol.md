# R-nvonly-post118 — hm2_cc2 NOP 巡检轮

- 日期: 2026-08-02 07:16 CST
- 主仓 HEAD: cbc4e7f (post117) → 本轮 post118
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复

## 本轮判稳: NOP 巡检轮 (0 改动, 0 重启)

### 数据 (30min 窗口, 注入数据)
| 指标 | 值 |
|------|-----|
| cc2 (cc4101-primary) 30min | 0 req (session 轮前无流量) |
| dsv4p_nv SR (hermes+openclaw) | 44.4% (4/9) — NVCF 侧限流, 非 cc2 |
| glm5_2_nv | 无故障扩散 (cc2 走 glm5_2_nv, 连续 18+ 轮稳定) |
| top error | all_tiers_exhausted ×5 (dsv4p 5key 全挂, hermes caller) |
| 30min fallback | f=9 (dsv4p 全挂 fallback ms, ms_gw 正常工作) |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) |

### 健康验证 (07:16 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| deadline (6h) | 0 ✓ |

## 分析
- cc2 无流量 = 无数据 = 无法优化 (正反馈循环: 改前必有数据).
- dsv4p_nv 限流 (周期性 429/all_tiers_exhausted) 属 NVCF 侧 + hermes/openclaw caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路连续 post100-post118 (19 轮) 无 dsv4p 故障扩散, 链路稳定无需调整.
- 与 post117 对比: dsv4p_nv 窗口略升 (44.4% vs 14.3%), 仍局限 hermes+dsv4p, 未扩散到 glm5_2_nv.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- glm5_2_nv 链路连续 19 轮稳定, 无需调整.
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据改后必验证.

## 参数快照 (2026-08-02 07:16 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
