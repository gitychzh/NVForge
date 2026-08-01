# R-nvonly-post117 — hm2 cc2 NOP 巡检轮 (2026-08-02 07:15 CST)

## 轮前链路分析 (注入数据, 07:13:32 CST)
- 上轮: R-nvonly-post116
- 容器: nv_gw / cc4101 / nv_gw_stable Up 5h, ms_gw / logs_db Up 2d

## 判稳结论
**NOP 巡检轮. 0 改动, 0 重启.**
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量), 无数据可判 cc2 SR, 链路健康无故障.
- dsv4p_nv SR=14.3% (1/7): hermes+openclaw caller, 非 cc2 链路 (cc2 走 glm5_2_nv).
  - top error: all_tiers_exhausted × 6 (5key 全挂, avg_dur 1225s), NVCF 侧 dsv4p 限流, 周期性 5min 一发 429.
  - fallback 发生率 f=7 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).
- 30min buffer/wait/keymanager 日志: 无 (cc2 0 req).
- glm5_2_nv 连续 post100-post117 (18 轮) 无 dsv4p 故障扩散.

## 配置快照 (注入, 未变)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s, TIER_TIMEOUT_BUDGET=180s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM=ms_gw:40007
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复

## 健康验证 (07:15 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 6 (全 hermes+dsv4p, 非 cc2) ✓ |
| 30min tier error | 0 rows (无 cc2 流量) ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0, FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
- 0 改动, 0 重启. NOP 巡检轮.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes/openclaw caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路连续 18 轮稳定, 无需调整.
