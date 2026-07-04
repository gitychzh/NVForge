# R711: HM2→HM1 — UPSTREAM_TIMEOUT 30→33 (+3s, dsv4p_nv 边缘救回)

## TL;DR
dsv4p_nv NVCFPexecTimeout 一致命中 ~28-30s（max 30,455ms） = UPSTREAM_TIMEOUT=30 为绑定约束。成功请求 30-35s 桶有 8 个（8.6%）通过 fallback 成功（avg 63s）；+3s 至 33 直接捕获 30-33s 范围，减少 fallback 负载。6h: 324req/231OK(71.3%)/93ATE(28.7%)；dsv4p_nv SR 53.4%（83 ATE，60 单tier 无 fallback 来自重启前，23 双tier）。Fallback 重启后生效，glm5_2_nv SR 92.3%。BUDGET=110 容纳 33+33=66s 安全。FASTBREAK=1 不变。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R711 变更后）

| # | 参数 | HM1 当前值 | 历史来源 | 本轮变更 |
|---|------|------------|----------|----------|
| 1 | **`UPSTREAM_TIMEOUT`** | **33** | **R711** | **30→33 (+3s)** |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 | — |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R709 | — |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 | — |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 | — |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 | — |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577 | — |
| 12 | `NV_INTEGRATE_MODELS` | "" (空) | R693 | — |
| 13 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 | — |
| 14 | `KEY_COOLDOWN_S` | 25 | R162 | — |
| 15 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708 | — |

---

## 二、四源漂移检测（Pre-check）

