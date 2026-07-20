# R2057: HM2→HM1 — KEY_COOLDOWN_S 90→60 (-30s)

## TL;DR
429 cycling 77.4% (24/31) despite 90s cooldown — zombie pairs (~30min cadence) cause key starvation. 60s is minimum safe boundary per anti-pattern. 60+0=60<<153 BUDGET safe. Single param; iron law: only change HM1 never HM2.

---

## 一、当前配置快照（R2057 部署前/后）

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
| 15 | `KEY_COOLDOWN_S` | 90→**60** | R2055→**R2057** |
| 16 | `NVU_TIER_BUDGET_DSV4P_NV` | 20 | R2052 |
| 17 | `NVU_TIER_BUDGET_GLM5_2_NV` | 20 | R2056 |
| 18 | `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | default |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
KEY_COOLDOWN_S: "90"  # R2055
```

### 2.2 源2 — 容器 env
```
KEY_COOLDOWN_S=90
```

### 2.3 源3 — 容器健康
```
/health → {"status": "ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 → 0 ERROR, 0 WARN
Only zombie_empty_completion entries (NVCF function-level, not config-fixable)
```

**结论：四源全部通过，无漂移。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近 100 行）
- **ERROR/WARN 计数**：0
- **Zombie 检测**：2 entries (glm5_2_nv, ~30min cadence, input_chars=194821/194750 > 100000 threshold)
- **BIG_INPUT breaker**：0 events (zombies caught by zombie_empty_completion detection before reaching BIG_INPUT)
- **Peer fallback**：0 events

### 3.2 DB 数据（6h 窗口）

| 指标 | 值 |
|------|-----|
| 总请求 | 30 |
| 成功 (OK) | 23 (76.67%) |
| 失败 | 7 |
| Zombie (NVCF empty200) | 6 (glm5_2_nv, ~30min pattern, 不可配置修复) |
| 真实 ATE (all_tiers_exhausted, 502) | 1 (glm5_2_nv, 40s duration, pre-R2056) |
| Phantom ATE (status=200) | 2 (dsv4p_nv) |
| Peer-fallback | 0 (all 6h) |
| Fallback | 0 (全部直连) |

### 3.3 延迟分析

| Model | Count | Avg (ms) | Min (ms) | Max (ms) |
|-------|-------|----------|----------|----------|
| dsv4p_nv | 2 | 9944 | 5836 | 14052 |
| glm5_2_nv | 28 | 11000 | 3629 | 24645 |

### 3.4 429 分析

| 指标 | 值 |
|------|-----|
| 429 cycling rate | 77.42% (24/31 reqs) |
| 0 cycles | 7 reqs (22.6%) |
| 1 cycle | 21 reqs (67.7%) |
| 2 cycles | 2 reqs (6.5%) |
| 3+ cycles | 0 |

**关键发现**：KEY_COOLDOWN_S=90 已 ≥60s 安全边界，但 429 率仍高达 77.4%。根因是 zombie 请求对 (~30min cadence) 消耗 key 后触发 90s 冷却，导致剩余 key 负载增加 → 429 级联。在低流量场景 (5 req/h, 5 keys) 下，60s 冷却足够让 key 完全冷却，且不会造成 key 饥饿。

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `KEY_COOLDOWN_S` | 90 | **60** (-30s) | 429 77.4% despite 90s; 60s = minimum safe boundary per anti-pattern; 60+0=60<<153 BUDGET; 5 keys 5req/h near-zero exhaustion risk | ✅ 执行 |
| `UPSTREAM_TIMEOUT` | 24 | — | 24s optimal, no change needed | ❌ |
| `TIER_TIMEOUT_BUDGET_S` | 153 | — | 153 sufficient for 20+20+100=140, no change needed | ❌ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 122 | — | Peer-fb not triggered (zombies bypass via zombie detection), no change needed | ❌ |

**预算安全验证**：60 (KEY) + 0 (TIER) = 60 ≤ 153 (TIER_TIMEOUT_BUDGET_S)。✅

**anti-pattern 检查**：KEY_COOLDOWN_S=60 ≥ 60s NVCF 窗口边界 → 安全区。✅

**最终决策**：仅执行 `KEY_COOLDOWN_S` 90→60。其余候选均被否决。

---

## 五、执行记录

1. **SSH 到 HM1**：`ssh -p 222 opc_uname@100.109.153.83`

2. **精准替换**（line 500, sed with | delimiter）：
   ```
   sed -i '500s|KEY_COOLDOWN_S: "90".*|KEY_COOLDOWN_S: "60"  # R2057 ...|'
   ```

3. **容器重建**：`docker compose up -d nv_gw` → Recreated + Started ✅

4. **四源验证**：
   - compose 值 = `"60"` (line 500, nv_gw section) ✅
   - env 值 = `KEY_COOLDOWN_S=60` ✅
   - `/health` → `{"status": "ok"}` ✅
   - ms_gw section line 186 still `"58"` (untouched) ✅

---

## 六、验证记录（Post-change，即时）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器健康 | healthy | ✅ |
| KEY_COOLDOWN_S | 60 (env) | ✅ |
| 总预算约束 | 60/153 | ✅ |
| 429 预期 | ↓ (60s vs 90s, key 更快回到轮转池) | ⏳ |
| ERROR/WARN | 0 | ✅ |

---

## 七、结论

R2057 完成。单参数 `KEY_COOLDOWN_S` 从 90 降至 60 (-30s)，目标是降低 zombie 请求对引发的 key 饥饿与 429 级联。60s = 429 反模式的安全边界最小值（≥NVCF 60s 窗口），在低流量场景 (5 keys, ~5 req/h) 下零 key 饥饿风险。6 个 zombie 均为 NVCF 函数级退化，不可配置修复。预算约束 60+0=60<<153 安全。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
