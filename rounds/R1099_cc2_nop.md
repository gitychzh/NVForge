# R1099 — cc2 NOP 巡检轮 (HM2 nv_gw 自优化)

时间: 2026-08-07 22:17 CST (轮前链路分析注入)
上轮: R1098 (NOP, cc2 主链 97/97=100% SR 零错误)

## 结论: NOP, 不改码

30min cc2 主链 100/100=100.0% SR, 零错误, 零 fallback, buffer 无重试直 flush, 无任何新签名
(cc2 范围)。唯一 3× zombie_empty_completion 全部归属 peer hermes, 非 cc2 之作。

## 依据 (实测 DB 2026-08-07 22:17 CST + /health)

- **30min nv_requests (cc4101-primary)**: status 仅 200 × **100** = 100.0% SR, 0 错误
  (injected import + 实时 10min 复核 caller=cc4101-primary count=29 全 200)。
- **30min 全量非-200 归属**: 唯一 3× zombie_empty_completion (status=502) 全部 caller=**hermes**
  (dsv4f0731_nv 线, peer)。—— 本轮实时 JOIN 复核: `caller|count` = `hermes|3` (peer 专属,
  cc4101-primary 0)。不进 cc2 专属指标。
- **全量 SR**: dsv4f0731_nv 97.9% (137/140), 3 bad 全为 hermes 归属。
- **fallback**: 0% (140 全走 primary, 无 fallback_triggered)。
- **nv_tier_attempts 30min**: 5 key 基本全 `pexec_success` (0/1/2/3/4=19/19/16/25/21); 仅 k3 1×
  `RemoteDisconnected` + k4 1× `empty_200` 一次性 transient。无持续 tier 错误, 无 buffer_exhausted。
- **buffer 日志**: 30min 无 NV-BUFFER-EXEC-FAIL / WAIT- 等待日志 = cc4101-primary 请求全 attempt-1
  直 flush 秒回, 零重试零级联。
- **容器 /health 2026-08-07 22:17 CST**: 40006 nv_gw http 200 (passthrough, health OK),
  4101 cc4101 http 200 (primary=dsv4f0731_nv)。docker ps: nv_gw Up 19h, cc4101 Up 18h。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **100/100 = 100.0% SR, 0 bad** | ✅ 全绿 |
| cc2 专属错误分类 | (cc2 专属 0 rows) 零错误 | ✅ |
| 全量 (含 peer) SR | dsv4f0731_nv 97.9% (137/140), 3 bad 全为 hermes | ✅ peer 归属 |
| fallback 触发率 | 0% (全走 primary) | ✅ |
| per-key tier 错误 | 基本全 pexec_success; 仅 k3 1× RD + k4 1× empty_200 一次性 | ✅ transient |
| buffer | 无重试日志 = 全 attempt-1 直 flush 秒回, 零级联零 buffer_exhausted | ✅ |
| container /health | nv_gw 200, cc4101 200 (Up 19h/18h) | ✅ |

## 下一步

- 延续 NOP。cc2 主链连续多轮 100% SR + zero fallback (R1093-R1098 镜像, 本轮 R1099 同样),
  无参数可调。
- **hermes 3× zombie_empty_completion** (dsv4f0731_nv 线) 持续关注, 归属 peer 非 cc2 不改动。
- 若 zombie_empty_completion 中出现 caller=cc4101-primary 才进 cc2 指标; 若 k3 RD / SSLEOFError
  在多 key **连续复发** 才查相应 mihomo 线路 (记忆 ssleof-transient R1077: 单次 NOP 自愈,
  持续分布才动手)。本轮 k3/k4 各 1× 一次性不构成复发。

## 参数快照 (未动, 同 R1098)
- 本轮零改动。见 R1098 参数快照。
- nv_gw env 复核 (R1098): NV_GLM52_MODE_CHAIN=pexec_us_rr, KEY_MODE_BINDING= 空,
  KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0。