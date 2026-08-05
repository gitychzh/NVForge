# R784 cc2 NOP 巡检

> 时间: 2026-08-05 ~08:21 CST
> 上轮: R783 (NOP, 49th consecutive 100%)
> 容器: nv_gw Up 5h, cc4101 Up 7h, dsv4p_nv40066 Up 12h

## 改动: 不改码 (NOP)

## 依据 (轮前链路分析 ~08:20 CST, 30min 窗口)

### cc2 链路 (cc4101-primary|glm5_2_nv)
- **116 req × 200 (SR=100%), 0 错误, 0 fallback** ✅
- 50th consecutive 100% (R735~R784)
- 流量 116 req/30min (上轮 107→116, +9 正常波动)

### tier 噪声 (本轮 19, 上轮 20→19, -1)
- NVCFPexecRemoteDisconnected ×14: k0:3 + k2:2 + k3:4 + k4:5 (k1:0)
- pexec_429 ×1: k0 (单次, KeyManager 退避消化)
- empty_200 ×1: k3 (NVCF 偶发空响应)
- 529_nv_overloaded ×3: k0+k1+k2 (NVCF 偶发过载)
- 全被 buffer/KeyManager 消化, cc4101-primary 零穿透
- 无 buffer/wait 日志 (全 attempt=1 即 success)

### k4 RemoteDisc 趋势 (连续 3 轮偏高)
- R782: 6, R783: 6, R784: 5 — 略降但仍为各 key 最高
- cc2 零穿透 (全 attempt=1 success, 不触发 buffer 重试) — buffer 容错有效
- 继续监控 k4 fid3 (b6029a96) 健康, 暂不行动 (无可改项)

### dsv4p_nv fallback 链路
- SR=100% (30/30), per-key 均衡 (k0:7+k1:6+k2:6+k3:6+k4:5)
- 应急链路健康

### 注入噪声 (非 cc2 链路)
- dsv4f0731_nv 502×7 + all_tiers_exhausted×6 + zombie_empty×1 全在 dsv4 hermes caller
- 零穿透 cc2

## 验证 (NOP 无需 restart)
- /health: nv_gw passthrough(5key) ok, cc4101 primary=glm5_2_nv ok
- docker ps: nv_gw Up 5h, cc4101 Up 7h, dsv4p_nv40066 Up 12h, nv_gw_stable Up 3d

## 判稳结论
- **cc2 nv_gw 链路连续 50 轮 (R735~R784) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 tier 噪声 19 (上轮 20→19, -1) — buffer 容错有效
- NOP 巡检轮 — 链路已稳, 无可改项
- cleanest 计数停在 27 (R774) — R774 后每轮 tier 噪声均>0, not cleanest

### SR 趋势
| 轮 | 30min 窗 SR | tier 噪声 | 备注 |
|---|---|---|---|
| R775 | 100% (83/83) | 20 | 41st, cleanest 停 27 |
| R776 | 100% (82/82) | 19 | 42nd |
| R777 | 100% (80/80) | 17 | 43rd |
| R778 | 100% (57/57) | 16 | 44th |
| R779 | 100% (67/67) | 18 | 45th |
| R780 | 100% (71/71) | 20 | 46th |
| R781 | 100% (70/70) | 20 | 47th |
| R782 | 100% (79/79) | 22 | 48th |
| R783 | 100% (107/107) | 20 | 49th |
| R784 | 100% (116/116) | 19 | **50th consecutive 100%, cleanest 停 27** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- 监控 k4 RemoteDisc (R782:6+R783:6+R784:5 连续 3 轮偏高) — 若持续可考虑排查 k4 fid3 (b6029a96) 健康
- 注入噪声全在 dsv4 hermes caller, 非本链路问题
- dsv4p_nv fallback 链路健康 (SR=100% 30/30), 应急链路 OK

## 参数快照 (R784, 实测无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, STREAM_TOTAL=470, HEADER=400, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF | fallback→dsv4p_nv40066(40066)
