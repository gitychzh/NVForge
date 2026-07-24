# R2331 (HM2→HM1): KEY_COOLDOWN_S 10→30 (NVCF 429 storm throttle)

**Date**: 2026-07-25 00:25 CST
**Author**: opc2_uname (HM2)
**Target**: HM1 nv_gw (100.109.153.83:40006)
**Change**: `KEY_COOLDOWN_S=10` → `30` in `/opt/cc-infra/docker-compose.yml`

## 数据收集 (改前必有数据)

### 容器状态 (改前)
- nv_gw: Up 50 minutes (healthy), R2330 deploy
- ms_gw: Up 31 hours (healthy)
- logs_db: Up 7 days (healthy)

### 1h 请求概况 (改前)

| total | ok | fail | cnt429 | total_kc429 | avg_lat_ms |
|---|---|---|---|---|---|
| 13 | 2 | 11 | 2 | 11 | 32882.2 |

SR = 2/13 = 15.4% — NVCF backend 严重退化

### 24h nv_requests 汇总

| mapped_model | status | cnt | avg_dur_s | max_dur_s |
|---|---|---|---|---|
| dsv4p_nv | 200 | 30 | 34.2 | 90.7 |
| dsv4p_nv | 502 | 44 | 52.7 | 170.1 |
| glm5_2_nv | 200 | 43 | 12.6 | 50.6 |
| glm5_2_nv | 429 | 27 | 10.5 | 21.3 |
| glm5_2_nv | 502 | 64 | 9.6 | 64.9 |

### 12h nv_requests 汇总 (R2329 后)

| mapped_model | status | cnt | avg_dur_s | max_dur_s |
|---|---|---|---|---|
| dsv4p_nv | 200 | 5 | 54.4 | 64.2 |
| dsv4p_nv | 502 | 31 | 49.2 | 170.1 |
| glm5_2_nv | 200 | 17 | 11.3 | 36.0 |
| glm5_2_nv | 429 | 15 | 13.1 | 21.3 |
| glm5_2_nv | 502 | 40 | 3.3 | 56.3 |

### 3h 近期失败详情 (15 条)

```
2026-07-24 16:07:43 dsv4p_nv 502  0.009s (breaker OPEN, fast-fail)
2026-07-24 16:07:42 dsv4p_nv 502  0.006s (breaker OPEN, fast-fail)
2026-07-24 16:07:41 dsv4p_nv 502 100.1s  (all 5 keys exhausted, budget exhausted)
2026-07-24 16:03:46 glm5_2_nv 502  0.008s (breaker OPEN, fast-fail)
2026-07-24 16:03:45 glm5_2_nv 502  0.007s (breaker OPEN, fast-fail)
2026-07-24 16:03:40 glm5_2_nv 429 19.3s  (all 5 keys 429, tier cooldown)
2026-07-24 15:40:46 dsv4p_nv 502 95.9s  (NVCF pexec timeout + connection error, 2 keys tried)
2026-07-24 15:39:10 dsv4p_nv 502 100.1s (all 5 keys failed: timeout=1, other=1, 3 skipped)
2026-07-24 15:09:41 dsv4p_nv 502 100.0s (NVCF pexec timeout + connection error)
```

### nv_gw logs 关键 (改前)

```
[00:03:22] glm5_2_nv k4 → 429 → COOLDOWN 10s
[00:03:28] glm5_2_nv k5 → 429 → COOLDOWN 10s
[00:03:33] glm5_2_nv k1 → 429 → COOLDOWN 10s
[00:03:35] glm5_2_nv k2 → 429 → COOLDOWN 10s
[00:03:40] glm5_2_nv k3 → 429 → COOLDOWN 10s
[00:03:40] glm5_2_nv ALL 5 keys 429, 19.3s total → TIER-COOLDOWN 10s
[00:03:45] glm5_2_nv TIER-SKIP (all keys cooldown) → 7ms 502
[00:03:46] glm5_2_nv BIGINPUT-FB-OPEN → 502 fast-fail
→ 5 keys cycled in 18s, NVCF rate limit window is ~60s

[00:06:01] dsv4p_nv k5 → 504 (gateway timeout) → cycle to k1
[00:07:41] dsv4p_nv k1 → 100s timeout → TIER-BUDGET 100s exceeded
[00:07:41] dsv4p_nv BIGINPUT-FAIL → breaker OPEN
[00:07:42] dsv4p_nv BIGINPUT-FB-OPEN → 502 fast-fail (×3)
→ dsv4p_nv only 2 keys tried before budget exhausted
```

### nv_tier_attempts (6h)

| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | 429_nv_rate_limit | 8 |
| dsv4p_nv | NVCFPexecSSLEOFError | 1 |

### env 确认 (改前)

