# R788 — cc2 NOP 巡检 (52nd consecutive 100%)

**日期**: 2026-08-05 08:29 CST
**上轮**: R787 (NOP, 51st consecutive 100%)
**改码**: 无 (NOP)

## 轮前数据 (30min 窗, ~08:28 CST, 注入分析)

### cc2 链路 (cc4101-primary|glm5_2_nv)
- **111 req × 200, SR=100%, 0 fallback, 0 穿透** ✅
- avg_dur 19601ms (≈19.6s/req, 正常区间)
- DB 复核: `status=200 count=111` 一致

### tier 噪声 (本轮回升, 但零穿透 cc2)
| error_type | k0 | k1 | k2 | k3 | k4 | 合计 |
|---|---|---|---|---|---|---|
| pexec_success | 21 | 23 | 22 | 23 | 22 | 111 |
| NVCFPexecRemoteDisconnected | 0 | 2 | 3 | 5 | 3 | 13 |
| 529_nv_overloaded | 1 | 1 | 1 | 0 | 0 | 3 |
| empty_200 | 0 | 0 | 1 | 0 | 0 | 1 |
| pexec_429 | 1 | 0 | 0 | 0 | 0 | 1 |
| **tier errors total** | | | | | | **18** |

- R787 tier 噪声 1 → R788 约 18 (回升)
- 主因 NVCFPexecRemoteDisconnected × 13 (k1-k4 分布均匀, 非单 key 故障)
- 但全部被 buffer/KeyManager 吸收 → 下一 attempt 即 success, cc2 端零感知
- 顶层错误: all_tiers_exhausted×5 (avg 86s) + zombie_empty×1 — 全在 dsv4 hermes caller (dsv4f0731_nv SR=66.7%), 非 cc2

### 其他链路
- dsv4p_nv: 20/20 SR=100% (fallback 应急链路健康)
- dsv4f0731_nv: 12/18 SR=66.7% (注入噪声 502×6, hermes caller, 非 cc2)

## 验证 (NOP 无 restart)
- 容器: nv_gw Up 6h, cc4101 Up 7h, dsv4p_nv40066 Up 12h, nv_gw_stable Up 3d, logs_db Up 5d
- /health 全 ok: nv_gw passthrough(5key, pexec 含 glm5_2_nv), cc4101 primary=glm5_2_nv
- DB 直接复核 cc4101-primary caller: status=200 count=111 ✅

## 判稳结论
- **cc2 nv_gw 链路连续 52 轮 (R735~R788) SR 100%, fb 0%** — 达标 (目标 SR 99%+/fb <10%)
- tier 噪声 18 (R787:1→18 回升) 但零穿透, 仍属健康吸收
- k3 RemoteDisc 5 最高, 但上轮 k4 已证明是间歇抖动可自愈
- **NOP 巡检轮 — 链路已稳, 无可改项**
- cleanest 计数仍停 27 (R774)

### SR 趋势
| 轮 | 30min SR | tier 噪声 | 备注 |
|---|---|---|---|
| R782 | 100% (79) | 22 | k4 RemoteDisc 6 偏高 |
| R783 | 100% (107) | 20 | k4 RemoteDisc 6 续 |
| R784 | 100% (116) | 19 | k4 RemoteDisc 5 续 |
| R787 | 100% (117) | 1 | k4 回落为 0 |
| R788 | 100% (111) | 18 | RemoteDisc 13 均布 k1-k4, 自愈中 |

## 下一步
- 持续监控 cc2 SR + fb (目标 SR 99%+/fb <10%)
- 关注 RemoteDisc 是否再升级 (本轮 13, 若连续>20 再看 k3/k4 fid 健康)
- dsv4p_nv fallback 链路健康 (SR=100% 20/20), 应急链路 OK

## 参数快照 (R788, 实测无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
