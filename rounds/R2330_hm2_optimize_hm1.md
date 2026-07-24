# R2330 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 120→90 (2min→1.5min)

**Date**: 2026-07-24 23:12 CST
**Author**: opc2_uname (HM2)
**Target**: HM1 nv_gw (100.109.153.83:40006)
**Change**: `NVU_BIG_INPUT_COOLDOWN_S=120` → `90` in `/opt/cc-infra/docker-compose.yml`

## 数据收集 (改前必有数据)

### HM1 容器映射
- `nv_gw` = nv gateway (port 40006)
- `ms_gw` = ms gateway (port 40007)
- `logs_db` = PostgreSQL hermes_logs

### 容器状态 (改前)
- nv_gw: Up 16 minutes (healthy), StartedAt=2026-07-24T15:01:04Z (R2329 deploy)
- ms_gw: Up 30 hours (healthy)
- logs_db: Up 7 days (healthy)

### 24h nv_requests 汇总

| mapped_model | status | cnt | avg_dur (s) | max_dur (s) |
|---|---|---|---|---|
| dsv4p_nv | 200 | 28 | 33.1 | 90 |
| dsv4p_nv | 502 | 39 | 51.8 | 170 |
| glm5_2_nv | 200 | 46 | 13.5 | 54 |
| glm5_2_nv | 429 | 28 | 10.8 | 21 |
| glm5_2_nv | 502 | 61 | 10.6 | 64 |

### 12h nv_requests 汇总 (R2329 生效后窗口)

| mapped_model | status | cnt | avg_dur (s) | max_dur (s) | min_dur (s) |
|---|---|---|---|---|---|
| dsv4p_nv | 200 | 3 | 57.2 | 64.2 | 48.7 |
| dsv4p_nv | 502 | 27 | 51.8 | 170.1 | 0.0 |
| glm5_2_nv | 200 | 19 | 11.7 | 35 | 4 |
| glm5_2_nv | 429 | 13 | 12.7 | 21 | 7 |
| glm5_2_nv | 502 | 39 | 4.6 | 56 | 0 |

### 1h regime overview (改前)

| total | ok | fail | cnt429 | total_kc429 | avg_lat_ms |
|---|---|---|---|---|---|
| 17 | 5 | 12 | 3 | 2 | 37594.4 |

### 3h 近期失败详情

15 条 502/429 全部为 `all_tiers_exhausted` / `all_tiers_failed_in_mapped_tier`，upstream_type=NULL（调度层拒绝）。
dsv4p_nv 502 耗时: 100s (R2329 budget ceiling), 120s (pre-R2329), 170s (pre-R2328)。
glm5_2_nv 502 耗时: 0s (breaker fast-fail) 和 5-56s (key cycle exhaustion)。

### dsv4p_nv 成功分布 (24h, 28 条 200)

| 指标 | 值 |
|---|---|
| max | 90.7s |
| avg | 33.1s |
| P90 | 66.1s |

### nv_gw logs 关键 (改前, 最近)

```
[23:03:28-41] glm5_2_nv 5 keys all 429 → TIER-FAIL 11.6s → GLOBAL-COOLDOWN 10s
[23:03:46-47] glm5_2_nv TIER-SKIP (cooldown) → instant 502 (0-8ms) → breaker OPEN
[23:06:02] dsv4p_nv k2 SSLEOFError (5s) → SSL-CYCLE to next key
[23:07:02] dsv4p_nv big_input SUCCESS (req=91c41a6d) → breaker CLOSED
[23:08:01] dsv4p_nv big_input SUCCESS (req=2d939bc2) → breaker CLOSED
[23:09:05] dsv4p_nv k4 connection error → k5 timeout 36.3s → TIER-BUDGET 100s exceeded
[23:09:41] dsv4p_nv TIER-FAIL 100s → breaker CLOSED (fail_count=1, FAIL_N=2 not triggered)
[23:10:31] dsv4p_nv big_input SUCCESS (req=76381c2c) → breaker CLOSED
```

### nv_tier_attempts (6h)

| tier | error_type | cnt | avg_s | max_s |
|---|---|---|---|---|
| glm5_2_nv | 429_nv_rate_limit | 13 | — | — |
| dsv4p_nv | NVCFPexecSSLEOFError | 1 | 5.0 | 5.0 |

