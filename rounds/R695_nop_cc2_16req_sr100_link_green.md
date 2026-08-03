# R695 — NOP 巡检 (cc2 流量持续 16req SR100%, 链路全绿, R661 ~40h+ clean)

**时间**: 2026-08-03 18:30 CST  
**上轮**: R694 (NOP, cc2 16req SR100% fb6.25%)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口实测 18:00-18:30 CST)

### cc2 真实 SR (cc_requests 表)
| total | ok | fb | sr |
|-------|----|----|----|
| 16 | 16 | 1 | **100.0%** |

- fallback 触发率: 1/16 = **6.25%** (< 10% 目标 ✅)
- cc2 用户可见 SR 100% — 目标达成

### nv_gw 全量 SR (所有 caller)
| status | count |
|--------|-------|
| 200 | 63 |
| 502 | 5 |

- nv_gw 全量 SR = 63/68 = **92.6%**
- 5×502 全非 cc2 管辖:
  - 4× NVStream_IncompleteRead (openclaw→glm5_2_nv, mid-stream 软挂非 cc2 流量)
  - 1× all_tiers_exhausted (hermes→dsv4p_nv, hermes 非 cc4101-primary caller)

### tier attempts per-key 错误分布 (glm5_2_nv)
| nv_key_idx | fid | upstream_type | total | ok |
|------------|-----|---------------|-------|----|
| 0 | integrat | nv_integrate | 1 | 0 |
| 1 | integrat | nv_integrate | 1 | 0 |
| 2 | 3b9748d8 | nvcf_pexec | 5 | 0 |
| 3 | integrat | nv_integrate | 4 | 0 |

| nv_key_idx | error_type | count |
|------------|------------|-------|
| 0 | IntegrateRemoteDisconnected | 1 |
| 0 | NVCFPexecRemoteDisconnected | 1 |
| 1 | IntegrateRemoteDisconnected | 1 |
| 2 | 429_nv_rate_limit | 6 |
| 2 | pexec_conn_RemoteDisconnected | 4 |
| 2 | pexec_success | 1 |
| 3 | integrate_success | 3 |
| 3 | integrate_conn_RemoteDisconnected | 1 |

- k2 (pexec fid3b9748d8): 429×6 + RemoteDisconnected×4 — NVCF 配额+连接间歇, 1× pexec_success 恢复
- k3 (integrate): 3× integrate_success + 1× RemoteDisconnected — 主力成功路径
- k0/k1 各 1× IntegrateRemoteDisconnected — 偶发, KeyMgr 5s 快速惩罚恢复

### KeyManager 日志 (最后 6 行)
```
[18:06:10] [NV-KEYMGR] transport_err tier=glm5_2_nv k3 type=RemoteDisconnected penalty=5s (no conn_count)
[18:21:51] [NV-KEYMGR] transport_err tier=glm5_2_nv k4 type=RemoteDisconnected penalty=5s (no conn_count)
[18:25:08] [NV-KEYMGR] transport_err tier=glm5_2_nv k3 type=RemoteDisconnected penalty=5s (no conn_count)
[18:27:09] [NV-KEYMGR] transport_err tier=glm5_2_nv k3 type=RemoteDisconnected penalty=5s (no conn_count)
[18:27:09] [NV-KEYMGR] transport_err tier=glm5_2_nv k3 type=RemoteDisconnected penalty=5s (no conn_count)
[18:28:22] [NV-KEYMGR] transport_err tier=glm5_2_nv k3 type=RemoteDisconnected penalty=5s (no conn_count)
```
- k3/k4 RemoteDisconnected penalty=5s no conn_count ×6 — 快速恢复生效 (不累计 conn_count, 5s 后可重试)

### buffer/wait 日志
- 无 BUFFER- 日志 (无 buffer 触发)
- 无 WAIT- 日志 (无全挂等 NVCF 恢复)

## 验证: NOP 无需 restart
- `curl /health`:
  - nv_gw ok (5 keys, pexec models: kimi_nv/dsv4p_nv/glm5_2_nv, default glm5_2_nv)
  - cc4101 ok (primary glm5_2_nv)
  - dsv4p_nv40066 ok (5 keys)
- `docker ps`: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 3h, nv_gw_stable Up 40h, opclaw4103/hm4104 Up 29min — 全 Up
- 配置实测无漂移:
  - NVU_DISABLE_MS_FALLBACK=1
  - NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr

## 下一步
- 持续监控 cc2 流量 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- k2 pexec 429×6 + RemoteDisconnected×4 — NVCF 配额+连接间歇, 若持续频发可考虑 k2 切 integrate
- k0/k1 IntegrateRemoteDisconnected 各 1× — 偶发, 关注是否蔓延
- openclaw glm5_2_nv NVStream_IncompleteRead ×4 — 非 cc2 管辖但关注是否蔓延
- 等 NVAnthCollect_IncompleteRead 是否再现 (R661 修复窗口 ~40h+ clean)

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
