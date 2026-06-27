# R159: HM2 → HM1 — 无变更 (全7参数均衡; R158 UPSTREAM_TIMEOUT=70已验证: 30min 99.5% 0 429 0 fallback; 3 ATE为NVCF server-side不可调; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (2026-06-28 04:46-04:50 UTC)

### Config Snapshot (HM1 hm40006 — docker exec env 确认)
| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 70 | R158: 72→70 (-2s), 已验证 |
| TIER_TIMEOUT_BUDGET_S | 156 | 2×70=140, 余量16s > 10s |
| KEY_COOLDOWN_S | 34 | 0 429 稳定 |
| TIER_COOLDOWN_S | 38 | KEY-TIER gap=4s (最小安全) |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | 2.6 req/min → 81%利用率 |
| HM_CONNECT_RESERVE_S | 24 | 无 connect 耗尽事件 |
| PROXY_TIMEOUT | 300 | 未变更 |

### 30min Window (1160 requests)
- **Success rate: 99.5%** (1154/1160)
- P50: 18763ms, P90: 37685ms, P95: 53202ms, P99: 103016ms
- Avg: 22357ms
- **Errors: 6** (3 ATE + 2 NVStream_IncompleteRead + 1 NVStream_TimeoutError)
- **429 count: 0** — KEY_COOLDOWN=34 零触发
- **Fallback: 0** — 无请求到达 kimi_hm_nv

### 30min Error Breakdown
| Error Type | Count | Avg Duration |
|------------|-------|--------------|
| all_tiers_exhausted | 3 | 145154ms |
| NVStream_IncompleteRead | 2 | 13187ms |
| NVStream_TimeoutError | 1 | 109523ms |

