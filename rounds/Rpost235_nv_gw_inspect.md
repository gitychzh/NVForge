# R-nvonly-post235 — hm2_cc2 NOP 巡检轮 (2026-08-02 12:55 CST)

## 本轮改动
0 改动, 0 重启. NOP 巡检轮.

## 依据
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量, 无数据可判 SR).
- 30min 错误分类: all_tiers_exhausted ×3 — 全为 hermes→dsv4p_nv 配额限流, 非 cc2 链路 (cc2 走 glm5_2_nv).
- 30min tier error: 0 rows.
- 30min buffer/wait 日志: 空 (cc2 无 buffer 事件).
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv.
- 全容器 Up 11h+, 0 restart, 0 cc2 链路故障.

## 验证
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 rows ✓ |
| 30min 错误分类 | all_tiers_exhausted ×3 (hermes→dsv4p_nv 限流, 非 cc2) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 与 cc2 无关的旁路数据
hermes→dsv4p_nv 30min: 7×200/4×429, SR≈70% (11req), all_tiers_exhausted ×3 (NVCF 配额限流, key2 单 key 扛 7×200).
glm5_2_nv 连续 post100-post235 (132 轮) 无 dsv4p 故障扩散.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
