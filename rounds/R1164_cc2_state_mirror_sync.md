# R1164 — cc2 STATE mirror sync: 恢复闭环 NOP

> 日期: 2026-08-08 | host: HM2 | 链路: cc4101-primary → nv_gw(40006) dsv4f0731_nv

## 结论
NOP 巡检轮, 不改码。cc2 (cc4101-primary) 实查 30min **93/93 全 200 = 100% SR**, 0 非-200。
跨七轮 (R1158→R1164) 整窗全绿。

## 数据 (实查 30min 2026-08-08 ~04:02 CST)
- **cc4101-primary 30min**: `200|93` = 100% SR, 0 非-200。
- **总线 30min**: `150×200 + 1×502` = SR 99.3%。
- **唯一错误**: `stream_first_byte_timeout × 1` @ 19:18, **caller=hermes** 归属 hermes 非 cc2。
  JOIN 铁证同 R1162/R1163 签名: 瞬时首次包超时, 非配置漂移、非新根因。
- **tier 30min**: 全 `pexec_success` (k0 22 / k1 16 / k2 18 / k3 17 / k4 21 = 94), 无 429/empty/新类型,
  fid 全 `281478d0-f307` 稳定。
- **fallback**: 0% (总线全 200 直通, 0 触发)。
- **buffer 日志**: 全 attempt-1 direct flush (elapsed 7-9s); req 10dc72c2 有 k3 `execute_failed`
  → 5s backoff → attempt-2 `success_tool_call` 自愈 (elapsed 19s, 34KB flush)。
  瞬时 k3 单次, 非退避耗尽、无 WAIT、无 buffer_exhausted。同记忆 `k3-transient-execute-failed-self-heal`。
- **容器**: nv_gw + cc4101 /health 全 ok, 未重启。nv_gw Up 24h, cc4101 Up 24h。

## 依据
- SR=100% ≥ 99% → NOP。
- 唯一 502 归属 hermes 非 cc2, 无 cc2 新错误。
- buffer 无退避耗尽/无 WAIT/无 buffer_exhausted。
- 容器全健康未重启。

## 验证
cc2 30min 93/93=100% SR; 唯一错误归属 hermes; tier 无新类型; fallback 0%; buffer 直通+k3 瞬时自愈;
容器全健康。跨七轮全绿, 无改码条件。

## 下一步
维持静稳观察。监控是否重现独立瞬时 burst 及复发间隔。Burst2 后已跨 120+ min 无 cc2 异常。
若下窗口再现 ≥2× buffer_exhausted 且 request_id 全新 (JOIN 归属 cc2) → 独立新事件,
按 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress (7900-7904)。
当前 NOP。

## 参数快照
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, 全 key bind fid 281478d0-f307 (dsv4f0731_nv 单模式)。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。