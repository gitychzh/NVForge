# R1236 cc2 nv_gw — NOP 巡检轮 (SR 100% (116/116), cc2-primary 100% (74/74), 0 错误)

**结论: NOP — 全 caller dsv4f0731_nv SR=100% (116/116), cc2-primary SR=100% (74/74),
30min 零错误 (无 502/IncompleteRead/buffer_exhausted), 连 2 窗全绿 0 错误, 不改码。**

## 本轮 cc2-primary 数据 (30min 窗口, 2026-08-08 ~10:02-10:32 CST)

| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 74 |
| hermes | 200 | 42 |

→ **dsv4f0731_nv 全 caller SR = 100% (116/116)** — 本轮全 200, 0 失败。
→ **cc4101-primary (cc2 主链) SR = 100% (74/74)** — 本轮 0 失败。

### 关键: 连 2 窗全绿, 无任何失败
- R1235 已确认 hermes 线 NVStream_IncompleteRead 收敛 (R1232-R1234 各 1 条 → R1235 消失)。
- 本轮 (R1236) 继续全 caller 0 错误 — **连 2 窗 (R1235/R1236) 全 200, 0 失败**, hermes 线
  收敛稳定, NVCF-side 弥散 transient 完全自愈。memory `primary-model-dsv4f0731-r1095` /
  `nvcf-shared-jitter` 验证: 单 caller 隔离 transient, NOP 自愈即可。

## 错误分类 (30min 全量)
| error_type | count | 归属 |
|---|---|---|
| (无错误) | 0 | — |

30min 无任何 error_type, 无 status!=200, 无 502/deadline。cc2 主链 + hermes 线全绿 (连 2 窗)。

## per-key (30min nv_tier_attempts)
k0~k4 全 pexec_success 主导 (k0:15/k1:12/k2:17/k3:16/k4:14), k1/k2/k4 各 1 条
NVCFPexecRemoteDisconnected, k1 另有 1 条 NVCFPexecTimeout (均 transient, attempt 换 key 自愈)。
无 single-key-stuck, 无单线杠杆, transient 弥散正常。

## buffer/wait 日志
无 buffer/wait/keymanager 日志 (30min) — 全 attempt-1 success, 无 retry 无 WAIT,
无 buffer_exhausted 归属 cc2。5 key 健康。

## 容器健康
- nv_gw /health ok (5 keys + dsv4f0731_nv 单模式, passthrough), Up 36h
- cc4101 /health ok (primary=dsv4f0731_nv), Up 31h
- docker ps: 双容器 Up, 无 restart

## 判定
- cc2-primary SR=100% (74/74) 达 NOP 门槛 (≥99%), 0 失败。
- **本轮全 caller 0 错误** (116/116), hermes 线收敛稳定, 连 2 窗全绿。
- 全 key pexec_success 主导, transient 弥散已换 key 自愈, 无单线/配置杠杆。
- **NOP 不改码**, 如实记录下轮观察。

## 下一步
1. **维持观察不改码**。cc2 主链 100%, 全 caller 0 错误, 无失败聚类, 无 mihomo 逐线排查需求
   (R1207 门槛未触发)。
2. **hermes 线收敛稳定** (R1235/R1236 连 2 窗全绿), 持续观察。若跨 caller 同刻 502 聚类
   (NVCF-side jitter 画像) 或 hermes 线错误连续增长才升级。
3. **ms_gw fallback**: NVU_DISABLE_MS_FALLBACK=0 恢复启用中, 本轮无 NVCF jitter 触发, 不动。