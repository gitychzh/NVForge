# R2049 — HM2 优化 HM1

**轮次**: R2049 (HM2→HM1)
**时间**: 2026-07-20 14:30 UTC
**角色**: HM2 (opc2_uname) 优化 HM1 (opc_uname@100.109.153.83)
**前轮**: R2048 (cc2 NOP), R2046 (oc2 NOP), R2045 (oc2 NOP)
**铁律**: 只改HM1配置，绝不改HM2本地

## 数据采集

### DB 最近10条请求 (hermes_logs.nv_requests)
| ts | model | status | duration_ms | error_type |
|---|---|---|---|---|
| 06:03:28 | glm5_2_nv | 502 | 8347 | zombie_empty_completion |
| 06:03:20 | glm5_2_nv | 200 | 7893 | — |
| 05:37:49 | dsv4p_nv | 200 | 5836 | all_tiers_exhausted (phantom ATE, status=200) |
| 05:37:35 | dsv4p_nv | 200 | 14052 | all_tiers_exhausted (phantom ATE, status=200) |
| 05:33:29 | glm5_2_nv | 502 | 40047 | all_tiers_exhausted |
| 05:33:20 | glm5_2_nv | 200 | 8281 | — |
| 05:03:44 | glm5_2_nv | 200 | 3629 | — |
| 05:03:35 | glm5_2_nv | 200 | 8535 | — |
| 05:03:20 | glm5_2_nv | 200 | 14278 | — |
| 04:33:26 | glm5_2_nv | 200 | 12318 | all_tiers_exhausted (phantom ATE, status=200) |

### 6h 统计 (29 requests total, very low traffic)
- **SR**: 24 OK / 5 fail = 82.8% (small sample, 29 req/6h = 4.8 req/h)
- **Error breakdown**: 4 zombie_empty_completion (all glm5_2_nv, avg 6043ms), 1 all_tiers_exhausted (glm5_2_nv, 40047ms)
- **429 cycling**: 25 total_429s across 22 requests (all glm5_2_nv)
- **Fallback**: 0 fallback occurred in 6h (all direct pexec)
- **Latency (OK only)**: dsv4p_nv avg 9944ms (2 reqs), glm5_2_nv avg 9723ms (22 reqs)
- **Phantom ATE**: 3 ATE with status=200 (no real harm)

### Docker logs (nv_gw, last 100)
- Container at 05:57 restart (docker daemon level)
- 06:03 zombie (186K chars, content=41 < 50, 8.3s) — BIGINPUT breaker was reset on restart, first zombie passed through
- No runtime error/warn in logs (clean)

### Live env (R2045/R2048 state before this round)
- NVU_BIG_INPUT_THRESHOLD=100000, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=10800
- KEY_COOLDOWN_S=0, TIER_COOLDOWN_S=0
- UPSTREAM_TIMEOUT=25, TIER_TIMEOUT_BUDGET_S=153
- NVU_EMPTY_200_FASTBREAK=1, NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=15, NVU_STREAM_TOTAL_DEADLINE_S=25

## 分析

1. **Zombie**: 4 zombies/6h 全部 glm5_2_nv，全部 >100K chars。BIGINPUT breaker (FAIL_N=1, COOLDOWN=10800=3h) 在容器重启后重置，第一个 zombie 穿过 breaker (06:03)，然后 breaker 打开。但 3h cooldown 意味着 breaker 一旦打开就持续 3h，期间所有 big-input 请求都被拦截→导致 ATE。3h 对于 ~5 req/h 的流量来说过长。

2. **ATE**: 1 real ATE (glm5_2_nv, 40047ms) + 3 phantom ATE (status=200, no real harm)。Low traffic, low risk.

3. **429 cycling**: 25/29 reqs on glm5_2_nv in 6h — KEY_COOLDOWN_S=0 导致 key 轮转无延迟，429s 全部安全处理无实际伤害。

4. **BREAKER COOLDOWN PROBLEM**: 3h 过长。1h cooldown 足以捕获 zombie 集群（通常在几分钟内发生），同时允许 breaker 在安静期重置，让合法大输入请求能及时通过。risk: low traffic (4.8 req/h), 5 keys, no exhaustion risk.

5. **NOP 冻结评估**: R2045/R2046/R2048 连续 3+ 轮 NOP 巡检，冻结理由成立 for those rounds。但本次发现 BIGINPUT COOLDOWN 优化空间 — 从 3h→1h，不影响 breaker 保护能力，仅缩短恢复窗口。

## 变更

**单参数**: `NVU_BIG_INPUT_COOLDOWN_S` 10800→3600 (3h→1h)

```diff
- NVU_BIG_INPUT_COOLDOWN_S: "10800"  # R1997 (HM2->HM1): ...
+ NVU_BIG_INPUT_COOLDOWN_S: "3600"   # R2049 (HM2->HM1): 10800->3600 (3h->1h)
```

**理由**: 3h cooldown 对 4.8 req/h 低流量过度 — breaker 一旦打开持续 3h 阻塞所有大输入。1h 仍能捕获 zombie 集群（数分钟内），但允许 breaker 在安静期重置，合法大输入请求及时通过。5 keys 5 req/h 无 key 耗尽风险。

**重启**: nv_gw container recreated (docker compose up -d nv_gw)

## 验证

- Live env 确认: `docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S` → `3600` ✓
- 预期: zombie 通过率不变（FAIL_N=1 仍在），但 breaker 恢复快，ATE 不应因 breaker 阻塞产生
- 30min/6h SR 应在稳态区间 (~82-95%)，受低流量小样本波动
- ⚠️ 低流量 (29req/6h) 预示后续回合 SR 统计需大窗口确认

## ⏳ 轮到HM1优化HM2
