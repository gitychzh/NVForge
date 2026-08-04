# R768 cc2 NOP — 34th consecutive 100% round (R735-R768)

> 时间: 2026-08-05 ~07:30 CST
> 上轮: R767 (33rd consecutive 100%, 21st cleanest, k3 429 归零)
> 容器: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, logs_db Up 5d

## 本轮改动: NOP (不改码)

## 依据 (created_at 实测校验, ~07:30 CST)

### cc2 链路 (cc4101-primary caller)
- **nv_requests: 89×200, 0 错误, SR=100%** — 连续第 34 轮 100%
- **cc_requests: 89 total / 89 ok / fb=0 / fb_pct=0.0%** — 无 fallback 触发
- **错误分类 (cc4101-primary caller, status!=200): 0 rows** — cc2 链路零错误

### glm5_2_nv tier (per-key, created_at 实测)
| key | ok (pexec_success) | errors |
|---|---|---|
| k0 | 20 | 0 |
| k1 | 16 | 0 |
| k2 | 18 | 0 |
| k3 | 17 | 0 |
| k4 | 19 | 0 |
| **total** | **90** | **0** |

- **5 key 全 0 错误** — k3 间歇 pexec_429 连续 2 轮 (R767-R768) 保持归零状态
- 与 R767 (0 错误) 持平 — 第 22 连续最干净轮

### 注入数据噪声 (-ts 时区 artifact, created_at 实测全 0 穿透)
- `all_tiers_exhausted×5` (avg_dur 88565ms) — 注入分类标记为 "30min", 实测 created_at 范围内 cc4101-primary caller 0 错误
- tier failures 17×RemoteDisc + 3×529 + 1×empty_200 — 全 tier 合计 (含 dsv4f0731_nv/dsv4f_nv 等 hermes caller tier), 非 glm5_2_nv tier
- glm5_2_nv tier `created_at` 实测: 仅 90×pexec_success, 0 错误
- → **零穿透 cc2**: cc2 89×200 / 0 fb / 0 error

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5), cc4101 ok — 全 ok
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, logs_db Up 5d — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 34 轮 (R735~R768) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 glm5_2_nv tier **零错误** — k3 间歇 429 自 R767 归零后连续 2 轮保持
- 流量 89 req/30min (上轮 R767 86→本轮 89, 稳定)
- NOP 巡检轮 — 链路已稳, 无可改项

## SR 趋势
| 轮 | 30min 窗 SR | tier 错误 | 备注 |
|---|---|---|---|
| R764 | 100% (100/100) | 1×429 (k3) | 30th consecutive, 18th cleanest |
| R765 | 100% (91/91) | 1×429 (k3) | 31st consecutive, 19th cleanest |
| R766 | 100% (81/81) | 1×429 (k3) | 32nd consecutive, 20th cleanest |
| R767 | 100% (86/87) | 0 | 33rd consecutive, 21st cleanest (k3 429 归零) |
| R768 | 100% (89/89) | 0 | **34th consecutive, 22nd cleanest (k3 429 归零连续 2 轮)** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- k3 间歇 pexec_429 已归零连续 2 轮 (R767-R768) — 若后续再出现且累积或穿透 cc2 再查 KeyManager 退避状态
- 注入数据噪声持续出现但 created_at 实测全 0 — 沿 ts 列时区 bug 解释 (R730 起实证)
- 流量稳定时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)

## 参数快照 (实测 env, 沿 R767, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode MODE_CHAIN=pexec_us_rr, KEY_MODE_BIND=空,
  KEY_FID_BIND=全 5 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, RR_US_PROXIES=7901,7894,7897,7896,7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130,
  PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
