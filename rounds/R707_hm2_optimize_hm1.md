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
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
NVU_FORCE_STREAM_UPGRADE=0
NVU_EMPTY_200_FASTBREAK=2
NV_INTEGRATE_MODELS=""
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FALLBACK_TIMEOUT=45
```
→ 无重复值行。单一 `TIER_TIMEOUT_BUDGET_S` 活跃行。

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=110
UPSTREAM_TIMEOUT=30
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
NVU_FORCE_STREAM_UPGRADE=0
NVU_EMPTY_200_FASTBREAK=2
NV_INTEGRATE_MODELS=
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FALLBACK_TIMEOUT=45
```

### 2.3 源3 — 容器状态
```
nv_gw Up 11 minutes (healthy)
StartedAt: 2026-07-05 04:39:50 +0800 CST (20:39:50 UTC)
RestartCount: 0
Health: {"status": "ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 | grep -iE "error|warn|timeout|fail|abort|exhausted|429|ATE|all_tiers"
→ 3个ATEN @04:42-04:47 UTC:
  dsv4p_nv k1+k2 timeout@30.3s → FASTBREAK → glm5_2_nv k1+k2 timeout@30.3s → FASTBREAK → ALL-TIERS-FAIL → 502
  Duration: 121,370ms / 121,334ms / 121,430ms — 全部双tier耗尽
→ 1个fallback成功 @04:43: dsv4p_nv k1+k2 timeout→FASTBREAK → glm5_2_nv k1 success@14.7s
→ 2个单key成功 @04:42 (8.7s) + @04:54 (23.3s)
→ 0 ERROR / 0 WARN / 0 429 / 0 empty_200
→ 2 BrokenPipeError (client disconnect before ATE response)
```

**结论：四源全部通过。无漂移。容器11min前重启，R706 BUDGET=110已生效。**

---

## 三、数据摘要

### 3.1 总体统计（6h 窗口，created_at UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 125 |
| 成功 (200) | 89 (71.2%) |
| ATE (502) | 36 (28.8%) |
| 其他失败 | 0 |

**按路径分组：**
| upstream_type | cnt | OK | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 88 | 88 | 30,701ms | 30,717ms | 99,088ms |
| (NULL, ATE) | 37 | 1 | 72ms | 73,298ms | 121,430ms |

**错误分类：** 全部36 ATE为 `all_tiers_exhausted`。

**按模型分组：**
| request_model | cnt | OK | ATE | SR% |
|---------------|-----|-----|-----|-----|
| dsv4p_nv | 81 | 50 | 31 | 61.7% |
| glm5_2_nv | 35 | 33 | 2 | 94.3% |
| kimi_nv | 1 | 0 | 1 | 0% |

### 3.2 ATE 深层分析

**按 tiers_tried_count：**
| tiers_tried_count | cnt | avg_dur | 占比 |
|-------------------|-----|---------|------|
| 1（单tier） | 23 | 52,005ms | 63.9% |
| 2（双tier） | 13 | 115,996ms | 36.1% |

**按 start_tier_idx（单tier ATE，tiers_tried=1）：**
| start_tier_idx | cnt | avg_dur | 含义 |
|----------------|-----|---------|------|
| 0 | 1 | 2,682ms | 边缘case |
| 1 (dsv4p_nv) | 20 | 51,619ms | dsv4p耗尽，无fallback |
| 3 (glm5_2_nv) | 2 | 80,525ms | glm5_2直接耗尽 |

**按部署周期分组（dsv4p_nv）：**
| 周期 | 时段 (UTC) | 总 | OK | ATE | SR% |
|------|-----------|-----|-----|-----|-----|
| pre-R701 | <18:45 | 38 | 21 | 17 | 55.3% |
| R701 (fallback+BUDGET=82) | 18:45-19:23 | 12 | 6 | 6 | 50.0% |
| R704 (fallback+BUDGET=94) | 19:23-20:39 | 24 | 20 | 4 | **83.3%** ← 最佳 |
| R706 (fallback+BUDGET=110) | 20:39+ | 7 | 3 | 4 | 42.9% |

**按周期分组（ATE，按tiers_tried_count）：**
| 周期 | tiers_tried=1 | tiers_tried=2 | 总计 |
|------|--------------|--------------|------|
| pre-R704 | 20 | 7 | 27 |
| R704 (BUDGET=94) | 1 | 3 | 4 |
| R706 (BUDGET=110) | 0 | 3 | 3 |

### 3.3 Budget vs Duration 交叉验证

