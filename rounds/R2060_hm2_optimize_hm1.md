# R2060: HM2→HM1 — TIER_COOLDOWN_S 0→60

## TL;DR
HM1 6h: 82.76% 429 cycling rate (24/29 reqs) with TIER_COOLDOWN_S=0. KEY_COOLDOWN_S=60 cools individual keys but TIER_COOLDOWN_S=0 means the tier restarts immediately after key cooldown, hitting the next key which is also still in NVCF's 60s rate-limit window. 0→60 forces tier pause for full NVCF rate window. KEY+TIER=60+60=120<153 BUDGET safe. Single param; iron law: only change HM1 never HM2.

---

## 一、当前配置快照（R2060 部署前/后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2053 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 153 | R2054 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | default |
| 5 | `TIER_COOLDOWN_S` | 0→**60** | R2042→**R2060** |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R2054 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R2053 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | default |
| 12 | `KEY_COOLDOWN_S` | 60 | R2057 |
| 13 | `NVU_TIER_BUDGET_DSV4P_NV` | 20 | R2052 |
| 14 | `NVU_TIER_BUDGET_GLM5_2_NV` | 20 | R2056 |
| 15 | `NVU_BIG_INPUT_COOLDOWN_S` | 2100 | R2059 |
| 16 | `NVU_BIG_INPUT_FAIL_N` | 1 | R1713 |
| 17 | `NVU_BIG_INPUT_THRESHOLD` | 90000 | R2058 |
| 18 | `NVU_BIG_INPUT_MODELS` | glm5_2_nv,dsv4p_nv | R1889 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
TIER_COOLDOWN_S: "0"  # R2042
KEY_COOLDOWN_S: "60"  # R2057
```

### 2.2 源2 — 容器 env
```
TIER_COOLDOWN_S=0
KEY_COOLDOWN_S=60
```

### 2.3 源3 — 容器健康
```
/health -> {"status": "ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 -> 0 ERROR, 0 WARN
Recent: NV-ZOMBIE-EMPTY glm5_2_nv (input=197713, content=12)
NV-GLM52-SUCCESS entries (k1/k5, 5.5s/9.7s)
```

**结论：四源全部通过，无漂移。KEY_COOLDOWN_S=60 已正确部署，TIER_COOLDOWN_S=0 待改。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近 100 行）
- **ERROR/WARN 计数**：0
- **Zombie 检测**：NV-ZOMBIE-EMPTY (glm5_2_nv, input=197713, content=12)
- **BIG_INPUT breaker**：R2059 部署后待观察
- **Peer fallback**：0 events

### 3.2 DB 数据（6h 窗口）

| 指标 | 值 |
|------|-----|
| 总请求 | 29 |
| 成功 (OK) | 21 (72.41%) |
| 失败 | 8 |
| Zombie (NVCF empty200) | 7 (glm5_2_nv, ~30min pattern, 不可配置修复) |
| 真实 ATE (all_tiers_exhausted, 502) | 1 (glm5_2_nv, 40047ms, pre-R2056 era) |
| Phantom ATE (status=200) | 4 (glm5_2_nv: 2, dsv4p_nv: 2) |
| Peer-fallback | 0 (all 6h) |
| Fallback | 0 (全部直连) |

### 3.3 延迟分析

| Model | Status | Count | Avg (ms) | Min (ms) | Max (ms) |
|-------|--------|-------|----------|----------|----------|
| dsv4p_nv | 200 | 2 | 9944 | 5836 | 14052 |
| glm5_2_nv | 200 | 19 | 10363 | 5518 | 24645 |
| glm5_2_nv | 502 | 7 | 11612 | 5679 | 40047 |

### 3.4 429 分析 — **主要问题**

| 指标 | 值 |
|------|-----|
| 429 cycling rate | **82.76%** (24/29 reqs) |
| 0 cycles | 5 reqs (17.2%) — 2 dsv4p_nv + 3 glm5_2_nv |
| 1 cycle | 23 reqs (79.3%) — all glm5_2_nv |
| 2 cycles | 1 req (3.4%) — glm5_2_nv |

**429 by model:**
| Model | 0 cycles | 1 cycle | 2 cycles |
|-------|----------|---------|----------|
| dsv4p_nv | 2 | 0 | 0 |
| glm5_2_nv | 3 | 23 | 1 |

### 3.5 Peer-FB 健康检查

HM1 peer-fb formula: `UPSTREAM_TIMEOUT=24 + PEER_FALLBACK=122 = 146 < BUDGET=153` → 7s margin, should trigger. But 0 peer-fb events in 6h → zombies are handled mid-stream before peer-fb path is reached. Only ATE path triggers peer-fb, and the only real ATE (502) was pre-R2056.

### 3.6 Zombie 输入大小分布

| Input Chars | Count | Status |
|------------|-------|--------|
| 197713 | 2 | zombie(502) |
| 194821 | 1 | zombie(502) |
| 194750 | 1 | zombie(502) |
| 194109 | 1 | zombie(502) |
| 191909 | 1 | zombie(502) |
| 186716 | 1 | zombie(502) |

---

## 四、决策分析

### 4.1 根因分析

**TIER_COOLDOWN_S=0 是 429 放大器**：

- KEY_COOLDOWN_S=60 冷却单个 key（>=NVCF 60s 窗口），key 冷却后重新进入轮转池
- 但 TIER_COOLDOWN_S=0 意味着 tier 在 key 冷却完后**立即重新开始**，无任何暂停
- 实际效果：key k1 被 429 → 冷却 60s → tier 立即试 k2 → k2 也在 NVCF 的同函数 rate-limit 窗口内 → 也被 429
- 结果：82.76% 的请求都经历 429 循环，23/29 个请求至少 1 次 429，每次 429 浪费 ~10s（key cooldown 60s 内等待）

**对比 HM2 历史成功模式**：R1819 时 HM1 的 TIER_COOLDOWN_S=63（与 KEY_COOLDOWN_S 相同），SR 86.2%。R2042 将 TIER_COOLDOWN_S 降到 0 导致 429 率飙升。

### 4.2 候选参数

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `TIER_COOLDOWN_S` | 0 | **60** | 82.76% 429 cycling; NVCF 60s rate window; KEY=60 already covers individual key cooling but tier needs pause too; KEY+TIER=60+60=120<153 BUDGET safe; low traffic (5 req/h, 5 keys) → no exhaustion risk | ✅ 执行 |
| `KEY_COOLDOWN_S` | 60 | — | Already at floor (>=60s NVCF window), 不可降 | ❌ |
| `UPSTREAM_TIMEOUT` | 24 | — | glm5_2 max=24645ms > 24s, 已边界紧张 | ❌ |
| `BUDGET` | 153 | — | KEY+TIER=120<153, 33s margin OK | ❌ |

### 4.3 预算安全验证

```
KEY_COOLDOWN_S + TIER_COOLDOWN_S = 60 + 60 = 120s
TIER_TIMEOUT_BUDGET_S = 153s
120 < 153 ✓ (33s margin)
```

### 4.4 Peer-FB 约束

```
UPSTREAM_TIMEOUT + PEER_FALLBACK = 24 + 122 = 146 < 153 ✓
HM2 NVU_TIER_BUDGET_GLM5_2_NV=120 < PEER_FALLBACK=122 ✓ (2s buffer)
HM2 NVU_TIER_BUDGET_DSV4P_NV=180 > PEER_FALLBACK=122 ✗ (but dsv4p_nv has 0 429s, ATE path rare)
```

### 4.5 429 anti-pattern 检查

KEY_COOLDOWN_S=60 ≥ 60s NVCF 窗口边界 → 安全区。TIER_COOLDOWN_S=60 = KEY_COOLDOWN_S → 一致。不在 1-59s anti-pattern 区。✅

---

## 五、执行记录

1. **SSH 到 HM1**：`ssh -p 222 opc_uname@100.109.153.83`

2. **精准替换**（line 505, nv_gw section only, sed with | delimiter）：
   ```
   sed -i '505s|TIER_COOLDOWN_S: "0".*|TIER_COOLDOWN_S: "60"  # R2060 (HM2->HM1): ...|'
   ```

3. **容器重建**：`docker compose up -d nv_gw` → Recreated + Started ✅

4. **四源验证**：
   - compose 值 = `"60"` (line 505, nv_gw section) ✅
   - env 值 = `TIER_COOLDOWN_S=60` ✅
   - `/health` → `{"status": "ok"}` ✅
   - 仅 1 实例 (line 505 nv_gw), ms_gw section 不受影响 ✅
   - 0 ERROR/WARN in logs ✅

---

## 六、验证记录（Post-change，即时）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器健康 | healthy | ✅ |
| TIER_COOLDOWN_S | 60 (env) | ✅ |
| KEY_COOLDOWN_S | 60 (unchanged) | ✅ |
| KEY+TIER=120 < BUDGET=153 | 33s margin | ✅ |
| Peer-FB formula | 24+122=146<153 | ✅ |
| 429 anti-pattern | 60≥60 safe | ✅ |
| ERROR/WARN | 0 | ✅ |

---

## 七、结论

R2060 完成。单参数 `TIER_COOLDOWN_S` 从 0 升至 60。82.76% 429 cycling 是 HM1 当前最大问题 — KEY_COOLDOWN_S=60 冷却单个 key 但 TIER_COOLDOWN_S=0 让 tier 立即重试下一个 key（仍在 NVCF 60s rate-limit 窗口内），导致几乎每个 glm5_2_nv 请求都经历 1-2 次 429。60s tier cooldown 强制 tier 暂停整个 NVCF rate 窗口，让所有 key 充分冷却后才重新尝试。KEY+TIER=60+60=120<153 BUDGET 安全。低流量无 key 耗尽风险。7 个 zombie 为 NVCF 函数级退化（不可配置修复），BIG_INPUT breaker (R2059, 35min cooldown) 待下一 zombie 触发验证。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
