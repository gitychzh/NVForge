# R742 — cc2 nv_gw NOP 巡检 (2026-08-05 05:06 CST)

> 上轮 R741 (NOP, 7th consecutive 100%) → 本轮 R742 NOP, 8th consecutive 100%

## 判稳结论: NOP (全面达标)

- **cc2 (cc4101-primary → nv_gw → glm5_2_nv) 30min SR=100% (81/81 nv_requests, 83/83 cc_requests), fb=0%**
- 连续第 **8 轮** SR 100% (R735~R742)
- 529 storm + empty_200/integrate_overloaded 微噪声持续, buffer 兜住, cc2 不可见
- 无可改项, 不动码

## 依据 (实测 ~05:06 CST, 注入数据 + created_at 口径核验)

### nv_requests 表 (nv_gw 层, 30min)
- cc4101-primary|glm5_2_nv|200|81 — 81×200, SR=100%
- per-key tier: k0-k4 各 15-17 pexec_success, 合计 81 = cc2 81×200 (完全一致)
- 529_nv_overloaded 散布 k0-k4 (各 6-8) + NVCFPexecRemoteDisconnected (各 1-2) — 被 buffer 兜住
- k3 empty_200×1, k4 529_integrate_overloaded×2 — 微噪声, cc2 不可见

### cc_requests 表 (cc4101 层, created_at 口径, 30min, 实测核验)
- upstream_used=primary, status=200, count=83, fb=0 — **83×200, 0 fallback, SR=100%**
- 注意: `ts` 列口径拉到 516 total/34fb 是旧时区数据混入 (STATE R730 实证 ts 时区 bug), 用 created_at 才是真实当前 30min

### 非 cc2 流量 (hermes→dsv4f0731_nv)
- 14×200 + 7×502 (SR 66.7%) — all_tiers_exhausted×6 + NVStream_IncompleteRead×1
- 这是 hermes caller 走 dsv4f0731_nv 的 NVCF 容量问题, **不是 cc2 nv_gw 链路**

### 注入数据 "f|102" 解读
- "30min fallback 发生率" 段 `f|102` 是 ts 列口径的聚合行截断, 非真实 fb 计数
- created_at 口径实测: 83 req, 0 fb — 真实 fb=0

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 8h, dsvf0731_nv40666 Up ~1h — 全 Up
- env 沿 R741, 无漂移
- dsvf0731_nv40666 不在 cc2 链路 (cc4101 primary/fallback 均未指向), 无影响

## SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 529 余波拖低 |
| R736 | 100% (47/47) | 余波平息 |
| R737 | 100% (51/51) | 持续稳定 |
| R738 | 100% (60/60) | 52e1ddb6 fid 529 被 buffer 兜住 |
| R739 | 100% (68/68) | empty_200/integrate_overloaded 微噪声不可见 |
| R740 | 100% (73/73) | 流量略增 |
| R741 | 100% (77/77) | pexec_success=77 与 cc2 200 一致 |
| **R742** | **100% (81 nv_req / 83 cc_req)** | **8th consecutive, fb=0 (created_at 实测)** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+ / fb <10%)
- 529 noise + empty_200 持续观察, 若泄漏到 cc2 (buffer 失效) 再查
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 实证)

## 参数快照 (实测 env, 沿 R741, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, MODE_CHAIN=pexec_us_rr, KEY_FID_BIND=全5key绑fid1=b1b22d03
  - KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007
  - STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
