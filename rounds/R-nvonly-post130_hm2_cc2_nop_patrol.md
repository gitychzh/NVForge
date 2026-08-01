# R-nvonly-post130 — NOP 巡检轮 (2026-08-02 07:50 CST)

## 轮前数据 (注入, 07:49:32 CST)
- 上轮: R-nvonly-post129 | 容器 nv_gw/cc4101 6h ago
- cc2 (cc4101-primary) 30min: **0 req** (无流量, 链路健康无故障)
- 仅 hermes+dsv4p_nv 6×429 (all_tiers_exhausted, 周期性 5min 一发, NVCF 侧 dsv4p 限流, 非 cc2 链路)
- 30min dsv4p_nv SR=0.0% (0/6), fallback f=6 (ms_gw fallback 已恢复正常工作)
- 30min cc2 buffer/wait/keymanager 日志: 无
- 6h stream_total_deadline: 0

## 判稳
SR 无数据 (cc2 0 req), 链路健康无故障, 无新错误, 无 deadline.
**判定: NOP 巡检轮, 0 改动, 0 重启.**

## 验证 (07:50 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, STAIRS=90×5, TOTAL_DEADLINE=450, TIER_TIMEOUT_BUDGET=180, UPSTREAM_TIMEOUT=90 ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量) ✓ |
| 6h stream_total_deadline | 0 ✓ |

## 本轮改动
无 (NOP 巡检轮).

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes caller, 非本轮职责.
- glm5_2_nv 链路连续 31 轮稳定 (post100-post130), 无需调整.

## 参数快照
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据, 改后必验证
