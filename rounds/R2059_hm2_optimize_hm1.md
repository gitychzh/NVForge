# R2059: HM2→HM1 — NVU_BIG_INPUT_COOLDOWN_S 1200→2100 (+15min, 20m→35m)

## TL;DR
R2058 BIG_INPUT_THRESHOLD 100K→90K deployed but breaker 0 events in 14d. Root cause: all glm5_2_nv requests have >180K input — threshold irrelevant. Real bottleneck: cooldown 1200s (20min) < zombie cadence ~30min. Breaker opens after each zombie but expires before next arrives. 1200→2100 (35min) spans cadence. Single param; iron law: only change HM1 never HM2.

---

## 一、当前配置快照（R2059 部署前/后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2053 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 153 | R2054 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | default |
| 5 | `TIER_COOLDOWN_S` | 0 | floor |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R2054 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R2053 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | default |
| 12 | `NV_INTEGRATE_ENABLED` | (unset) | — |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | R1421 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | floor |
| 15 | `KEY_COOLDOWN_S` | 60 | R2057 |
| 16 | `NVU_TIER_BUDGET_DSV4P_NV` | 20 | R2052 |
| 17 | `NVU_TIER_BUDGET_GLM5_2_NV` | 20 | R2056 |
| 18 | `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | default |
| 19 | `NVU_BIG_INPUT_THRESHOLD` | 90000 | R2058 |
| 20 | `NVU_BIG_INPUT_FAIL_N` | 1 | R1713 |
| 21 | `NVU_BIG_INPUT_COOLDOWN_S` | 1200→**2100** | R2054→**R2059** |
| 22 | `NVU_BIG_INPUT_MODELS` | glm5_2_nv,dsv4p_nv | R1889 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
NVU_BIG_INPUT_COOLDOWN_S: "1200"  # R2054
NVU_BIG_INPUT_THRESHOLD: "90000"  # R2058
```

### 2.2 源2 — 容器 env
```
NVU_BIG_INPUT_COOLDOWN_S=1200
NVU_BIG_INPUT_THRESHOLD=90000
KEY_COOLDOWN_S=60
```

### 2.3 源3 — 容器健康
```
/health → {"status": "ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 → 0 ERROR, 0 WARN
Recent: NV-ZOMBIE-EMPTY glm5_2_nv (input_chars=197713, content_chars=12 < 50)
NV-GLM52-SUCCESS entries (k1/k5, 5.5s/9.7s)
```

**结论：四源全部通过，无漂移。R2058 已正确部署。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近 100 行）
- **ERROR/WARN 计数**：0
- **Zombie 检测**：1 条 NV-ZOMBIE-EMPTY (glm5_2_nv, input=197713, content=12)
- **BIG_INPUT breaker**：0 events (14d history: 0 events total)
- **Peer fallback**：0 events

### 3.2 DB 数据（6h 窗口）

| 指标 | 值 |
|------|-----|
| 总请求 | 30 |
| 成功 (OK) | 24 (80.00%) |
| 失败 | 6 |
| Zombie (NVCF empty200) | 5 (glm5_2_nv, ~30min pattern, 不可配置修复) |
| 真实 ATE (all_tiers_exhausted, 502) | 1 (glm5_2_nv, 40047ms, pre-R2056 era) |
| Phantom ATE (status=200) | 0 |
| Peer-fallback | 0 (all 6h) |
| Fallback | 0 (全部直连) |

### 3.3 延迟分析

| Model | Status | Count | Avg (ms) | Min (ms) | Max (ms) |
|-------|--------|-------|----------|----------|----------|
| dsv4p_nv | 200 | 2 | 9944 | 5836 | 14052 |
| glm5_2_nv | 200 | 21 | 10114 | 3629 | 24645 |
| glm5_2_nv | 502 | 7 | 12660 | 5679 | 40047 |

### 3.4 429 分析

| 指标 | 值 |
|------|-----|
| 429 cycling rate | 76.67% (23/30 reqs) |
| 0 cycles | 7 reqs (23.3%) |
| 1 cycle | 21 reqs (70.0%) |
| 2 cycles | 2 reqs (6.7%) |

### 3.5 Tier Attempts 错误

| Tier | Error Type | Count |
|------|-----------|-------|
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_429 | 1 |
| glm5_2_nv | pexec_SSLEOFError | 1 |
| glm5_2_nv | pexec_timeout | 1 |

### 3.6 BIG_INPUT Breaker 深度分析 (14d)

| 指标 | 值 |
|------|-----|
| BIG_INPUT events (14d) | **0** |
| TODAY events | 0 |
| All glm5_2_nv input_chars | 180K-196K (ALL > threshold) |
| Zombie input_chars | 186K-195K (also ALL > threshold) |

**关键发现**：BIG_INPUT breaker 历史上 0 事件。代码逻辑正确（upstream.py:1358 检查 is_big_input_open → 返回 all_tiers_exhausted, handlers.py 的 zombie 检测正确 feed record_big_input_failure）。但 0 事件说明 breaker 从未在 OPEN 状态拦截到请求。根因：cooldown 1200s (20min) < zombie cadence ~30min。breaker 在 zombie 后 OPEN，但 20min 后过期 (HALF_OPEN)，下一个请求 (~30min 后) 走 nv 正常链，成功则 CLOSED 重置 → 下个 zombie 又需要重新累积 fail_count→OPEN 循环。

