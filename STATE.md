# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1235 (NOP 巡检轮 — 全 caller dsv4f0731_nv SR=100% (116/116), cc2-primary 100% (73/73), 30min 零错误, hermes 线 IncompleteRead 收敛, 不改码)**
> 主链 fid: **281478d0-f307** 稳定, dsv4f0731_nv 单模式 (active 流量)
> 全 caller (30min): `200|116` → SR=100% (116/116), **本轮 0 错误**。
> **cc4101-primary (cc2 主链) = 200|73 → SR=100%, 本轮 0 失败**。
> 本轮全 caller 0 error (无 502/IncompleteRead/buffer_exhausted)。前 3 窗 (R1232/1233/1234)
> 各 1 条 hermes 线 NVStream_IncompleteRead 画像**本轮消失**, NVCF-side transient 完全收敛。
> per-key k0~k4 全 pexec_success 主导 (14~17), k1: 1 条 NVCFPexecRemoteDisconnected attempt 换 key 自愈。
> 无 buffer_exhausted 归属 cc2, 无 deadline, 无任何失败聚类。
> 容器 health ok (nv_gw 5 keys, cc4101 primary=dsv4f0731_nv)。

## 本轮 (R1235) 改动 + 依据 + 验证

### 改动: 无 (NOP)。cc2-primary SR=100% (73/73), 全 caller 0 错误 (116/116),
### hermes 线 IncompleteRead 收敛, 无杠杆可改, 如实记录下轮观察。

### 依据 (注入分析, 2026-08-08 10:27 CST / 02:27 UTC)

- **30min 全 caller**: cc4101-primary `200|73`, hermes `200|43` → **dsv4f0731_nv SR=100% (116/116)**,
  **本轮零错误** (无 502/IncompleteRead/buffer_exhausted)。
- **cc4101-primary (cc2 主链) = 200|73 → SR=100%, 本轮 0 失败**。
- **hermes 线 IncompleteRead 收敛**: 前 3 窗 (R1232/R1233/R1234) 各 1 条 hermes 线
  `NVStream_IncompleteRead` (非 cc2) → 本轮**消失**。memory `primary-model-dsv4f0731-r1095`:
  zombie/IncompleteRead 类多属 hermes 线非 cc2; `nvcf-shared-jitter`: single-caller isolated
  transient, NOP 自愈即可, 约 3 窗周期收敛。
- **错误分类 30min**: (无错误), 0 条 status!=200。
- **per-key 30min**: k0~k4 全 pexec_success 主导 (k0:14/k1:11/k2:17/k3:17/k4:14), k1: 1 条
  NVCFPexecRemoteDisconnected (transient, attempt 换 key + AKE fail-fast 自愈)。无 single-key-stuck。
- **buffer/wait 日志**: 30min 无 buffer/wait/keymanager 日志, 全 attempt-1 success, 无 retry
  无 WAIT, 无 buffer_exhausted 归属 cc2。
- **容器**: nv_gw Up 31h /health ok (5 keys + dsv4f0731_nv), cc4101 Up 31h ok (primary=dsv4f0731_nv)。

### 验证
无改动, 无 restart。cc2-primary 100%, 全 caller 0 错误, 5 key 健康, hermes 线 transient 收敛。
容器 health ok。

## 参数快照 (nv_gw + cc4101, 与 R1234 一致, 无漂移)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (5 key 全 bind fid 281478d0-f307, dsv4f0731_nv 单模式)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1232 (SR 99.2%, 唯一 502 = hermes 线 NVStream_IncompleteRead, cc2-primary 100% (77/77)) →
R1233 (SR 99.1%, 唯一 502 = hermes 线 NVStream_IncompleteRead (diff request, 不聚类),
cc2-primary 100% (72/72)) → R1234 (SR 99.2%, 唯一 502 = hermes 线 NVStream_IncompleteRead
(连 3 窗同画像 diff request, 不聚类), cc2-primary 100% (76/76)) → R1235 (**SR 100% (116/116),
全 caller 0 错误, hermes 线 IncompleteRead 收敛, cc2-primary 100% (73/73)**)。NVCF-side 弥散
transient 完全收敛, 5key/IP 全健康, 无单线/配置杠杆, NOP。

## 下一步
1. **维持观察不改码**。cc2 主链 100%, 全 caller 0 错误, 无失败聚类, 无 mihomo 逐线排查需求
   (R1207 门槛未触发)。
2. **hermes 线 IncompleteRead 已收敛** (连 3 窗 R1232-R1234 各 1 条 hermes 线 → R1235 消失),
   持续观察。若跨 caller 同刻 502 聚类 (NVCF-side jitter 画像) 或 hermes 线错误连续增长才升级观察。
3. **ms_gw fallback**: NVU_DISABLE_MS_FALLBACK=0 恢复启用中, 本轮无 NVCF jitter 触发, 不动。
