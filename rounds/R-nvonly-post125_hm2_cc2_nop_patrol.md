# R-nvonly-post125 — NOP 巡检轮 (2026-08-02 07:36 CST)

## 基线
- 上轮: R-nvonly-post124 (65d6e44, NOP 巡检轮)
- 主仓 HEAD: 65d6e44 (本轮 NOP, 无新改动)
- 容器: nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d

## 本轮数据 (30min 窗口)
- cc2 (cc4101-primary): 0 req → 无流量, 链路健康无故障
- 0 cc2 tier error, 0 buffer/wait 日志, 0 stream_total_deadline (6h)
- 其他 caller (非 cc2 链路): hermes+dsv4p_nv 3×200 + 5×429(all_tiers_exhausted)
  - dsv4p_nv SR=37.5% (3/8): NVCF 侧 dsv4p 限流, 周期性 5min 一发 429, 非 cc2 链路
  - 与 post124 对比 (37.5% vs 44.4%): 持平, 仍局限 hermes+dsv4p, 未扩散到 glm5_2_nv
- 30min fallback f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作)

## 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | 全 Up ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| 30min tier error | 0 rows ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER 5×90s=450s, cc4101 470s ✓ |

## 改动
- 0 改动, 0 重启 (NOP 巡检轮)

## 判稳依据
- cc2 0 req 无流量无故障, 链路全 Up, env 配置正确, 0 stream_total_deadline (6h)
- dsv4p_nv 限流属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw glm5_2_nv)
- glm5_2_nv 链路连续 post100-post125 (26 轮) 稳定, 无 dsv4p 故障扩散

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes/openclaw caller, 非本轮职责.
- glm5_2_nv 链路稳定, 无需调整.
