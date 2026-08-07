# R1118 cc2 NOP — 2026-08-07 (HM2 nv_gw 自优化)

## 结论: NOP 巡检轮 (不改码)

30min cc2 主链 **105/105 = 100.0% SR 零错误** (cc4101-primary 经 nv_gw 40006, primary model=dsv4f0731_nv);
fallback 0% (104 total, fb=0); cc2 范围错误分类 (无错误); 唯一 1× 502 zombie_empty_completion
归属 **hermes** (bad fid 52e1ddb6, k1, dur 2001ms), 非 cc2; per-key 全 pexec_success 为主 (fid 281478d0),
仅 fid 52e1ddb6 的 k1 1× RD + k1 1× empty_200 + k4 1× empty_200 一次性 distributed transient
(单请求 buffer 自愈, 无 multi-key 连续复发); buffer 全 attempt-1 direct flush; 容器全 200。

## 依据 (实时 DB/health 复核 2026-08-08 00:0x CST)

- **30min nv_requests (cc4101-primary)**: status 仅 200 × **105** = 100.0% SR, 0 错误。
  (cc2 专属零错误, 连续多轮 R1096-R1118 保持)。
- **dsv4f0731_nv 全量 SR**: 151/152 = **99.3%**。唯一流失为 502 zombie_empty_completion (归属 hermes)。
- **30min 全量非-200 归属 (实时 DB 复核)**: 唯一 1 行 `caller=hermes, function_id=52e1ddb6, nv_key_idx=1,
  status=502, error_type=zombie_empty_completion, duration_ms=2001 → 归属 hermes 非 cc2`
  (历史记忆: zombie_empty_completion/502 归属 hermes/dsv4f0731_nv 线, 泄漏源=越界容器 40666, 宿主分离)。
  **cc4101-primary 无任何非-200。**
- **fallback**: 0% (104 total, fallback_triggered=0, 全走 primary)。
- **nv_tier_attempts 30min**: tier=dsv4f0731_nv, 全 `pexec_success` 为主 (fid 281478d0: k0=22 k1=19 k2=18
  k3=22 k4=23)；仅 fid **52e1ddb6** (历史记忆坏 fid) 的 k1 1× `NVCFPexecRemoteDisconnected`
  + k1 1× `empty_200` + k4 1× `empty_200` 一次性 distributed transient 单请求 buffer 自愈。
  量 (总 3x) 单请求一次性, 无 multi-key 连续复发, 非配置漂移。
  (注: 上轮 k4 是 1× RD, 本轮 k4 转为 1× empty_200 — 同 fid 52e1ddb6 泄漏线上的分布式 transient,
  单请求, 无级联, 非 cc2 性能问题。)
- **buffer 日志**: 全 `attempt=1` direct flush, 无重试无级联无 buffer_exhausted、无 WAIT (同 R1117 基线)。
- **容器 /health 2026-08-08 00:0x CST**: 40006 nv_gw http 200 (Up 20h, primary=dsv4f0731_nv, 5 key),
  4101 cc4101 http 200 (Up 20h)。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **105/105 = 100.0% SR, 0 bad** | ✅ 全绿 |
| cc2 专属错误分类 | (无错误) 零错误 | ✅ |
| 非-200 归属 | 唯一 1 行 zombie_empty_completion 归属 **hermes** (fid 52e1ddb6, k1, 2s) 非 cc2 | ✅ |
| fallback 触发率 | 0% (104 total, fb=0, 全走 primary) | ✅ |
| per-key tier 错误 | 全 pexec_success (fid 281478d0); 仅 fid 52e1ddb6 的 k1 1× RD + k1 1× empty_200 + k4 1× empty_200 一次性 transient 单请求自愈, 无 multi-key 连续复发 | ✅ |
| buffer | 全 attempt-1 direct flush, 无重试无级联无 buffer_exhausted | ✅ |
| container /health | nv_gw 200 (Up 20h), cc4101 200 (Up 20h) | ✅ |

## 下一步
- 延续 NOP。cc2 主链连续多轮 (R1096-R1118) 100% SR + zero fallback, 无参数可调。
- **k1/k4 错误** (fid 52e1ddb6): 量小 (总 3x, 均单请求: k1 1× RD + k1 1× empty_200 + k4 1× empty_200),
  一次性 distributed transient, 单请求 buffer 自愈, 与历史记忆模式一致 (泄漏源=越界容器 40666
  hermes 线, 宿主分离)。k4 本轮转 empty_200 (上轮 RD) 仍单请求无级联, 不构成配置漂移。
  仅当 RD/error 在多 key **连续复发** (多个独立请求多 key 持续失败) 才查链路/mihomo 线路。
- **唯一 502 (bad fid 52e1ddb6 zombie_empty_completion, caller=hermes, dur 2s)**: 非 cc2 范围,
  历史记忆归属模式, 单请求 transient, 不处置。
- 若 zombie_empty_completion 或其他错误中出现 caller=cc4101-primary (c.parent) 才进 cc2 指标并处置。