# R707: HM2→HM1 — 零变更轮（R706验证通过，发现FALLBACK_GRAPH历史部署缺口）

## TL;DR
R706部署后~11min数据：6req/3OK(50%)/3ATE(50%) — 低流量窗口，样本过小。所有3 ATE均为双tier耗尽（dsv4p_nv+glm5_2_nv各~61s=~121s），NVCF上游不可用，非配置可修复。深层根因分析发现：R700的FALLBACK_GRAPH配置（dsv4p_nv→glm5_2_nv）在R701重启前未生效，导致pre-R704窗口20个单tier ATE。R704后（fallback生效+BUDGET=94）dsv4p_nv SR升至83.3%——近6h最佳。系统当前稳定，零变更。发现FALLBACK_HEALTH_THRESHOLD为死参数（未被func_health.py使用）。单参数每轮；铁律：只改HM1不改HM2。

---

## 一、当前配置快照（R706 部署后，无变更）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 30 | R701 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | **110** | R706 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | R695 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577 |
| 12 | `NV_INTEGRATE_ENABLED` | (未设置，默认1) | — |
| 13 | `NV_INTEGRATE_MODELS` | "" (空) | R693 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 |
| 15 | `KEY_COOLDOWN_S` | 25 | R162 |

---

## 二、四源漂移检测（Pre-check）

