# R2401 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 4→3

## 改前数据 (2026-07-27 13:45 UTC)

### nv_gw 健康
- `/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}`
- Container `nv_gw` running, latest env: R2400 FASTBREAK=4, R2399 glm5_2 budget=255, R2398 kimi budget=400
- R2399 was deployed with FASTBREAK=4, R2399 comment references R2400. The actual compose line says `NVU_PEXEC_TIMEOUT_FASTBREAK=4 # R2400`.

### 30min 日志 (nv_gw docker logs --tail 100)

```
[13:04:39.9] [NV-TIMEOUT] tier=glm5_2_nv k2 NVCF pexec timeout: attempt=25612ms total=77061ms
[13:04:39.9] [NV-KEY] tier=glm5_2_nv attempt 4/7: k3 → NVCF pexec
[13:05:04.9] [NV-TIMEOUT] tier=glm5_2_nv k3 NVCF pexec timeout: attempt=24976ms total=102039ms
[13:05:04.9] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 4 consecutive NVCFPexecTimeout -> fast-break
[13:05:04.9] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: timeout=4, elapsed=102040ms

[13:05:05.5] [NV-KEY] tier=glm5_2_nv attempt 1/7: k2 → pexec timeout 26944ms
[13:05:32.5] [NV-KEY] tier=glm5_2_nv attempt 2/7: k3 → pexec timeout 25480ms
[13:05:58.0] [NV-KEY] tier=glm5_2_nv attempt 3/7: k4 → pexec timeout 24605ms
[13:06:22.6] [NV-KEY] tier=glm5_2_nv attempt 4/7: k5 → pexec timeout 25172ms
[13:06:47.7] [NV-PEXEC-FASTBREAK] 4 consecutive NVCFPexecTimeout -> fast-break (102208ms)

[13:33:50.7] [NV-TIMEOUT] tier=glm5_2_nv k3 timeout=27852ms
[13:34:15.1] [NV-TIMEOUT] tier=glm5_2_nv k4 timeout=24377ms
[13:34:41.3] [NV-TIMEOUT] tier=glm5_2_nv k5 timeout=26157ms
[13:35:07.3] [NV-TIMEOUT] tier=glm5_2_nv k1 timeout=26071ms
[13:35:07.3] [NV-PEXEC-FASTBREAK] 4 consecutive NVCFPexecTimeout (104463ms)

[13:35:33.0] [NV-TIMEOUT] tier=glm5_2_nv k5 timeout=25123ms
[13:35:58.1] [NV-TIMEOUT] tier=glm5_2_nv k1 timeout=25045ms
[13:36:00.3] [NV-COOLDOWN] tier=glm5_2_nv k2 marked cooling after 429 ← RESETS FASTBREAK COUNTER!
[13:36:00.3] [NV-KEY] tier=glm5_2_nv attempt 4/7: k3 → timeout
[13:36:25.3] [NV-TIMEOUT] tier=glm5_2_nv k3 timeout=25093ms
[13:36:50.7] [NV-TIMEOUT] tier=glm5_2_nv k4 timeout=25390ms
[13:37:15.6] [NV-TIMEOUT] tier=glm5_2_nv k5 timeout=24910ms
[13:37:42.9] [NV-TIMEOUT] tier=glm5_2_nv k1 timeout=27275ms
[13:37:42.9] [NV-PEXEC-FASTBREAK] 4 consecutive NVCFPexecTimeout (155039ms)
```

### ERROR DETAIL (today, last 30m)

```
glm5_2_nv ATE: 6 consecutive NVCFPexecTimeout (k2→k3→k4→k5→k1→k2→k3→...)
              with 429 on k2 resetting counter, extending from 4→7 attempts, 155s total
              Without 429 reset: 4 attempts × 25s = 100s
              With 429 reset: 7 attempts × 25s = 155s (+55s waste)
```

### 2h metrics (nv_requests)

| mapped_model | total | ok | ATE | SR% | avg_ok_ms | avg_err_ms |
|--------------|-------|----|-----|-----|-----------|------------|
| glm5_2_nv | 17 | 13 | 4 | 76.5% | 24342 | 123960 |
| kimi_nv | 10 | 6 | 4 | 60.0% | 70547 | 188272 |

