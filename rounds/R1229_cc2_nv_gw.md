# R1229 — cc2 nv_gw semi-NOP 观察轮 (SR 97.1%, 2 真实 502 buffer_exhausted, NVCF-side 弥散瞬态)

**轮号**: R1229
**时间**: 2026-08-08 09:45 CST (01:45 UTC)
**容器**: nv_gw 35h up, cc4101 30h up
**primary**: dsv4f0731_nv (单模式, 全 5 key bind fid 281478d0-f307)

## 结论: semI-NOP, 不改码/不改 mihomo

30min cc2-primary **SR = 97.1% (67/69)**, 2 真实 502 buffer_exhausted。
与 R1228 同类: 共享 NVCF 上游瞬时 jitter, 弥散跨 key/IP, 无单线差负载。
全 egress IP 100%, 5 key 全健康, 失败在跨 key buffer 内死亡 (每 attempt 换 key)。
**无单线杠杆 → 维持观察 (R1077 教训: 弥散瞬态改线=回归风险)**。

## 数据 (轮前注入 + 自查询补证)

### 30min cc4101-primary
| status | count | avg_dur |
|---|---|---|
| 200 | 67 | 15967ms |
| 502 | 2 | 125312ms (buffer_exhausted) |

### 2h 全量失败 (3 个真实 502, 全 buffer_exhausted)
- 01:10:13 72e396bb → 502 buffer_exhausted 118s
- 01:19:49 a17ed596 → 502 buffer_exhausted 128s
- 01:40:06 ce5ec111 → 502 buffer_exhausted 122s

### 跨 caller (同小时 01:00)
- cc4101-primary: 98 总, 95 ok, **3 bad**
- hermes: 78 总, **78 ok, 0 bad**

⚠️ 与 R1228 差异: 本轮 **无跨 caller 相关** (hermes 同小时 100%)。
R1228 是双 caller 同挂; 本轮 jitter 簇更小/更短, 只有 cc2 单 caller 撞上。
同 terminal 签名 (buffer_exhausted, ~118-128s), 但 NVCF-side 范围收窄。

### per-egress-IP 2h (无单线恶化)
| egress_ip | total | ok | bad |
|---|---|---|---|
| 134.195.101.193 | 169 | 169 | 0 |
| 134.195.101.195 | 114 | 114 | 0 |
| 134.195.101.180 | 113 | 113 | 0 |
| 134.195.101.197 | 91 | 91 | 0 |

3 个失败 request**无 egress_ip 归属** (空) → 死在跨 key buffer 内, 未到任何单线。
**认定无单一差代理线** (R1207 触发门槛=单线集中恶化, 本round不满足)。

### tier attempts (n_tier=dsv4f0731_nv) 2h
5 key 全健康均匀: k0~k4 各 62~69 pexec_success。
transient (NVCFPexecRemoteDisconnected/Timeout) 弥散 k0/k1/k2/k3 (3/1/2/2 attempts),
每失败 attempt 已按要求换 key, 无 single-key-stuck。

## 根因判断

与 R1228 结论一致: **共享 NVCF 上游瞬时连接抖动** → 5key×90s buffer 内全换仍败 →
AKE fail-fast → skip WaitQueue → 502 buffer_exhausted。
本轮无跨 caller 相关 (hermes 同小时 100%), jitter 簇更窄更短, 但同 terminal 签名。
全部 egress IP/key 健康, 无单线/配置杠杆可改 (R1077)。

## 改动
无。semi-NOP 观察轮。未 restart, 未动 mihomo。

## 验证
- nv_gw /health ok (5 keys, proxy_role=passthrough)
- cc4101 /health ok (primary=dsv4f0731_nv)
- 无参数漂移

## 上轮 → 本轮
R1228 (SR 96.6%, 2 真实 502, 跨 caller 相关) → R1229 (SR 97.1%, 2 真实 502, 仅 cc2 单 caller)。
两类同为 NVCF-side 弥散瞬时 jitter, 本窗口收窄, 5key/IP 全健康。

## 下一步
1. **维持观察不改码**。仅当出现 **单条 egress IP/key 集中恶化** (可达 ~1%+ 差线) 或
   连续 >2 轮 buffer_exhausted 聚类才拉 mihomo 逐线排查。
2. 跟踪 buffer_exhausted terminal 频率。flast-transient self-heal 一贯有效 (单 req attempt-1/2)。
3. ms_gw fallback 恢复启用中 (NVU_DISABLE_MS_FALLBACK=0)。本轮 buffer_exhausted 未走 ms_gw 触发
   (fallback f=116 无因 NVCF jitter 536), 正常。