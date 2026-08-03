# R1005: HM2→HM1 — KEY_COOLDOWN_S 15→25 (reduce 429 cascade on glm5_2_nv)

**Date**: 2026-08-03
**Host**: HM1 (opc_uname @ 100.109.153.83)
**Container**: nv_gw (port 40006)
**Commit**: (this commit)

## 1. 触发

HM1 提交了新 commit `dc54758` (R-dsv4p-key3-integrate) 到 GitHub。检测脚本判定轮到 HM2 执行优化。

## 2. 改前数据 (2026-08-03 23:17 CST, 3h window)

### 2.1 概览

| 窗口 | 总 | 成功 | 错误 | SR |
|------|-----|------|------|------|
| 3h | 24 | 12 | 12 | 50.0% |

### 2.2 per-model per-status

| model | status | cnt | avg_ms | max_ms | min_ms |
|-------|--------|-----|--------|--------|--------|
| glm5_2_nv | 200 | 7 | 29,746 | 65,809 | 15,180 |
| glm5_2_nv | 502 | 11 | 21,394 | 80,119 | 8 |
| dsv4p_nv | 200 | 5 | 37,358 | 66,059 | 15,462 |
| dsv4p_nv | 502 | 1 | 103,231 | 103,231 | 103,231 |

→ glm5_2_nv SR=39% (7/18), dsv4p_nv SR=83% (5/6). glm5_2_nv 是主要问题。

### 2.3 nv_tier_attempts (3h, 5 rows)

| tier | key_idx | error_type | elapsed_ms |
|------|---------|------------|------------|
| glm5_2_nv | k1 | NVCFPexecSSLEEOFError | 5,004 |
| glm5_2_nv | k2 | NVCFPexecTimeout | 36,316 |
| glm5_2_nv | k2 | 429_nv_rate_limit | — |
| dsv4p_nv | k3 | NVCFPexecSSLEEOFError | 13,415 |
| dsv4p_nv | k4 | NVCFPexecRemoteDisconnected | 42,578 |

→ 429_nv_rate_limit on k2 + SSLEOF(2) + PexecTimeout(1) + RemoteDisconnected(1).

### 2.4 nv_gw 日志关键错误 (最近100行)

```
[22:33:24] [NV-COOLDOWN] tier=glm5_2_nv k2 marked cooling after 429
[22:33:24] [NV-CYCLE] tier=glm5_2_nv k2 → 429 (429_nv_rate_limit), cycling to next key
[22:33:28] [NV-COOLDOWN] tier=glm5_2_nv k3 marked cooling after 429
[22:34:05] [NV-TIMEOUT] tier=glm5_2_nv k5 NVCF pexec timeout: attempt=35741ms total=44098ms
[22:34:41] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=2, timeout=2, other=1, elapsed=80112ms
[22:34:41] [NV-ALL-TIERS-FAIL] ABORT-NO-FALLBACK
[22:34:41] [NV-BIGINPUT-FAIL] big_input breaker OPEN for glm5_2_nv (state=OPEN,7,179)
[23:04:34] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=1, timeout=2, elapsed=72798ms
[23:04:34] [NV-BIGINPUT-FB-OPEN] big_input breaker OPEN (state=OPEN,7,179)
```

→ 429 cascade pattern: k2 429 → k3 429 → k4 conn_error → k5 timeout → k1 timeout → fastbreak → tier fail.
   big_input breaker stays OPEN, cascading immediate 502s for subsequent requests.

### 2.5 cc4101 日志 (caller side)

```
[16:52:53] [PRIMARY-FAIL] primary (glm5_2_nv) server_5xx status=502 after 46232ms
[16:53:58] [PRIMARY-FAIL] primary (glm5_2_nv) timeout status=0 after 60035ms
[17:05:31] [PRIMARY-BREAKER-OPEN] primary circuit OPEN -> fast-fail 503
[22:55:50] [ZOMBIE-CONTENT-FILTER] (cc-glm5-2) upstream sent finish_reason=content_filter
[22:55:50] [ERR] zombie empty stream — emitting api_error SSE so CC retries
```

→ cc4101 sees primary 502/timeout, breaker opens, zombie content_filter events.

### 2.6 HM1 nv_gw 配置 (改前)

```
UPSTREAM_TIMEOUT=34
KEY_COOLDOWN_S=15           ← 本次修改目标
TIER_COOLDOWN_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_EMPTY_200_FASTBREAK=2
NVU_TIER_BUDGET_GLM5_2_NV=300
NVU_TIER_BUDGET_DSV4P_NV=120
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=7
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=375000
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,...
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv
```

## 3. 根因分析

**问题**: glm5_2_nv 429 rate-limit cascade across keys.

**机制**:
1. NVCF 对单个 key 429 rate-limit 后, 限流窗口通常 60s+
2. KEY_COOLDOWN_S=15 时, 429 key 仅冷却 15s 就重新进入轮转
3. 轮转到该 key 时再次 429 (NVCF 限流仍在生效)
4. 5 个 key 中 2-3 个被 429 → 剩余 key 超时 (35s+) → fastbreak 触发 → tier fail
5. 整个 tier fail 耗时 72-80s, 大输入请求触发 big_input breaker OPEN
6. breaker OPEN 后后续请求立即 502 (8-11ms), 持续 180s

**R2418 历史**: KEY_COOLDOWN_S 10→15 时已识别此 cascade 模式, 注释明确写道 "15s sweet spot" 但当前数据显示 15s 仍不够.

**R1004 precedent**: KEY_COOLDOWN_S=25 在 R1004 窗口 10h+ 稳定运行, 所有 tier 零错误.

## 4. 修改

`/opt/cc-infra/docker-compose.yml` nv_gw service:

```
- KEY_COOLDOWN_S=25  # R1005 (HM2->HM1): 15->25
```

**预期效果**:
- 429 key 冷却 25s (vs 15s), 给 NVCF rate-limit 1.67x 更长时间清除
- 减少 429 cascade 概率: key 轮转时更可能已解除限流
- 减少 tier fail 耗时 (从 72-80s 降低, 因更少 key 被 429 浪费)
- 间接减少 big_input breaker OPEN 频率

**风险**: 极低. R1004 已验证 25s 稳定. 25s 仍在 5-key×25s=125s < TIER_BUDGET=300s 范围内.

## 5. 部署验证

```
docker compose up -d nv_gw
→ Container nv_gw Recreated, Started, Up (healthy)

curl http://localhost:40006/health
→ {"status": "ok", "nv_num_keys": 5, ...}

docker exec nv_gw env | grep KEY_COOLDOWN_S
→ KEY_COOLDOWN_S=25  ✓
```

Startup logs clean, RR counters restored, no errors.

## 6. 不改 HM2

HM2 (本机 opc2_uname) 配置未触碰. 铁律遵守.

## ⏳ 轮到HM1优化HM2
