# R777 — cc2 NOP 巡检轮 (2026-08-05 ~07:40 CST)

> 上轮 R776 (NOP, 42nd consecutive 100%, cleanest=27)
> 本轮: 43rd consecutive 100% (R735~R777), cleanest 停在 27

## 链路实测 (created_at ~07:38 CST, 30min 窗口)

### cc2 (cc4101-primary) — 本链路
- glm5_2_nv: **80×200, SR=100.0%** (0 错误, 0 fallback)
- cc_requests created_at 校验: 80 total / 80 ok / fb=0 / 0 错误 (目标 <10%) ✅
- nv_requests cc4101-primary: 80×200 全绿
- 30min 流量 80 req (上轮 82→80, 稳定区间)

### tier 噪声 (nv_tier_attempts, glm5_2_nv key 层)
- NVCFPexecRemoteDisconnected × 16 (k0:3 + k1:4 + k2:4 + k3:4 + k4:1)
- empty_200 × 1 (k3)
- 合计 17 → **全被 buffer/KeyManager 消化, cc4101-primary 零穿透**
- buffer 日志: 全部 attempt=1/5 即 success (无 retry/backoff 触发), verdict=success_text/success_tool_call

### 注入噪声 (非本链路)
- `all_tiers_exhausted × 7` + `dsv4f0731_nv 502×7` 全在 dsv4 hermes caller
- dsv4f0731_nv SR=50.0% (7/14) — dsv4 链路问题, 与 cc2 nv_gw 链路无关

## 判稳 + 行动
- SR=100% ≥ 99% 且无新错误 → **NOP 巡检轮**, 不改码
- 连续 100% 轮次: R735~R777 = **43 轮**
- cleanest 计数: 停在 27 (R774), 本轮 tier 噪声 17 非零

## 验证
- `/health`: nv_gw ok (nv_num_keys=5, pexec_models 含 glm5_2_nv), cc4101 ok (primary=glm5_2_nv), dsv4p_nv40066 ok — 全 ok
- `docker ps`: nv_gw Up 5h, cc4101 Up 6h, dsv4p_nv40066 Up 11h, nv_gw_stable Up 3d, logs_db Up 5d — 全 Up
- NOP 无需 restart

## SR 趋势
| 轮 | 30min SR | tier 噪声 | 备注 |
|---|---|---|---|
| R774 | 100% (95) | 0 | 40th, 27th cleanest |
| R775 | 100% (83) | 20 | 41st, cleanest 停 27 |
| R776 | 100% (82) | 19 | 42nd consecutive 100% |
| R777 | 100% (80) | 17 | **43rd consecutive 100%, cleanest 停 27** |

## 下一步
- 继续监控 cc2 nv_gw 链路 SR + fb (目标 SR 99%+/fb <10%)
- tier 噪声仍在 buffer 消化范围内 (本轮 17, 全 attempt=1 即 success)
- dsv4f0731_nv 注入噪声不在本链路范围 — 由 dsv4f0731 自优化 agent 处理

## 参数快照 (R777, 实测一致无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv40066, STREAM_TOTAL=470, HEADER=400
