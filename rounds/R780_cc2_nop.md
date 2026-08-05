# R780 — cc2 NOP 巡检 (2026-08-05 ~08:03 CST)

## 改动: 不改码 (NOP)

## 依据 (轮前链路分析 ~08:02 CST, 30min 窗口)
- cc2 (cc4101-primary) glm5_2_nv: 71×200, SR=100%, 0 错误, 0 fallback
- tier 噪声 20 (NVCFPexecRemoteDisconnected×17 + empty_200×2 + 529_nv_overloaded×1):
  - k0:4+k1:1+k2:3+k3:4+k4:5 RemoteDisc (均匀分布, 无单点聚集)
  - k1+k3 各 1 empty_200 (NVCF 偶发空响应, buffer retry 1 次消化)
  - k1:1 529_nv_overloaded (NVCF 偶发过载, 不持续)
- per-key pexec_success: k0:13+k1:11+k2:15+k3:17+k4:13 = 69 (全 attempt=1 即 success)
- 无 buffer/wait 日志 (全 attempt=1, 未触发 retry/backoff)
- 注入噪声 (dsv4f0731_nv 502×9 + all_tiers_exhausted×8 + zombie_empty_completion×1) 全在 dsv4 hermes caller, 非本链路
- dsv4p_nv SR=100% (12/12), fallback 链路健康

## 验证 (NOP 无需 restart)
- 容器: nv_gw Up 10h, cc4101 Up 6h — 运行中 (注入数据已确认)
- cc4101-primary 30min: 71 nv / 71 ok / 0 err / 0 fb — 零穿透坐实

## 判稳结论
- **46 轮 (R735~R780) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- tier 噪声 20 全被 buffer/KeyManager 消化, cc4101-primary 零穿透
- 流量 71 req/30min (上轮 R779 67→71, 流量持续回升)
- NOP 巡检轮 — 链路已稳, 无可改项
- cleanest 停 27 (R774 后每轮 tier 噪声均>0)

### SR 趋势
| 轮 | 30min 窗 SR | tier 噪声 | 备注 |
|---|---|---|---|
| R774 | 100% (95/95) | 0 | 40th, 27th cleanest |
| R775 | 100% (83/83) | 20 | 41st, cleanest 停 27 |
| R776 | 100% (82/82) | 19 | 42nd consecutive 100% |
| R777 | 100% (80/80) | 17 | 43rd consecutive 100% |
| R778 | 100% (57/57) | 16 | 44th consecutive 100% |
| R779 | 100% (67/67) | 18 | 45th consecutive 100% |
| R780 | 100% (71/71) | 20 | **46th consecutive 100%, cleanest 停 27** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- tier 噪声仍在 buffer 消化范围内 (17 RemoteDisc + 2 empty_200 + 1 529, 全 attempt=1 success) — 不影响 cc2 可见 SR
- 注入噪声 (dsv4f0731_nv 502×9 + all_tiers_exhausted×8 + zombie_empty×1) 全在 dsv4 hermes caller, 非本链路
- dsv4p_nv fallback 链路健康 (SR=100%), 应急链路 OK

## 参数快照 (R780, 与 R779 一致无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv40066, STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF | fallback→dsv4p_nv40066(40066)