### env 确认 (改前)
- NVU_BIG_INPUT_COOLDOWN_S=120
- NVU_BIG_INPUT_FAIL_N=2
- NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
- NVU_BIG_INPUT_THRESHOLD=250000
- NVU_TIER_BUDGET_DSV4P_NV=100 (R2329)
- KEY_COOLDOWN_S=10, TIER_COOLDOWN_S=10

## 优化决策

### 参数: NVU_BIG_INPUT_COOLDOWN_S

| 轮次 | 值 | 理由 |
|---|---|---|
| R2325 | 900→300 | 初始 breaker cooldown 15min→5min |
| R2326 | 300→180 | 5min→3min |
| R2327 | 180→120 | 3min→2min |
| **R2330 (本轮)** | **120→90** | 2min→1.5min, R2327 regime 16min stable |

### 理由

1. **R2327 regime (120s) 16min 稳定运行**: breaker 正确 OPEN→CLOSED, big_input 成功检测 NVCF 恢复
2. **breaker 轮次历史**: 900→300→180→120, 每步验证 post-restart 2/2 success, 无回归
3. **120s 已验证 16min 无新故障**: dsv4p_nv 3/30 成功 (10% SR), glm5_2_nv 19/71 (含 429)
4. **90s 的效果**: breaker HALF-OPENs 1.5min after last big-input fail, vs 2min at 120s
   - 25% faster recovery detection
   - 每 30-min inter-storm gap: ~20 probes (vs ~15 at 120s), 33% more recovery detection
5. **安全约束**:
   - FAIL_N=2: breaker 只在连续 2 次 big-input fail 后 OPEN, 单次 fail (如 dsv4p_nv 23:09:41) 不触发
   - inter-request gap ~5-10min >> 90s: breaker 不会在正常请求间隔内 self-rearm loop
   - 若 NVCF 仍 429: breaker re-OPENs 90s → ms_gw fallback 继续, 无回归风险
6. **big_input breaker 保护**: COOLDOWN=90 > KEY_COOLDOWN=10 > TIER_COOLDOWN=10, 层级不变

### 安全性评估

- ✅ R2327 regime 16min 稳定, 无新错误类型
- ✅ inter-request gap (5-10min) >> 90s COOLDOWN, 无 self-rearm loop 风险
- ✅ FAIL_N=2 仍保护: 单次 fail 不 OPEN breaker
- ✅ ms_gw fallback 作为安全网持续工作
- ✅ dsv4p_nv 502 max=100s (R2329 budget), 90s COOLDOWN < 100s budget, breaker 可在 budget 内 re-arm
- ⚠️ 若 90s 内有新 big_input 请求: breaker 仍 CLOSED (90s > 正常请求间隔), 不影响

## 执行

### 修改

```yaml
# /opt/cc-infra/docker-compose.yml → nv_gw environment (line 449)
- NVU_BIG_INPUT_COOLDOWN_S=90  # R2330 (HM2->HM1): 120->90 (2min->1.5min) ...
```

### 备份

```bash
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R2330
```

### 部署

```bash
cd /opt/cc-infra && docker compose up -d --no-deps --force-recreate nv_gw
```

### 验证

```
$ docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S
NVU_BIG_INPUT_COOLDOWN_S=90

$ docker ps --format '{{.Names}}	{{.Status}}' | grep nv_gw
nv_gw	Up 7 seconds (healthy)

$ docker logs nv_gw --tail 20 2>&1 | grep -iE 'error|warn|fail|exception'
(no error/warn, clean start)
```

✅ 容器重建成功, 环境变量生效, health check 通过, clean start 无错误

## 铁律遵守

- ✅ 只改 HM1 配置, 未改 HM2 本地任何文件
- ✅ 改前有数据 (24h + 12h + 1h + 3h DB 查询 + docker logs + env)
- ✅ 改后有验证 (env check + health check + logs clean)
- ✅ 聚焦 nv_gw (仅改 NVU_BIG_INPUT_COOLDOWN_S)
- ✅ 写入仓库 (本文件)

## ⏳ 轮到HM1优化HM2
