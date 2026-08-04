# R776 — cc2 NOP 巡检轮 (2026-08-05 ~07:40 CST)

> 上轮 R775 (NOP, 41st consecutive 100%, cleanest=27)
> 本轮: 42nd consecutive 100% (R735~R776), cleanest 停在 27

## 链路实测 (created_at ~07:34 CST, 30min 窗口)

### cc2 (cc4101-primary) — 本链路
- glm5_2_nv: **82×200, SR=100.0%** (0 错误, 0 fallback)
- cc_requests: 82 total / 82 ok / fb=0% (目标 <10%) ✅
- 30min 流量 82 req (上轮 83, 稳定区间)

### tier 噪声 (nv_tier_attempts, glm5_2_nv key 层)
- NVCFPexecRemoteDisconnected × 17 (k0:4 + k1:4 + k2:4 + k3:3 + k4:2)
- empty_200 × 2 (k3)
- 529 × 1 (上轮 R775 残留窗口)
- 合计 20 → **全被 buffer/KeyManager 消化, cc4101-primary 零穿透**

### 注入噪声 (非本链路)
- `all_tiers_exhausted × 8` + `dsv4f0731_nv 502×8` 全在 dsv4 hermes caller
- dsv4f0731_nv SR=42.9% (6/14) — dsv4 链路问题, 与 cc2 nv_gw 链路无关

## 判稳 + 行动
- SR=100% ≥ 99% 且无新错误 → **NOP 巡检轮**, 不改码
- 连续 100% 轮次: R735~R776 = **42 轮**
- cleanest 计数: 停在 27 (R774), 本轮 tier 噪声 19 非零

## 验证
- `/health`: nv_gw ok (nv_num_keys=5), cc4101 ok (primary=glm5_2_nv), dsv4p_nv40066 ok — 全 ok
- `docker ps`: nv_gw Up 5h, cc4101 Up 6h, dsv4p_nv40066 Up 11h, logs_db Up 5d — 全 Up
- NOP 无需 restart

## SR 趋势
| 轮 | 30min SR | tier 噪声 | 备注 |
|---|---|---|---|
| R773 | 100% (104) | 24 | 39th, cleanest 停 26 |
| R774 | 100% (95) | 0 | 40th, 27th cleanest |
| R775 | 100% (83) | 20 | 41st, cleanest 停 27 |
| R776 | 100% (82) | 19 | **42nd consecutive 100%, cleanest 停 27** |

## 下一步
- 继续监控 cc2 nv_gw 链路 SR + fb (目标 SR 99%+/fb <10%)
- tier 噪声仍在 buffer 消化范围内 — 不影响 cc2 可见 SR
- dsv4f0731_nv 注入噪声不在本链路范围 — 由 dsv4f0731 自优化 agent 处理

## 参数快照 (R776, 实测一致无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv40066, STREAM_TOTAL=470, HEADER=400
