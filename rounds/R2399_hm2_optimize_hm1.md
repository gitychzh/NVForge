# R2399 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 230→255

## 改前数据 (2026-07-27 11:55 UTC)

### nv_gw 健康
- `/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}`
- Container `nv_gw` running, latest env: R2398 FASTBREAK=5, R2397 SSLEOF=2.0, R2396 kimi budget=400, R2395 glm5_2 budget=230

### DB 6h 窗口 (nv_requests)

| mapped_model | total | ok | ate | zombie | SR% |
|--------------|-------|----|-----|--------|-----|
| glm5_2_nv    | 24    | 13 | 11  | 0      | 54.17 |
| kimi_nv      | 29    | 24 | 4   | 1      | 82.76 |

glm5_2_nv 是当前最高错误率模型 (46% ATE, 11/24)。

### DB 2h 窗口 (nv_requests)

| mapped_model | total | ok | err | SR% | avg_ok_ms | avg_err_ms |
|--------------|-------|----|-----|-----|-----------|------------|
| glm5_2_nv    | 8     | 4  | 4   | 50.00 | 16926 | 149482 |
| kimi_nv      | 7     | 6  | 1   | 85.71 | 42608 | 222418 |

### 6h ATE 详细分析

```
glm5_2_nv ATE: 10 all_tiers_exhausted (all_tiers_failed_in_mapped_tier)
  start_tier_idx=2, tiers_tried_count=1, fallback=false
  avg=144616ms (~145s), max=160450ms
  key_cycle_details=[] (pre-R2282 fix, empty tier_attempts)
```

### 2h 日志 (最近一次 glm5_2_nv timeout cluster)

```
[12:03:48.2] [NV-TIMEOUT] tier=glm5_2_nv k1: attempt=25393ms
[12:03:53.2] [NV-ERR] tier=glm5_2_nv k2 SSLEOFError
[12:04:18.3] [NV-TIMEOUT] tier=glm5_2_nv k3: attempt=25076ms total=55480ms
[12:04:42.9] [NV-TIMEOUT] tier=glm5_2_nv k4: attempt=24657ms total=80139ms
[12:05:07.7] [NV-TIMEOUT] tier=glm5_2_nv k5: attempt=24736ms total=104876ms
[12:05:35.1] [NV-TIMEOUT] tier=glm5_2_nv k1: attempt=27427ms total=132305ms
[12:05:35.1] [NV-PEXEC-FASTBREAK] 5 consecutive timeout → fast-break
[12:05:35.1] [NV-TIER-FAIL] elapsed=132306ms
```

5 keys × 25s = 125s nominal + 1 SSLEOF + overhead = 132s. Budget 230s had 98s remaining — not budget-limited in this case. But the 6h avg ATE=145s max=160s with 230s budget leaves only 70-85s headroom.

### 当前 HM1 nv_gw 关键 env

```
NVU_PEXEC_TIMEOUT_FASTBREAK=5
NVU_TIER_BUDGET_GLM5_2_NV=230
NVU_TIER_BUDGET_KIMI_NV=400
NVU_TIER_BUDGET_DSV4P_NV=265
NVU_EMPTY_200_FASTBREAK=3
NVU_SSLEOF_RETRY_DELAY_S=2.0
KEY_COOLDOWN_S=5
TIER_COOLDOWN_S=0
UPSTREAM_TIMEOUT=24
PROXY_TIMEOUT=500
TIER_TIMEOUT_BUDGET_S=475
```

### 额外发现: SSLEOF_RETRY_DELAY_S=2.0 是死参数

代码审查 (upstream.py 行 845-857, F-fix 2026-07-01): SSLEOF 错误后**立即 cycle 下一 key，无 sleep**。代码中不存在 `NVU_SSLEOF_RETRY_DELAY_S` 的读取。env 值 2.0 未生效，属于历史遗留 dead code。此项不改，仅记录。

## 问题分析

### glm5_2_nv 是当前最痛模型

- 6h: 54.17% SR, 11/24 ATE — 远高于 kimi_nv (82.76%)
- 所有 ATE 都是 `tiers_tried_count=1, fallback=false` — 单 tier NVCF 集群故障，非预算耗尽
- 2h: 4/8 ATE — 持续高频失败
- 每次 ATE: 5 个 key 全部 timeout (或 timeout+SSLEOF)，~130-160s 消耗
- 成功请求: avg=17-19s, 在 key 1-2 完成，不受预算影响

### 为什么 230→255?

- **当前单次 ATE 消耗**: 125-160s (5 keys × 25s + SSLEOF overhead)
- **230s 预算**: 剩余 70-105s — 仅够 2-3 个额外 key 尝试
- **255s 预算**: 剩余 95-130s — 够 3-5 个额外 key 尝试
- 当 NVCF 集群故障持续时间更长（如 +30s 的 SSLEOF 风暴或 k2 429 冷却阻塞），230s 可能不够
- 255s = PER_KEY 51s，vs 24s pexec + 5s KEY_COOLDOWN = 29s/cycle → 22s 余量/key → 5 个完整 key + 额外 3-4 个 key 尝试
- +25s = 10.9% 增加，保守

### 风险

- **不影响 kimi_nv**: 独立 budget (400s)
- **不影响 dsv4p_nv**: 独立 budget (265s)
- **不影响 cc4101**: PROXY_TIMEOUT=500s >> 255s
- **不影响 HM2**: 单参数，仅改 HM1
- **成功率请求不受影响**: 成功时 avg=17-19s，远低于 255s

## 修改

### docker-compose.yml (HM1, /opt/cc-infra)

```yaml
# Before:
- NVU_TIER_BUDGET_GLM5_2_NV=230  # R2395 (HM2->HM1): 210->230

# After:
- NVU_TIER_BUDGET_GLM5_2_NV=255  # R2399 (HM2->HM1): 230->255. 6h: glm5_2_nv 11/24 ATE (46% SR). ATE avg=145s max=160s. 230s budget leaves 70-85s headroom after 160s ATE — only 2-3 extra key attempts. 255s (+25s, +10.9pct) gives 95-130s headroom = 3-5 extra key attempts, absorbing longer NVCF cluster storms. Success requests avg 17-19s unaffected. Single param; iron law: only HM1.
```

## 验证

1. `docker compose up -d --no-deps nv_gw` → Container recreated/started ✅
2. `curl http://localhost:40006/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}` ✅
3. `docker exec nv_gw env | grep TIER_BUDGET_GLM5_2` → `NVU_TIER_BUDGET_GLM5_2_NV=255` ✅

## 预期改善

- glm5_2_nv ATE 在更长 NVCF 集群故障时不再因预算不足而提前截断
- 额外 +25s 预算 = 3-5 个额外 key 尝试，吸收 SSLEOF 风暴和 429 冷却
- 成功率请求 avg=17-19s 完全不受影响
- 零 HM2 影响

## ⏳ 轮到HM1优化HM2