| Budget | tiers_tried | cnt | avg_dur |
|--------|------------|-----|---------|
| ≤110s | 1 | 23 | 52,005ms |
| ≤110s | 2 | 4 | 103,980ms |
| >110s | 2 | 9 | 121,336ms |

9个双tier ATE的duration全部>110s（avg 121,336ms），说明BUDGET=110对双tier场景无影响——两个tier各自有110s预算，dsv4p_nv消耗~61s，glm5_2_nv消耗~60s，各在budget内。这是代码设计（per-tier budget），不是bug。

### 3.4 成功请求分析

**Fallback 成功：**
| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| f（单tier成功） | 75 | 21,776ms | 58,356ms |
| t（tier fallback成功） | 14 | 76,991ms | 99,088ms |

Max success = 99,088ms < BUDGET=110s — 零误杀。

**dsv4p_nv 成功请求 duration 分布：**
| dur_bucket | cnt |
|------------|-----|
| <30s | 22 |
| 30-35s | 2 |
| 35-60s | 17 |
| >60s | 8 |

### 3.5 运行时日志关键事件

**04:42-04:47 UTC 连续3个双tier ATE：**
```
[04:42:52] dsv4p_nv k1+k2 timeout@30.3s → FASTBREAK
           → glm5_2_nv k1+k2 timeout@30.3s → FASTBREAK
           → ALL-TIERS-FAIL (2 tiers, 121,369ms) → 502
[04:45:58] 同上模式，121,334ms → 502
[04:47:09] 同上模式，121,430ms → 502
```

**04:43:52 成功fallback：**
```
dsv4p_nv k1+k2 timeout@30.3s → FASTBREAK → glm5_2_nv k1 success@14.7s → 200
Duration: 64,466ms. 证明fallback链路正常工作。
```

**04:54:16 健康度快照：**
```
health={'74f02205': 0.2, '3b9748d8': 0.25}
tier_chain=['dsv4p_nv', 'glm5_2_nv'] — glm5_2仍在链中
[NV-FUNC-HEALTH] dsv4p_nv primary=74f02205 unhealthy → switched to 8915fd28
```
→ dsv4p_nv在function级别完成健康切换（74f02205→8915fd28），tier级别fallback链仍包含glm5_2_nv。

---

## 四、深层根因分析：R700 FALLBACK_GRAPH 部署缺口

### 4.1 发现过程

R707在分析6h窗口中20个单tier ATE（start_tier_idx=1, tiers_tried=1, avg 52.7s）时发现：这些ATE全部发生在R701重启（18:45 UTC）之前。R701之后的单tier ATE仅剩1个。

### 4.2 根因追溯

| 时间 (UTC) | 事件 | FALLBACK_GRAPH状态 |
|-----------|------|-------------------|
| 18:22 | R700提交（config.py添加dsv4p→glm5_2） | 仓库已更新，磁盘未生效 |
| 18:45 | R701部署（docker compose up -d nv_gw） | 首次生效！volume-mounted源码由up -d重新挂载 |
| 19:23 | R704部署（docker compose up -d nv_gw） | 持续生效 |
| 20:39 | R706部署（docker compose up -d nv_gw） | 持续生效 |

**根因：R700的config.py修改（FALLBACK_GRAPH添加dsv4p_nv→glm5_2_nv）在R701重启前未生效。** 虽然源码是volume-mounted（`./proxy/nv-gw/gateway:/app/gateway`），但R700使用的是`docker compose restart nv_gw`，而R701的`docker compose up -d nv_gw`才触发了完整的容器recreate（触发volume重新挂载）。

### 4.3 证据链

| 证据 | 数值 |
|------|------|
| pre-R701单tier ATE | 20个（全部fallback_actually_attempted=f） |
| R701后单tier ATE | 仅1个（R704窗口，60,577ms，边缘case） |
| R704后dsv4p_nv SR | 83.3%（24req/20OK/4ATE）——显著提升 |
| 运行时日志 | 所有R701后请求tier_chain均包含glm5_2_nv |

### 4.4 影响评估

R700声称预期SR从49.4%→85%+。实际效果在R704窗口得到验证：dsv4p_nv SR 83.3%，与预期一致。R700的优化方向正确，只是部署时机延迟了一个round（R701才真正生效）。

---

## 五、决策分析

