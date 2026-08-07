# R1100 — cc2 NOP 巡检轮 (HM2 nv_gw 自优化)

时间: 2026-08-07 22:23 CST (轮前链路分析注入)
上轮: R1099 (NOP, cc2 主链 100/100=100% SR 零错误)

## 结论: NOP, 不改码

30min cc2 主链 100/100=100.0% SR, 零错误, 零 fallback。唯一 3× zombie_empty_completion 全部
归属 peer hermes, 非 cc2 之作。buffer 基本全 attempt-1 直 flush, 仅 1× execute_failed 5s backoff
attempt-2 自愈, 零级联零 buffer_exhausted。cc2 范围无新签名 → 不改码。

## 依据 (实测 DB 2026-08-07 22:23 CST + /health)

- **30min nv_requests (cc4101-primary)**: status 仅 200 × **100** = 100.0% SR, 0 错误。
- **30min 全量非-200 归属**: 唯一 3× zombie_empty_completion (status=502) 全部 caller=**hermes**
  (peer)。本轮实时查询 `caller|status|count` = `hermes|502|3` (cc4101-primary 0) —— JOIN 归属铁证。
- **全量 SR**: dsv4f0731_nv 98.0% (144/147), 3 bad 全为 hermes 归属。
- **fallback**: 0% (147 全走 primary)。
- **nv_tier_attempts 30min**: 5 key 基本全 `pexec_success` (0/1/2/3/4=19/22/14/24/21); 仅 k3 2×
  `NVCFPexecRemoteDisconnected` 一次性 transient (上轮 1×, 本轮 2×, 总量 24 success 杂音小),
  无持续 tier 错误, 无 buffer_exhausted。
- **buffer 日志 30min**: 基本全 attempt-1 直 flush 秒回 (1-9s)。唯一异常 req=2e019d25:
  attempt-1 execute_failed (key=k5), 5s backoff, attempt-2 成功 200 (elapsed=47.6s) 自愈。
  零级联零 buffer_exhausted (SSLEOFError 无复发)。
- **容器 /health 2026-08-07 22:23 CST**: 40006 nv_gw http 200 (passthrough, nv_num_keys=5,
  nvcf_pexec_models 含 dsv4f0731_nv, default=glm5_2_nv), 4101 cc4101 http 200 (primary=dsv4f0731_nv)。
  docker ps: nv_gw Up 19h, cc4101 Up 19h。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **100/100 = 100.0% SR, 0 bad** | ✅ 全绿 |
| cc2 专属错误分类 | (cc2 专属 0 rows) 零错误 | ✅ |
| 全量 (含 peer) SR | dsv4f0731_nv 98.0% (144/147), 3 bad 全为 hermes | ✅ peer 归属 |
| fallback 触发率 | 0% (全走 primary) | ✅ |
| per-key tier 错误 | 基本全 pexec_success; 仅 k3 2× RD 一次性 transient | ✅ 零持续 tier 错误 |
| buffer | 全 attempt-1 直 flush; 仅 1× execute_failed (k5) 5s backoff attempt-2 自愈, 零级联 | ✅ 自愈 |
| container /health | nv_gw 200, cc4101 200 (Up 19h/19h) | ✅ |

## 下一步

- 延续 NOP。cc2 主链连续多轮 100% SR + zero fallback (R1093-R1100 镜像, 本轮 R1100 同样),
  无参数可调。
- **k3 RD 2× (R1099 1× → 本轮 2×)**: 轻微上升但为一次性 distributed transient, 单请求自愈
  (buffer 铁证), 不构成多 key 连续复发。仅当 k3 RD 在多 key **连续复发** (多个独立请求在多 key
  持续失败) 才查 k3 mihomo 7896 线路。
- **hermes 3× zombie_empty_completion** (dsv4f0731_nv 线) 持续关注, 归属 peer 非 cc2 不改动。
- 若 zombie_empty_completion 中出现 caller=cc4101-primary 才进 cc2 指标。

## 参数快照 (未动, 同 R1099)
- 本轮零改动。见 R1099 参数快照。
- nv_gw env 复核 (R1098): NV_GLM52_MODE_CHAIN=pexec_us_rr, KEY_MODE_BINDING= 空,
  KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0。