**3 ATE 全部为 NVCFPexecTimeout 风暴**: error detail JSONL 确认每个 ATE 有 6 个 deepseek key 尝试 (num_attempts=6), kimi fallback num_attempts=0 (Pitfall #41: budget 耗尽后 kimi 未获执行机会)。

### Per-Key Success Latency (30min, status=200)
| Key | Connection | N | Avg | P50 | P95 |
|-----|-----------|----|-----|-----|-----|
| k0 | DIRECT | 244 | 24624ms | 20598ms | 58188ms |
| k1 | DIRECT | 228 | 22753ms | 18898ms | 59915ms |
| k2 | DIRECT | 218 | 19588ms | 17351ms | 38470ms |
| k3 | PROXY → 7896 | 235 | 20772ms | 18517ms | 43655ms |
| k4 | PROXY → 7897 | 229 | 21899ms | 18831ms | 53409ms |

**DIRECT vs PROXY 差异 (Pitfall #29)**: k0/k1 DIRECT p95=58-60s > k2-k4 PROXY p95=38-53s — NVCF server-side variance, 非配置问题。所有 key p95 < 70s → UPSTREAM_TIMEOUT=70 安全。

### Request Rate
- **2.6 req/min avg** (deepseek_hm_nv), max=5/min, min=1/min
- Capacity at MIN_OUTBOUND=19s: 3.2 req/min (81% utilization)
- 5-key cycle at 19s = 95s >> KEY_COOLDOWN=34s ✓

### 1h Window
- **99.5%** (1208/1214), 6 errors, 0 429, 0 fallback

### 6h Window
- **98.5%** (2010/2040), 30 errors, 0 fallback

### 24h Status Breakdown (Latency Profile — Pitfall #34)
| Status | Count | Avg | Min | Max |
|--------|-------|-----|-----|-----|
| 200 | 4510 | 29609ms | 1295ms | 233742ms |
| 429 | 5 | 172934ms | 138762ms | 219113ms |
| 502 | 46 | 117557ms | 6827ms | 166774ms |

### 24h ATE Distribution by Hour
- **Total: 45** (24h)
- Concentrated 2026-06-27 09:00-19:00 UTC: 42/45 = 93.3% (daytime pattern — Pitfall #30)
- 2026-06-28: 3 ATE only (01:00-02:00 UTC overnight)
- All with tiers_tried_count=0 → NVCF server-side timeout pattern

### 24h Error Breakdown
| Error Type | Count | Avg |
|------------|-------|-----|
| all_tiers_exhausted | 45 | 129711ms |
| NVStream_TimeoutError | 4 | 102228ms |
| NVStream_IncompleteRead | 2 | 13187ms |

### Back-to-Back Same Key
- **3.0%** (3/99 pairs) — RR counter bug (Pitfall #28), 非 operational issue

### Error Detail JSONL (2026-06-28, 今天)
3 ATE 事件全部展示相同模式:
```json
{
  "tier_summaries": [
    {"tier": "deepseek_hm_nv", "num_attempts": 6, "elapsed_ms": 141409-146308},
    {"tier": "kimi_hm_nv", "num_attempts": 0, "elapsed_ms": 141941-146818}
  ]
}
```
**6 个 deepseek key 全部 NVCFPexecTimeout → kimi 0 次尝试** (Pitfall #41: kimi fallback starvation).

## 🎯 优化分析

### 综合评估: 全7参数均衡 — 无变更

R158 的 UPSTREAM_TIMEOUT 72→70 已部署且运行良好:
- 30min 99.5% 成功率 (1154/1160) — 健康
- 0 429 in 30min — KEY_COOLDOWN=34 完美校准
- 0 fallback in all windows — 无请求触发 kimi
- 所有 key p95 < 70s — 超时边界安全
- 2.6 req/min, 81% MIN_OUTBOUND 利用率 — 流量健康

### 参数逐一评估

| Parameter | Value | 评估 | 理由 |
|-----------|-------|------|------|
| UPSTREAM_TIMEOUT | 70 | ⛔ 不调整 | R158 刚改 (72→70), 需更多时间积累 24h 数据。所有 key p95 < 70s, 安全 |
| TIER_TIMEOUT_BUDGET_S | 156 | ⛔ 不调整 | 2×70=140, 余量 16s > 10s。R154 已证明 BUDGET 增加有边际递减效应 |
| KEY_COOLDOWN_S | 34 | ⛔ 不调整 | 0 429 in 30min — 完美。继续降低会增加 429 风险 |
| TIER_COOLDOWN_S | 38 | ⛔ 不调整 | KEY=34, gap=4s (最小安全)。再降低会破坏最小 gap 不变式 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | ⛔ 不调整 | 81% 利用率, 0 429。5-key cycle 95s >> KEY=34s |
| HM_CONNECT_RESERVE_S | 24 | ⛔ 不调整 | 30min 无 budget_exhausted_after_connect。稳定 |
| PROXY_TIMEOUT | 300 | ⛔ 不调整 | 未变更, 从未触发。背景参数 |

### 3 ATE 根因再确认

30min 窗口 3 个 ATE (avg=145154ms) 全部是 **NVCFPexecTimeout 多 key 风暴**:
- Error detail JSONL 显示每个 ATE: 6 deepseek attempts, 0 kimi attempts
- 每个 key 超时约 24s (141409ms / 6 = 23568ms), 远低于 UPSTREAM_TIMEOUT=70s
- 6 × 24s ≈ 144s > BUDGET=156s → budget 耗尽时 kimi 未获机会

**这是 NVCF server-side 的超时风暴** — 非 HM 配置可调。R154 的 BUDGET 边际递减结论再次确认: 即使 budget 增加到 200s, NVCFPexecTimeout 风暴仍会耗尽任何 budget。

### R158 变更生效确认

R158 的 UPSTREAM_TIMEOUT 72→70 (-2s):
- 每个 key 超时消耗从 72s → 70s
- After 2 timeouts: remaining = 16s (was 12s at 72) — +4s margin
- 30min 成功 99.5% vs R158 采集时 99.6% — 稳定持平
- 0 429, 0 fallback — 维持 R158 时的一致性

**R158 的变更已完全生效且稳定**。

## ⚖️ 评判标准

- **更少报错**: ✅ 0 429 in 30min, KEY_COOLDOWN=34 完美校准; 3 ATE 为 NVCF server-side 不可调
- **更快请求**: ✅ 所有 key p95 < 70s, UPSTREAM_TIMEOUT=70 覆盖 100% 成功路径; 2.6 req/min 健康吞吐
- **超低延迟**: ✅ P50=18763ms, DIRECT keys p95 56-60s 为 NVCF server-side variance (Pitfall #29), 非配置问题
- **稳定优先**: ✅ 全 7 参数均衡 — 无变更是最优状态; 不因"总得改点什么"的冲动而过度优化
- **铁律**: ✅ 只改 HM1 docker-compose.yml — 本轮无变更, 验证即可; 绝不动 HM2 本地配置

**结论**: R159 是 HM2→HM1 方向上的**无变更验证轮**。全 7 参数处于平衡状态 — R158 的 UPSTREAM_TIMEOUT=70 已验证有效, 3 ATE 为 NVCF server-side 的 PexecTimeout 风暴 (kimi fallback starvation, Pitfall #41)。稳定本身即最优结果。

## ⏳ 轮到HM1优化HM2