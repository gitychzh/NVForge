# R2156 (HM2→HM1): KEY_COOLDOWN_S 50→48 (-2s)

## 改前数据 (6h pre-R2156, ~2026-07-21 04:17Z)

| 指标 | 值 |
|------|-----|
| 6h 总请求 | 38 |
| 6h OK | 32 (84.2% SR) |
| 6h 失败 | 6 (3 ATE + 3 zombie) |
| avg OK latency | 17,988ms |
| avg OK TTFB | 17,987ms |
| max OK | 153,777ms |
| key_cycle_429s | 51 total (35/38 reqs, 1.46 cycles/req) |

### 按模型
| 模型 | 请求 | OK | 失败 | 失败类型 |
|------|------|-----|------|----------|
| glm5_2_nv | 35 | 32 | 3 | zombie_empty_completion (avg 10,157ms) |
| dsv4p_nv | 3 | 0 | 3 | all_tiers_exhausted (avg 1,861ms) |

### 按错误类型
| 错误类型 | 数量 | avg ms |
|----------|------|--------|
| all_tiers_exhausted | 3 | 1,861 |
| zombie_empty_completion | 3 | 10,157 |

### 容器状态
- nv_gw: Up 16 minutes (healthy), StartedAt 04:16:55Z
- docker logs: 零 error/warn
- POST-RESTART (16min): 2/2 OK, 5,314ms, 8,138ms

### 当前参数
```
KEY_COOLDOWN_S=50 (R2153)
TIER_COOLDOWN_S=32 (R2154)
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=153
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_BIG_INPUT_COOLDOWN_S=2100
NVU_BIG_INPUT_FAIL_N=3
NVU_EMPTY_200_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=0.1
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

## 优化决策

**KEY_COOLDOWN_S 50→48 (-2s)**

交替 KEY→TIER 模式继续：
- R2153: KEY 52→50
- R2154: TIER 34→32
- R2156: KEY 50→48

安全验证：
- KEY+TIER = 48+32 = 80 << 153 BUDGET (73s margin)
- 5 keys × 48s cooldown = 240s total key bandwidth / cycle
- 38 req / 6h = 6.3 req/h, 5 keys, near-zero exhaustion risk
- Key cycling 1.46 cycles/req is normal rotation (NVCF 429s, not config-fixable)
- 3 dsv4p ATE are pre-empted (0 tier_attempts, upstream NVCF degradation)
- 3 zombie are glm5_2 content-filter (NVCF server-side, not config-fixable)

保守 2s reduction，继续微修 KEY cooldown 缩小失败路径等待时间。

## 执行
1. Edit `/opt/cc-infra/docker-compose.yml` on HM1: KEY_COOLDOWN_S 50→48
2. `docker compose up -d nv_gw` → healthy
3. Verify: `docker exec nv_gw env | grep KEY_COOLDOWN_S` → 48 ✓

## 验证
- curl /health: status=ok, nv_gw healthy
- KEY_COOLDOWN_S=48 verified in container env
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2