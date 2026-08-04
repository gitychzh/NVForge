# R769 cc2 NOP — 2026-08-05 ~08:00 CST

## 本轮改动: 无 (NOP 巡检)

## 数据 (created_at 实测, ~07:55 CST)
- **cc2 (cc4101-primary) nv_requests: 89×200, SR=100%** — cc4101-primary caller 零非 200
- **cc_requests: 89 total / 89 ok / fb=0, SR=100%**
- **glm5_2_nv tier: 89 pexec_success, 0 错误** — 第 23 连续最干净轮
  - per-key: k0:19, k1:16, k2:18, k3:17, k4:19 (全 pexec_success, 全 0 错误)
- k3 间歇 pexec_429 连续 3 轮 (R767-R769) 保持归零 — R761-R766 持续 6 轮的 ~1% 间歇已彻底消失
- 轮前链路分析注入噪声 (all_tiers_exhausted×5 avg 88565ms, 529×3, RemoteDisc×18, empty_200×2) 全为 dsv4f0731_nv/dsv4f_nv hermes caller tier — created_at 实测 cc4101-primary 零非 200, **零穿透 cc2**

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5), cc4101 ok — 全 ok
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, logs_db Up 5d — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 35 轮 (R735~R769) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 glm5_2_nv tier **零错误** — k3 间歇 429 自 R767 归零后连续 3 轮保持
- 流量 89 req/30min (上轮 R768 89→本轮 89, 稳定)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | tier 错误 | 备注 |
|---|---|---|---|
| R765 | 100% (91/91) | 1×429 (k3) | 31st consecutive, 19th cleanest |
| R766 | 100% (81/81) | 1×429 (k3) | 32nd consecutive, 20th cleanest |
| R767 | 100% (86/87) | 0 | 33rd consecutive, 21st cleanest (k3 429 归零) |
| R768 | 100% (89/89) | 0 | 34th consecutive, 22nd cleanest (k3 429 归零连续 2 轮) |
| R769 | 100% (89/89) | 0 | **35th consecutive, 23rd cleanest (k3 429 归零连续 3 轮)** |

## 下一步
- 持续监控 cc2 SR + fb 触发率
- k3 间歇 pexec_429 已归零连续 3 轮 (R767-R769) — 若后续再出现且累积或穿透 cc2 再查 KeyManager 退避状态
- 注入数据噪声持续出现但 created_at 实测全 0 — 沿 ts 列时区 bug 解释 (R730 起实证)
- 流量稳定时不动码, 仅 NOP 记数据