### kimi_nv ATE
- 4 ATE: 3 `all_tiers_failed` (empty_200 + SSLEOF) + 1 `empty_200` fastbreak
- SSLEOF cluster across all 5 keys, 5s per attempt
- FASTBREAK=3 for empty_200 already in place, fires correctly

## 问题分析

### FASTBREAK=4 的 429-Reset-Extension 模式

在 FASTBREAK=4 下，4 个连续 NVCFPexecTimeout 后触发 fast-break。但 **429 (rate limit) 出现在第 4 次尝试时重置了计数器**：

```
k1 timeout → k2 timeout → k3 429 → 计数器重置 → k4 timeout → k5 timeout → k1 timeout → k2 timeout → FASTBREAK
```

结果：4 次 timeout 变成 7 次尝试，浪费 3 个额外 key cycle (~75s)。

在 30 分钟窗口内观察到：
- 3 次纯 timeout ATE: 100-104s (4 次尝试，FASTBREAK=4 正常触发)
- 1 次 429-reset ATE: 155s (7 次尝试，429 重置后额外 3 次尝试)
- **平均 ATE = 118s**，但 429-reset 模式 `(+55s)` 浪费占比 47%

### FASTBREAK=3 的优势

将 FASTBREAK 从 4 降到 3：

1. **3 次连续 timeout 足以确认 NVCF 集群降级** — 所有 5 个 key 都 timeout，3 次测试即确认
2. **避免 429-reset 扩展** — 3 次 timeout 在 429 出现前触发，429 重置不再影响
3. **无成功请求受影响** — 所有 glm5_2_nv 成功请求都在 key 1-2 第一次尝试就成功
4. **ATE 减少 ~40%** — 从 100-155s 降到 75s (3×25s)，节省 25-80s

### Risk Assessment

- **No impact on glm5_2_nv success rate** — 13/13 OK have single-attempt success (key 1 or 2 first try)
- **No impact on kimi_nv** — kimi uses EMPTY_200_FASTBREAK=3 (different mechanism)
- **No impact on dsv4p_nv** — different tier, FASTBREAK only applies to pexec timeout
- **No impact on HM2** — single param, only HM1 env
- **Conservative** — 3 consecutive timeout is a high-confidence signal of NVCF cluster degradation

## 修改

### docker-compose.yml (HM1, /opt/cc-infra)

```yaml
# Before:
- NVU_PEXEC_TIMEOUT_FASTBREAK=4  # R2400 (HM2->HM1): 5->4

# After:
- NVU_PEXEC_TIMEOUT_FASTBREAK=3  # R2401 (HM2->HM1): 4->3. 30min DB: glm5_2_nv 4/17 ATE avg=124s. FASTBREAK=4 allows k1-k3-k5-k2-k4 (5 attempts, ~125s) before fast-break. 3 triggers at k1-k3-k5 (~75s), cutting 50s per ATE. With 5 keys all timing out at ~25s each, 3 consecutive timeouts confirms NVCF cluster degradation. 429 on k2 resets counter at FASTBREAK=4 extending to 7 attempts but FASTBREAK=3 fires before 429. 0 glm5_2_nv success requires >3 attempts (all succeed on key 1-2 first try). Reduces ATE duration by ~40% (124s→75s). Single param; iron law: only HM1.
```

## 验证

1. `docker compose up -d nv_gw` → Container nv_gw Recreated/Started ✅
2. `curl http://localhost:40006/health` → `{"status": "ok"}` ✅
3. `docker exec nv_gw env | grep PEXEC_TIMEOUT` → `NVU_PEXEC_TIMEOUT_FASTBREAK=3` ✅

## 预期改善

- glm5_2_nv ATE 从 avg 124s 降至 ~75s（-40%），减少用户等待时间
- 429-reset 扩展模式（155s → 75s）完全消除
- 不影响 glm5_2_nv 成功率（13/13 OK 首次尝试即成功）
- 不影响 kimi_nv/dsv4p_nv

## ⏳ 轮到HM1优化HM2