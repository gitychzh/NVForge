# R1160 cc2 repair self NOP — 整窗 96/96 全 200 跨轮全绿

日期: 2026-08-08 03:15 CST | 容器: nv_gw (28h), cc4101 (23h) | 主链 fid 281478d0-f307

## 结论: NOP (无改码)

cc2 (cc4101-primary) 整窗 100% SR, 0 非-200, 无新错误、无新类型。按铁律 SR≥99% 且无新错误 → NOP 巡检轮。

## 数据 (30min 窗口)

| 项 | 值 |
|---|---|
| cc2-primary | 200×96 = **100% SR, 0 非-200** |
| 总线 dsv4f0731_nv | SR=99.4% (154/155) |
| 总线非-200 | NVStream_IncompleteRead ×1 @18:59:58 UTC, **caller=hermes** (fid 281478d0), 非 cc2 |
| tier | 全 pexec_success (k0=19,k1=17,k2=21,k3=20,k4=19), 无 429/empty/新类型 |
| fallback | **0%** (f\|155 全直通) |
| buffer 日志 | 全 attempt-1 success direct flush (1.9-17.8s), 无退避/WAIT/buffer_exhausted |
| 容器 | nv_gw + cc4101 /health 全 ok, 未重启 |

## 分析

Burst2 彻底滚出后链路静稳已跨三轮 (R1158→R1160)。唯一非-200 均为 hermes 线瞬时
egress 抖动 (IncompleteRead), JOIN request_id 归属 hermes 非 cc2; 非配置漂移、非新类型。
buffer 全首跳 success, 无 buffer_exhausted 回归。

## 下一步

维持静稳观察。监控核心: 是否重现独立瞬时 burst。若下个窗口再现 ≥2× buffer_exhausted
且 request_id 全新 (非 3a582e6c/25c3a92b) → 独立新事件, 深挖 dsv4f0731_nv egress 线路
(7900-7904) per 记忆 `ssleof-error-transient-egress-blip`。当前仍判定瞬时抖动, NOP。

## 参数 (无变更)

- nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, BUFFER_MAX_RETRIES=5 (90×5=450s),
  DISABLE_MS_FALLBACK=0, KEY_COOLDOWN_S=30, 全 key bind fid 281478d0 (dsv4f0731_nv 单模式)
- cc4101: PRIMARY=dsv4f0731_nv (nv_gw:40006), FALLBACK=glm5_2_ms (ms_gw:40007),
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3