# R773 cc2 NOP 巡检 (2026-08-05 ~07:25 CST)

> 上轮: R772 (NOP, 38th consecutive 100%, 26th cleanest)

## 本轮改动: 不改码 (NOP)

## 依据 (created_at 实测校验, ~07:23 CST)
- **cc2 (cc4101-primary) glm5_2_nv: nv_requests 104×200 (SR=100%), 0 错误**
- **cc_requests: 104 total / 104 ok / 0 fallback (fb=0%, 目标<10%)** — 创建时间实测
- 注入数据轮前窗口: cc4101-primary 101×200 (轮前快照) → 104 (created_at 校验), fb=0
- **glm5_2_nv tier (per-key, 30min nv_tier_attempts)**:
  - k0: pexec_success ×?, NVCFPexecRemoteDisconnected ×5
  - k1: pexec_success, NVCFPexecRemoteDisconnected ×4
  - k2: pexec_success, 529_nv_overloaded ×1, NVCFPexecRemoteDisconnected ×6
  - k3: pexec_success, NVCFPexecRemoteDisconnected ×2, empty_200 ×2
  - k4: pexec_success, NVCFPexecRemoteDisconnected ×4
  - 合计: 101 pexec_success (轮前快照), 21 RemoteDisc + 1 529 + 2 empty_200 = 24 上游噪声
- **上游噪声全部被 buffer/KeyManager/多key轮转消化**, 零穿透 cc2 (cc4101-primary 0 错误 0 fb)
- **本轮与 R772 对比**: 上游噪声略增 (R772 tier 0 错误 → R773 24 噪声), 但 cc2 仍 100% — 链路容错有效

### 噪声链路隔离 (hermes caller, 非 cc2)
- dsv4f0731_nv SR=63.6% (14/22), dsv4f_nv SR=50% (1/2) — hermes caller tier
- all_tiers_exhausted×8 + fallback×1, 502×8 — 全在 dsv4f 系, 零穿透 cc4101-primary

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5), cc4101 ok — 全 ok
- `docker ps`: nv_gw Up 5h, cc4101 Up 6h, dsv4p_nv40066 Up 11h, logs_db Up 5d — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 39 轮 (R735~R773) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮上游 24 噪声, cc2 仍 100% — 第 39 连续 100% 轮 (注意: 本轮 tier 有噪声, 非 cleanest 轮, cleanest 计数维持 26)
- 流量 104 req/30min (上轮 R772 96→本轮 104, 稳定区间)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | tier 噪声 | 备注 |
|---|---|---|---|
| R769 | 100% (89/89) | 0 | 35th, 23rd cleanest |
| R770 | 100% (93/93) | 0 | 36th, 24th cleanest |
| R771 | 100% (98/98) | 0 | 37th, 25th cleanest |
| R772 | 100% (96/96) | 0 | 38th, 26th cleanest |
| R773 | 100% (104/104) | 24 | **39th consecutive 100%, cleanest 停在 26** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- 本轮 tier 层 RemoteDisc×21 + 529×1 + empty_200×2 重新出现 (R772 完全归零) — 若本轮为偶发则 NOP, 若 R774 持续累积且穿透 cc2 再查 KeyManager 退避/NVCF 端
- k3 间歇 pexec_429 此轮未在 tier 报表显示 — 继续观察
