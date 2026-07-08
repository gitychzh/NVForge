# R883: HM2→HM1 — NOP (false trigger, 38/38 100% 6h SR, zero ATE, 1 rescued fallback, identical to R865-R882)

## TL;DR
6h window: 38/38 OK (100.0% SR), zero ATE, zero config errors, 1 fallback rescued (glm5_2→dsv4p_nv). NVCF glm5_2 3b9748d8 partially recovered from DEGRADED (Jul 7 100% → Jul 8 intermittent 504+timeout). All 6 NOP gates pass. 铁律：只改HM1不改HM2。

---

## 一、当前配置快照（R883 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | R754 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 114 | R737 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R709 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 |
| 8 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R755 |
| 9 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 |
| 10 | `NVU_EMPTY_200_FASTBREAK` | 1 | R774 |
| 11 | `NV_INTEGRATE_MODELS` | "" (all pexec) | R694 |
| 12 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 |
| 13 | `KEY_COOLDOWN_S` | 25 | R162 |
| 14 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "66" ✅
TIER_TIMEOUT_BUDGET_S: "114" ✅
NVU_PEXEC_TIMEOUT_FASTBREAK: "1" ✅
NVU_EMPTY_200_FASTBREAK: "1" ✅
FALLBACK_HEALTH_THRESHOLD: "0.10" ✅
NV_INTEGRATE_KEY_COOLDOWN_S: "0" ✅
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "66" ✅
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=66 ✅
TIER_TIMEOUT_BUDGET_S=114 ✅
NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✅
NVU_EMPTY_200_FASTBREAK=1 ✅
FALLBACK_HEALTH_THRESHOLD=0.10 ✅
NV_INTEGRATE_KEY_COOLDOWN_S=0 ✅
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 ✅
NVU_CONNECT_RESERVE_S=0 ✅
MIN_OUTBOUND_INTERVAL_S=0 ✅
KEY_COOLDOWN_S=25 ✅
TIER_COOLDOWN_S=25 ✅
```

### 2.3 源3 — 容器状态
```
nv_gw: Up 7 hours (healthy)
docker-compose.yml = env = 一致 ✅
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100
→ tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...}) ✅
→ tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={...}) ✅
→ NV-CYCLE: 504 → cycle → NVCFPexecTimeout → fastbreak → fallback → success ✅
→ ZERO ERROR/WARN in logs ✅
→ FALLBACK_GRAPH bidirectional working ✅
```

**结论：四源全部通过。无漂移。所有参数在 floor 值。**

---

## 三、数据摘要

### 3.1 6h 总体统计 (UTC)

| 指标 | 值 |
|------|---|
| 总请求 | 38 |
| OK (200) | 38 |
| ATE | 0 |
| **6h SR** | **100.0%** |

### 3.2 6h 按模型

| mapped_model | total | ok | SR | avg_dur | min_dur | max_dur |
|---|---|---|---|---|---|---|
| glm5_2_nv | 38 | 38 | 100.0% | 22,737ms | 1,933ms | 144,743ms |

> 注：max_dur=144,743ms 是 1 次 fallback (glm5_2→dsv4p_nv, 数据库 6h 窗口外但日志可见)，直接路径 avg ~20s。

### 3.3 6h 错误类型

| error_type | cnt |
|---|---|
| (none) | 0 |

零 error。6h 窗口 38/38 全部成功。

### 3.4 nv_tier_attempts (6h)

| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | 504_nv_gateway_timeout | 1 |
| glm5_2_nv | NVCFPexecTimeout | 1 |

仅 2 次 tier attempt 错误，均来自 1 次 fallback 事件（10:03 UTC）：
- k2: 504_nv_gateway_timeout → cycle to k3
- k3: NVCFPexecTimeout (51,475ms) → fastbreak (1 key) → fallback to dsv4p_nv → success

### 3.5 Fallback

| fallback_occurred | total | ok | SR |
|---|---|---|---|
| f (direct) | 37 | 37 | 100.0% |
| t (fallback) | 1 | 1 | 100.0% |

Fallback 100% SR。唯一 fallback 事件：glm5_2_nv k2 504 → k3 NVCFPexecTimeout → fastbreak → dsv4p_nv k1 → success (144.7s total)。

### 3.6 NVCF glm5_2 恢复状态

Jul 7: glm5_2 NVCF function 3b9748d8 100% DEGRADED（对所有 5 key 返回 400 DEGRADED）
Jul 8: 部分恢复。当前表现为间歇性 504 + NVCFPexecTimeout，大多数请求正常返回。

| 日期 | 状态 | 影响 |
|------|------|------|
| Jul 7 19:33-21:05 UTC | 100% DEGRADED (400) | 所有 glm5_2 请求走 fallback → dsv4p_nv |
| Jul 8 08:00-10:00 UTC | 正常运行 | 直接成功，零错误 |
| Jul 8 10:03 UTC | 单次 504+timeout | 1 fallback rescued |
| Jul 8 10:03-11:34 UTC | 正常运行 | 8/8 直接成功 |

NVCF 上游波动，零配置可修。FALLBACK_GRAPH 始终有效。

---

## 四、NOP 决策 (6 Gates)

### Gate 1: All ATEs double-tier? ✅
0 ATE total。无 ATE 需要分析。

### Gate 2: Zero single-tier ATEs? ✅
0 ATE total。FALLBACK_GRAPH 双向工作，所有 fallback 100% SR。

### Gate 3: NVCFPexecTimeout buffer ≥3s? ✅
唯一天内 NVCFPexecTimeout 在 51,475ms，UPSTREAM=66s，buffer=14.5s >> 3s。Non-binding。

### Gate 4: FALLBACK_GRAPH bidirectional and working? ✅
```
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={...})
```
Both directions confirmed in logs。Fallback 100% SR (1/1 in 6h window)。

### Gate 5: Fallback SR = 100%? ✅
1/1 fallback 100% SR。Fallback path is reliable。

### Gate 6: All params at floor/optimal values? ✅
UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1,
FALLBACK_HEALTH=0.10, CONNECT_RESERVE=0, MIN_OUTBOUND=0,
INTEGRATE_COOLDOWN=0, FORCE_STREAM=0, FORCE_STREAM_UPGRADE_TIMEOUT=66

**→ Decision: NOP (zero parameter change, zero compose change, zero container restart)**

---

## 五、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| ALL | — | — | 6h 100% SR, 0 ATE, all 6 gates pass | ❌ NOP |

**否决原因：**

1. **6h 100% SR** — 38/38 OK，零 ATE，零 error。系统已收敛到最优状态。
2. **NVCF glm5_2 恢复中** — NVCF function 3b9748d8 从 Jul 7 100% DEGRADED 恢复到 Jul 8 间歇性 504+timeout（绝大多数请求正常）。上游故障，零配置可修。
3. **FALLBACK_GRAPH 始终有效** — 1 次 fallback 100% 救回。R819 code fix（400→NONCYCLE-ERR immediate fallback）已验证。
4. **所有 compose 参数已在 floor 值** — 任何修改非但无益，反而可能破坏当前稳定基线。
5. **false trigger** — git commit 为 HM1 自己提交（"这是我提交的, 不触发"），检测脚本误判。系统无实际变更。

---

## 六、执行记录

**无操作。** 零参数变更，零 compose 变更，零容器重启。

### 不改的项

- 所有 compose 参数不变（UPSTREAM=66, BUDGET=114, FASTBREAK=1, 等均已在 floor）
- config.py 不变（R819 code fix 已验证: 400→NONCYCLE-ERR immediate fallback）
- 本机 (HM2) 配置不变
- 铁律: 只改 HM1 不改 HM2

---

## 七、验证记录（Post-change, NOP）

| 指标 | 数值 | 状态 |
|------|------|------|
| 6h SR | 38/38 (100.0%) | ✅ |
| 单tier ATE | 0 | ✅ |
| Fallback SR | 1/1 (100%) | ✅ |
| FALLBACK_GRAPH | bidirectional working | ✅ |
| NVCFPexecTimeout | 1 (51,475ms, buffer 14.5s) | ✅ |
| 400 cycle waste | Fixed (R819 NONCYCLE-ERR) | ✅ |
| 容器健康 | Up 7h (healthy) | ✅ |
| Compose↔Env 一致 | 全部通过 | ✅ |

---

## 八、结论

R883 NOP。6h window 系统已收敛到最优状态：100% SR, 0 ATE, FALLBACK_GRAPH 双向工作, 所有参数在 floor 值。NVCF glm5_2 3b9748d8 正在从 DEGRADED 恢复（Jul 7 100%→Jul 8 间歇性），上游波动零配置可修。本次为 false trigger（HM1 自己提交），与 R865-R882 完全一致。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2