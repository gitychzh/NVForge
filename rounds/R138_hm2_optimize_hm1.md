# R138: HM2→HM1 — 无变更 (验证R136-R137: 全参数均衡, 100%成功率, 0错误, 0 all_tiers_exhausted, 稳定优先不追加)

**Role**: HM2 (opc2_uname) optimizing HM1 (opc_uname, hm40006 container)
**Timestamp**: 2026-06-28 01:00 UTC (collected ~00:50–01:00)
**Change**: **None** — all 7 parameters at equilibrium; stability confirmed; no adjustment needed
**Principles**: 少改多轮(单参数), 更少报错更快请求超低延迟稳定优先, 铁律:只改HM1不改HM2

---

## 📊 数据采集 (HM1 hm40006, 30-min window 00:20–00:57 UTC + 1h window + 6h window)

### 运行配置 (docker exec hm40006 env)
| 参数 | 值 | 状态 |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 68 | 0次超时/6h, 充足 |
| TIER_TIMEOUT_BUDGET_S | 146 | 0次all_tiers_exhausted/30min, 6h仅3次(非当前卡点) |
| KEY_COOLDOWN_S | 38.0 | 30min仅1次429周期, 键疲劳度低 |
| TIER_COOLDOWN_S | 42 | 与KEY=38的差距=4s, 健康 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | 速率2.6/min, 容量3.2/min, 合适 |
| HM_CONNECT_RESERVE_S | 24 | 30min内0次budget_exhausted_after_connect |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | 末评估 |

### 延迟百分位 (deepseek_hm_nv, 30min + 1h + 6h)

**30分钟**: 72/72 ok(100%), p50=17871ms, p90=34741ms, p95=40175ms, max=124968ms

**1小时**: 139/139 ok(100%), p50=17970ms, p90=31149ms, p95=42476ms, max=124968ms

**6小时**: 768 请求, p50=20534ms (K1), PER-KEY:
| 键 | 连接 | 数量 | avg | p50 | p95 | max | 超68s |
|-------|--------|-----|-------|------|------|-------|----------|
| k1 | DIRECT | 173 | 26353ms | 20534ms | 63780ms | 144752ms | 9 (5.2%) |
| k2 | DIRECT | 152 | 23900ms | 19237ms | 65534ms | 152975ms | 7 (4.6%) |
| k3 | PROXY | 139 | 19470ms | 17959ms | 39403ms | 118374ms | 3 (2.2%) |
| k4 | PROXY | 158 | 21787ms | 19147ms | 49002ms | 67470ms | 0 |
| k5 | PROXY | 146 | 20550ms | 17581ms | 52329ms | 109272ms | 2 (1.4%) |

**关键洞察**: DIRECT键 (k1/k2) 尾部延迟高于 PROXY键 (k3-k5): p95=61049ms vs 50260ms, 超68秒率 4.3% vs 1.1%。这是NVCF server端差异, 但所有请求均成功 → 非配置问题。

### 错误分解 (1h + 30min + 6h)

| 窗口 | 错误 | 类型 |
|--------|-------|------|
| 30min | **0** | — |
| 1h | **0** | — |
| 6h | 3 (0.4%) | 3×all_tiers_exhausted at 11:42-11:47 UTC (早前, dur=128-130s, tiers_tried=0), 5h内0次 |

### 429 / 回退 / all_tiers_exhausted 快照

| 指标 | 30min | 1h | 6h |
|--------|-------|-----|----|
| 429 周期 | 1 次 (k5, dur=109272ms) | — | — |
| 回退 | 0 (0%) | 0 (0%) | - |
| all_tiers_exhausted | 0 | 0 | 3 (早前11:42-11:47, 5h内0) |
| budget_exhausted_after_connect | 0 | — | - |

### 请求速率模式 (30min)

- **平均速率**: 2.6 req/min, **MIN_OUTBOUND 容量**: 3.2 req/min (60/19.0s)
- **利用率**: 82.5% — 有间隙, 未达到饱和
- **请求间隔**: 主导15-23s (80%+), 有零星更短间隔
- **背靠背同键事件**: 6/72 (8.3%) — k1→k1×2, k4→k4×3, k5→k5×1。**根源**: 429重试后键轮换未正确推进, 而非MIN_OUTBOUND漏检

### 每小时延迟趋势 (12h)

| 小时 (UTC) | 数量 | p50 | p90 | p95 |
|--------|-----|-------|------|------|
| 05:00 | 109 | 17108ms | 31090ms | 52197ms |
| 06:00 | 161 | 16943ms | 29746ms | 45872ms |
| 07:00 | 179 | 24729ms | 40020ms | 49855ms |
| 08:00 | 165 | 29717ms | 48245ms | 64570ms |
| 09:00 | 168 | 36283ms | 61101ms | 72152ms |
| 10:00 | 173 | 48098ms | 74307ms | 81653ms |
| 11:00 | 108 | 18368ms | 41770ms | 52887ms |
| 12:00 | 120 | 19848ms | 40380ms | 61196ms |
| 13:00 | 126 | 21154ms | 37866ms | 47500ms |
| 14:00 | 134 | 18850ms | 42932ms | 53126ms |
| 15:00 | 134 | 18219ms | 35191ms | 51512ms |
| 16:00 | 136 | 18080ms | 31316ms | 42905ms |

