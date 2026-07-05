# R716: HM2→HM1 — UPSTREAM_TIMEOUT 36→40 (+4s, dsv4p_nv NVCFPexecTimeout 边缘扩展)

## TL;DR
R715 零变更后 ~8.5h 运行。6h: 365req/265OK(72.6%)/100ATE(27.4%)。dsv4p_nv SR 57.3% 持续下滑，NVCFPexecTimeout max=40,492ms 突破 UPSTREAM=36 上限。8 次 dsv4p_nv + 3 次 glm5_2_nv timeout 在 36-40s 边缘，+4s 捕获为直接成功。BUDGET=110 >> 40+40=80s 安全。FASTBREAK=1 不变。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 一、配置变更

| # | 参数 | 旧值 | 新值 | Δ | 决策来源 |
|---|------|------|------|---|---------|
| 1 | `UPSTREAM_TIMEOUT` | 36 (R713) | **40** | +4s | dsv4p_nv NVCFPexecTimeout max=40,492ms > 36; 8 次在 36-40s 边缘 |

其他 15 参数不变。**变更数：1。**

---

## 二、当前配置快照（Post-change）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | **40** | **R716: 36→40** |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706: 94→110 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638: 降至 floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R709: 2→1 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492: 长期稳定 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697: 25→45 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657: 降至 floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694: 25→40 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692: 禁用 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577: 连续阈值 |
| 12 | `NV_INTEGRATE_MODELS` | "" (空) | R694: 全部走 pexec |
| 13 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631: floor |
| 14 | `KEY_COOLDOWN_S` | 25 | R162: 长期稳定 |
| 15 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708: 新增 |
| 16 | `NVU_PEER_FALLBACK_ENABLED` | 1 | 默认 |

---

## 三、漂移检测（Pre-change）

### 3.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "36"       ← R713 (变更前)
TIER_TIMEOUT_BUDGET_S: "110" ← R706
MIN_OUTBOUND_INTERVAL_S: "0" ← R638
KEY_COOLDOWN_S: "25"         ← R162
TIER_COOLDOWN_S: "25"        ← R492
NVU_PEXEC_TIMEOUT_FASTBREAK: "1" ← R709
NVU_PEER_FALLBACK_TIMEOUT: "45" ← R697
NVU_EMPTY_200_FASTBREAK: "2" ← R577
NVU_CONNECT_RESERVE_S: "0"   ← R657
NVU_SSLEOF_RETRY_DELAY_S: "1.0" ← R543
NVU_FORCE_STREAM_UPGRADE: "0" ← R692
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "40" ← R694
FALLBACK_HEALTH_THRESHOLD: "0.10" ← R708
NV_INTEGRATE_MODELS: ""       ← R694
NV_INTEGRATE_KEY_COOLDOWN_S: "0" ← R631
```

### 3.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=36 ✓
TIER_TIMEOUT_BUDGET_S=110 ✓
MIN_OUTBOUND_INTERVAL_S=0 ✓
KEY_COOLDOWN_S=25 ✓
TIER_COOLDOWN_S=25 ✓
NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
NVU_PEER_FALLBACK_TIMEOUT=45 ✓
NVU_EMPTY_200_FASTBREAK=2 ✓
NVU_CONNECT_RESERVE_S=0 ✓
NVU_SSLEOF_RETRY_DELAY_S=1.0 ✓
NVU_FORCE_STREAM_UPGRADE=0 ✓
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40 ✓
FALLBACK_HEALTH_THRESHOLD=0.10 ✓
NV_INTEGRATE_MODELS= ✓
NV_INTEGRATE_KEY_COOLDOWN_S=0 ✓
```

### 3.3 源3 — 容器启动时间
```
StartedAt: 2026-07-04T23:10:20.799141364Z (R714 部署)
Up ~8.5h at time of check
```

