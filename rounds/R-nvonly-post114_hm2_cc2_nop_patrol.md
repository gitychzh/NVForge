# R-nvonly-post114 (hm2_cc2) — NOP 巡检轮

## 本轮改动
- 0 改动, 0 重启. NOP 巡检轮.

## 依据 (轮前链路分析 2026-08-02 07:05 CST)
- cc2 (cc4101-primary) 30min: 0 req. session 轮前无流量, 无数据可判 cc2 SR.
- dsv4p_nv 故障仍局限 hermes caller: SR=44.4% (4/9, 3×200+1×openclaw200 + 5×429/all_tiers_exhausted),
  周期性 5min 一发 429 (22:40 200×3, 22:45-23:05 429×5), NVCF 侧 dsv4p 限流, 非 cc2 链路 (cc2 走 glm5_2_nv).
- 30min fallback 发生率: f=9 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).
- glm5_2_nv 链路连续 post100-post114 (15 轮) 无故障扩散.

## 健康验证 (07:05 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量) ✓ |
| env 配置 | NVU_DISABLE_MS_FALLBACK=0, buffer 5×90s=450s, cc4101 deadline 470s ✓ |

## 参数快照 (2026-08-02 07:05 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=ms_gw:40007
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据改后必验证

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责.
- glm5_2_nv 链路连续 15 轮稳定, 无需调整.
