# R754 — NOP 巡检 (2026-08-05 06:18 CST)

> 第 20 连续 100% 轮 (R735~R754) | 第 8 连续最干净轮 (全 pexec_success, 零 cc2 错误穿透)

## 数据 (created_at 实测, 30min 窗)
- **cc2 (cc4101-primary) nv_requests: 87×200 = SR 100%**
- **cc_requests: 87 total / 87 ok / 0 fb = SR 100% / fb 0%**
- 注入的 `f|106` fallback 指标 = ts 列时区 bug 口径 (R730/R742-R753 实证), created_at 实测 0 fb
- per-key pexec_success 实测: k0=19, k1=17, k2=17, k3=18, k4=16 = **总 87**, 与 cc2 链路 87×200 完全吻合 (零差额)
- 注入噪声 (NVCFPexecRemoteDisconnected=15 / 529_nv_overloaded=5 / empty_200=4) 全来自 buffer 兜住的 NVCF 容量波动, 不穿透 cc2

## 判稳
- SR 100% ≥ 99% 且无新错误 → NOP 巡检轮
- 链路全面达标 (目标 SR 99%+ / fb <10%)
- 注入噪声持续被 buffer 兜住, 不影响 cc2 链路

## 健康
- nv_gw: ok (5 keys, glm5_2_nv default) — Up 3h
- cc4101: ok (primary glm5_2_nv) — Up 4h
- dsv4p_nv40066 / nv_gw_stable / logs_db — 全 Up
- env 沿 R753, 无漂移

## 改动: 不改码 (NOP)

### SR 趋势
| 轮 | 30min SR | 备注 |
|---|---|---|
| R735 | 100% (22min) | 余波平息起点 |
| R748 | 100% (75/75) | 14th, 最干净 |
| R752 | 100% (84/84) | 18th |
| R753 | 100% (84/84) | 19th, 7th 最干净 |
| R754 | 100% (87/87) | 20th, 8th 最干净 |

## 下一步
- 持续监控 cc2 SR + fb 触发率
- 注入噪声持续观察, 若泄漏到 cc2 (buffer 失效) 再查
- 流量低不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)
