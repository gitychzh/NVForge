# R766 — cc2 NOP 巡检 (2026-08-05 ~07:00 CST)

> 第 32 连续 100% 轮 (R735-R766) | 第 20 连续最干净轮

## 本轮改动: 无改码 (NOP)

## 依据 (created_at 实测校验, ~07:00 CST)

### cc2 链路 SR (created_at 列, caller=cc4101-primary)
- nv_requests: **81×200 (SR=100%)**, 0 errors — 连续第 32 轮 100%
- cc_requests: **81 total / 81 ok / fb=0 (SR=100%)**

### per-key tier 分布 (nv_tier_attempts, tier=glm5_2_nv)
| key | pexec_success | 其他错误 |
|---|---|---|
| k0 | 18 | 0 |
| k1 | 15 | 0 |
| k2 | 16 | 0 |
| k3 | 17 | 1×pexec_429 (buffer 吸收, 零穿透 cc2) |
| k4 | 15 | 0 |

- total: 81 pexec_success + 1 pexec_429 — 第 20 连续最干净轮

### ts 列注入噪声 (R730 起实证为时区 bug artifacts)
- 注入: 12×NVCFPexecRemoteDisconnected + 3×529_nv_overloaded + 1×empty_200 + 1×pexec_429
- created_at 实测: **仅 1×pexec_429 (k3)** — RemoteDisc/529/empty 全是 ts 时区 bug artifacts, 零穿透 cc2

### 流量
- 81 req/30min (R765: 91, 略低但稳定)

## 健康验证 (NOP 无需 restart)
- nv_gw: ok (nv_num_keys=5, pexec_models 含 glm5_2_nv), Up 4h
- cc4101: ok (primary=glm5_2_nv), Up 5h
- dsv4p_nv40066: ok, Up 10h
- logs_db: Up 5 days — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 32 轮 (R735~R766) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- R761~R766 每轮 1×pexec_429 (k3, buffer 吸收) — ~1%, 持续模式, 不影响 cc2 可见 SR
- 第 20 连续最干净轮 (5key 0 错误除 k3 1×429)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R763 | 100% (100/100) | 29th, 17th cleanest |
| R764 | 100% (100/100) | 30th, 18th cleanest |
| R765 | 100% (91/91) | 31st, 19th cleanest |
| R766 | 100% (81/81) | **32nd, 20th cleanest** |

## 下一步
- 持续监控 cc2 SR + fb 触发率
- k3 间歇 pexec_429 已持续 6 轮 (R761-R766), ~1%, 若累积或穿透 cc2 再查 KeyManager 退避
- 流量稳定时不动码, 仅 NOP 记数据

## 参数快照 (实测 env, 沿 R765, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode MODE_CHAIN=pexec_us_rr, KEY_MODE_BIND=空,
  KEY_FID_BIND=全 5 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, RR_US_PROXIES=7901,7894,7897,7896,7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130,
  PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