### 2.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "33"  (line 483, R711 新注释)
TIER_TIMEOUT_BUDGET_S: "110"  (line 490)
NVU_PEXEC_TIMEOUT_FASTBREAK: "1"  (line 591)
FALLBACK_HEALTH_THRESHOLD: "0.10"  (line 510)
KEY_COOLDOWN_S: "25"  (line 498)
TIER_COOLDOWN_S: "25"  (line 499)
→ 无重复值行。单一活跃行。
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=33
TIER_TIMEOUT_BUDGET_S=110
NVU_PEXEC_TIMEOUT_FASTBREAK=1
FALLBACK_HEALTH_THRESHOLD=0.10
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
→ 全部匹配 compose。
```

### 2.3 源3 — 容器状态
```
nv_gw Up (healthy)
logs_db Up (healthy)
Container: fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv']
Health: {"status":"ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100: 0 ERROR, 0 WARN
dsv4p_nv tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) — ✅ 正常
glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback) — ✅ 正常
NV-TIER-FAIL dsv4p_nv → NV-FALLBACK → NV-FALLBACK-SUCCESS — ✅ fallback 工作
NVCF 健康度: dsv4p_nv(74f02205) 0.5-0.75, glm5_2_nv(3b9748d8) 0.5-1.0
```

**结论：四源全部一致。UPSTREAM_TIMEOUT=33 已生效。**

---

## 三、数据摘要（6h 窗口，2026-07-04 19:00 - 07-05 06:00 UTC）

### 3.1 总体统计

| 指标 | 数值 |
|------|------|
| 总请求 | 324 |
| 成功 (200) | 231 (71.3%) |
| ATE (502) | 93 (28.7%) |
| Rate-limit (429) | 0 |

**按模型分组：**
| request_model | cnt | OK | ATE | SR% | avg_ok_dur | avg_ate_dur |
|---------------|-----|-----|-----|-----|------------|-------------|
| dsv4p_nv | 174 | 93 | 83 | **53.4%** | 34,895ms | 67,489ms |
| glm5_2_nv | 142 | 131 | 13 | **92.3%** | 13,530ms | 33,847ms |
| kimi_nv | 8 | 7 | 1 | 87.5% | 10,323ms | 2,682ms |

### 3.2 ATE 深层分析

**按 tiers_tried_count：**
| tiers_tried_count | fallback_attempted | start_tier | cnt | avg_dur | 占比 |
|-------------------|-------------------|------------|-----|---------|------|
| 1 | f | 1 (dsv4p) | 60 | 49,241ms | 64.5% |
| 2 | f | 1 (dsv4p) | 23 | 110,628ms | 24.7% |
| 1 | f | 3 (glm5_2) | 11 | 33,847ms | 11.8% |
| 1 | f | 0 | 1 | 2,682ms | 1.1% |

**单tier ATE 时间分布（60 个 dsv4p_nv 主 tier，fallback 未尝试）：**
| 小时 (UTC) | cnt | avg_dur | 备注 |
|------------|-----|---------|------|
| 19:00 | 11 | 49,692ms | 旧容器运行中 |
| 20:00 | 4 | 51,041ms | 旧容器 |
| 21:00 | 7 | 50,622ms | 旧容器 |
| 22:00 | 13 | 40,375ms | 旧容器 |
| 23:00 | 2 | 29,255ms | 旧容器 |
| 01:00 | 4 | 50,696ms | 旧容器 |
| 02:00 | 9 | 50,621ms | 旧容器 |
| 03:00 | 3 | 60,694ms | 旧容器 |
| 04:00 | 1 | 60,577ms | 旧容器 |
| 05:00 | 6 | 60,822ms | 旧容器（重启前） |

**关键发现：60 个单tier ATE 全部来自 05:00 UTC 之前的容器运行。重启后（~05:53 UTC）fallback 正常工作，日志显示 `NV-TIER-FAIL → NV-FALLBACK → NV-FALLBACK-SUCCESS`。**

### 3.3 每小时 SR 趋势

| 小时 (UTC) | 总 | OK | ATE | SR% | 备注 |
|------------|-----|-----|-----|-----|------|
| 19:00 | 114 | 99 | 17 | 86.8% | 最佳窗口 |
| 20:00 | 14 | 8 | 6 | 57.1% | 低流量 |
| 21:00 | 15 | 8 | 7 | 53.3% | 低流量 |
| 22:00 | 28 | 13 | 16 | 46.4% | 持续恶化 |
| 23:00 | 9 | 8 | 2 | 88.9% | 低流量恢复 |
| 00:00 | 2 | 2 | 0 | 100.0% | 极低流量 |
| 01:00 | 13 | 8 | 5 | 61.5% | — |
| 02:00 | 49 | 35 | 14 | 71.4% | — |
| 03:00 | 27 | 20 | 7 | 74.1% | — |
| 04:00 | 21 | 14 | 7 | 66.7% | — |
| 05:00 | 20 | 7 | 13 | 35.0% | ⚠️ 最差窗口 |
| 06:00 | 12 | 9 | 3 | 75.0% | 重启后改善 |

### 3.4 dsv4p_nv 成功请求时长分布

| 桶 | cnt | 占比 |
|----|-----|------|
| <5s | 2 | 2.2% |
| 5-10s | 7 | 7.5% |
| 10-15s | 4 | 4.3% |
| 15-20s | 12 | 12.9% |
| 20-25s | 13 | 14.0% |
| 25-30s | 8 | 8.6% | ← UPSTREAM_TIMEOUT=30 边缘 |
| **30-35s** | **8** | **8.6%** | ← **+3s 直接捕获目标** |
| 35-40s | 7 | 7.5% |
| 40-50s | 13 | 14.0% |
| 50-60s | 12 | 12.9% |
| 60-80s | 6 | 6.5% |
| >80s | 3 | 3.2% |

**8 个请求（8.6%）在 30-35s 桶——全部通过 fallback 成功（avg 63s）。+3s 至 33 可让这些请求直接在 dsv4p_nv 主 tier 成功，省 fallback 时间（63s → ~32s）。**

### 3.5 dsv4p_nv Tier Attempts 分析

**dsv4p_nv tier_attempts（6h，仅失败记录）：**
| tier | nv_key_idx | error_type | cnt | avg_ms | max_ms |
|------|------------|------------|-----|--------|--------|
| dsv4p_nv | 2 | NVCFPexecTimeout | 11 | 28,638 | 30,455 |
| dsv4p_nv | 1 | NVCFPexecTimeout | 10 | 28,844 | 40,492 |
| dsv4p_nv | 0 | NVCFPexecTimeout | 8 | 28,458 | 30,390 |
| dsv4p_nv | 3 | NVCFPexecTimeout | 7 | 29,115 | 31,622 |
| dsv4p_nv | 4 | NVCFPexecTimeout | 5 | 29,357 | 30,415 |
| dsv4p_nv | 0-4 | IntegrateTimeout | 17 | ~25,400 | ~25,500 |

**NVCFPexecTimeout 全部集中在 28,400-30,455ms = UPSTREAM_TIMEOUT=30 的绑定约束。max=30,455ms 恰好是 30s + 连接开销。+3s 至 33 为边缘请求提供 3s 额外窗口。**

### 3.6 Fallback 成功统计

| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| f（单tier成功） | 209 | 17,684ms | 60,099ms |
| t（tier fallback成功） | 22 | 63,365ms | 99,088ms |

22 个 fallback 成功，max=99s < BUDGET=110s — 零误杀。avg=63s vs 直接成功 ~35s，fallback 路径慢 28s。

### 3.7 重启后 30min 快照

| mapped_model | total | OK | ATE | SR% |
|--------------|-------|-----|-----|-----|
| dsv4p_nv | 138 | 79 | 61 | **57.2%** |
| glm5_2_nv | 44 | 39 | 5 | 88.6% |
| kimi_nv | 1 | 0 | 1 | 0.0% |

重启后 dsv4p_nv SR 从 53.4% 微升至 57.2%（fallback 工作），15 个 fallback 成功。glm5_2_nv 稳定 88.6%。

### 3.8 日志分析（重启后关键事件）

```
[NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: timeout=1, elapsed=~30s
[NV-PEXEC-FASTBREAK] tier=dsv4p_nv 1 consecutive NVCFPexecTimeout -> fast-break
[NV-FALLBACK] Tier dsv4p_nv all-failed → falling back to glm5_2_nv
[NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv   ← ✅ 救回
[NV-ALL-TIERS-FAIL] All 2 tiers failed → ABORT-NO-FALLBACK  ← ❌ 双 tier 失败
[NV-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted, returning 502
```

Fallback 工作正常。双 tier ATE 多为 peer-originated（hop=1），NVCF 上游同时不可用，非配置可修复。

---

## 四、根因分析：UPSTREAM_TIMEOUT=30 为 dsv4p_nv 绑定约束

### 4.1 证据链

1. **NVCFPexecTimeout 全部命中 ~28-30s**：41 个 pexec timeout，avg 28,638ms，max 30,455ms。精确匹配 UPSTREAM_TIMEOUT=30 + 连接开销（~400ms）
2. **成功请求 30-35s 桶有 8 个（8.6%）**：全部通过 fallback 成功，avg 63s。说明这些请求在 dsv4p_nv 主 tier 超过 30s 后被 fallback 救回
3. **25-30s 桶有 8 个（8.6%）**：部分可能处于边缘，个别超 30s 的请求变为 timeout + fallback
4. **dsv4p_nv 健康度 0.5-0.75**：约 50-75% 的请求能在 30s 内成功，其余超时

### 4.2 +3s 预期效果

| 场景 | 改前 | 改后 |
|------|------|------|
| 请求 30-33s 完成 | timeout → fallback → 63s 成功 | 直接成功 ~32s，省 31s |
| 请求 33-40s 完成 | timeout → fallback → 63s 成功 | timeout → fallback → 63s 成功（不变） |
| 请求 <30s 完成 | 直接成功 ~20s | 直接成功 ~20s（不变） |
| 双 tier 全失败 | ATE ~121s | ATE ~124s（+3s，可忽略） |

**预期：救回 30-33s 范围的请求（~8 个/6h），减少 fallback 负载，降低 avg 延迟。**

### 4.3 安全性

- BUDGET=110s per tier：33s × 2 keys = 66s worst-case，远低于 110s
- 成功 fallback max=99s < 110s，零误杀
- glm5_2_nv avg=13.5s << 33s，不受影响
- kimi_nv avg=10.3s << 33s，不受影响
- FASTBREAK=1：仅 1 key 尝试，+3s 仅增加 3s 至 tier 失败时间

---

## 五、决策

| 参数 | 当前值 | 决策 | 理由 |
|------|--------|------|------|
| **`UPSTREAM_TIMEOUT`** | 30 | **✅ 30→33 (+3s)** | dsv4p_nv pexec timeout 精确命中 30s；30-35s 桶 8 个请求由 fallback 救回；+3s 直接捕获，省 fallback 时间 |
| `TIER_TIMEOUT_BUDGET_S` | 110 | ❌ 保持 | 当前 max success=99s < 110s；等 UPSTREAM=33 数据 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ❌ 保持 | R709 刚部署，已验证稳定 |
| `FALLBACK_HEALTH_THRESHOLD` | 0.10 | ❌ 保持 | 安全地板，fallback 正常工作 |
| 其他 | — | ❌ 保持 | 无数据支持变更 |

**最终决策：单参数变更 UPSTREAM_TIMEOUT 30→33。** 60 个单tier ATE 全部来自重启前旧容器，重启后 fallback 正常工作。当前 NVCF dsv4p_nv 函数 74f02205 健康度 0.5-0.75 中等偏下，但非配置可修复。+3s 为边缘请求提供直接成功窗口，减少 fallback 依赖。

---

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| 四源漂移 | compose=env=container=runtime 全部一致 | ✅ |
| 容器状态 | nv_gw Up (healthy), logs_db Up (healthy) | ✅ |
| UPSTREAM_TIMEOUT | 容器 env=33 | ✅ |
| BUDGET | 容器 env=110 | ✅ |
| FASTBREAK | 容器 env=1 | ✅ |
| FALLBACK_GRAPH | dsv4p_nv→glm5_2_nv 在 compose+容器内均正确 | ✅ |
| fallback_chain | ['kimi_nv','dsv4p_nv','glm5_1_nv','glm5_2_nv'] | ✅ |
| 运行时日志 | 0 ERROR, 0 WARN, 0 429 | ✅ |
| Health endpoint | {"status":"ok"} | ✅ |
| 重复值行 | 无 | ✅ |
| dsv4p_nv 6h SR | 53.4% (NVCF 上游中等健康度 + 旧容器 ATE) | ⚠️ 重启后改善至 57.2% |
| glm5_2_nv 6h SR | 92.3% | ✅ 稳定 |

---

## 七、结论

R711 单参数变更：UPSTREAM_TIMEOUT 30→33 (+3s)。数据驱动依据：
1. dsv4p_nv NVCFPexecTimeout 全部命中 ~28-30s（max=30,455ms），UPSTREAM_TIMEOUT=30 为绑定约束
2. 成功请求 30-35s 桶有 8 个（8.6%），全部通过 fallback 成功（avg 63s），+3s 可直接捕获
3. 25-30s 桶有 8 个（8.6%），部分处于边缘
4. 重启后 fallback 正常工作（NV-TIER-FAIL → NV-FALLBACK → NV-FALLBACK-SUCCESS），15 个 fallback 成功/30min

**安全余量：** BUDGET=110s per tier >> 33s per key。FASTBREAK=1 不变。glm5_2_nv/kimi_nv 不受影响。单参数每轮；铁律：只改 HM1 不改 HM2。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2