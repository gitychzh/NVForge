# R770 cc2 NOP — 2026-08-05 ~08:30 CST

## 本轮改动: 无 (NOP 巡检)

## 数据 (created_at 实测, ~08:25 CST)
- **cc2 (cc4101-primary) nv_requests: 93×200, SR=100%** — cc4101-primary caller 零非 200
- **cc_requests: 93 total / 93 ok / fb=0, SR=100%**
- **glm5_2_nv tier: 93 pexec_success, 0 错误** — 第 24 连续最干净轮
  - per-key: k0:20, k1:17, k2:17, k3:19, k4:20 (全 pexec_success, 全 0 错误)
- k3 间歇 pexec_429 连续 4 轮 (R767-R770) 保持归零 — R761-R766 持续 6 轮的 ~1% 间歇已彻底消失
- **本轮 tier 层连 RemoteDisc/529/empty_200 也全部归零** — R770 是 R735 以来最纯净的一轮
- 轮前链路分析注入噪声 (all_tiers_exhausted×6, all_tiers_exhausted×1无名) 全为 dsv4f0731_nv/dsv4f_nv hermes caller tier — created_at 实测 cc4101-primary 零非 200, **零穿透 cc2**

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5), cc4101 ok — 全 ok
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, logs_db Up 5d — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 36 轮 (R735~R770) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 glm5_2_nv tier **零错误, 零 RemoteDisc, 零 529, 零 empty_200** — R735 以来最纯净的一轮
- 流量 93 req/30min (上轮 R769 89→本轮 93, 略升, 稳定区间)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | tier 错误 | 备注 |
|---|---|---|---|
| R766 | 100% (81/81) | 1×429 (k3) | 32nd consecutive, 20th cleanest |
| R767 | 100% (86/87) | 0 | 33rd consecutive, 21st cleanest (k3 429 归零) |
| R768 | 100% (89/89) | 0 | 34th consecutive, 22nd cleanest (k3 429 归零连续 2 轮) |
| R769 | 100% (89/89) | 0 | 35th consecutive, 23rd cleanest (k3 429 归零连续 3 轮) |
| R770 | 100% (93/93) | 0 | **36th consecutive, 24th cleanest (k3 429 归零连续 4 轮, tier 全噪声归零)** |

## 下一步
- 持续监控 cc2 SR + fb 触发率
- k3 间歇 pexec_429 已归零连续 4 轮 (R767-R770) — 若后续再出现且累积或穿透 cc2 再查 KeyManager 退避状态
- 注入数据噪声持续出现但 created_at 实测全 0 — 沿 ts 列时区 bug 解释 (R730 起实证)
- 流量稳定时不动码, 仅 NOP 记数据
