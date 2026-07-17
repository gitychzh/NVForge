# R1717: HM2→HM1 — UPSTREAM_TIMEOUT 66→60 (-6s)

## 数据 (HM1, 近6h, 2026-07-17 12:00–18:00 UTC)

```
70 req / 59 OK (84.3% SR) / 11 fail
9 zombie_empty_completion (glm5_2_nv, all >250K chars)
2 all_tiers_exhausted (dsv4p_nv, ~70s each)
0 BIG_INPUT breaker triggers (container restarted 18:04, fresh)
max_ok=51.8s, avg_ok=13.2s, p99_ok=49.5s
100% key_cycle_429s (glm5_2_nv only)
```

### 错误明细
```
error_type              | cnt | model
zombie_empty_completion |   9 | glm5_2_nv (all >250K: 295K-330K)
all_tiers_exhausted     |   2 | dsv4p_nv (both ~70s)
```

### dsv4p_nv ATE 详情
```
ts=18:07:19: k2 SSLEOF→k3 504 timeout(64s)→k4 fastbreak(6.6s)=70s total
ts=18:04:55: k3 504 timeout(64s)→k4 fastbreak(6.6s)=69s total
Both peer-fallback to HM2 → 502 after 70s → peer-fb wasted
```

### 僵尸甜点（间隔≈30分钟）
```
ts                  total_input_chars  duration_ms
17:33:33            323428              13773
17:05:03            330072               3038
16:06:52            314954               7647
15:03:30            307024              13434
14:33:30            304772               9919
14:04:23            299366               6270
13:35:37            303551               4927
13:03:31            295685               9551
12:33:31            295893               6628
```

### 容器状态
```
nv_gw started: 2026-07-17 18:04:52 (R1715 deploy)
BIG_INPUT breaker: FAIL_N=1, COOLDOWN=2400, THRESHOLD=250000
logs: 0 NV-BIGINPUT 日志 → breaker 从未触发过（容器重启后无新僵尸）
```

## 分析

R1716 将 BIG_INPUT_COOLDOWN 从 1800→2400 确保 breaker 覆盖僵尸30分钟 cadence，但僵尸间隔约30分钟意味着 breaker 触发后下一个僵尸仍需30分钟 — 在2400s cooldown 内，第二个僵尸会触发 re-arm。但本轮容器 18:04 重启，至今无僵尸命中 breaker（全在重启前）。

UPSTREAM_TIMEOUT=66 浪费了 dsv4p_nv ATE 路径上的时间：k3 在 64s 超时后 k4 仍在 6.6s fastbreak。max OK=51.8s，60s 给 8.2s 缓冲。

NVCFPexecTimeout 历史最大值 62.6s（R988），但当前数据 max OK=51.8s，且 FASTBREAK=1 确保 k3 在 60s 超时后直接 fastbreak 不再试 k4 → 节约 ~6s/ATE。

## 变更

**UPSTREAM_TIMEOUT: 66 → 60 (-6s, -9.1%)**

- max OK=51.8s, 60s 缓冲=8.2s ✓
- dsv4p_nv ATE: k3 在 60s (旧 64s) 超时 → fastbreak → 69s→63s, 省 6s/ATE
- BIG_INPUT breaker (FAIL_N=1, COOLDOWN=2400): 僵尸路径先触发 breaker → ATE → peer-fb, 不受 UPSTREAM 影响
- Budget: 60+125=185>150 capped → peer-fb 得 90s > 72s ✓
- 单参数, 铁律: 只改HM1不改HM2

## 验证

```
$ docker exec nv_gw env | grep UPSTREAM_TIMEOUT
UPSTREAM_TIMEOUT=60 ✓

$ curl -s http://localhost:40006/health
{"status": "ok", ...} ✓

$ docker exec nv_gw env | grep -E '^(NVU_|TIER_|KEY_|UPSTREAM_|MIN_OUTBOUND)' | sort
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_BIG_INPUT_COOLDOWN_S=2400 ✓
NVU_BIG_INPUT_FAIL_N=1 ✓
NVU_BIG_INPUT_MODELS=glm5_2_nv ✓
NVU_BIG_INPUT_THRESHOLD=250000 ✓
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=125
NVU_PEER_FB_SKIP_MODELS=
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_TIER_BUDGET_DSV4P_NV=70
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=60
TIER_TIMEOUT_BUDGET_S=150
UPSTREAM_TIMEOUT=60 ✓
```

无容器漂移, 所有参数与compose一致 ✓

## 预算检查

| 路径 | 耗时 | 预算 |
|---|---|---|
| OK (max) | 51.8s | << 150 ✓ |
| zombie→BIGINPUT→peer-fb | 0+125=125s | < 150 ✓ |
| dsv4p ATE→peer-fb | 60+125=185→cap 150 | peer-fb 得 90s > 72 ✓ |
## ⏳ 轮到HM1优化HM2
