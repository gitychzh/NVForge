# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1231 (NOP 巡检轮 — SR 98.7%, 唯一 502 = ce5ec111 连续第2窗边界 re-sample, 0 新失败, latest 15min 100%, 不改码)**
> 主链 fid: **281478d0-f307** 稳定, dsv4f0731_nv 单模式 (active 流量)
> 失败 (30min cc4101-primary): `200|74 + 502|1` → SR=98.7% (74/75)。
> 唯一 502 = `ce5ec111`@01:40 (buffer_exhausted 122s) = **R1229/R1230 已记录的同 request**,
> age=24min 仍窗内边界 re-sample, **本轮 (自 R1230 01:56 快照) 0 新 cc2 失败**。
> R1229 另两个 (72e396bb@01:10, a17ed596@01:19) 仍可见但 45+min 旧, 即将滚出。
> 3 次 buffer_exhausted 全簇 01:10-01:40 单 burst 时窗, 之后 24min 无复发 → NVCF-side 弥散瞬态 (R1077)。
> latest 15min cc4101-primary = 100% (39/39) self-heal 完好; k2 单 key execute_failed 由 attempt-2 自愈。
> 无 egress_ip/key 归属 (死跨 key buffer 内), 全 egress IP/key 健康 (无单线杠杆)。容器 health ok.

## 本轮 (R1231) 改动 + 依据 + 验证

### 改动: 无 (NOP)。本轮唯一 502 是同一 ce5ec111 连续第 2 窗边界 re-sample, 0 新失败,
### latest 15min 100% self-heal, 无单线/配置杠杆可改, 如实记录下轮观察。

### 依据 (自查询, 2026-08-08 02:04 UTC)

- **30min cc2-primary**: `200|74 + 502|1` → **SR=98.7% (74/75)**。
- **唯一 502**: ce5ec111 @01:40:06 buffer_exhausted 122s, **age=now()−created_at=24min20s** (查询时刻 02:04),
  仍窗内 → 滚动窗口边界 re-sample。该 request **R1229 最先记录, R1230 首见, 本轮连续第 2 窗出现**,
  **不是新 request** (固定 created_at 01:40:06, 只会越滚越旧, 03:04 必滚出)。**本轮 0 新失败**。
- R1229 另两个失败 (72e396bb@01:10/a17ed596@01:19) 2h 内仍可见, 均已 45+min 旧, 非本轮新失败。
- **2h 全 caller buffer_exhausted**: cc4101-primary 3 (全已记录) + hermes 1 (NVCF 共享 jitter)。
  3 次全簇 01:10-01:40 单 burst, 之后 24min 无新失败 → 非持续聚类。
- **latest 15min cc4101-primary**: `200|39` → **100% self-heal**。
- **buffer 日志**: 多数 attempt-1 success (7-15s flush)。唯一 `96a1262e` attempt-1 execute_failed (key=k2, 47s)
  → 5s backoff → attempt-2 success_tool_call (72s, 12991b flush) = k2 单 key transient 自愈, 非回归。
- **per-key 30min**: k0~k4 全 pexec_success 主导 (13~16), transient NVCFPexecRemoteDisconnected 弥散
  k0:2/k1:1/k2:1/k3:1, 每条已换 key + AKE fail-fast, 无 single-key-stuck。
- **容器**: nv_gw /health ok (5 keys + dsv4f0731_nv), cc4101 ok (primary=dsv4f0731_nv)。

### 验证
无改动, 无 restart。buffer attempt-1 success 主导 + 唯一 k2 失败 attempt-2 自愈, latest 15min 100%。容器 health ok。

## 参数快照 (nv_gw + cc4101, 与 R1230 一致, 无漂移)

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
R1230 (SR 98.75%, 唯一 502 = R1229 边界重采样, 0 新失败) → R1231 (SR 98.7%,
唯一 502 = ce5ec111 连续第 2 窗边界 re-sample, 本轮 0 新失败, latest 15min 100%)。
NVCF-side 弥散瞬时 jitter 收敛后无复发, 5key/IP 全健康, 无单线/配置杠杆, NOP。

## 下一步
1. **维持观察不改码**。ce5ec111 (01:40) 下轮 (03:04 后) 必滚出; 仅连续 >2 轮新 buffer_exhausted
   聚类 (R1207 门槛) 才拉 mihomo 逐线排查。当前 0 新失败, 观察。
2. **跟踪 buffer_exhausted**: 3 失败全簇 01:10-01:40 单 burst, 无后续复发。若新 request 跨多 key
   连续失败 (AKE fail-fast 频繁), 深入 NVCF 侧排查。
3. **ms_gw fallback**: NVU_DISABLE_MS_FALLBACK=0 恢复启用中。本轮无因 NVCF jitter 触发, 不动。