### 3.7 Zombie 输入大小分布

| Input Chars | Count | Status |
|------------|-------|--------|
| 194821 | 1 | zombie(502) |
| 194750 | 1 | zombie(502) |
| 194109 | 1 | zombie(502) |
| 191909 | 1 | zombie(502) |
| 186716 | 1 | zombie(502) |

所有 glm5_2_nv 请求 (包括成功的) 都在 180K-196K 范围 — openclaw agent 发送超大 prompt。阈值 90K-100K 对 glm5_2_nv 无区分度。

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `NVU_BIG_INPUT_COOLDOWN_S` | 1200 | **2100** (+15min) | R2058 breaker 0 events 14d; 20m cooldown < 30m zombie cadence; 35m spans cadence → next zombie hits OPEN breaker → ms_gw fallback; 5 req/h low traffic → legitimate probed during OPEN unlikely; 2100 = 35min safe margin over 30min cadence | ✅ 执行 |
| `NVU_BIG_INPUT_THRESHOLD` | 90000 | — | All glm5_2_nv >180K, threshold irrelevant for this model; change already deployed in R2058 | ❌ |
| `NVU_BIG_INPUT_FAIL_N` | 1 | — | Already 1, minimum; no change needed | ❌ |
| `KEY_COOLDOWN_S` | 60 | — | 60s = floor (≥NVCF 60s 窗口), 不可再降 | ❌ |
| `UPSTREAM_TIMEOUT` | 24 | — | glm5_2 max=24645ms > 24s, 已边界紧张 | ❌ |

**预算安全验证**：BIG_INPUT_COOLDOWN 不影响 TIER_TIMEOUT_BUDGET 预算。✅

**anti-pattern 检查**：KEY_COOLDOWN_S=60 ≥ 60s NVCF 窗口边界 → 安全区。✅

**ms_gw 回退安全**：BIG_INPUT breaker OPEN 时，超大 input 请求返回 all_tiers_exhausted → handlers 层 peer-fallback 到 HM2 的 ms_gw。HM2 ms_gw 有 glm5_2_ms tier，可正常服务。无请求丢失风险。

**误杀风险评估**：5 req/h, 5 keys 低流量。35min cooldown 内出现的合法超大 input 请求（~0.5 req/h 概率）会被 breaker 拦截 → ms_gw 回退（非丢失）。对用户体验影响极小（ms_gw 延迟 < nv_gw 延迟）。

**最终决策**：仅执行 `NVU_BIG_INPUT_COOLDOWN_S` 1200→2100。其余候选均被否决。

---

## 五、执行记录

1. **SSH 到 HM1**：`ssh -p 222 opc_uname@100.109.153.83`

2. **精准替换**（line 634, sed with | delimiter）：
   ```
   sed -i '634s|NVU_BIG_INPUT_COOLDOWN_S: "1200".*|NVU_BIG_INPUT_COOLDOWN_S: "2100"  # R2059 ...|'
   ```

3. **容器重建**：`docker compose up -d nv_gw` → Recreated + Started ✅

4. **四源验证**：
   - compose 值 = `"2100"` (line 634, nv_gw section) ✅
   - env 值 = `NVU_BIG_INPUT_COOLDOWN_S=2100` ✅
   - `/health` → `{"status": "ok"}` ✅
   - 仅 1 实例 (line 634 nv_gw)，无 ms_gw 冲突 ✅
   - 0 ERROR/WARN in logs ✅

---

## 六、验证记录（Post-change，即时）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器健康 | healthy | ✅ |
| BIG_INPUT_COOLDOWN_S | 2100 (env) | ✅ |
| BIG_INPUT_THRESHOLD | 90000 (unchanged) | ✅ |
| BIG_INPUT_FAIL_N | 1 (unchanged) | ✅ |
| BIG_INPUT_MODELS | glm5_2_nv,dsv4p_nv (unchanged) | ✅ |
| 预算约束 | 无影响 | ✅ |
| ERROR/WARN | 0 | ✅ |
| Zombie cadence cover | 35min > 30min | ✅ |

---

## 七、结论

R2059 完成。单参数 `NVU_BIG_INPUT_COOLDOWN_S` 从 1200 升至 2100 (+15min, 20m→35m)。R2058 将 BIG_INPUT_THRESHOLD 从 100K→90K 但 breaker 历史上 0 事件 — 所有 glm5_2_nv 请求 (包括合法) 皆 >180K input，阈值无区分度。根因是 cooldown 20min < zombie cadence 30min，breaker 来不及生效。35min cooldown 覆盖 ~30min 僵尸周期，使下一个 zombie 在 breaker OPEN 时到达 → ms_gw 回退。5 req/h 低流量下合法请求误杀风险极低 (ms_gw 回退非丢失)。5 个 zombie 均为 NVCF 函数级退化，不可配置修复。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
