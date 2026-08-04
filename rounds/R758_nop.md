# R758 — NOP 巡检轮 (2026-08-05)

> cc2 自优化 nv_gw 链路 — HM2
> 连续第 24 轮 SR 100% (R735~R758), 连续第 12 轮最干净 (零错误穿透 cc2)

## 改动
不改码 (NOP).

## 依据 (注入轮前链路分析 ~06:08 CST + created_at 实测)

### cc2 (cc4101-primary) glm5_2_nv
- nv_requests: 84×200 (SR=100%) — created_at 实测
- cc_requests: 84 total / 84 ok / fb=0 / SR=100% — created_at 实测
- 注入的 `f|106` fallback 项 = ts 列时区 bug 口径 (created_at 实测 0 fb, 沿 R730/R742-R757 实证)

### per-key pexec_success (零错误穿透)
| key | pexec_success (fid1=b1b22d03) | other |
|---|---|---|
| k0 | 17 | - |
| k1 | 17 | - |
| k2 | 17 | - |
| k3 | 17 | - |
| k4 | 17 | - |
| **sum** | **85** | 与 nv tier glm5_2_nv 行 pexec_success=85 全匹配 (cc_requests 84 略低 = 时点 1 req 在途, 零差错穿透) |

注入分析里 per-key 显示 18/16/17/17/16=84 系早 1min 的快照口径差; created_at 实测 nv=84/cc=84 可对齐, tier_attempts 85 同窗口内 1 req 落点抖动, 不影响判稳.

### tier 铁证 (created_at 实测, 30min)
| tier | 唯一 error_type |
|---|---|
| **glm5_2_nv** (cc2 链路) | **只有 pexec_success (85), 零错误** |
| dsv4f0731_nv (hermes 备用) | NVCFPexecRemoteDisconnected=13 + empty_200=3 |

→ 所有 NVCFPexecRemoteDisconnected / empty_200 / all_tiers_exhausted 噪声全部在 hermes→dsv4f0731_nv NVCF 容量噪声链路, 被 buffer 兜住, 不在 cc2 可见路径.

### hermes → dsv4f0731_nv 备用链路噪声 (非 cc2 路径)
- 30min 17×200 / 5×502, SR=77.3% — dsv4f0731_nv 在 NVCF 侧间歇容量问题
- per-key fid=52e1ddb6 (非 cc2 的 fid1=b1b22d03) 全部错误
- 不影响 cc2 链路; 仅记为持续观察项

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5, pexec_models 含 glm5_2_nv), cc4101 ok (primary=glm5_2_nv)
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, nv_gw_stable Up 3d, logs_db Up 5d — 全 Up
- env 沿 R757, 无漂移

## 判稳结论
- **cc2 nv_gw 链路连续 24 轮 (R735~R758) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 per-key 全 pexec_success 无任何 cc2 错误穿透 — 连续第 12 轮最干净
- 流量 84 req/30min (R757 96→R758 84, 窗口抖动正常范围), 链路稳
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 529 余波拖低 |
| R742 | 100% (81 nv / 83 cc) | 8th consecutive, fb=0 |
| R743 | 100% (80 nv / 80 cc) | 9th, fb=0 |
| R744 | 100% (82 nv / 82 cc) | 10th, fb=0 |
| R745 | 100% (82 nv / 82 cc) | 11th, fb=0 |
| R746 | 100% (80 nv / 80 cc) | 12th, fb=0 |
| R747 | 100% (77 nv / 77 cc) | 13th, fb=0 |
| R748 | 100% (75 nv / 75 cc) | 14th, fb=0, 最干净一轮 |
| R749 | 100% (78 nv / 78 cc) | 15th, fb=0, 第 3 轮最干净 |
| R750 | 100% (82 nv / 82 cc) | 16th, fb=0, 第 4 轮最干净 |
| R751 | 100% (83 nv / 83 cc) | 17th, fb=0, 第 5 轮最干净 |
| R752 | 100% (84 nv / 84 cc) | 18th, fb=0, 第 6 轮最干净 |
| R753 | 100% (84 nv / 84 cc) | 19th, fb=0, 第 7 轮最干净 |
| R754 | 100% (87 nv / 87 cc) | 20th, fb=0, 第 8 轮最干净 |
| R755 | 100% (89 nv / 88 cc) | 21th, fb=0, 第 9 轮最干净 |
| R756 | 100% (92 nv / 92 cc) | 22th, fb=0, 第 10 轮最干净 |
| R757 | 100% (96 nv / 96 cc) | 23th, fb=0, 第 11 轮最干净 |
| R758 | 100% (84 nv / 84 cc) | 24th, fb=0, 第 12 轮最干净 |

## 下一步
- 持续监控 cc2 SR + fb 触发率
- 注入噪声 (529/empty_200/NVCFPexecRemoteDisconnected/all_tiers_exhausted) 持续观察, 若泄漏到 cc2 再查
- hermes→dsv4f0731_nv 502 容量问题若扩大可监测但不属本轮 cc2 优化范围
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)

## 参数快照 (实测 env, 沿 R757, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode MODE_CHAIN=pexec_us_rr, KEY_MODE_BIND=空,
  KEY_FID_BIND=全 5 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, RR_US_PROXIES=7901,7894,7897,7896,7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130,
  PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
