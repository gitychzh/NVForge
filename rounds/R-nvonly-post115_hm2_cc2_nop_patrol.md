# R-nvonly-post115 — NOP 巡检轮 (2026-08-02 07:10 CST)

## 轮前数据 (注入, 07:08 CST 拉取窗口)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量产生, 无数据可判 cc2 SR)
- 其他 caller (hermes/openclaw, 非 cc2 链路):
  - hermes|dsv4p_nv: 3×200 + 5×429 (all_tiers_exhausted)
  - openclaw|dsv4p_nv: 1×200
  - dsv4p_nv SR=44.4% (4/9), 周期性 5min 一发 429
- 30min fallback: f=9 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作)
- 30min tier error: 0 cc2 流量
- 30min buffer/wait 日志: 无 (cc2 0 req)

## 判稳 + 行动
SR 判定: cc2 0 req 无数据, 链路健康无故障 → **NOP 巡检轮**.
dsv4p_nv 44.4% 仍属 NVCF 侧 dsv4p 限流 + hermes caller, 与 cc2 (glm5_2_nv) 链路无关, 非本轮职责.
glm5_2_nv 链路连续 post100-post115 (16 轮) 无 dsv4p 故障扩散, 无需调整.

## 改动
0 改动, 0 重启.

## 健康验证 (07:10 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓ |

## 参数快照 (2026-08-02 07:10 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=ms_gw:40007
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据改后必验证

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes caller, 非本轮职责.
- glm5_2_nv 链路连续 16 轮稳定, 无需调整.
