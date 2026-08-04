# R749 — cc2 nv_gw NOP 巡检轮

> 时间: 2026-08-05 05:35 CST | 上轮: R748 | 改动: 不改码 (NOP)

## 链路实测 (created_at 核验, 30min 窗)

### cc2 (cc4101-primary) — 本轮焦点
| 指标 | nv_requests | cc_requests | 备注 |
|---|---|---|---|
| 总请求 | 78 | 78 | 完全一致 |
| 200 成功 | 78 | 78 | SR=100.0% |
| fallback 触发 | — | 0 | fb=0.0% (created_at 实测) |
| 注入 f\|90 | — | ts 列时区 bug 口径 | created_at 实测 0 fb (沿 R742-R748 实证) |

→ **SR=100%, fb=0% — 第 15 连续 100% 轮 (R735~R749)**

### per-key pexec_success (created_at, nv_tier_attempts glm5_2_nv, 30min)
| key | pexec_success | 合计 |
|---|---|---|
| k0 | 16 | 16 |
| k1 | 15 | 15 |
| k2 | 15 | 15 |
| k3 | 17 | 17 |
| k4 | 15 | 15 |
| 总 | 78 | = cc2 78×200 完全一致 |

**全 5key 均 pexec_success, 零错误穿透 cc2** — 连续第 3 轮最干净

### 注入噪声 (全部来自 hermes→dsv4f0731_nv, 不在 cc2 路径)
- hermes dsv4f0731_nv: 200×3 + 502×10 = SR=23.1% — NVCF 容量 (不穿透)
- all_tiers_exhausted ×8 (hermes 路径, avg_dur 92030ms)
- NVStream_IncompleteRead ×2 (hermes 路径)
- 注入的 per-key 噪声 (NVCFPexecRemoteDisconnected=15 / 529_nv_overloaded=3 / empty_200=1) 全来自 hermes→dsv4f0731_nv 上游 NVCF, 不在 cc2 路径
- → cc2 实测 nv_tier_attempts 全 pexec_success, 零错误穿透

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, dsvf0731_nv40666 Up 49s (刚重启, hermes 用不影响 cc2), nv_gw_stable Up 3d, logs_db Up 5d — 全 Up
- env 沿 R748, 无漂移

## 判稳结论
- **cc2 nv_gw 链路连续 15 轮 (R735~R749) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 per-key 全 pexec_success 无任何 cc2 错误穿透 — 连续第 3 轮最干净
- hermes→dsv4f0731_nv 502 + IncompleteRead 是 NVCF 容量, 不影响 cc2 链路
- dsvf0731_nv40666 刚重启 (Up 49s) 是 hermes 容器, 不在 cc2 路径, 无影响
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 529 余波拖低 |
| R736-R741 | 100% | 2nd-7th consecutive |
| R742 | 100% (81 nv / 83 cc) | 8th consecutive, fb=0 (created_at 实测) |
| R743 | 100% (80 nv / 80 cc) | 9th |
| R744 | 100% (82 nv / 82 cc) | 10th |
| R745 | 100% (82 nv / 82 cc) | 11th |
| R746 | 100% (80 nv / 80 cc) | 12th |
| R747 | 100% (77 nv / 77 cc) | 13th |
| R748 | 100% (75 nv / 75 cc) | 14th, 最干净 (全 pexec_success) |
| R749 | 100% (78 nv / 78 cc) | 15th consecutive, fb=0 (created_at 实测), 连续第 3 轮最干净 |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- 注入噪声持续观察, 若泄漏到 cc2 (buffer 失效) 再查
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)

## 参数快照 (实测 env, 沿 R748, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode MODE_CHAIN=pexec_us_rr, KEY_MODE_BIND=空,
  KEY_FID_BIND=全 5 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, RR_US_PROXIES=7901,7894,7897,7896,7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130,
  PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