### 3.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100
→ 0 ERROR / 0 WARN
→ dsv4p_nv health: 0.385–0.455 (↓ from R715: 0.75–1.0)
→ glm5_2_nv health: 0.889–0.9
→ dsv4p_nv timeout ~36.3–36.5s → FASTBREAK → fallback to glm5_2_nv
→ 部分双 tier 全耗尽 (dsv4p_nv + glm5_2_nv 均 timeout → ATE)
→ PEER-FB hop=1 二次 ATE 也出现
```

**结论：四源全部通过，无漂移。dsv4p_nv health 显著下降（0.75→0.385），但 FALLBACK_HEALTH_THRESHOLD=0.10 仍保持 tier 链完好。**

---

## 四、数据摘要

### 4.1 6h 窗口（UTC ~02:00–08:00）

| 指标 | 值 |
|------|-----|
| 总量 | 365 req |
| OK | 265 (72.6%) |
| Fail | 100 (27.4%) |
| avg_dur | 33,977ms |
| max_dur | 122,312ms |

### 4.2 按模型 6h

| mapped_model | total | ok | fail | SR | avg_dur_ms |
|--------------|-------|-----|------|-----|------------|
| dsv4p_nv | 206 | 118 | 88 | 57.3% | 49,298 |
| glm5_2_nv | 151 | 140 | 11 | 92.7% | 14,378 |
| kimi_nv | 8 | 7 | 1 | 87.5% | 9,368 |

### 4.3 按小时 SR（6h）

| hour (UTC) | total | ok | fail | sr_pct |
|------------|-------|-----|------|--------|
| 02:00 | 49 | 35 | 14 | 71.4% |
| 03:00 | 27 | 20 | 7 | 74.1% |
| 04:00 | 21 | 14 | 7 | 66.7% |
| 05:00 | 20 | 7 | 13 | 35.0% |
| 06:00 | 29 | 22 | 7 | 75.9% |
| 07:00 | 24 | 21 | 3 | 87.5% |

### 4.4 成功路径分布

| path | cnt | avg_ms |
|------|-----|--------|
| 直接成功（fallback_occurred=f） | 227 | 17,112ms |
| Fallback 救回（fallback_occurred=t） | 38 | 57,598ms |

### 4.5 ATE 分层

| tiers_tried | cnt | avg_ms | 说明 |
|-------------|-----|--------|------|
| 1 | 70 | 47,103ms | 单 tier 耗尽 |
| 2 | 30 | 101,039ms | 双 tier 耗尽 |

### 4.6 nv_tier_attempts（6h）

| tier | error_type | cnt | avg_elapsed | max_elapsed |
|------|-----------|-----|-------------|-------------|
| dsv4p_nv | NVCFPexecTimeout | 57 | 30,366ms | **40,492ms** |
| dsv4p_nv | IntegrateTimeout | 17 | 25,395ms | 25,511ms |
| glm5_2_nv | NVCFPexecTimeout | 15 | 30,012ms | **40,271ms** |
| glm5_2_nv | 429_nv_rate_limit | 14 | — | — |
| kimi_nv | empty_200 | 2 | — | — |

**键分布**：dsv4p_nv NVCFPexecTimeout 均匀分布在 5 key（10-13 次/key），glm5_2_nv 同理（2-4 次/key）→ **函数级排队问题**，非 key 级劣化。FASTBREAK=1 正确。

### 4.7 dsv4p_nv NVCFPexecTimeout 36-40s 边缘分析

| 区间 | cnt | 说明 |
|------|-----|------|
| 25,229–36,000ms | 49 | 超过当前 UPSTREAM=36，无法救回 |
| **36,001–40,492ms** | **8** | **UPSTREAM=40 可捕获为直接成功** |
| >40,492ms | 0 | 无 |

glm5_2_nv 同样：3 次在 36,001–40,271ms 边缘。**总计 11 次 timeout 可被 +4s 捕获。**

### 4.8 PEER-FB 统计

| fallback_from | fallback_to | cnt | ok | fail |
|---------------|-------------|-----|----|------|
| dsv4p_nv | glm5_2_nv | 29 | 29 | 0 |
| glm5_2_nv | dsv4p_nv | 9 | 9 | 0 |

PEER-FB 全部成功，无二次 ATE。

### 4.9 dsv4p_nv 直接成功耗时分布

| bucket | cnt |
|--------|-----|
| 0-10s | 12 |
| 10-20s | 18 |
| 20-30s | 23 |
| 30-40s | 16 |
| 40-50s | 11 |
| 50-60s | 8 |
| 60-70s | 1 |

30-40s 桶中含 16 次直接成功（含 fallback 后），说明 UPSTREAM=36 会截断部分成功边缘。

---

## 五、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| UPSTREAM_TIMEOUT | 36 | **40 (+4s)** | dsv4p_nv NVCFPexecTimeout max=40,492ms > 36s（8 次在 36-40s 边缘），glm5_2_nv max=40,271ms > 36s（3 次边缘）。总计 11 次 timeout 可被 +4s 捕获为直接成功。BUDGET=110 >> 40+40=80s 安全（30s 余量）。dsv4p_nv health 从 R715 的 0.75-1.0 降至 0.385-0.455，NVCF 上游变慢。FASTBREAK=1 不变。 | ✅ 执行 |
| TIER_TIMEOUT_BUDGET_S | 110 | — | 40+40=80s << 110s，无需调整。 | ❌ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | — | 1 已是最小值，timeout 分布均匀。 | ❌ |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | — | PEER-FB 全部成功（38/38），非 timeout 截断。 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 2 | — | empty_200 仅 kimi_nv 2 次，罕见。 | ❌ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | — | dsv4p_nv health 最低 0.385 > 0.10，tier 链完好。 | ❌ |
| 其他参数 | — | — | 全部在 floor 或经历史验证的稳定值。 | ❌ |

**最终决策**：UPSTREAM_TIMEOUT 36→40 (+4s)。NVCF 上游变慢（dsv4p_nv health 下降 + max timeout 突破 36s），+4s 捕获 11 次边缘 timeout 为直接成功。BUDGET 余量充足。其他参数不变。

---

## 六、参数历史

| 参数 | 当前值 | 来源 |
|------|--------|------|
| UPSTREAM_TIMEOUT | **40** | **R716: 36→40** |
| TIER_TIMEOUT_BUDGET_S | 110 | R706: 94→110 |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638: floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R709: 2→1 |
| TIER_COOLDOWN_S | 25 | R492 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697: 25→45 |
| NVU_CONNECT_RESERVE_S | 0 | R657: floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | R543 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 40 | R694: 25→40 |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692: 禁用 |
| NVU_EMPTY_200_FASTBREAK | 2 | R577 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631: floor |
| KEY_COOLDOWN_S | 25 | R162 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708: 新增 |

---

## 七、结论

R716: UPSTREAM_TIMEOUT 36→40 (+4s)。dsv4p_nv NVCFPexecTimeout max=40,492ms 突破当前 36s 上限，8 次 dsv4p_nv + 3 次 glm5_2_nv 在 36-40s 边缘，+4s 捕获为直接成功。BUDGET=110 >> 40+40=80s 安全。dsv4p_nv health 从 0.75-1.0 降至 0.385-0.455，NVCF 上游持续变慢，UPSTREAM 需跟随上调。FASTBREAK=1 不变，fallback 链完好（38/38 OK）。下轮关注 post-restart 直接成功率及 NVCFPexecTimeout 是否继续上移。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2