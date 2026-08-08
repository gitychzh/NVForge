# R1232 cc2 nv_gw — NOP 巡检轮 (SR 99.2%, cc2-primary 100% (77/77), 唯一 502 归属 hermes 线)

**结论: NOP — cc2-primary SR=100% (77/77), 唯一 502 = hermes NVStream_IncompleteRead (非 cc2 主链),
0 cc2 新失败, latest 窗口全 200, 不改码。**

## 本轮 cc2-primary 数据 (30min 窗口, 2026-08-08 ~09:40-10:10 CST)

| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 77 |
| hermes | 200 | 45 |
| hermes | 502 | 1 |

→ **dsv4f0731_nv 全 caller SR = 99.2% (120/121)**
→ **cc4101-primary (cc2 主链) SR = 100% (77/77)** — 本轮 0 失败。

### 唯一 502 归属判定: hermes 线, 非 cc2
- `NVStream_IncompleteRead` × 1, avg_dur 38288ms, 归属 caller=**hermes**, 非 cc4101-primary。
- 这也是 dsv4f0731_nv **hermes 线**的 singular transient (memory `primary-model-dsv4f0731-r1095`:
  zombie/IncompleteRead 多归属 hermes 线非 cc2 主链; `nvcf-shared-jitter` 弥散画像)。
- cc2-primary 请求 0 失败, 无任何 buffer_exhausted/deadline 归属。

## 错误分类 (30min 全量)
| error_type | count | 归属 |
|---|---|---|
| NVStream_IncompleteRead | 1 | hermes 线, dsv4f0731_nv (非 cc2) |

## per-key (30min nv_tier_attempts)
k0~k4 全 pexec_success 主导 (k0:14/k1:11/k2:18/k3:16/k4:14), NVCFPexecRemoteDisconnected
弥散 k0:2/k1:2/k2:1/k3:1 (每条 attempt 换 key, AKE fail-fast 生效)。无 single-key-stuck, 无单线杠杆。

## buffer/wait 日志
多请求 attempt-1 success 主导, 无 retry 无 WAIT, 无 buffer_exhausted 归属 cc2。k 健康。

## 容器健康
- nv_gw /health ok (5 keys + dsv4f0731_nv 单模式)
- cc4101 /health ok (primary=dsv4f0731_nv)

## 判定
- cc2-primary SR=100% (77/77) 达 NOP 门槛 (≥99%), 0 失败。
- 唯一 502 = hermes 线 NVStream_IncompleteRead, 归属非 cc2 主链, out-of-scope。
- 全 key pexec_success 主导, transient 弥散已换 key 自愈, 无单线/配置杠杆。
- **NOP 不改码**, 如实记录下轮观察。

## 下一步
1. **维持观察不改码**。cc2 主链 100%, 无失败聚类, 无 mihomo 逐线排查需求 (R1207 门槛未触发)。
2. **跟踪 hermes dsv4f0731_nv IncompleteRead**: 若跨 caller 同刻 502 聚类 (NVCF-side jitter 画像)
   才关注; 现在单条 isolated, 不动。
3. **ms_gw fallback**: NVU_DISABLE_MS_FALLBACK=0 恢复启用中, 本轮无 NVCF jitter 触发, 不动。