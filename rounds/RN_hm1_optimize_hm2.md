# R292: HM1→HM2 — MIN_OUTBOUND_INTERVAL_S 9.0→7.0 (-2.0s)

**Role**: HM1 (opc_uname) 优化 HM2
**Timestamp**: 2026-06-29 17:24 CST
**Change**: MIN_OUTBOUND_INTERVAL_S: 9.0 → 7.0 (-2.0s)
**Category**: 少改多轮 — 单一参数优化, 减少inter-key dead time

## Data Collection (30-min Window)

### 1. PostgreSQL hm_requests (30min)
```
total=144 (138 glm5.1_hm_nv + 6 null-tier)
success=134 (93.06%)
errors=10

Breakdown:
  NVStream_IncompleteRead: 6 (k0×3, k4×3)
  all_tiers_exhausted:   4 (null-tier, avg 123303ms)
```

### 2. Per-Key Latency (successful requests, 30min)
```
k0: avg=23414ms p90=38937ms p95=39713ms (22 reqs)
k1: avg=19706ms p90=34922ms p95=38994ms (30 reqs)
k2: avg=23328ms p90=48391ms p95=49653ms (24 reqs)
k3: avg=24394ms p90=40789ms p95=51690ms (24 reqs)
k4: avg=25297ms p90=50139ms p95=50219ms (24 reqs)
```

### 3. Error by Key (30min)
```
k0: 3×NVStream_IncompleteRead (avg 22611ms)
k4: 3×NVStream_IncompleteRead (avg 41753ms)
(null): 4×all_tiers_exhausted (avg 123303ms)
```

### 4. Tier Attempts (30min)
```
NVCFPexecProxyConnectionError: 172
empty_200:                      2
NVCFPexecRemoteDisconnected:    1
NVCFPexecgaierror:             1
```

### 5. Temporal Burst (3-Window)
```
10-min burst:   38 total, 2 errors (176 attempts, 172 proxy err)
20-min prior:   94 total, 8 errors
```

### 6. Docker Logs (SSLEOF / Budget)
```
No budget-break logs found in last 500 lines
SSLEOFError retries working: 3s backoff, all keys retry ↓
Recent SSLEOF: k1(×4), k4(×2), k2(×1), k3(×1), k5(×1)
```

### 7. Running Env Vars
```
MIN_OUTBOUND_INTERVAL_S=9.0  → 7.0 (this round)
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
HM_CONNECT_RESERVE_S=22
TIER_TIMEOUT_BUDGET_S=128
UPSTREAM_TIMEOUT=70
```

## Analysis

### 1. 核心发现: Inter-Key Dead Time 占预算比例

**7 keys × 9.0s inter-key gap = 54s 纯 dead time** (占 128s budget 的 42%)
- 54s 的 inter-key 间隔中, 只有 0-1 个 key 在做实际请求
- 剩下 5+ 个 key 在等待其 slot → 浪费 budget

**如果 4-5 个 key 快速失败 (NVCFPexecProxyConnectionError, 1-3ms):**
- 实耗时间: 5×9.0s = 45s dead time + 0s actual
- 剩余 budget: 128-45 = 83s for 最后 2-3 个 key
- 最后 2-3 个 key 每个可耗 ~27-41s → 够用

**但如果每个 key 都慢 (20-50s per key):**
- 7 keys × (9s dead + 20-50s actual) ≈ 200-400s
- Budget 128s 不够 → `all_tiers_exhausted` @ 123s

### 2. 4 all_tiers_exhausted @ 123s: 紧贴 Budget

- 123s avg → 紧贴 TIER_TIMEOUT_BUDGET_S=128
- 减 2s inter-key gap → 7 keys 省 12s dead time → 剩余更多 time 给 actual key work
- 预期: 这些 4 个失败能转为成功 (extra 12s margin)

### 3. 为什么选 MIN_OUTBOUND_INTERVAL_S (而非其他参数)

| 参数 | 当前值 | 为什么不选 |
|------|--------|-----------|
| KEY_COOLDOWN_S | 38 | 影响 subsequent requests 的 key 复用, 不直接影响单次请求内 key 轮转 |
| TIER_COOLDOWN_S | 22 | 只有 all_tiers_exhausted 后触发, 4 个失败中已触发 |
| UPSTREAM_TIMEOUT | 70 | NVStream 超时已固定, 减 TO 会 cut 掉正在跑的 key |
| HM_CONNECT_RESERVE_S | 22 | connect_reserve 是 TCP 握手预留, 不是 inter-key 间隔 |
| **MIN_OUTBOUND_INTERVAL_S** | **9.0** | **直接影响单次请求内 key 轮转 dead time → 选此项** |

### 4. Budget 验证

```
减少前: 7 keys × 9.0s dead = 54s (42% of 128s)
减少后: 7 keys × 7.0s dead = 42s (33% of 128s)
节省: 12s → 给 actual key work 更多时间
```

| 指标 | 减少前 | 减少后 |
|------|-------|--------|
| Inter-key dead time (7 keys) | 54s | 42s |
| Dead time / Budget % | 42% | 33% |
| Available for actual key work | 74s | 86s |
| 预期 all_tiers_exhausted → 0 | 4 | 0 |

## Execution

### 1. 修改 docker-compose.yml (HM2 remote)
```bash
ssh -p 222 opc2_uname@100.109.57.26 'sed -i "s/MIN_OUTBOUND_INTERVAL_S: \\\"9.0\\\"/MIN_OUTBOUND_INTERVAL_S: \\\"7.0\\\"/" /opt/cc-infra/docker-compose.yml'
# 更新 comment:
sed -i '...9.0→7.0 -2.0s MIN_OUTBOUND精简; 30min: 144req/93.06% succ...'
```

### 2. 部署 (GHCR unreachable → --no-build)
```bash
cd /opt/cc-infra && docker compose up -d --no-build hm40006
# → Container hm40006 Recreated
# → Container hm40006 Started
```

### 3. 验证
```bash
docker exec hm40006 env | grep MIN_OUTBOUND_INTERVAL_S
# → MIN_OUTBOUND_INTERVAL_S=7.0 ✓
```

## 铁律 Followed

- ✅ 只改 HM2 配置 — docker-compose.yml on HM2 only, 不改 HM1 本地
- ✅ 不 touch mihomo — 无 systemctl/pkill/stop/restart
- ✅ 少改多轮 — 单一参数 -2.0s (≤4 units)
- ✅ 同一方向 — reduce (缩小 dead time)
- ✅ 数据驱动 — 基于 30min DB stats + 3-window burst analysis

## Expected Effects

| Metric | Before (R291) | After (R292) | Direction |
|--------|----------------|---------------|-----------|
| Success Rate | 93.06% | ≥95% | ↑ |
| all_tiers_exhausted | 4 (30min) | 0 | ↓ |
| NVStream_IncompleteRead | 6 | ≤6 | → |
| Inter-key dead time | 54s (42%) | 42s (33%) | ↓ |
| Avg latency (success) | ~24s | ~23s | ↓ |

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记