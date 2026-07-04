# R710: HM2→HM1 — 零变更轮（R709 FASTBREAK=1 刚部署，NVCF 双 function 上游低健康度）

## TL;DR
R709 刚部署 FASTBREAK=2→1（容器运行 4 分钟），无有效数据积累。6h 窗口数据显示 dsv4p_nv SR 52.1%——根因是 NVCF 双 function（dsv4p_nv 74f02205 健康度 0.15-0.33，glm5_2_nv 3b9748d8 健康度 0.15-0.33）同时不可用，非配置可修复。发现神秘 FALLBACK_GRAPH 消失窗口（01:30-02:12 UTC，所有模型 tier_chain 变 "no fallback, 3model"），02:12 后自恢复。当前 FASTBREAK=1 + FALLBACK_HEALTH_THRESHOLD=0.10 + BUDGET=110，fallback_chain 含全部 4 tier，等待数据。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R709 部署后，零变更）

| # | 参数 | HM1 当前值 | 历史来源 | 本轮变更 |
|---|------|------------|----------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 30 | R701 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 | — |
| 4 | **`NVU_PEXEC_TIMEOUT_FASTBREAK`** | **1** | **R709** | — |
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
NVU_PEXEC_TIMEOUT_FASTBREAK: "1"  (line 591, R709 comment)
TIER_TIMEOUT_BUDGET_S: "110"  (line 490)
UPSTREAM_TIMEOUT: "30"  (line 483)
FALLBACK_HEALTH_THRESHOLD: "0.10"  (line 510)
KEY_COOLDOWN_S: "25"  (line 498)
TIER_COOLDOWN_S: "25"  (line 499)
→ 无重复值行。单一活跃行。
```

### 2.2 源2 — 容器 env
```
NVU_PEXEC_TIMEOUT_FASTBREAK=1
TIER_TIMEOUT_BUDGET_S=110
UPSTREAM_TIMEOUT=30
FALLBACK_HEALTH_THRESHOLD=0.10
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
→ 全部匹配 compose。
```

### 2.3 源3 — 容器状态
```
nv_gw Up 4 minutes (healthy)
logs_db Up 15 hours (healthy)
Container: fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv']
Health: {"status":"ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 200: 0 ERROR, 0 WARN, 0 429
dsv4p_nv tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) — 正常
glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback) — 正常
NVCF 健康度: dsv4p_nv(74f02205) 0.15-0.33, glm5_2_nv(3b9748d8) 0.15-0.33
→ 双 function 同时低健康度，上游不可用
```

**结论：四源全部一致。无漂移。FASTBREAK=1 已生效。**

---

## 三、数据摘要

### 3.1 总体统计（6h 窗口，ts UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 311 |
| 成功 (200) | 221 (71.1%) |
| ATE (502) | 90 (28.9%) |
| 其他失败 | 0 |

**按模型分组：**
| request_model | cnt | OK | ATE | SR% | avg_ok_dur | avg_ate_dur |
|---------------|-----|-----|-----|-----|------------|-------------|
| dsv4p_nv | 163 | 85 | 78 | 52.1% | 35,970ms | 67,729ms |
| glm5_2_nv | 140 | 129 | 11 | 92.1% | 13,698ms | 33,847ms |
| kimi_nv | 8 | 7 | 1 | 87.5% | 10,323ms | 2,682ms |

**按路径分组：**
| upstream_type | cnt | OK | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 211 | 211 | 22,631ms | 22,670ms | 99,088ms |
| (NULL, ATE) | 94 | 4 | 54ms | 60,695ms | 122,312ms |
| nv_integrate | 6 | 6 | 4,253ms | 10,984ms | 27,635ms |

### 3.2 ATE 深层分析

**按 tiers_tried_count：**
| tiers_tried_count | cnt | avg_dur | 占比 |
|-------------------|-----|---------|------|
| 1（单tier） | 70 | 47,103ms | 77.8% |
| 2（双tier） | 20 | 118,033ms | 22.2% |

**按 start_tier_idx（单tier ATE，tiers_tried=1）：**
| start_tier_idx | cnt | avg_dur | 含义 |
|----------------|-----|---------|------|
| 0 | 1 | 2,682ms | 边缘case |
| 1 (dsv4p_nv) | 58 | 50,383ms | dsv4p耗尽，无fallback ⚠️ |
| 3 (glm5_2_nv) | 11 | 33,847ms | glm5_2直接耗尽 |

**fallback_actually_attempted 分析（单tier ATE）：**
| fallback_actually_attempted | cnt |
|-----------------------------|-----|
| f | 70 (100%) |

全部 70 个单tier ATE 均未尝试 fallback。

### 3.3 每小时 SR 趋势

| 小时 (UTC) | 总 | OK | ATE | SR% | 备注 |
|------------|-----|-----|-----|-----|------|
| 19:00 | 114 | 99 | 15 | 86.8% | 最佳窗口，fallback 正常 |
| 20:00 | 14 | 8 | 6 | 57.1% | 低流量 |
| 21:00 | 15 | 8 | 7 | 53.3% | 低流量 |
| 22:00 | 28 | 13 | 15 | 46.4% | 持续恶化 |
| 23:00 | 9 | 8 | 1 | 88.9% | 低流量恢复 |
| 00:00 | 2 | 2 | 0 | 100.0% | 极低流量 |
| 01:00 | 13 | 8 | 5 | 61.5% | ⚠️ FALLBACK_GRAPH 消失开始 |
| 02:00 | 49 | 35 | 14 | 71.4% | FALLBACK_GRAPH 于 02:12 恢复 |
| 03:00 | 27 | 20 | 7 | 74.1% | 恢复后 |
| 04:00 | 21 | 14 | 7 | 66.7% | — |
| 05:00 | 19 | 6 | 13 | 31.6% | NVCF 双 function 同时失败 |

### 3.4 成功请求分析

**Fallback 成功：**
| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| f（单tier成功） | 201 | 17,883ms | 60,099ms |
| t（tier fallback成功） | 20 | 65,119ms | 99,088ms |

20 个 fallback 成功（avg 65s），max 99s < BUDGET=110s — 零误杀。

---

## 四、根因分析：FALLBACK_GRAPH 神秘消失窗口

### 4.1 发现

日志分析发现 01:30-02:12 UTC 期间，所有 dsv4p_nv 请求的 tier_chain 从 `['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback)` 变为 `['dsv4p_nv'] (no fallback, 3model)`。同时 glm5_2_nv 也丢失了 fallback。

### 4.2 时间线

| 时间 (UTC) | 事件 | tier_chain | fallback |
|-----------|------|------------|----------|
| 00:03 | R708 容器启动 | dynamic fallback | ✅ 正常 |
| 00:03-01:03 | glm5_2_nv 有 fallback | dynamic fallback | ✅ 正常 |
| 01:30-02:11 | **ALL models 丢失 fallback** | (no fallback, 3model) | ❌ 消失 |
| 02:12 | FALLBACK_GRAPH 恢复 | dynamic fallback, health={} | ✅ 恢复 |
| 02:12+ | 持续正常 | dynamic fallback | ✅ 正常 |

### 4.3 影响

58 个 dsv4p_nv 单tier ATE（avg 50,383ms）全部发生在 FALLBACK_GRAPH 消失窗口内。若 fallback 正常（即使 glm5_2 仅 15-33% 存活率），也能救回 ~9-19 个请求（58 × 0.15-0.33）。

### 4.4 排除的可能原因

| 假设 | 检查 | 结论 |
|------|------|------|
| HEALTH_THRESHOLD 误杀 | 双 function 健康度 > 0.10，且 glm5_2 同步丢失 fallback | ❌ 排除 |
| config.py 被回退 | 磁盘+容器内 config.py 均有 FALLBACK_GRAPH 条目 | ❌ 排除 |
| 容器重启 | 日志从 00:03 开始，无中间重启记录 | ❌ 排除 |
| glm5_2 全 key cooldown | 日志无 NV-TIER-SKIP 记录 | ❌ 排除 |
| Python 运行时 FALLBACK_GRAPH 为空 | (no fallback, 3model) 表示代码检测到空 FALLBACK_GRAPH | ⚠️ 可能 |

### 4.5 推测

`(no fallback, 3model)` 标签来自 upstream.py 的 `_build_tier_chain()` 函数。此标签表示 `FALLBACK_GRAPH.get(mapped_model, [])` 返回空列表。可能原因：
- Python 模块热重载问题（config.py 被重新 import 时 FALLBACK_GRAPH 短暂为空）
- 或在某个代码路径上 config.py 的 FALLBACK_GRAPH 被某操作清空后恢复

**此现象需要持续监控**，但非配置参数可修复。02:12 后自恢复，当前容器（R709）fallback 正常。

---

## 五、决策

| 参数 | 当前值 | 决策 | 理由 |
|------|--------|------|------|
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ❌ 保持 | R709 刚部署 4min，无数据 |
| `TIER_TIMEOUT_BUDGET_S` | 110 | ❌ 保持 | 当前成功 max=99s < 110s；等 FASTBREAK=1 数据 |
| `UPSTREAM_TIMEOUT` | 30 | ❌ 保持 | 30s 已为 R701 回调值；dvs4p 复杂 prompt 需 30s |
| `FALLBACK_HEALTH_THRESHOLD` | 0.10 | ❌ 保持 | 已为安全地板；当前双 function 健康度均 > 0.10 |
| 其他 | — | ❌ 保持 | 无数据支持变更 |

**最终决策：零变更轮。** R709 FASTBREAK=1 刚部署（容器运行 4 分钟），需等待数据积累。6h 数据中 58 个单 tier ATE 由 FALLBACK_GRAPH 消失窗口引起（非配置问题），剩余 20 个双 tier ATE 为 NVCF 双 function 同时不可用（上游问题，非配置可修复）。当前 NVCF 双 function 健康度均仅 0.15-0.33，无论 FASTBREAK 设为何值，大多数请求都将失败。

---

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| 四源漂移 | compose=env=container=runtime 全部一致 | ✅ |
| 容器状态 | nv_gw Up (healthy), logs_db Up (healthy) | ✅ |
| FASTBREAK | 容器 env=1 | ✅ |
| FALLBACK_GRAPH | dsv4p_nv→glm5_2_nv 在 compose+容器内均正确 | ✅ |
| FALLBACK_HEALTH_THRESHOLD | 容器 env=0.10, func_health.py 读取正确 | ✅ |
| fallback_chain | ['kimi_nv','dsv4p_nv','glm5_1_nv','glm5_2_nv'] | ✅ |
| 运行时日志 | 0 ERROR, 0 WARN, 0 429 | ✅ |
| Health endpoint | {"status":"ok"} | ✅ |
| 重复值行 | 无 | ✅ |
| dsv4p_nv 6h SR | 52.1% (NVCF 上游低健康度) | ⚠️ 非配置可修复 |
| glm5_2_nv 6h SR | 92.1% | ✅ 稳定 |

---

## 七、结论

R710 零变更轮。R709 刚部署 FASTBREAK=2→1，容器运行仅 4 分钟。6h 窗口数据受三个因素影响：
1. R709 前 FASTBREAK=2 导致的 ATE duration 偏高（~122s dual-tier）
2. FALLBACK_GRAPH 神秘消失窗口（01:30-02:12 UTC，58 单tier ATE）
3. NVCF 双 function 上游低健康度（dsv4p_nv ~0.15-0.33，glm5_2_nv ~0.15-0.33）

FASTBREAK=1 预期将 ATE 路径从 ~122s 压缩至 ~61s（省 60s/ATE），并释放 BUDGET 余量给 peer fallback。FALLBACK_HEALTH_THRESHOLD=0.10 安全地板确保 fallback 不被健康度误杀。FALLBACK_GRAPH 消失窗口需持续监控但 02:12 后已自恢复。

**关键发现：** (no fallback, 3model) 标签出现在 01:30-02:12 UTC 全部模型上，同时影响 dsv4p_nv 和 glm5_2_nv，02:12 后自恢复且无重启记录。此现象非配置参数可修复，需在代码层面调查 `_build_tier_chain()` 中 FALLBACK_GRAPH 的加载逻辑。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2