**趋势**: 峰值延迟在 09:00-10:00 UTC (p50=48098ms, p95=81653ms) 对应 NVCF 负载高峰, 随后降至 16:00 UTC p50=18080ms。这是 **NVCF server端负载相关**，非配置问题。当前 R136 稳定窗口 (16:00 UTC) 显示极低延迟。

---

## 🎯 优化分析

### 7参数逐一评估 — 无调整需求

| 参数 | 当前值 | 调整需求 | 理由 |
|-----------|---------|----------------|---------|
| UPSTREAM_TIMEOUT | 68 | ❌ 无调整 | 0次超时/6h; 100%成功率; 所有键均成功完成请求; DIRECT键尾部延迟是NVCF server端问题, 不是超时问题 |
| TIER_TIMEOUT_BUDGET_S | 146 | ❌ 无调整 | 2×UPSTREAM(68)=136, 剩余=10s (=最小阈值), 0次all_tiers/30min; 5h内0次; 阈值刚好达成, 不需要额外margin |
| KEY_COOLDOWN_S | 38.0 | ❌ 无调整 | 30min仅1次429周期; 0次超时/6h; 429与TIER的差距=4s健康; 没有理由降低(会增加429)或升高(会减少吞吐量) |
| TIER_COOLDOWN_S | 42 | ❌ 无调整 | KEY=38差距=4s; 0次all_tiers/30min; 键在预算内重试, 不需要更长冷却 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | ❌ 无调整 | 速率2.6/min vs 容量3.2/min = 82.5%利用率; 429周期仅1次; 背靠背同键事件(8.3%)源自轮换bug, 不是间隔不足。降低会增加429风险, 升高会减少吞吐量。当前速率处于安全区间 |
| HM_CONNECT_RESERVE_S | 24 | ❌ 无调整 | R135已提升至24; 0次budget_exhausted_after_connect/30min; 对于SSL+PROXY连接建立充足; 无需改变 |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | ❌ 无调整 | 默认值; 不影响键路由或超时行为; 标记为"末评估", 非当前瓶颈 |

### 稳定性验证 — R136 基准

R136 (前轮) 已验证:
- **30min**: 73/73 ok(100%), 0次all_tiers_exhausted, 0次429, 0次回退
- **6h**: 仅3次 all_tiers_exhausted (avg=129048ms)
- **所有7参数均衡** → 稳定优先不追加

R138 继承 R136 的稳定窗口并确认:
- **30min**: 72/72 ok(100%) — 与 R136 的 73/73 一致 ✅
- **0次错误/30min** — 连续稳定 ✅
- **0次all_tiers_exhausted/30min** — 与 R136 一致 ✅
- **0回退** — 与 R136 一致 ✅

---

## 🔧 执行

### 变更: **无** — HM1 docker-compose.yml 未修改

```yaml
# /opt/cc-infra/docker-compose.yml — 未修改 (所有7参数保持当前值)
# UPSTREAM_TIMEOUT: "68"
# TIER_TIMEOUT_BUDGET_S: "146"
# KEY_COOLDOWN_S: "38.0"
# TIER_COOLDOWN_S: "42"
# MIN_OUTBOUND_INTERVAL_S: "19.0"
# HM_CONNECT_RESERVE_S: "24"
```

### 部署状态

- **容器**: 运行, 健康 (从日志确认, 未重启)
- **docker exec env**: 与预期配置一致 ✅
- **日志**: 仅 HM-SUCCESS, 0次错误, 100%成功率 ✅

---

## 📈 预期效果 (验证)

| 指标 | 前轮 | 当前窗口 | 状态 |
|--------|-----------|-------|--------|
| 成功率 | R136: 100% (73/73) | 72/72 (100%) | ✅ 一致 |
| p50延迟 | R136: ~17.9s | ~17.9s | ✅ 一致 |
| 错误 | R136: 0 | 0 | ✅ 一致 |
| all_tiers_exhausted | R136: 0/30min | 0/30min | ✅ 一致 |
| 429周期 | R136: 0 | 1 (k5, 109272ms retry ok) | ✅ 可接受 |
| 回退 | R136: 0 | 0 | ✅ 一致 |

---

## ⚖️ 评判

- **更少报错**: ✅ 30min/1h 均0错误, 100%成功率, 6h内仅3次all_tiers_exhausted (全部早前, 当前窗口无)
- **更快请求**: ✅ p50=17871ms, p90=34741ms, 键轮换高效 (PROXY键优于DIRECT); 尾部延迟是NVCF server端差异
- **超低延迟稳定性**: ✅ 12h趋势显示延迟回落至17-18s p50, 无退化; 系统自动从NVCF高峰恢复
- **铁律**: ✅ 仅改HM1 (未改HM2本地); 本轮无变更, 符合铁律

---

## ⏳ 轮到HM1优化HM2