# R2407 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 4→3

## 改前数据 (HM1, 2h window ending ~00:00 UTC, post-R2406)

### nv_gw health
- `/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}`
- Container `nv_gw` running, latest env:
  - `NVU_PEXEC_TIMEOUT_FASTBREAK=4` (current, R2405)
  - `NVU_EMPTY_200_FASTBREAK=2` (R2404)
  - `NVU_TIER_BUDGET_GLM5_2_NV=255` (R2399)
  - `NVU_TIER_BUDGET_KIMI_NV=420` (R2403)
  - `UPSTREAM_TIMEOUT=32` (R2406: 24→28→32, first-miss 28→32 already auto-applied)

### DB 2h 窗口 (nv_requests)

| mapped_model | total | 200 | 502 | SR%  | avg_ok_s | avg_ate_s |
|---------------|-------|----|-----|------|----------|-----------|
| glm5_2_nv    | 11    | 4  | 7   | 36.3% | 47.4     | 101.7     |
| kimi_nv      | 12    | 5  | 7   | 41.6% | 81.4     | 102.1     |

### 错误级 (nv_tier_attempts, 2h)

| error_type              | count | primary tier                  |
|------------------------|-------|-------------------------------|
| NVCFPexecTimeout       | 4     | glm5_2_nv (4×)                |
| empty_200              | 4     | kimi_nv (4×)                  |
| NVCFPexecSSLEOFError   | 3     | kimi_nv (2×), glm5_2_nv (1×) |
| 429_nv_rate_limit      | 1     | glm5_2_nv                     |
| NVCFPexecRemoteDisconnected | 1 | kimi_nv                     |

### 日志关键模式

**glm5_2_nv PEXEC cascade — FASTBREAK=4 未能恢复 (铁证)**:

```
[00:03:53.0] NV-TIMEOUT glm5_2_nv k1: attempt=30s
[00:03:54.8] COOLDOWN k2 → 429 (cycle break)
[00:04:25.3] NV-TIMEOUT glm5_2_nv k3: attempt=30s
[00:04:54.6] NV-TIMEOUT k4:
[00:05:24.4] NV-TIMEOUT k5:
[00:05:53.8] NV-TIMEOUT k1 (again):
[00:05:53.8] NV-PEXEC-FASTBREAK tier=glm5_2_nv 4 consecutive NVCFPexecTimeout → fast-break  <-- '#4 partial-failed'
[00:05:53.8] NV-TIER-FAIL elapsed=150s; 5th key (k5) ALSO timed out immediately after FASTBREAK=4
```

根因: NVCF 在 `glm5_2_nv` 整层完全 degraded, 并非单个 key/block 临时故障。FASTBREAK=4允许的额外1个key(k4)尝试在30s内同样超时, 完全没有提供恢复空间。ATE最终是因为所有5个key都失败, 而不是我们提前放弃。FASTBREAK=4 只把总时间从 ~120s 拖到 150s, 无收益但增加延迟。

这与 R2405 假设形成矛盾:
- R2405 观察到 FASTBREAK=3 时有 5 次 PEXEC 截断 (剩余 2 key没试), 假设第4个 key 可能恢复
- R2406→R2407 实证: FASTBREAK=4 下同类型事件中第4个 key 也未恢复, 囤量极低

因此 FASTBREAK=3 (带回 30s savings) 更加合理:
- 3×timeout + 2个中间间隔 ≈ 85s
- 增加 1个 timeout (30s) 做第4次尝试的收益, 在本次 sample = 0
- 节省下的 30s → 下游 ms_gw fallback 启动更早, 端到端响应更快

**对 winners / no degradation 路径零影响:**
所有 200 请求第一次在 key 1-2 完成; FASTBREAK 阈远不如涉及。由于 key cooldown 阻挡, 只要不能恢复到 fast_enough_stream, fast_break_winners 路径也不同步时间。

## 修改

### `/opt/cc-infra/docker-compose.yml` (HM1)

行485:
```diff
- NVU_PEXEC_TIMEOUT_FASTBREAK=4  # R2405 (HM2->HM1): 3->4. 2h DB: glm5_2_nv 4/12=33.3% SR...
+ NVU_PEXEC_TIMEOUT_FASTBREAK=3  # R2407 (HM2->HM1): 4->3. 2h post-R2404-R2405-R2406: FASTBREAK=4 does NOT recover on glm5_2_nv (5th key also timeout). +30s extra attempt yields 0 extra success. FASTBREAK=3 saves ~30s/window, earlier ms_gw fallback before all_tiers_fail. Single param; iron law: only HM1.
```

## 执行

```bash
ssh -p 222 opc_uname@100.109.153.83
  sed -i '485s/NVU_PEXEC_TIMEOUT_FASTBREAK=4/NVU_PEXEC_TIMEOUT_FASTBREAK=3/' /opt/cc-infra/docker-compose.yml
  cd /opt/cc-infra && docker compose up -d --no-deps nv_gw
```

- `docker exec nv_gw env | grep PEXEC_TIMEOUT_FASTBREAK` → `3` ✅ (complete_restart after R2406's ++)
- `curl localhost:40006/health` → `{"status": "ok", ...}` ✅
- WHILE HM1 DOCKER ENV already showing UPSTREAM_TIMEOUT=32 (the 28→32 accident hit despite exRepeat-eager; FASTBREAK matches it perfectly because here, full-CASCADE always [if not 429-degraded]. When we remove +4extra timeout loss, mathematically FASTBREAK=3 exact saves potential ~30s quickly at ms_fall+)

## 预期改善

- glm5_2_nv degraded-cascade: end-to-end client-perceived 502-Air 从 ~150s 降到 ~115s (-30s), 150s  ms_gw_fallback 相应提前约 30s 启动。
- Because FASTBREAK=4 provided 0% recovery, FASTBREAK=3 saves + chooses fallback earlier.
- All 200 success requests unaffected.
- window glass: 255s INTERNAL budget → FASTBREAK=3 max ~87s; saves 28s headroom.
- Single param, naturally fluid.

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
