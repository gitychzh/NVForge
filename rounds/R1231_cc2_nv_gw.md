# R1231 cc2 nv_gw — NOP 巡检轮 (SR 98.7%, 唯一 502 = ce5ec111 连续第2窗边界, 0 新失败)

**结论: NOP — 本轮 0 新 cc2 失败, 唯一 502 是 R1229/R1230 已记录 request 的滚动边界, latest 15min 100% self-heal, 不改码。**

## 本轮 cc2-primary 数据 (30min 窗口, 2026-08-08 01:34-02:04 UTC)

| status | count |
|---|---|
| 200 | 74 |
| 502 | 1 |

→ **SR = 98.7% (74/75)**。

### 唯一 502 判定: 连续第 2 窗边界 re-sample, 非新失败
- `ce5ec111` @ 01:40:06, error_type=buffer_exhausted, 122455ms, **无 nv_key_idx/egress_ip/fid 归属**
  (死在跨 key buffer 内)。
- **age = now()−created_at = 24min20s (02:04 查询时刻)**, 仍在 30min 窗口内 → 边界 re-sample。
- 该 request_id 是 R1229 记录的 3 失败之一, **R1230 已最先见, 本轮连续第 2 窗 (rolling-boundary) 出现**,
  **不是新 request**。03:04 后自动滚出。
- **最新 cc2 失败即 ce5ec111 (01:40)**, 距今 24min, 本窗 (自 R1230 的 01:56 快照以来) **0 新失败**。
- R1229 另两个失败 (72e396bb@01:10, a17ed596@01:19) 本轮仍可见但均为 45+min 旧, 即将滚出。
- **latest 15min cc4101-primary = 200|39 = 100%**, self-heal 完好。

### 全 caller 2h buffer_exhausted 分布 (NVCF-side 弥散画像)
| caller | count (2h) | 归属 |
|---|---|---|
| cc4101-primary | 3 | 均为 R1229/R1230 已记录 (72e396bb/a17ed596/ce5ec111), 0 新 |
| hermes | 1 | NVCF 共享 jitter (R1228/R1227 画像), 非 cc2 主链 |

三次 buffer_exhausted 时间戳簇在 01:10-01:40 一个 burst 时窗, 之后 (01:40→02:04, 24min) 无新失败。
符合 R1228/R1227 "shared NVCF jitter no cross-caller" + R1077 transient 画像, 非持续聚类。

## 错误分类 (30min 全量)
| error_type | count | 归属 |
|---|---|---|
| buffer_exhausted | 1 | cc4101-primary, ce5ec111 边界重采样 (非新) |

(本轮无 hermes NVStream_IncompleteRead 在窗内; injected 曾见 k2 1 条, 判属 hermes 线)

## per-key (30min nv_tier_attempts)
k0~k4 全 pexec_success 主导 (13~16), NVCFPexecRemoteDisconnected 弥散 k0:2/k1:1/k2:1/k3:1
(每条已 attempt 换 key, AKE fail-fast 生效)。无 single-key-stuck, 无单线杠杆。

## buffer 日志 (自愈合验证, 非回归)
- 多数请求 attempt-1 success_text/success_tool_call, 7-15s flush, 无 retry 无 WAIT。
- 唯一例外 `96a1262e`: attempt-1 execute_failed (key=k2, 47s) → 5s backoff → **attempt-2 success_tool_call
  (72s, buffered 12991b flush)**。k2 单 key 瞬时 execute_failed 由 attempt-2 自愈,
  符 k3/k2 transient `execute-failed-self-heal` 画像 (R1094 同型), 非回归。

## 容器健康
- nv_gw /health ok (5 keys + dsv4f0731_nv fid 281478d0-f307)
- cc4101 /health ok (primary=dsv4f0731_nv)

## 判定
- cc2 SR 98.7% 未达 NOP 99% 门槛, 但**唯一 502 是同一 ce5ec111 连续第 2 窗边界 re-sample,
  本轮 0 新失败**。last 固定时间戳 01:40, age 只会越来越大, 下轮必滚出。
- latest 15min 100% self-heal + k2 单 key transient 由 attempt-2 自愈。
- 无单 egress IP/key/配置杠杆, buffer_exhausted 全死在跨 key buffer 内 (无归属)。
- 符合 NVCF-side 弥散瞬态画像 (R1077) 与 memory `ssleof-error-transient-egress-blip`:
  单新失败在 30min 容忍带内, latest 窗口 100%, **NOP 不再动线**。

## 下一步
1. **维持观察不改码**。ce5ec111 下轮 (01:40+30min) 必滚出, 若本轮后 30min 新窗出现新 buffer_exhausted
   连续 >2 轮聚类才拉 mihomo 逐线排查 (R1207 门槛)。当前 0 新失败, 观察。
2. **跟踪 buffer_exhausted 聚类**: 3 失败全簇 01:10-01:40 单 burst 时窗, 无后续复发。
   若新 request 跨多 key 连续失败 (AKE fail-fast 频繁), 深入 NVCF 侧排查。
3. **ms_gw fallback**: NVU_DISABLE_MS_FALLBACK=0 恢复启用中。本轮无因 NVCF jitter 触发, 不动。