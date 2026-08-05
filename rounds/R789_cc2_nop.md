# R789 — cc2 nv_gw NOP 巡检 (2026-08-05 ~08:40 CST)

## 结论: NOP — 第 53 轮连续 100% (R735~R789)

### 数据 (30min 窗口, 实弹 DB 复核)
- **cc4101-primary|glm5_2_nv: 111 req × 200, SR=100%**, 0 fallback, 0 穿透 ✅
- cc_requests: 111 total / 111 ok / 0 fb / SR=100.0%

### tier 噪声 (16, R788:18→16 略降, 全吸收)
| 错误 | count | 分布 |
|---|---|---|
| pexec_success | 111 | k0:21 k1:23 k2:23 k3:20 k4:23 |
| NVCFPexecRemoteDisconnected | 12 | k1:2 k3:5 k4:4 k2:1 — k3/k4 偏高(续) |
| 529_nv_overloaded | 2 | k0:1 k2:1 |
| empty_200 | 1 | k2 |
| pexec_429 | 1 | k0 |

- 所有噪声被 buffer/KeyManager 吸收 → 下一 attempt success → cc2 零感知

### 顶层错误
- all_tiers_exhausted × 4 全在 dsv4 hermes caller (dsv4f0731_nv SR=76.5% 13/17), 非 cc2

### 容器健康
- nv_gw Up 6h (passthrough, 5key, glm5_2_nv), cc4101 Up 7h (primary=glm5_2_nv), dsv4p_nv40066 Up 12h
- /health 全 ok

### 观察: k3/k4 RemoteDisc 持续偏高
- R782-R784: k4 偏高 (5-6)
- R788: 13 均布 k1-k4
- R789: 12, k3:5+k4:4 占 9/12
- k3/k4 = integrate+5IP path (fid2 3b9748d8 / fid3 b6029a96)
- 但 buffer 有效吸收, cc2 零感知, 无单 key 持续故障迹象
- 判定为 NVCF 侧间歇抖动, 非链路缺陷, 不达改码阈值

### cleanest 计数: 27 (R774 含 100% SR)

### SR 趋势
| 轮 | 30min SR | 噪声 | 备注 |
|---|---|---|---|
| R784 | 100% (116) | 19 | k4 RemoteDisc 5 续 |
| R787 | 100% (117) | 1 | k4 回落 0 |
| R788 | 100% (111) | 18 | RemoteDisc 13 均布 |
| R789 | 100% (111) | 16 | k3/k4 RemoteDisc 9 偏高 |

## 下一步
- 持续监控 SR 99%+ / fb <10%
- k3/k4 RemoteDisc 若连续多轮 >15 且偶发穿透 cc2 → 排查 k3 fid2/k4 fid3 integrate 健康度
- dsv4p_nv fallback 健康 (18/18 SR=100%), 应急路径 OK

## 参数快照 (无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: MIN_OUTBOUND_INTERVAL_S=10, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
