# R762: HM2 nv_gw 401/403 auth-failed → cycle next key (修复 k3 失效致整 request 502)

> 根因: k3 NVAPI key 失效返回 403 Forbidden, 命中 Non-cycling 分支直接 return,
> 放弃整 request (不 cycle k4/k5/k1/k2). 1 key 失效 = 整 502, peer-fb 兜底.
> 软件修复: 401/403 加入 should_cycle, cycle 到下一 key + 标 cooldown.

## 改前数据 (40min)

### 静默失败 5 次 (NV-ALL-TIERS-FAIL 768ms 内)
```
[01:33:05.0] [NV-KEY] tier=dsv4p_nv attempt 1/7: k3 → NVCF pexec 74f02205-c7b... DIRECT
[01:33:06.1] [NV-ALL-TIERS-FAIL] All 1 tiers failed, elapsed=1096ms, ABORT-NO-FALLBACK
```
中间无 NV-TIMEOUT/NV-CONN/NV-ERR/NV-CYCLE 日志, error_detail 里 tier_attempts 为空.
5 次 (01:33/01:34/01:45/01:47/01:49), peer-fb 救回 3 次, 2 次真 502 (含 01:36 peer-fb 90s timeout).

### 直接测 5 key pexec (确认根因)
```
k1: status=200 OK
k2: status=200 OK
k3: status=403 Forbidden "Authorization failed"  ← NVAPI key 失效
k4: status=200 OK
k5: status=200 OK
```

### 根因 (双重 bug)
1. k3 NVAPI key 失效 (403 Authorization failed) — 平台侧, 需换 key (CC 不可修)
2. nv_gw should_cycle = resp.status in (429, 408, 500, 502, 503, 504, 202) — 不含 401/403,
   命中 "Non-cycling error → report; return result" 直接放弃整 request, 不 cycle 其他 key.
   且该分支不打日志 (静默失败), 不 append key_cycle_attempts (tier_attempts 为空).

## 改动 (upstream.py, _try_pexec_keys + _try_integrate_keys)

| 改动 | 改前→改后 | 理由 |
|---|---|---|
| should_cycle 集合 | (429,408,500,502,503,504,202) → (401,403,429,408,500,502,503,504,202) | 401/403 是 per-key auth 失败, 非 request 问题, 应 cycle |
| cycle_reason | 加 401_nv_auth_failed/403_nv_auth_failed (pexec) / 401/403_integrate_auth_failed | 可追溯 |
| 401/403 cooldown | 无 → mark_key_cooling (default) | 避免反复试失效 key (浪费 ~1s/次) |
| Non-cycling 日志 | 静默 → NV-NONCYCLE-ERR / NV-INTEGRATE-NONCYCLE-ERR | 避免静默失败, 便于诊断 |

### 不改
- k3 NVAPI key 本身 (平台侧, 需用户换 key; 软件修复后 k3 被 cooldown 跳过, 影响隔离)
- nv_gw/ms_gw 其他逻辑 (模块化)
- HM1 (冻结)
- 41xx 适配器 (不受影响, nv_gw 不再 502 就不会触发 fallback)

## 改后验证

### 7 个 dsv4p 请求全 200 OK
```
req1: 200 10.2s, req2: 200 18.8s, req3: 200 1.8s, req4: 200 8.2s,
req5: 200 6.6s, req6: 200 16.0s, req7: 200 7.9s
```

### k3 被跳过 (日志确认)
```
[01:57:41.3] [NV-KEY] k3 attempt 1/7 → DIRECT
[01:57:42.0] [NV-AUTH-FAIL] k3 403 auth failed, marked cooling, cycling to next key
[01:57:42.0] [NV-CYCLE] k3 → 403 (403_nv_auth_failed), cycling to next key
[01:57:42.0] [NV-KEY] attempt 2/7: k4 → DIRECT
[01:57:43.1] [NV-SUCCESS] k4 succeeded after 1 cycle attempts
```
k3 cooldown 后 2min 内未再被 attempt.

### 502 数对比
- 改前 30min: 8 次 NV-ALL-TIERS-FAIL
- 改后 5min: 1 次 (改前残留请求), 之后 0

## 预期
- k3 失效不再致 502, 直接 cycle k4/k5 (省 ~1s, 不再 peer-fb 90s)
- dsv4p_nv SR 显著上升 (k3 路径从 502→200)
- 失效 key 自动 cooldown, 不浪费 budget

## 风险
- 低: 401/403 cycle 是 per-key 隔离, 不影响其他 key
- 回滚: upstream.py.bak.R762

## 遗留
- k3 NVAPI key 需用户更换 (平台侧, 软件修复已隔离其影响)
- ms_gw stream_no_data cycle (非阻塞, 下轮观察)
- HM1 同步待授权 (HM1 k3 可能也失效, 需同样修复)
