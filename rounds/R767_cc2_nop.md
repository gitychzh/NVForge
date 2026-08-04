# R767 cc2 NOP 巡检 — 2026-08-05 07:05 CST

## 改动: 不改码 (NOP)

## 依据 (created_at 实测校验, ~07:05 CST)
- **cc2 (cc4101-primary) glm5_2_nv: nv_requests 86×200 (SR=100%), cc_requests 87 total / 87 ok / fb=0** — 连续第 33 轮 100%
- glm5_2_nv tier: 85 pexec_success, **0 错误** — 第 21 连续最干净轮 (比 R766 更干净, R766 有 1×pexec_429)
- **5 key 全 0 错误** — per-tier 实测 glm5_2_nv 只有 pexec_success, 无任何错误类型
- 注入数据噪声 (17 RemoteDisc + 2 529_nv_overloaded + 1 empty_200) 全部来自 dsv4f0731_nv tier (hermes caller), 零穿透 cc2
  - dsv4f0731_nv SR=92.1% (24/26+20 noise) 是 hermes caller 自身链路问题, 非 cc2
- 本轮再次实证: cc2 决策必须以 created_at 实测为准, 注入数据仅作背景参考

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5, pexec_models 含 glm5_2_nv), cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, logs_db Up 5d — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 33 轮 (R735~R767) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 glm5_2_nv tier **零错误** — k3 间歇 pexec_429 在本轮消失 (R761-R766 持续 6 轮后本轮归零)
- 流量 87 req/30min (上轮 R766 81→本轮 87, 稳定)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R763 | 100% (100/100) | 29th consecutive, 17th cleanest (105 pexec + 1×429) |
| R764 | 100% (100/100) | 30th consecutive, 18th cleanest (105 pexec + 1×429) |
| R765 | 100% (91/91) | 31st consecutive, 19th cleanest (97 pexec + 1×429, 5key 0 错除 k3 429) |
| R766 | 100% (81/81) | 32nd consecutive, 20th cleanest (81 pexec + 1×429) |
| R767 | 100% (86/87) | **33rd consecutive, 21st cleanest (85 pexec, 0 错误, k3 429 本轮归零)** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- k3 间歇 pexec_429 在 R767 归零 — 若后续再出现且累积或穿透 cc2 再查 KeyManager 退避状态
- 注入数据噪声持续出现但 created_at 实测全 0 — 沿 ts 列时区 bug 解释 (R730 起实证)
- 流量稳定时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)
