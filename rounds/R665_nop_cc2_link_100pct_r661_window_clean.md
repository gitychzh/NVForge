# R665: NOP 巡检轮 — cc2 链路 100% 持续, R661 修复窗口仍无 IncompleteRead 再现

## TL;DR
R661 (handlers.py:1853 NV-ANTH-COLLECT-BUFRETRY) restart @08:02 UTC 后 ~2.5h 窗口:
- cc2 (cc4101-primary/glm5_2_nv) 60min: 5×200 SR=100%, 0 error
- cc4101 真实 SR 60min=100% (5/5, 0 fallback), 6h=100% (16/16, fb=6.25%)
- tier 60min glm5_2_nv: success×5 (k0 pexec b1b22d03×2 + k1 integrate×1 + k3 integrate×2) + transport_fail×4 (k2/k4 SSLEOF×2 + RemoteDisconnected×2) — buffer 重试覆盖后用���仍 200
- deadline 6h stream_total_deadline=0 (健康)
- /health ok 5keys, 配置无漂移
- R661 修复目标 (IncompleteRead→502) 窗口仍无再现事件 — 持续观察

不改码。

## 基线 (R665 实测)
| 指标 | 值 | 判定 |
|---|---|---|
| cc2 60min nv_gw SR | 5/5 = 100% | ✅ ≥99% |
| cc4101 60min 真实 SR | 5/5 = 100%, fb=0 | ✅ |
| cc4101 6h 真实 SR | 16/16 = 100%, fb=1 (6.25%) | ✅ |
| 6h stream_total_deadline | 0 | ✅ 健康 |
| tier 60min transport fail | 4 (k2/k4 SSLEOF+RemoteDisconnected) | ⚠️ buffer 覆盖 OK |
| R661 IncompleteRead 再现 | 0 (2.5h 窗口) | ✅ 修复持续有效 |
| 配置漂移 | 无 | ✅ |

## tier 60min per-key 分布 (glm5_2_nv)
| key | fid | upstream | 结果 | count |
|---|---|---|---|---|
| 0 | b1b22d03 | pexec | pexec_success | 2 |
| 1 | integrate | integrate | integrate_success | 1 |
| 2 | 3b9748d8 | pexec | pexec_SSLEOFError | 1 |
| 2 | 3b9748d8 | pexec | pexec_conn_RemoteDisconnected | 1 |
| 3 | integrate | integrate | integrate_success | 2 |
| 4 | b6029a96 | pexec | pexec_SSLEOFError | 1 |

注: k2/k4 传输失败经 buffer 5key 轮转后用户最终 200 — mark_transport 5-10s 短惩罚不累计 conn_count, KeyManager 未冻结。

## 注入数据说明
轮前注入的 30min dsv4p_nv SR=84.4% (32req) + all_tiers_exhausted×5 均来自 **hermes caller** (非 cc2 链路), 是 dsv4p_nv NVCF 侧配额型 5key 全 429 — nv_gw COOLDOWN 日志确认 `tier=dsv4p_nv all keys 429` 重复触发。不影响 cc4101-primary 路径 (cc4101 fallback 指向独立容器 dsv4p_nv40066:40066, 非 nv_gw 内 dsv4p tier)。

## 下一步
- 等下一波 cc4101-primary 流量 + IncompleteRead 再现 → 查 NV-ANTH-COLLECT-BUFRETRY 日志判断 R661 是否生效
- 若 IncompleteRead 再现仍落 502 → 深查 handlers.py:1853 触发条件是否命中
- hermes/dsv4p all_tiers_exhausted 配额型持续 → 关注 dsv4p_nv40066 fallback 路径可用性

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
