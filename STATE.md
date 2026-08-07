# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1100 (NOP 巡检轮/不改码 — cc2 主链 100/100=100.0% SR 零错误 (cc4101-primary 经 nv_gw, primary model=dsv4f0731_nv); 全量 dsv4f0731_nv 98.0% fallback 0%; 3× zombie_empty_completion 全部归属 hermes (dsv4f0731_nv 线, peer) 非 cc2, JOIN 复核 caller=hermes 专属; per-key 基本全 pexec_success 仅 k3 2× RD 一次性 transient; buffer 全 attempt-1 直flush 仅 1× execute_failed (k5) 5s backoff attempt-2 自愈 零级联零 buffer_exhausted; 容器全 200)**
> cc4101-primary (主 nv_gw:40006) 实测 30min = **100/100 = 100.0% SR, 0 bad** (cc2 专属零错误)
> — **零 502, 零错误(cc2), 零 fallback, 无任何新签名(cc2 范围)**
> 全量 (含 peer) dsv4f0731_nv SR = 98.0% (144/147), 3 bad 全为 hermes 归属
> 3× 502 zombie_empty_completion — caller=**hermes** (peer), tier=dsv4f0731_nv → 归属 peer 非 cc2 主链 (JOIN 铁证, caller|status=hermes|502|3)
> tier 错误: 30min 5 key 基本全 pexec_success (0/1/2/3/4=19/22/14/24/21), 仅 k3 2× RD 一次性 transient (上轮 1×, 总量 24 success 杂音小)
> buffer: 基本全 attempt-1 直 flush 秒回 (1-9s); 仅 1× req=2e019d25 attempt-1 execute_failed (k5) 5s backoff attempt-2 成功 47.6s 自愈, 零级联零 buffer_exhausted
> 容器 (/health 2026-08-07 22:23 CST): nv_gw 200 (passthrough, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, default=glm5_2_nv), cc4101 200 (primary=dsv4f0731_nv); docker ps nv_gw Up 19h, cc4101 Up 19h
> 上轮: R1099 (NOP, 100/100=100% SR 零错误)

## 本轮 (R1100) 改动 + 依据 + 验证

### 改动: 无 (NOP。30min cc2 主链 100/100=100.0% SR 零错误零 fallback, buffer 基本全 attempt-1 直 flush
### 秒回, 仅 1× execute_failed (k5) 5s backoff attempt-2 自愈。唯一 3× zombie_empty_completion 全部
### 归属 hermes (peer caller, dsv4f0731_nv 线), JOIN 复核 caller=hermes 专属。非 cc2 之作。
### cc2 范围无新签名 → 不改码)

### 依据 (实测 DB 2026-08-07 22:23 CST + 实时复核 + /health)

- **30min nv_requests (cc4101-primary)**: status 仅 200 × **100** = 100.0% SR, 0 错误。
- **30min 全量非-200 归属**: 唯一 3× zombie_empty_completion (status=502) 全部 caller=**hermes**
  (dsv4f0731_nv 线, peer)。本轮实时查询 `caller|status|count` = `hermes|502|3` (cc4101-primary 0)
  —— JOIN 归属铁证 (记忆 bad-fid-52e1ddb6 判归属法)。
- **fallback**: 0% (147 全走 primary, 无 fallback_triggered)。
- **nv_tier_attempts 30min**: 5 key 基本全 `pexec_success` (0/1/2/3/4=19/22/14/24/21); 仅 k3 2×
  `NVCFPexecRemoteDisconnected` 一次性 transient (上轮 1× → 本轮 2×, 但总量 success 24 杂音小,
  单请求 buffer 自愈)。无持续 tier 错误, 无 buffer_exhausted。
- **buffer 日志**: 基本全 attempt-1 直 flush 秒回 (1-9s)。唯一 req=2e019d25: attempt-1 execute_failed
  (key=k5), 5s backoff, attempt-2 成功 200 (elapsed=47.6s) 自愈。零级联零 buffer_exhausted
  (SSLEOFError 无复发)。
- **容器 /health 2026-08-07 22:23 CST**: 40006 nv_gw http 200 (passthrough, nv_num_keys=5,
  nvcf_pexec_models 含 dsv4f0731_nv, default=glm5_2_nv), 4101 cc4101 http 200 (primary=dsv4f0731_nv)。
  docker ps: nv_gw Up 19h, cc4101 Up 19h。

### 本轮数据

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
- 延续 NOP。cc2 主链连续多轮 100% SR + zero fallback (R1093-R1100 镜像, 本轮 R1100 同样), 无参数可调。
- **k3 RD 2× (R1099 1× → 本轮 2×)**: 轻微上升但为一次性 distributed transient, 单请求 buffer 自愈
  (铁证 req=2e019d25), 不构成多 key 连续复发。仅当 k3 RD 在多 key **连续复发** (多个独立请求多 key
  持续失败) 才查 k3 mihomo 7896 线路。
- **hermes 3× zombie_empty_completion** (dsv4f0731_nv 线) 持续关注, 归属 peer 非 cc2 不改动。
- 若 zombie_empty_completion 中出现 caller=cc4101-primary (c.parent) 才进 cc2 指标。

## 参数快照 (未动, 同 R1099)
- 本轮零改动。见 R1099 参数快照。
- nv_gw env 复核: NV_GLM52_MODE_CHAIN=pexec_us_rr, KEY_MODE_BINDING= 空, KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0。