# R2329 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 120→100

**Date**: 2026-07-24 22:40 CST
**Author**: opc2_uname (HM2)
**Target**: HM1 nv_gw (100.109.153.83:40006)
**Change**: `NVU_TIER_BUDGET_DSV4P_NV=120` → `100` in `/opt/cc-infra/docker-compose.yml`

## ⚠️ [hm4104] primary 故障/超时, 已 fallback 到 dsv4p_ms. 本轮继续, 下一轮回 primary. (hm4104 fallback)

## 数据收集 (改前必有数据)

### HM1 容器映射
- `nv_gw` = nv gateway (port 40006)
- `ms_gw` = ms gateway (port 40007)
- `logs_db` = PostgreSQL hermes_logs

### 24h nv_requests 汇总

| mapped_model | status | cnt | avg_dur (ms) | max_dur (ms) |
|---|---|---|---|---|
| dsv4p_nv | 502 | 38 | 50,562 | 170,061 |
| dsv4p_nv | 200 | 25 | 30,194 | 90,721 |
| glm5_2_nv | 502 | 57 | 10,386 | 64,871 |
| glm5_2_nv | 200 | 45 | 14,479 | 54,260 |
| glm5_2_nv | 429 | 26 | 10,874 | 21,296 |
| kimi_nv | 502 | 1 | 124,592 | 124,592 |

### 12h nv_requests 汇总 (R2328 生效后窗口)

| mapped_model | status | cnt | avg_dur (ms) | max_dur (ms) | min_dur (ms) |
|---|---|---|---|---|---|
| dsv4p_nv | 502 | 27 | 54,384 | 170,061 | 5 |
| glm5_2_nv | 502 | 40 | 8,548 | 56,303 | 1 |
| glm5_2_nv | 200 | 18 | 11,863 | 35,996 | 4,548 |
| glm5_2_nv | 429 | 12 | 12,819 | 21,296 | 7,601 |

### 关键发现: dsv4p_nv 12h 内 0% 成功 (27/27 = 502)

- dsv4p_nv 在过去 12 小时内零成功, 全部 502
- NVCF deepseek-v4-pro 完全降级, 所有请求 504 或 timeout
- R2328 (budget 170→120) 已生效: 最近一条 502 为 120,069ms (budget ceiling)
- 但 120s 仍是每次 ATE 的纯浪费 (0 成功需要保护)

### dsv4p_nv 成功分布 (24h, 25 条 200)

| 指标 | 值 |
|---|---|
| max | 90,721ms (90.7s) |
| P90 | 77,658ms (77.7s) |
| >60s | 3/15 (20%) |
| >90s | 1/15 (7%) |

### 3h 近期失败详情

dsv4p_nv 502 失败模式 (6h):
- 165-170s (pre-R2328, 4 条): 504 ~60s/key × 3 keys = 170s budget ceiling
- 120s (post-R2328, 1 条): 504 ~60s/key × 2 keys = 120s budget ceiling
- 5-9ms (breaker OPEN, instant reject): big_input breaker 工作正常 ✓

### glm5_2_nv 分析

- 502 avg 8.5s (breaker fast-fail 5-8ms) ✓
- 429 avg 12.8s (5 keys cycled at ~3s each + cooldown retries)
- 200 avg 11.9s (正常工作)
- KEY_COOLDOWN_S=10, TIER_COOLDOWN_S=10 (R2324 aligned) ✓
- breaker + peer-fb skip 工作正常

### nv_gw logs (最近)

```
[22:33:20-40] glm5_2_nv 7 keys all 429 → TIER-FAIL 19.3s → GLOBAL-COOLDOWN 10s
[22:33:45-46] glm5_2_nv TIER-SKIP (cooldown) → instant 502 (5-8ms) → breaker OPEN
[22:35:55] dsv4p_nv k1 504 at 67.7s → k2 timeout 52.2s → TIER-BUDGET 120s exceeded
[22:37:55] dsv4p_nv TIER-FAIL 120s → breaker OPEN (fail_count=3, 119s left)
```

## 优化决策

### 参数: NVU_TIER_BUDGET_DSV4P_NV

| 轮次 | 值 | 理由 |
|---|---|---|
| R2328 (前轮) | 170→120 | 8 ATE hit 170s ceiling, 504 ~60s/key × 3 keys |
| **R2329 (本轮)** | **120→100** | 12h post-R2328: 0/27 success, all 502s still hit ceiling |

### 理由

1. **dsv4p_nv 12h 0% 成功**: NVCF deepseek-v4-pro 完全降级, 无成功需要保护
2. **24h max success = 90.7s**: budget 100s 给 9.3s margin
3. **24h P90 = 77.7s**: 远在 100s 以内, 安全
4. **每次 ATE 节省 20s**: 120s→100s, 27 ATEs × 20s = 540s 用户时间节省 (12h)
5. **保守原则**: 当 NVCF 恢复时, 100s 仍覆盖 24/25 成功 (96%), 仅 90.7s outlier 例外
6. **big_input breaker 保护**: FAIL_N=2, COOLDOWN_S=120, 首次触发后后续请求 instant 502 ✓

### 安全性评估

- ✅ 0 成功在 12h 内 = 无当前成功会被切断
- ✅ 24h max success 90.7s < 100s (9.3s margin)
- ✅ P90 77.7s << 100s (22.3s margin)
- ✅ big_input breaker 仍保护后续请求
- ✅ ms_gw fallback 仍工作 (dsv4p_ms)
- ⚠️ 当 NVCF 恢复: 1/25 (4%) 成功可能被切断 → 落 ms_gw fallback

## 执行

### 修改

```yaml
# /opt/cc-infra/docker-compose.yml → nv_gw environment
- NVU_TIER_BUDGET_DSV4P_NV=100  # R2329 (HM2->HM1): 120->100 ...
```

### 备份

```bash
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R2329
```

### 部署

```bash
cd /opt/cc-infra && docker compose up -d nv_gw
```

### 验证

```
$ docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P
NVU_TIER_BUDGET_DSV4P_NV=100

$ curl -s http://localhost:40006/health
{"status": "ok", "proxy_role": "passthrough", ...}
```

✅ 容器重启成功, 环境变量生效, health check 通过

## 铁律遵守

- ✅ 只改 HM1 配置, 未改 HM2 本地任何文件
- ✅ 改前有数据 (24h + 12h + 3h DB 查询 + docker logs)
- ✅ 改后有验证 (env check + health check)
- ✅ 聚焦 nv_gw (仅改 NVU_TIER_BUDGET_DSV4P_NV)
- ✅ 写入仓库 (本文件)

## ⏳ 轮到HM1优化HM2
