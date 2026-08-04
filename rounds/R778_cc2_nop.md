# R778 — cc2 NOP 巡检轮 (2026-08-05 ~07:55 CST)

> 上轮 R777 (NOP, 43rd consecutive 100%, cleanest=27)
> 本轮: 44th consecutive 100% (R735~R778), cleanest 停在 27

## 链路实测 (轮前链路分析 ~07:51 CST, 30min 窗口)

### cc2 (cc4101-primary) — 本链路
- glm5_2_nv: **57×200, SR=100.0%** (0 错误, 0 fallback)
- cc4101-primary 30min: 57 req 全 200, 0 fb (fb=0%, 目标 <10%) ✅
- 30min 流量 57 req (上轮 80→57, 流量偏低但稳定)
- avg_dur 28577ms, 全 200

### tier 噪声 (nv_tier_attempts, glm5_2_nv key 层)
- NVCFPexecRemoteDisconnected × 15 (k0:2 + k1:3 + k2:3 + k3:4 + k4:3)
- empty_200 × 1 (k1)
- 合计 16 → **全被 buffer/KeyManager 消化, cc4101-primary 零穿透**
- per-key pexec_success: k0:12 + k1:9 + k2:11 + k3:13 + k4:12 = 57 次 success (与 57 req 一致, 全 attempt=1)
- buffer 日志: 无 buffer/wait 日志 (全 attempt=1 即 success, 未触发 retry)

### 注入噪声 (非本链路)
- `all_tiers_exhausted × 8` + `dsv4f0731_nv 502×8` 全在 dsv4 hermes caller (dsv4f0731_nv model)
- dsv4f0731_nv SR=38.5% (5/13) — dsv4 链路问题, 与 cc2 nv_gw 链路无关
- dsv4p_nv (备用链路): SR=100% (4/4), 健康

## 判稳 + 行动
- SR=100% ≥ 99% 且无新错误 → **NOP 巡检轮**, 不改码
- 连续 100% 轮次: R735~R778 = **44 轮**
- cleanest 计数: 停在 27 (R774), 本轮 tier 噪声 16 非零

## 验证
- 轮前链路分析: nv_gw 容器 10 hours ago, cc4101 6 hours ago — 运行中
- cc4101-primary caller 全 200, fb=0/57 — 链路健康
- NOP 无需 restart

## SR 趋势
| 轮 | 30min SR | tier 噪声 | 备注 |
|---|---|---|---|
| R774 | 100% (95) | 0 | 40th, 27th cleanest |
| R775 | 100% (83) | 20 | 41st, cleanest 停 27 |
| R776 | 100% (82) | 19 | 42nd consecutive 100% |
| R777 | 100% (80) | 17 | 43rd consecutive 100% |
| R778 | 100% (57) | 16 | **44th consecutive 100%, cleanest 停 27** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- tier 噪声仍在 buffer 消化范围内 (16 次 RemoteDisc, 全 attempt=1 success) — 不影响 cc2 可见 SR
- 注入噪声 (dsv4f0731_nv 502×8 + all_tiers_exhausted×8) 全在 dsv4 hermes caller — 非本链路问题
