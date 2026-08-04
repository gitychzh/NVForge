# R763 cc2 NOP 巡检 — 2026-08-05 06:42 CST

## 改动: 不改码 (NOP)

## 依据 (created_at 实测校验, ~06:42 CST)
- **cc2 (cc4101-primary) glm5_2_nv: nv_requests 100×200 (SR=100%), cc_requests 100 total / 100 ok / fb=0** — 连续第 29 轮 100%
- glm5_2_nv tier: 105 pexec_success + 1 pexec_429 (buffer 吸收, 零穿透 cc2) — 连续第 17 轮最干净
- **5 key 全 0 错误** (per-key k0=21/k1=24/k2=19/k3=23/k4=19 全 pexec_success)
- 注入数据噪声 (all_tiers_exhausted×5) 全来自非 cc2 tier (dsv4f0731_nv / dsv4f_nv), 零穿透 cc2
  - dsv4f0731_nv SR=90.9% / dsv4f_nv SR=50% 是 hermes caller 自身链路问题, 非 cc2
- 本轮再次实证: cc2 决策必须以 created_at 实测为准, 注入数据仅作背景参考

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5, pexec_models 含 glm5_2_nv), cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 29 轮 (R735~R763) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 glm5_2_nv tier 1×pexec_429 (buffer 吸收) — 数量极小 (<1%), 不影响 cc2 可见 SR
- 流量 100 req/30min (上轮 R762 实测 99→本轮 100, 稳定)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R760 | 100% (85 nv / 87 cc) | 26th consecutive, fb=0, 14th cleanest (tier 零错误) |
| R761 | 100% (90 nv / 90 cc) | 27th consecutive, fb=0, 15th cleanest (95 pexec + 1×429) |
| R762 | 100% (99 nv / 99 cc) | 28th consecutive, fb=0, 16th cleanest (104 pexec + 1×429, 5key 全 0 错) |
| R763 | 100% (100 nv / 100 cc) | **29th consecutive, fb=0, 17th cleanest (105 pexec + 1×429, 5key 全 0 错)** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- glm5_2_nv tier 间歇 pexec_429 (R761/R762/R763 各 1 次) — 数量极小 (<1%), 若累积或穿透 cc2 再查 KeyManager 退避状态
- 注入数据噪声持续出现但 created_at 实测全 0 — 沿 ts 列时区 bug 解释
- 流量稳定时不动码, 仅 NOP 记数据
