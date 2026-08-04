# R774 cc2 NOP 巡检 (2026-08-05 ~07:30 CST)

> 上轮: R773 (NOP, 39th consecutive 100%, cleanest 停在 26)

## 本轮改动: 不改码 (NOP)

## 依据 (created_at 实测校验, ~07:28 CST)

### 实测 (本轮 created_at 窗口)
- **cc2 (cc4101-primary) glm5_2_nv: nv_requests 95×200 (SR=100%), 0 错误**
- **cc_requests: 95 total / 95 ok / 0 fallback (fb=0%, 目标<10%)** — created_at 校验
- **glm5_2_nv tier (nv_tier_attempts 30min): pexec_success ×95, 0 错误** — 本轮 tier 噪声实际归零 ⭐
- 注入数据 (07:26:32 快照): 94×200 + tier 21 RemoteDisc/1 529/2 empty_200 — 是更早窗口残留, 本轮 created_at 校验已清零

### 容错链路验证 (buffer 日志)
- req=8955b95c: attempt 1 k3 execute_failed (all_keys_exhausted) → backoff 5s → attempt 2 success_text (48s) — **buffer 多 attempt 成功消化单 key 失败, 零穿透**
- 其余请求均 attempt 1 直接成功 (9s~18s)

### 健康检查
- `/health`: nv_gw ok (nv_num_keys=5, 5 个 NV model), cc4101 ok (primary=glm5_2_nv)
- `docker ps`: nv_gw Up 5h, cc4101 Up 6h, dsv4p_nv40066 Up 11h, logs_db Up 5d — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 40 轮 (R735~R774) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- **本轮 tier 噪声 0** (实测 nv_tier_attempts 0 错误) — 回到 cleanest 状态, 27th cleanest
- 流量 95 req/30min (上轮 104→95, 稳定区间)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | tier 噪声 | 备注 |
|---|---|---|---|
| R771 | 100% (98/98) | 0 | 37th, 25th cleanest |
| R772 | 100% (96/96) | 0 | 38th, 26th cleanest |
| R773 | 100% (104/104) | 24 | 39th, cleanest 停在 26 |
| R774 | 100% (95/95) | 0 | **40th consecutive 100%, 27th cleanest** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- 本轮 tier 噪声再归零 — cleanest 计数恢复递增
- k3 间歇 execute_failed (本轮 1 次, 被 buffer attempt 2 消化) — 单 key 偶发仍在, 但不影响 cc2 可见 SR

## 参数快照 (R774, 实测)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv40066, STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF | fallback→dsv4p_nv40066(40066)
