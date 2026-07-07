# R819: HM2→HM1 — 移除 pexec/integrate 路径 400_nvcf_degraded 的 key cycle，遇 DEGRADED 立即 abort tier → fallback

**时间**: 2026-07-08 03:30 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）
**分析窗口**: 6h (20:30–03:00 UTC)

---

## TL;DR

glm5_2_nv function `3b9748d8-1d85` 持续 NVCF DEGRADING，所有 5 key 均返回 `400_nvcf_degraded`。R818 修复了 func_health 阈值使 cross-model fallback 恢复，但 pexec/integrate 路径的 `should_cycle` 仍包含 `400`，导致每请求仍逐个 cycle 5 个 key（~7s 浪费），然后才 fallback 到 dsv4p_nv。R819 将 `400` 从 `should_cycle` 中移除，遇 `400_nvcf_degraded` 直接 non-cycling abort tier → fallback，节省 ~6s/request。

**修复**: `upstream.py` 两个 `should_cycle` 集合（pexec L621 + integrate L238）移除 `400`。

**单参数少改多轮。铁律：只改HM1不改HM2。**

---

## 一、问题诊断

### 1.1 R818 后状态

R818 修复了 `func_health.HEALTH_THRESHOLD` 硬编码 0.80 → 0.10，cross-model fallback 已恢复：

```
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True
         tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
```

但 pexec 路径的 `should_cycle` 仍包含 `400`（L621），导致每个 key 返回 `400_nvcf_degraded` 后继续 cycle 到下一个 key：

```
[NV-CYCLE] tier=glm5_2_nv k1 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k2 → 400 (400_nvcf_degraded), cycling to next key
... (all 5 keys, ~1s each)
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: other=7, elapsed=6931ms
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
```

**浪费 ~7s/request** 在注定全部失败的 key cycle 上。

### 1.2 DB 数据（6h，R818 前）

| 指标 | 值 |
|------|-----|
| Total | 52 |
| OK (200) | 13 |
| ATE (502) | 39 |
| **SR** | **25.0%** |

| request_model | cnt | ok | fail | SR% | avg_ms | max_ms |
|---------------|-----|-----|------|------|--------|--------|
| dsv4p_nv | 11 | 8 | 3 | 72.7 | 48,233 | 68,217 |
| glm5_2_nv | 41 | 5 | 36 | 12.2 | 26,934 | 125,593 |

39 个 ATE 全部是 `all_tiers_exhausted`。

### 1.3 为什么 400 不应该 cycle

NVCF function DEGRADED 是**function-level** 状态——同一个 function 的所有 key 共享同一条 NVCF 部署，DEGRADED 时所有 key 均返回 400。逐个 cycle 5 个 key 注定全部失败，纯粹浪费时间和算力。正确做法：遇第一个 400 立即 abort tier → fallback 到 dsv4p_nv。

---

## 二、修复执行

### 2.1 代码变更

**文件**: `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py`（bind mount，修改后 `docker restart nv_gw` 生效）

**变更 1**: pexec 路径（L621）移除 `400`：

```diff
-                should_cycle = resp.status in (400, 401, 403, 429, 408, 500, 502, 503, 504, 202)
+                should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
```

**变更 2**: integrate 路径（L238）同样移除 `400`：

```diff
-                should_cycle = resp.status in (400, 401, 403, 429, 408, 500, 502, 503, 504, 202)
+                should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
```

`cycle_reason` 中的 `"400_nvcf_degraded"` / `"400_integrate_degraded"` 分支保留为 dead code（400 不再进入 `if should_cycle:` 块），无副作用。后续轮次可清理。

**变更 3**: 重启容器加载新代码

```bash
docker restart nv_gw
```

### 2.2 验证

**E2E 测试**（glm5_2_nv 请求）：

```
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=False
         tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[NV-TIER] Starting tier=glm5_2_nv model=z-ai/glm-5.2 func=3b9748d8-1d8...
[NV-NONCYCLE-ERR] tier=glm5_2_nv k3 resp.status=400 non-cycling, aborting tier (no key cycle).
                  body={"status": 400, "detail": "Function id '3b9748d8...': DEGRADED function cannot be invoked"}
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[NV-TIER] Starting tier=dsv4p_nv model=deepseek-ai/deepseek-v4-pro func=74f02205-c7b...
[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

- ✅ 遇 400 立即 `NV-NONCYCLE-ERR`（不再 cycle 其余 4 key）
- ✅ 仅耗时 ~1.1s 即 abort tier（vs 之前 ~7s）
- ✅ fallback 到 dsv4p_nv 成功 → 200 OK

**容器代码确认**：

```
$ docker exec nv_gw grep -n 'should_cycle' /app/gateway/upstream.py
238: should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
621: should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
```

---

## 三、为什么这是安全的

1. **NVCF function DEGRADED 是 function-level** — 所有 key 共享同一 function，一个 key 400 意味着全部 400，cycle 无意义。
2. **Fallback 已工作** — R818 恢复 cross-model fallback（glm5_2_nv → dsv4p_nv），400 立即 abort 后 fallback 可用。
3. **401/403/429/408/500/502/503/504/202 仍 cycle** — 这些是 per-key 瞬态错误，cycle 换 key 可能救回，保留原逻辑。
4. **TIER_TIMEOUT_BUDGET_S=114 保护** — 即使 fallback 目标 dsv4p_nv 也 surge，不会无限等待。
5. **无 env 变量变更** — 纯代码变更，仅 2 行 diff。

---

## 四、HM1 当前参数（本次仅代码变更，无 env 变更）

| 参数 | 值 | 来源 |
|------|-----|------|
| **pexec should_cycle 400** | **移除** | **R819 新** |
| **integrate should_cycle 400** | **移除** | **R819 新** |
| func_health HEALTH_THRESHOLD | 0.10 (env: NVU_FALLBACK_HEALTH_THRESHOLD) | R818 |
| UPSTREAM_TIMEOUT | 66 | R754 |
| TIER_TIMEOUT_BUDGET_S | 114 | R737 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R768 floor |
| NVU_EMPTY_200_FASTBREAK | 1 | R774 floor |
| NVU_CONNECT_RESERVE_S | 0 | R657 floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708 floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R755 aligned |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631 floor |
| KEY_COOLDOWN_S | 25 | R162 |
| TIER_COOLDOWN_S | 25 | R492 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | R543 |
| NV_INTEGRATE_MODELS | "" (空) | R693 |

---

## 五、结论

R819 移除了 pexec/integrate 路径中对 `400_nvcf_degraded` 的 key cycle 行为。修复后：

- glm5_2_nv 请求遇第一个 400 立即 abort tier（~1s vs 之前 ~7s）
- 立即 fallback 到 dsv4p_nv（cross-model fallback 已由 R818 恢复）
- 节省 ~6s/request 浪费在注定失败的 key cycle 上
- 无 env 变更，仅 2 行代码 diff

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2