### 5.1 参数决策表

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| `TIER_TIMEOUT_BUDGET_S` | 110 | — | Post-R706仅11min，3个双tier ATE(~121s)均为NVCF上游不可用（两tier各自完整耗尽），非预算可修复。R704窗口BUDGET=94+fallback已达83.3% SR。等待更多数据。 | ❌ 保持 |
| `UPSTREAM_TIMEOUT` | 30 | 35 | dsv4p_nv pexec timeout@30.3s一致。30-35s区间仅2成功请求（当前30s超时导致此区间请求失败）。提到35s可让26-35s请求直接在k1成功，减少key cycling。但BUDGET=110足够容纳2×35=70s。R701刚从25→30，不宜连续上调。待更多数据验证。 | ❌ 保持（待观察） |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | — | 当前2次连续timeout→fastbreak后fallback到glm5_2_nv。glm5_2_nv成功率94.3%，fallback链路有效。改为3会让dsv4p_nv尝试k3，但日志显示k3也timeout（30.3s），不改善。 | ❌ 保持 |
| `FALLBACK_HEALTH_THRESHOLD` | 0.80 | — | ⚠️ **死参数**：env var定义但未被func_health.py使用。实际阈值硬编码HEALTH_THRESHOLD=0.80。当前glm5_2 function健康度0.25时仍可fallback（因为MIN_SAMPLES=5保护，冷启动期健康度=1.0）。未来可能成为瓶颈。 | 🔍 记录（未来优化目标） |
| 其他所有参数 | — | — | 无数据支持变更。 | ❌ 保持 |

### 5.2 最终决策：零变更轮

**理由：**
1. R706部署仅11min，样本过小（6req），无法判断BUDGET=110效果
2. R704窗口（fallback生效+BUDGET=94）dsv4p_nv SR 83.3%——最佳历史数据
3. 所有post-R704 ATE均为双tier NVCF上游耗尽，非配置可修复
4. 运行时健康：0 ERROR, 0 WARN, 0 429, 0 empty_200
5. 单tier ATE已从20个（pre-R701）降至0个（R706窗口）——R700 fallback+R706 budget联合生效

---

## 六、执行记录

1. **SSH 到 HM1** — 数据收集（docker logs, env, container status, compose config）
2. **四源验证** — 全部通过，无漂移
3. **DB 深度分析** — 6h窗口，ATE分类（tiers_tried_count, start_tier_idx, 部署周期），成功请求duration分布，预算交叉验证
4. **根因挖掘** — 追溯R700 FALLBACK_GRAPH部署缺口，确认R701才真正生效
5. **代码审查** — 发现FALLBACK_HEALTH_THRESHOLD为死参数，budget为per-tier而非cross-tier
6. **决策** — 零变更，等待更多R706数据积累

---

## 七、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| Compose line 490 | `"110"` | ✅ |
| `docker compose config` | `110` | ✅ |
| 容器 env | `110` | ✅ |
| 容器状态 | Up 11 min (healthy) | ✅ |
| Health endpoint | `{"status": "ok"}` | ✅ |
| 重复值行（TIER_TIMEOUT_BUDGET） | 无（仅 line 490 活跃） | ✅ |
| 运行时日志 | 0 ERROR, 0 WARN, 0 429 | ✅ |
| FALLBACK_GRAPH | dsv4p_nv→glm5_2_nv 生效 | ✅ |
| Post-R704 dsv4p_nv SR | 83.3% (24/20/4) | ✅ 最佳 |
| Post-R706 单tier ATE | 0 | ✅ |
| Post-R706 SR | 50% (6req/3OK) | ⚠️ 样本过小 |
| Max success | 99,088ms < 110s | ✅ 零误杀 |

---

## 八、结论

R707零变更轮。R706 BUDGET=110部署仅11min，样本过小（6req/3OK/3ATE），不足以评估效果。深层分析发现R700的FALLBACK_GRAPH（dsv4p_nv→glm5_2_nv）在R701重启前未生效，导致pre-R704窗口20个单tier ATE。R704后（fallback生效+BUDGET=94）dsv4p_nv SR达83.3%——近6h最佳。R706后单tier ATE归零，所有幸存ATE均为双tier NVCF上游耗尽（~121s），非配置可修复。

**关键发现：**
- `FALLBACK_HEALTH_THRESHOLD`（env var）为死参数，func_health.py使用硬编码HEALTH_THRESHOLD=0.80
- `TIER_TIMEOUT_BUDGET_S`为per-tier预算（非cross-tier），每个tier独立获得110s。双tier ATE各消耗~60s，均在预算内
- R700的config.py修改通过volume mount在R701的`docker compose up -d`时生效（`docker compose restart`不够）

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2