### 2.1 源1 — Compose 文件
```
TIER_TIMEOUT_BUDGET_S: "110"  (line 490, R706 comment)
UPSTREAM_TIMEOUT: "30"  (line 483, R701)
KEY_COOLDOWN_S: "25"  (line 498)
TIER_COOLDOWN_S: "25"  (line 499)
```
→ 无重复值行。单一 `TIER_TIMEOUT_BUDGET_S` 活跃行。

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=110
UPSTREAM_TIMEOUT=30
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
```
→ 全部匹配compose。

### 2.3 源3 — 容器状态
```
nv_gw Up 11 minutes (healthy)
StartedAt: 2026-07-05 04:39:50 +0800 CST (20:39:50 UTC)
Health: {"status": "ok"}
```

### 2.4 源4 — 运行时日志
```
3个ATEN @04:42-04:47 UTC: dsv4p_nv k1+k2 timeout→FASTBREAK→glm5_2_nv k1+k2 timeout→FASTBREAK→ALL-TIERS-FAIL (~121s)
1个fallback成功 @04:43: dsv4p_nv k1+k2 timeout→FASTBREAK→glm5_2_nv k1 success@14.7s (64.5s)
0 ERROR / 0 WARN / 0 429 / 0 empty_200
```

**结论：四源全部通过。无漂移。R706 BUDGET=110已生效。**

---

## 三、数据摘要

### 3.1 总体统计（6h 窗口，created_at UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 125 |
| 成功 (200) | 89 (71.2%) |
| ATE (502) | 36 (28.8%) |

**按模型分组：**
| request_model | cnt | OK | ATE | SR% |
|---------------|-----|-----|-----|-----|
| dsv4p_nv | 81 | 50 | 31 | 61.7% |
| glm5_2_nv | 35 | 33 | 2 | 94.3% |

### 3.2 ATE 深层分析

**按部署周期分组（dsv4p_nv）：**
| 周期 | 时段 (UTC) | 总 | OK | ATE | SR% |
|------|-----------|-----|-----|-----|-----|
| pre-R701 | <18:45 | 38 | 21 | 17 | 55.3% |
| R701 (fallback+BUDGET=82) | 18:45-19:23 | 12 | 6 | 6 | 50.0% |
| R704 (fallback+BUDGET=94) | 19:23-20:39 | 24 | 20 | 4 | **83.3%** ← 最佳 |
| R706 (fallback+BUDGET=110) | 20:39+ | 7 | 3 | 4 | 42.9% |

**按周期（ATE tiers_tried）：**
| 周期 | tiers_tried=1 | tiers_tried=2 |
|------|--------------|--------------|
| pre-R704 | 20 | 7 |
| R704 (BUDGET=94) | 1 | 3 |
| R706 (BUDGET=110) | 0 | 3 |

### 3.3 Budget vs Duration 交叉验证

| Budget | tiers_tried | cnt | avg_dur |
|--------|------------|-----|---------|
| ≤110s | 1 | 23 | 52,005ms |
| ≤110s | 2 | 4 | 103,980ms |
| >110s | 2 | 9 | 121,336ms |

9个双tier ATE全部>110s（avg 121,336ms）。TIER_TIMEOUT_BUDGET_S为per-tier预算（非cross-tier），每个tier独立获得110s。dsv4p_nv消耗~61s，glm5_2_nv消耗~60s，各在预算内。

### 3.4 成功请求分析

**Fallback 成功：**
| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| f（单tier成功） | 75 | 21,776ms | 58,356ms |
| t（tier fallback成功） | 14 | 76,991ms | 99,088ms |

Max success = 99,088ms < BUDGET=110s — 零误杀。

---

## 四、深层根因分析：R700 FALLBACK_GRAPH 部署缺口

### 4.1 发现

R707在分析6h窗口中20个单tier ATE（start_tier_idx=1, tiers_tried=1, avg 52.7s）时发现：这些ATE全部发生在R701重启（18:45 UTC）之前。R701后的单tier ATE仅剩1个。

### 4.2 根因追溯

| 时间 (UTC) | 事件 | FALLBACK_GRAPH状态 |
|-----------|------|-------------------|
| 18:22 | R700提交（config.py添加dsv4p→glm5_2） | 仓库已更新，磁盘未生效 |
| 18:45 | R701部署（docker compose up -d nv_gw） | **首次生效**（volume重新挂载） |
| 19:23 | R704部署 | 持续生效 |
| 20:39 | R706部署 | 持续生效 |

**根因：R700的config.py修改在R701重启前未生效。** R700使用`docker compose restart nv_gw`，R701的`docker compose up -d nv_gw`才触发容器recreate+volume重新挂载。

### 4.3 影响

R700预期SR从49.4%→85%+。实际在R704窗口验证：dsv4p_nv SR 83.3%，与预期一致。R700优化方向正确，部署时机延迟了一个round。

---

## 五、决策

| 参数 | 当前值 | 决策 | 理由 |
|------|--------|------|------|
| `TIER_TIMEOUT_BUDGET_S` | 110 | ❌ 保持 | 仅11min数据，样本过小。R704窗口BUDGET=94+fallback SR 83.3%已很好 |
| `UPSTREAM_TIMEOUT` | 30 | ❌ 保持 | R701刚从25→30，不宜连续上调。待更多数据 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | ❌ 保持 | 当前2次timeout→fallback有效。k3也timeout，3不改善 |
| `FALLBACK_HEALTH_THRESHOLD` | 0.80 | 🔍 记录 | **死参数**：未被func_health.py使用。实际阈值硬编码0.80 |
| 其他 | — | ❌ 保持 | 无数据支持变更 |

**最终决策：零变更轮。** 系统刚重启11min，需等待数据积累。

---

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| 四源漂移 | 全部一致 | ✅ |
| 容器状态 | Up (healthy) | ✅ |
| 运行时日志 | 0 ERROR/WARN/429 | ✅ |
| FALLBACK_GRAPH | dsv4p_nv→glm5_2_nv 生效 | ✅ |
| Post-R704 dsv4p_nv SR | 83.3% | ✅ 最佳 |
| Post-R706 单tier ATE | 0 | ✅ |
| Max success vs BUDGET | 99s < 110s | ✅ 零误杀 |

---

## 七、结论

R707零变更轮。R706 BUDGET=110部署仅11min，数据不足。深层分析揭示R700 FALLBACK_GRAPH在R701重启前未生效的历史缺口——20个单tier ATE的根因。R704后（fallback+BUDGET=94）dsv4p_nv SR达83.3%为近6h最佳。R706后单tier ATE归零，幸存ATE均为NVCF双tier上游耗尽。系统稳定，等待更多数据。

**关键发现：** `FALLBACK_HEALTH_THRESHOLD` env var为死参数（func_health.py未使用）。`TIER_TIMEOUT_BUDGET_S`为per-tier预算（非cross-tier）。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2