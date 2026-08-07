# R1159 cc2_repair_self NOP — 整窗全 200, 唯一错误归属 hermes

状态: NOP (不改码)
时间: 2026-08-08 03:10 CST (≈ 19:10 UTC)
主链: dsv4f0731_nv 经 nv_gw pexec (全 5 key bind fid 281478d0-f307)

## 结论
注入 30min (≈02:40-03:10 CST) cc4101-primary **`200|94` = 100% SR, 0 非-200** — 自 R1158
Burst2 彻底滚出后, 跨两轮窗口稳定全绿。总线 dsv4f0731_nv SR=99.3% (150/151), 唯 1× 502
归属 **hermes** (NVStream_IncompleteRead, request d6130cae), 非 cc2, 非新类型。→ NOP 不改码。

## 实查证据 (2026-08-08 03:10 CST)

- **注入 30min cc4101-primary**: `200|94` = 100% SR, 0 非-200。
- **注入 30min 总线**: `dsv4f0731_nv SR=99.3% (150/151)`; cc4101-primary 94, hermes 56+1×502。
- **实查错误归属**: 唯一 `NVStream_IncompleteRead` (request d6130cae, 18:59:58 UTC, fid 281478d0)
  **caller = hermes**, 非 cc2 请求。瞬时 egress 抖动, 非配置漂移、非新类��。
- **tier (30min)**: 全 `pexec_success` (key0=19, key1=17, key2=20, key3=20, key4=18), 无 429/empty/新类型。
- **fallback**: 0 触发 (30min f|151 全 200 直通)。
- **buffer/wait/keymanager 日志**: 无 (无 buffer 事件、无 WAIT、无退避日志)。
- **容器 (实查)**: nv_gw + cc4101 /health 全 ok, 未重启。nv_gw 5 key 全 bind fid 281478d0。

## 改动
无 (NOP 巡检轮)。

## 验证
cc2 (cc4101-primary) 30min 94/94 = 100% SR, 0 非-200; 唯一错误 CARITABLE JOIN 归属 hermes 非 cc2;
tier 全 pexec_success 无新类型; fallback 0%; buffer 无事件; 容器全健康。链路稳定无改码条件。

## 下一步
维持静稳观察。穿越两轮 (R1158→R1159) 整窗全绿, Burst2 风暴后链路已完全静稳。核心监控不变:
**是否重现独立瞬时 burst 及复发间隔**。若再现 ≥2× buffer_exhausted 且 request_id 全新则为独立新事件,
按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904)。
当前仍判定瞬时 egress 抖动, NOP。

## 参数快照 (本轮无变更)
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s),
  NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2 (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1158 (NOP — Burst2 彻底滚出, non200_since_18_37=0) → R1159 确认: 整窗 94/94 全 200, 递延干净,
唯一错误归属 hermes 非 cc2。链路跨两轮全绿, 无新事件。