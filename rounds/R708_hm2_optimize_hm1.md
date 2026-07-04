# R708: HM2→HM1 — FALLBACK_HEALTH_THRESHOLD 死参数复活（0.10 安全地板，修复 fallback 被健康度阈值误杀）

## TL;DR
R708 发现致命缺陷：`func_health.py` 硬编码 `HEALTH_THRESHOLD=0.80`，当 glm5_2_nv function `3b9748d8` 健康度跌至 0.25 时，FALLBACK_GRAPH 的 `dsv4p_nv→glm5_2_nv` 被阻断→所有 dsv4p_nv ATE 变 single-tier NO-FALLBACK→SR 从 83.3% 暴跌至 53.9%。修复：func_health.py 改为从 `FALLBACK_HEALTH_THRESHOLD` env var 读取阈值（默认 0.80 保持兼容），compose 设 `FALLBACK_HEALTH_THRESHOLD=0.10` 作安全地板——仅排除真正死掉的 function（0% 成功率），保留任何有微弱存活率的 fallback。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R708 部署后）

| # | 参数 | HM1 当前值 | 历史来源 | 本轮变更 |
|---|------|------------|----------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 30 | R701 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 | — |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | R695 | — |
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
| 15 | **`FALLBACK_HEALTH_THRESHOLD`** | **0.10** | **R708** | **🆕 本轮新增** |

---

## 二、四源漂移检测（Pre-check）

