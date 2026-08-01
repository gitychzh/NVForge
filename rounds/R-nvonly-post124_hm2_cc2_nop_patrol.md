# R-nvonly-post124 — HM2 cc2 NOP 巡检轮

## 元数据
- 日期: 2026-08-02 (CST, 轮前链路分析注入时间 07:34:32)
- 主机: HM2 (100.109.57.26, opc2_uname)
- 链路: cc2 → cc4101(4101) → nv_gw(40006, glm5_2_nv) → NVCF, fallback ms_gw(40007) 已恢复
- 上轮: post123 (NOP, 0req, 链路健康)
- 本轮动作: NOP 巡检, 0 改动 0 重启

## 本轮判稳依据 (轮前链路分析注入 + 07:35 复核)
| 项 | 结果 |
|----|------|
| cc4101-primary (cc2) 30min SR | 0 rows (无流量, 链路健康无故障) |
| 30min tier error | 0 rows |
| stream_total_deadline (6h) | 0 |
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv |
| 容器 | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d |
| env | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), buffer 5×90s=450s, cc4101 deadline 470s |
| buffer/wait 日志 | 无 (cc2 0 req) |

## 其他 caller (非 cc2 链路, 仅记录)
- hermes/openclaw 打 dsv4p_nv SR=44.4% (4/9: 4×200 + 5×429 all_tiers_exhausted)
- 周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式, 非 cc2 链路 (cc2 走 glm5_2_nv)
- 与 post123 持平 (44.4% vs 44.4%), 未扩散到 glm5_2_nv
- 30min fallback 发生率 f=9 (dsv4p 全挂 fallback ms, fallback 已恢复正常工作)

## 行动
- 0 改动, 0 重启
- glm5_2_nv 链路连续 post100-post124 (25 轮) 稳定
- dsv4p_nv 限流属 NVCF 侧 + hermes/openclaw caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller)

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- 关注 dsv4p_nv 是否扩散到 glm5_2_nv (目前未扩散).