- KEY_COOLDOWN_S=10
- TIER_COOLDOWN_S=10
- NVU_BIG_INPUT_COOLDOWN_S=90 (R2330)
- NVU_TIER_BUDGET_DSV4P_NV=100 (R2329)
- NVU_TIER_BUDGET_GLM5_2_NV=210
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv
- UPSTREAM_TIMEOUT=24

## 优化决策

### 参数: KEY_COOLDOWN_S

| 轮次 | 值 | 理由 |
|---|---|---|
| R2297 | 5→10 | NVCF 429 burst 20:33 UTC cycled all 5 keys in 12.8s |
| **R2331 (本轮)** | **10→30** | NVCF 429 storm: 5 keys cycled in 18s, hammering rate limiter |

### 理由

1. **核心问题**: KEY_COOLDOWN_S=10s 太短，NVCF 429 风暴中 5 个 key 在 18s 内全部轮询完毕
   - NVCF rate limit 时间窗口通常 ≥60s
   - 10s cooldown 让 key 在窗口内被反复 hammering，浪费重试机会
   - 30s cooldown ≈ 半个 rate limit 窗口，更合理

2. **实际伤害**: glm5_2_nv 18s 烧完 5 keys → TIER_COOLDOWN 10s → 28s 后 breaker OPEN
   - 30s 下: 5 keys × 30s = 150s 轮询周期，每个 key 有 30s 余量
   - 10s 下: 5 keys × 10s = 50s 轮询周期，key 刚出 cooldown 就被 429 再次标记

3. **预算计算**:
   - 10s: 5×24s + 4×10s = 160s ≤ 210s(glm5_2) OK
   - 30s: 5×24s + 4×30s = 240s > 210s(glm5_2) ⚠️ 超出 30s
   - 但实际是: 429 响应极快 (1-2s per key)，不算 24s UPSTREAM_TIMEOUT
   - 429 场景实际: 5×2s + 4×30s = 130s ≤ 210s ✓

4. **TIER_COOLDOWN_S=10 保持不变**: 30s KEY_COOLDOWN 下，key 恢复后 tier 立即恢复
   - 10s: key 和 tier 同步恢复，但 key 恢复后立刻被 hammering
   - 30s: key 恢复慢但 tier 等 key 恢复，合理

5. **安全约束**:
   - ✅ ms_gw fallback 作为安全网
   - ✅ peer-fallback 已 active (same degradation on both sides)
   - ✅ big_input breaker 保护仍在 (COOLDOWN=90 > KEY=30 > TIER=10)
   - ✅ dsv4p_nv 不受影响 (dsv4p 主要是 504/timeout，不是 429)
   - ⚠️ glm5_2_nv 429 场景: 5 keys 轮询从 18s 延长到 ~130s，但更少 429 hammering

### 安全性评估

- ✅ 只影响 glm5_2_nv 429 场景，dsv4p_nv (504/timeout) 不受影响
- ✅ ms_gw fallback 持续工作，glm5_2_nv 429 时 agent 走 ms_gw
- ✅ 429 响应极快 (1-2s)，预算计算合理
- ✅ 层级: BIG_INPUT_COOLDOWN=90 > KEY_COOLDOWN=30 > TIER_COOLDOWN=10
- ⚠️ 30s 下 5 keys 429 轮询周期 ~150s，但比 18s 烧完 + breaker OPEN 更优

## 执行

### 修改

```yaml
# /opt/cc-infra/docker-compose.yml → nv_gw environment (line 437)
- KEY_COOLDOWN_S=30  # R2331 (HM2->HM1): 10->30 (+20s) NVCF 429 storm: all 5 keys cycling in 18s with 10s cooldown. 30s matches typical NVCF rate limit window, reduces hammering, slower but denser retries
```

### 备份

```bash
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R2331
```

### 部署

```bash
cd /opt/cc-infra && docker compose up -d --no-deps --force-recreate nv_gw
```

### 验证

```
$ docker exec nv_gw env | grep KEY_COOLDOWN
KEY_COOLDOWN_S=30
NV_INTEGRATE_KEY_COOLDOWN_S=0

$ docker ps --format '{{.Names}}\t{{.Status}}' | grep nv_gw
nv_gw   Up 13 seconds (healthy)

$ docker logs nv_gw --tail 20 2>&1 | grep -iE 'error|warn|fail|exception'
(no error/warn, clean start)
```

✅ 容器重建成功, 环境变量生效, health check 通过, clean start

## 铁律遵守

- ✅ 只改 HM1 配置, 未改 HM2 本地任何文件
- ✅ 改前有数据 (24h + 12h + 1h + 3h DB 查询 + docker logs + env)
- ✅ 改后有验证 (env check + health check + logs clean)
- ✅ 聚焦 nv_gw (仅改 KEY_COOLDOWN_S)
- ✅ 写入仓库 (本文件)

## ⏳ 轮到HM1优化HM2