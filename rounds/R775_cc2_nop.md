# R775 cc2 NOP 巡检 (2026-08-05 ~07:40 CST)

> 上轮: R774 (NOP, 40th consecutive 100%, 27th cleanest)

## 本轮改动: 不改码 (NOP)

## 依据 (created_at 实测校验, ~07:38 CST)

### 注入数据 (07:30:32 快照, caller × model × status)
- cc4101-primary|glm5_2_nv|200|84 — **cc2 链路 84×200, SR 100%**
- 注入噪声: hermes|dsv4f0731_nv|502|7 + all_tiers_exhausted×7 — 全在 dsv4f0731/dsv4f hermes caller, 零穿透 cc4101-primary

### 实测 (本轮 created_at 窗口, 校验注入数据)
- **cc2 (cc4101-primary) glm5_2_nv: nv_requests 83×200 (SR=100%), 0 错误** ⭐
- **cc_requests: 83 total / 83 ok / 0 fallback (fb=0%, 目标<10%)** — created_at 校验
- **tier 噪声 (nv_tier_attempts 30min, glm5_2_nv): RemoteDisc×17 + empty_200×2 + 529×1 = 20** — 全部被 buffer/KeyManager 消化, cc4101-primary 零穿透
- 30min nv_gw SR 100% (cc4101-primary 角度), tier 同期 pexec_success 主导

### 健康检查
- `/health`: nv_gw ok (nv_num_keys=5, 5 个 NV model), cc4101 ok (primary=glm5_2_nv)
- `docker ps`: nv_gw Up 5h, cc4101 Up 6h, dsv4p_nv40066 Up 11h, logs_db Up 5d — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 41 轮 (R735~R775) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- **本轮 tier 噪声 20** (RemoteDisc×17 + empty_200×2 + 529×1) — 比 R774 (0) 反弹但全被 buffer 吸收, cleanest 停在 27
- 流量 83 req/30min (上轮 95→83, 稳定区间)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | tier 噪声 | 备注 |
|---|---|---|---|
| R772 | 100% (96/96) | 0 | 38th, 26th cleanest |
| R773 | 100% (104/104) | 24 | 39th, cleanest 停在 26 |
| R774 | 100% (95/95) | 0 | 40th, 27th cleanest |
| R775 | 100% (83/83) | 20 | **41st consecutive 100%, cleanest 停在 27** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- tier 噪声仍在 buffer 消化范围内 (本轮 20, 上轮 0) — 不影响 cc2 可见 SR
- 注入噪声 (dsv4f0731_nv 502×7 + all_tiers_exhausted×7) 全在 dsv4 hermes caller, 非本链路问题
