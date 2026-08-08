# R1230 cc2 nv_gw — NOP 巡检轮 (SR 98.75%, 1 边界重采样, latest 15min 100%)

**结论: NOP — 无新 cc2 失败, 链路 self-heal 到 latest 15min 100%, 不改码。**

## 本轮 cc2-primary 数据 (30min 窗口, 2026-08-08 01:26-01:56 UTC)

| status | count |
|---|---|
| 200 | 79 |
| 502 | 1 |

→ **SR = 98.75% (79/80)**, 较 R1229 (97.1%) 回升。

### 唯一 502 判定: 滚动窗口边界重采样, 非新失败
- `ce5ec111` @ 01:40:06, error_type=buffer_exhausted, 122455ms, **无 nv_key_idx/egress_ip/fid 归属**
  (死在跨 key buffer 内)。
- 该 request_id 已是 **R1229 已记录的 3 个失败之一** (R1229 窗口见 01:40:06 ce5ec111)。
  本轮是新 30min 窗口的边界 re-sample, **不是新 request**。
- R1229 另两个失败 (72e396bb@01:10, a17ed596@01:19) 已滚动出窗, 本轮不再出现。
- **latest 15min cc4101-primary = 200|41 = 100%**, self-heal 完好。

### hermes 干扰 (非 cc2 范围)
- `92eb7e97` @ 01:54:41, NVStream_IncompleteRead, nv_key_idx=2, 38288ms → hermes 线 (NV_STREAM), 非 cc2 主链 caller。按 72e 判属 hermes, 不归 cc2。

## 错误分类 (30min 全量)
| error_type | count | 归属 |
|---|---|---|
| buffer_exhausted | 1 | cc4101-primary, 边界重采样 (R1229 同 request) |
| NVStream_IncompleteRead | 1 | hermes 线, 非 cc2 主链 |

## per-key (30min nv_tier_attempts)
k0~k4 全 pexec_success 主导 (14~16), 仅 NVCFPexecRemoteDisconnected 弥散 1~2 条/key (k0:2, k1:1, k2:1, k3:1)。
无 single-key-stuck, 无单线杠杆。每失败 attempt 已换 key + AKE fail-fast 生效。

## 容器健康
- nv_gw /health ok (5 keys + dsv4f0731_nv fid 281478d0-f307)
- cc4101 /health ok (primary=dsv4f0731_nv)
- nv_gw buffer 日志 latest: BUFFER-ATTEMPT attempt=1 → VERDICT=success_tool_call → SUCCESS,
  无 retry/WAIT, 10-12s flush, 无缓冲堆积。

## 判定
- cc2 SR 98.75% 未达 NOP 99% 门槛, 但**唯一 502 是 R1229 已记录的边界重采样, 本轮 0 新失败**。
- 符合 NVCF-side 弥散瞬态画像 (R1077), 与 memory `ssleof-error-transient-egress-blip` 一致:
  单新失败在 30min 容忍带内, latest 窗口已 100%, **NOP 不再动线**。

## 下一步
1. **维持观察不改码**。仅出现单条 egress IP/key 集中恶化 (可达 ~1%+ 差线) 或连续 >2 轮
   新 buffer_exhausted 聚类才拉 mihomo 逐线排查。当前 0 新失败, 观察。
2. **跟踪 buffer_exhausted**: 单 req ce5ec111 已跨两轮窗口 re-sample, 下一轮应滚出。
   若连续多轮出现同一/新 request 且跨多 key, 深入 NVCF 侧。
3. ms_gw fallback启用中 (NVU_DISABLE_MS_FALLBACK=0), 无因 NVCF jitter 触发, 不动。