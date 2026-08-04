# R751 — NOP 巡检轮 (2026-08-05, ~05:55 CST)

> cc2 (cc4101-primary) → nv_gw(40006) → glm5_2_nv (pexec+fid1, 5key×5US-IP)

## 改动: 不改码 (NOP)

## 依据 (实测 ~05:55 CST, 30min 窗, created_at 实测核验)

### cc2 链路 (created_at 实测)
- **nv_requests (cc4101-primary): 83×200, SR=100%** — 零非-200
- **cc_requests: 83 total / 83 ok / 0 fb, SR=100%, fb=0%**
- 注入分析 `f|103` fallback 段确认是 `ts` 列时区 bug 口径 (沿 R730/R742-R750 实证); created_at 实测 0 fallback

### per-key 分布 (created_at 实测, tier=glm5_2_nv)
| key | pexec_success | 错误 |
|---|---|---|
| k0 | 17 | 0 |
| k1 | 17 | 0 |
| k2 | 17 | 0 |
| k3 | 17 | 0 |
| k4 | 15 | 0 |
| **总** | **83** | **0** |

**全 5 key 仅 pexec_success, 零错误穿透 cc2** — 连续第 5 轮最干净

### 注入噪声 (不在 cc2 路径, 被 fid1 buffer 兜住)
- all_tiers_exhausted × 8 / NVStream_IncompleteRead × 2 (avg_dur 35690ms) → hermes→dsv4f0731_nv 上游 NVCF 容量
- NVCFPexecRemoteDisconnected × 19 / 529_nv_overloaded × 5 / empty_200 × 1 → 同上, 非 cc2 链路
- dsv4f0731_nv SR=52.4% (11/21) 是 hermes caller 链路, 非 cc2

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, nv_gw_stable Up 3d, logs_db Up 5d — 全 Up
- env 沿 R750, 无漂移

## 判稳结论
- **cc2 nv_gw 链路连续 17 轮 (R735~R751) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 per-key 全 pexec_success 无任何 cc2 错误穿透 — 连续第 5 轮最干净
- 注入噪声全来自 hermes→dsv4f0731_nv NVCF 容量, 被 buffer 兜住, 不影响 cc2 链路
- NOP 巡检轮 — 链路已稳, 无可改项

## SR 趋势
| 轮 | 30min SR | 备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 529 余波拖低 |
| R736-R740 | 100% | 持续稳定 |
| R741 | 100% (77/77) | pexec_success=77 与 cc2 200 一致 |
| R742-R745 | 100% (80-82) | 8th-11th consecutive, fb=0 |
| R746-R747 | 100% (77-80) | 12th-13th, fb=0 |
| R748 | 100% (75/75) | 14th, 最干净 |
| R749 | 100% (78/78) | 15th, 连续第 3 轮最干净 |
| R750 | 100% (82 nv / 82 cc) | 16th, 连续第 4 轮最干净 |
| R751 | 100% (83 nv / 83 cc) | 17th, 连续第 5 轮最干净 |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- 注入噪声 (529/empty_200/NVCFPexecRemoteDisconnected) 持续观察, 若泄漏到 cc2 (buffer 失效) 再查
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)

## 参数快照 (实测 env, 沿 R750, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode MODE_CHAIN=pexec_us_rr, KEY_MODE_BIND=空,
  KEY_FID_BIND=全 5 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, RR_US_PROXIES=7901,7894,7897,7896,7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130,
  PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
