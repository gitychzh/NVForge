# R1101 — cc2 NOP 巡检轮 (HM2 nv_gw 自优化)

时间: 2026-08-07 22:30 CST (轮前链路分析注入)
上轮: R1100 (NOP, cc2 主链 100/100=100% SR 零错误)

## 结论: NOP, 不改码

30min cc2 主链 102/102=100.0% SR, 零错误, 零 fallback。唯一 1× zombie_empty_completion 归属
peer hermes, 非 cc2之作。per-key 基本全 pexec_success (k3 2× RD 与上轮持平, 未上升, 单请求 buffer
自愈, 非多 key 连续复发)。buffer 全 attempt-1 直 flush 1-14s, 零重试零级联零 buffer_exhausted。
cc2 范围无新签名 → 不改码。

## 依据 (实测 DB 2026-08-07 22:30 CST + /health)

- **30min nv_requests (cc4101-primary)**: status 仅 200 × **102** = 100.0% SR, 0 错误。
- **30min 全量非-200 归属**: 唯一 1× zombie_empty_completion 全部 caller=**hermes** (peer)。
  本轮实时查询 `caller|count` = `hermes|1` (cc4101-primary 0) —— JOIN 归属铁证。
- **fallback**: 0% (cc_requests 103 全走 primary, fallback_triggered=0)。
- **nv_tier_attempts 30min**: 5 key 基本全 `pexec_success` (0/1/2/3/4=19/22/15/25/22); 仅 k3 2×
  `NVCFPexecRemoteDisconnected` 一次性 distributed transient (与上轮 2× 持平, 未上升; 总量 success
  25 杂音小, 单请求 buffer 自愈)。零 buffer_exhausted, 零持续 tier 错误。
- **buffer 日志**: 全 attempt-1 直 flush 秒回 (NV-BUFFER-SUCCESS elapsed 1-14s), 零重试零级联零
  buffer_exhausted。无 buffer/wait/keymanager 惩罚日志。
- **容器 /health 2026-08-07 22:30 CST**: 40006 nv_gw http 200, 4101 cc4101 http 200。docker ps:
  nv_gw Up 19h, cc4101 Up 19h, nv_gw_stable Up 5d。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **102/102 = 100.0% SR, 0 bad** | ✅ 全绿 |
| cc2 专属错误分类 | (cc2 专属 0 rows) 零错误 | ✅ |
| 非-200 归属 | 1× zombie_empty_completion, caller=hermes (peer) | ✅ peer 归属 |
| fallback 触发率 | 0% (103 全走 primary) | ✅ |
| per-key tier 错误 | 基本全 pexec_success; 仅 k3 2× RD (与上轮持平) 一次性 transient | ✅ 零持续 tier 错误 |
| buffer | 全 attempt-1 直 flush 1-14s, 零重试零级联零 buffer_exhausted | ✅ |
| container /health | nv_gw 200, cc4101 200 (Up 19h/19h) | ✅ |

## 下一步
- 延续 NOP。cc2 主链连续多轮 100% SR + zero fallback (R1099-R1101 同), 无参数可调。
- **k3 RD 2×**: 与上轮持平未上升, 一次性 distributed transient, 单请求 buffer 自愈, 不构成
  multi-key 连续复发。仅当 k3 RD 在多 key **连续复发** (多个独立请求多 key 持续失败) 才查 mihomo 7896。
- **hermes 1× zombie_empty_completion** (peer) 持续关注, 归属 peer 非 cc2 不改动。
- 若 zombie_empty_completion 中出现 caller=cc4101-primary (c.parent) 才进 cc2 指标。

## 参数快照 (未动, 同 R1100)
- 本轮零改动。nv_gw: NV_GLM52_MODE_CHAIN=pexec_us_rr, KEY_MODE_BINDING= 空,
  KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0, NVU_DISABLE_MS_FALLBACK=0。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400。