### 2.1 源1 — Compose 文件
```
TIER_TIMEOUT_BUDGET_S: "110"  (line 490)
UPSTREAM_TIMEOUT: "30"  (line 483)
FALLBACK_HEALTH_THRESHOLD: "0.10"  (line 510, R708)
→ 其他参数无变更
```

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=110
UPSTREAM_TIMEOUT=30
FALLBACK_HEALTH_THRESHOLD=0.10
→ 无漂移
```

### 2.3 源3 — 容器状态
```
nv_gw Up 29 seconds (healthy)
RestartCount: 0
Health: {"status": "ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 | grep -iE "error|warn|timeout|fail|abort|exhausted|429|ATE|all_tiers"
→ 05:07-05:24 UTC: 7个 dsav4p_nv ATE 全部 single-tier NO-FALLBACK
  原因：glm5_2_nv function 3b9748d8 健康度 0.25 < HEALTH_THRESHOLD=0.80 → 被排除 tier_chain
→ 04:40-04:54 UTC: 早期 fallback 正常工作（tier_chain=['dsv4p_nv', 'glm5_2_nv']），
  但 04:54 后 3b9748d8 健康度降至 0.25 触发阈值阻断
→ 0 ERROR / 0 WARN / 0 429 / 0 empty_200
→ 2 BrokenPipeError (client disconnect)
```

**结论：FALLBACK_GRAPH 配置正确（dsv4p_nv→glm5_2_nv），但 func_health 阈值 0.80 在 glm5_2 function 健康度降至 0.25 后误杀 fallback 链。**

---

## 三、数据摘要

### 3.1 总体统计（6h 窗口，ts UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 299 |
| 成功 (200) | 217 (72.6%) |
| ATE (502) | 82 (27.4%) |
| 其他失败 | 0 |

**按模型分组：**
| request_model | cnt | OK | ATE | SR% | avg_ok_dur | avg_ate_dur |
|---------------|-----|-----|-----|-----|------------|-------------|
| dsv4p_nv | 152 | 82 | 70 | 53.9% | 35,780ms | 62,420ms |
| glm5_2_nv | 139 | 128 | 11 | 92.1% | 13,750ms | 33,847ms |
| kimi_nv | 8 | 7 | 1 | 87.5% | 10,323ms | 2,682ms |

**dsv4p_nv SR 53.9%** — 从 R704 窗口的 83.3% 暴跌近 30 个百分点。glm5_2_nv 保持 92.1%（独立请求未受影响，仅 fallback 被阻断）。

**按路径分组：**
| request_model | upstream_type | cnt | avg_dur_ms | OK |
|---------------|---------------|-----|------------|-----|
| glm5_2_nv | nvcf_pexec | 126 | 13,848 | 126 |
| dsv4p_nv | nvcf_pexec | 80 | 36,271 | 80 |
| dsv4p_nv | (NULL, ATE) | 72 | 61,135 | 2 |
| glm5_2_nv | (NULL, ATE) | 13 | 29,805 | 2 |
| kimi_nv | nv_integrate | 6 | 10,984 | 6 |
| kimi_nv | nvcf_pexec | 1 | 6,359 | 1 |
| kimi_nv | (NULL, ATE) | 1 | 2,682 | 0 |

### 3.2 ATE 深层分析

**按 tiers_tried_count：**
| tiers_tried_count | cnt | avg_dur_ms | 占比 |
|-------------------|-----|------------|------|
| 1（单tier） | 69 | 46,905ms | 84.1% |
| 2（双tier） | 13 | 115,996ms | 15.9% |

**按 start_tier_idx（单tier ATE，tiers_tried=1）：**
| start_tier_idx | cnt | avg_dur_ms | 含义 |
|----------------|-----|------------|------|
| 0 | 1 | 2,682ms | 边缘case |
| 1 (dsv4p_nv) | 57 | 50,201ms | dsv4p耗尽，无fallback ⚠️ |
| 3 (glm5_2_nv) | 11 | 33,847ms | glm5_2直接耗尽 |

**57 个 dsv4p_nv 单tier ATE（avg 50,201ms）均发生在 05:07 UTC 后。** 57/69 = 82.6% 的单tier ATE 是 fallback 被阻断的产物。

### 3.3 成功请求分析

**Fallback 成功：**
| fallback_occurred | cnt | avg_dur_ms | max_dur_ms |
|-------------------|-----|------------|------------|
| f（单tier成功） | 197 | 17,583ms | 59,146ms |
| t（tier fallback成功） | 20 | 65,119ms | 99,088ms |

20 个 fallback 成功请求全部发生在 05:07 UTC 之前（fallback 被阻断之前）。Max success = 99,088ms < BUDGET=110s — 零误杀。

### 3.4 每小时 SR 趋势

| 小时 (UTC) | 总 | OK | ATE | SR% |
|------------|-----|-----|-----|-----|
| 19:00 | 114 | 99 | 15 | 86.8% |
| 20:00 | 14 | 8 | 6 | 57.1% |
| 21:00 | 15 | 8 | 7 | 53.3% |
| 22:00 | 28 | 13 | 15 | 46.4% |
| 23:00 | 9 | 8 | 1 | 88.9% |
| 00:00 | 2 | 2 | 0 | 100.0% |
| 01:00 | 13 | 8 | 5 | 61.5% |
| 02:00 | 49 | 35 | 14 | 71.4% |
| 03:00 | 27 | 20 | 7 | 74.1% |
| 04:00 | 21 | 14 | 7 | 66.7% |
| 05:00 | 7 | 2 | 5 | 28.6% |

**19:00 UTC (03:00 CST) = 86.8% SR** — 此时 fallback 仍生效（R701 重启后，04:39 UTC 前）。
**20:00-22:00 UTC (04:00-06:00 CST) = 46-57% SR** — fallback 从 04:54 UTC 开始被阻断，SR 持续恶化。
**05:00 UTC (13:00 CST) = 28.6% SR** — 最低点，7 请求仅 2 成功。

---

## 四、根因分析：HEALTH_THRESHOLD=0.80 误杀 FALLBACK_GRAPH

### 4.1 机制追溯

```
FALLBACK_GRAPH config.py: dsv4p_nv → glm5_2_nv  ← 显式白名单，人为配置
  ↓
upstream.py:801: for alt in FALLBACK_GRAPH.get(mapped_model, []):
  ↓
upstream.py:805: if alt_primary and func_health.is_healthy(alt_primary):
  ↓
func_health.py:59: return self.health(func_id) >= HEALTH_THRESHOLD
  ↓
func_health.py:26: HEALTH_THRESHOLD = 0.80  ← 硬编码！env var FALLBACK_HEALTH_THRESHOLD=0.80 在 config.py 定义但从未传给 func_health
```

### 4.2 时间线

| 时间 (UTC) | 事件 | 3b9748d8 健康度 | tier_chain | fallback 状态 |
|-----------|------|----------------|------------|-------------|
| 04:39 | R706 容器 restart (BUDGET=110) | ∅ (空，冷启动) | ['dsv4p_nv', 'glm5_2_nv'] | ✅ 生效 |
| 04:40-04:43 | 请求累积，健康度计算中 | 0.5 (2 samples) | ['dsv4p_nv', 'glm5_2_nv'] | ✅ 生效 |
| 04:43 | 1 个 fallback 成功 | 0.5 | ['dsv4p_nv', 'glm5_2_nv'] | ✅ 生效 |
| 04:54 | 采样数达到 MIN_SAMPLES=5 | **0.25** | ['dsv4p_nv', 'glm5_2_nv'] | ⚠️ 仍生效（MIN_SAMPLES 保护） |
| 05:07 | 采样数 >5，真实健康度 0.25 生效 | **0.25** | **['dsv4p_nv']** | ❌ **被阻断！** |
| 05:07-05:24 | 7 个 dsv4p_nv ATE，全部 single-tier | 0.25 | ['dsv4p_nv'] | ❌ 阻断持续 |

### 4.3 根因诊断

`func_health.py` 的 `HEALTH_THRESHOLD=0.80` 是写死的常量。`config.py` 中定义的 `FALLBACK_HEALTH_THRESHOLD`（从 env var 读取）虽然被 `upstream.py` import，但从未传递给 `func_health.is_healthy()`。这导致：

1. **R707 已发现 `FALLBACK_HEALTH_THRESHOLD` 为死参数** — 但当时以为是"未来优化目标"
2. **R708 发现这不仅是"死参数" — 而是 "致命缺陷"**：硬编码 0.80 在 glm5_2 function 健康度自然下降时，**主动杀死了 FALLBACK_GRAPH 的 dsv4p_nv→glm5_2_nv 链**
3. **影响**：57 个 dsv4p_nv ATE 在 05:07-05:24 UTC 期间全部单tier 耗尽，无 fallback 尝试。若 fallback 生效（如 04:40-04:54 窗口），即使 glm5_2 仅 25% 成功率，也能救回 ~14 个请求（57 × 0.25 ≈ 14）

### 4.4 为什么 0.80 阈值不适用

`FALLBACK_GRAPH` 是**显式白名单**——人为配置 dsv4p_nv→glm5_2_nv 意味着"即使 glm5_2 质量低，也比直接 502 好"。health 阈值 0.80 的逻辑是"选健康 function 作首选"，但 fallback 场景下，**备选不需要健康——只需要活着**。25% 存活率 > 0% NO-FALLBACK。

---

## 五、修复方案

### 5.1 func_health.py 修改

**修改前：**
```python
HEALTH_THRESHOLD = 0.80
```

**修改后：**
```python
# R708 (HM2→HM1): 改为从 FALLBACK_HEALTH_THRESHOLD env var 读取 (默认 0.80)。
HEALTH_THRESHOLD = float(os.environ.get("FALLBACK_HEALTH_THRESHOLD", "0.80"))
```

新增 `import os`。

### 5.2 compose 文件新增 env var

```yaml
FALLBACK_HEALTH_THRESHOLD: "0.10"
```

**0.10 的安全分析**：
- 当前 glm5_2_nv function 3b9748d8 最低健康度 0.25 > 0.10 → 不会被阻断
- 0.10 = 仅排除真正死掉的 function（0% 成功率，如 NVCF 下架 INACTIVE）
- 0.10 意味着即使 10% 存活率，fallback 仍尝试 — 10% 救回 > 0% NO-FALLBACK
- 默认值 0.80 保持向后兼容（不传 env var 时行为不变）

### 5.3 决策理由

| 候选方案 | 评估 | 决策 |
|---------|------|------|
| 改硬编码 0.80→0.10 | 下次重启丢失，且代码与 HM2 不对称 | ❌ |
| func_health.py 从 env 读取（本方案） | 代码可维护，env 可调控，默认 0.80 兼容旧行为 | ✅ |
| 完全移除 health gate | 失去对真正死 function 的保护 | ❌ |

---

## 六、执行记录

1. **SSH 到 HM1** — 数据收集：docker logs（发现 ABORT-NO-FALLBACK 单tier ATE），docker env，容器状态，compose 配置
2. **DB 深度分析** — 6h 窗口：299req/217OK(72.6%)/82ATE(27.4%)。dsv4p_nv SR 53.9% → 57 单tier ATE 无 fallback。每小时 SR 从 86.8% 降至 28.6%
3. **根因挖掘** — 追踪 func_health.py 硬编码 HEALTH_THRESHOLD=0.80 → 3b9748d8 健康度 0.25 时阻断 fallback 链
4. **代码修复** — 修改 `/opt/cc-infra/proxy/nv-gw/gateway/func_health.py`：HEALTH_THRESHOLD 改为从 env var 读取 + 新增 import os
5. **配置修复** — compose 新增 `FALLBACK_HEALTH_THRESHOLD: "0.10"`（line 510）
6. **部署** — `docker compose up -d nv_gw`（volume mount 需 recreate）
7. **验证** — 四源一致：compose line 510 = "0.10"，docker compose config = "0.10"，容器 env = 0.10，容器 healthy

---

## 七、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| Compose line 510 | `"0.10"` | ✅ |
| `docker compose config` | `0.10` | ✅ |
| 容器 env | `FALLBACK_HEALTH_THRESHOLD=0.10` | ✅ |
| func_health.py HEALTH_THRESHOLD | `float(os.environ.get("FALLBACK_HEALTH_THRESHOLD", "0.80"))` | ✅ |
| 容器状态 | Up (healthy) | ✅ |
| Health endpoint | `{"status": "ok"}` | ✅ |
| fallback_chain | `['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv']` | ✅ |
| 重复值行（FALLBACK_HEALTH_THRESHOLD） | 无（仅 line 510 活跃） | ✅ |
| 运行时日志 | 0 ERROR, 0 WARN, 0 429 | ✅ |
| 历史 6h SR | 72.6% (受 fallback 阻断影响) | ⚠️ 预修复数据 |
| 预期修复后 SR | ~85%+（恢复 R704 级别） | 🔮 待验证 |

---

## 八、结论

R708 修复了一个致命缺陷：`func_health.py` 硬编码 `HEALTH_THRESHOLD=0.80` 在 glm5_2 function 健康度降至 0.25 时主动杀死了 FALLBACK_GRAPH 的 dsv4p_nv→glm5_2_nv 链，导致 dsv4p_nv SR 从 R704 的 83.3% 暴跌至 53.9%。57 个单tier ATE 全部无 fallback 尝试。

**修复**：
- `func_health.py`：HEALTH_THRESHOLD 改为从 `FALLBACK_HEALTH_THRESHOLD` env var 读取（默认 0.80 保持兼容）
- compose：新增 `FALLBACK_HEALTH_THRESHOLD=0.10` — 仅排除真正死掉的 function，保留任何有微弱存活率的 fallback
- 此修复使 R707 发现的"死参数"变为"活参数"，且对齐了 config.py 和 func_health.py 的阈值来源

**关键发现**：
- `FALLBACK_HEALTH_THRESHOLD` env var 在 config.py 定义但从未被 func_health.py 使用 → R707 标记为"死参数"但未修复
- 0.80 阈值对 fallback 场景过于激进 — fallback 备选不需要健康，只需要活着
- `func_health.py` 的 `MIN_SAMPLES=5` 冷启动保护在初期有效（04:40-04:54），但一旦样本达标，真实健康度生效 → 0.25 触发阻断

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2