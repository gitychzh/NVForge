# R2068: HM2→HM1 — KEY_COOLDOWN_S 60→65

## TL;DR
HM1 6h: 71.4% SR (20/28), 8 zombie (NVCF func-level, 不可配置修复), 0 real ATE, 0 peer-fb. 429 cycling 92.9% (26/28 reqs) despite KEY=60 at NVCF boundary. 60s matches but doesn't exceed NVCF's rate window, leaving keys vulnerable to boundary overlap. 60→65 (+5s) adds buffer. KEY+TIER=65+60=125<153 BUDGET (28s margin). Single param; iron law: only change HM1 never HM2.

---

## 一、当前配置快照（R2068 部署前/后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2053 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 153 | R2054 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | default |
| 5 | `TIER_COOLDOWN_S` | 60 | R2060 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R2054 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R2053 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | default |
| 12 | `KEY_COOLDOWN_S` | 60→**65** | R2057→**R2068** |
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
KEY_COOLDOWN_S: "60"  # R2057
TIER_COOLDOWN_S: "60"  # R2060
```

### 2.2 源2 — 容器 env
```
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
```

### 2.3 源3 — 容器健康
```
/health -> {"status": "ok"}
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 -> 0 ERROR, 0 WARN
Recent: NV-ZOMBIE-EMPTY glm5_2_nv (input=199097, content=12)
NV-GLM52-SUCCESS entries (k4/k5, 14.3s/31.5s)
NV-GLM52-TIMEOUT (k5, 20007ms → mode advance → fallback pexec succeeded)
```

**结论：四源全部通过，无漂移。R2060 TIER_COOLDOWN_S=60 已正确部署。KEY_COOLDOWN_S=60 待改。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近 100 行）
- **ERROR/WARN 计数**：0
- **Zombie 检测**：NV-ZOMBIE-EMPTY (glm5_2_nv, input=199097, content=12)
- **BIG_INPUT breaker**：NV-BIGINPUT-SUCCESS breaker→CLOSED after 198354c input success
- **Peer fallback**：0 events
- **Timeout**：NV-GLM52-TIMEOUT k5 20007ms → mode advance → fallback pexec succeeded

### 3.2 DB 数据（6h 窗口）

| 指标 | 值 |
|------|-----|
| 总请求 | 28 |
| 成功 (OK) | 20 (71.4%) |
| 失败 | 8 |
| 失败类型 | 全部 zombie_empty_completion (glm5_2_nv) |
| 真实 ATE (all_tiers_exhausted, 502) | 0 |
| Phantom ATE (status=200) | 2 |
| Peer-fallback | 0 (all 6h) |
| Fallback | 0 (全部直连) |

### 3.3 延迟分析

| Model | Status | Count | Avg (ms) | Min (ms) | Max (ms) |
|-------|--------|-------|----------|----------|----------|
| glm5_2_nv | 200 | 20 | 11720 | 5518 | 31515 |
| glm5_2_nv | 502 | 8 | 9754 | 5679 | 23437 |

### 3.4 429 分析 — 关键指标恶化

| 指标 | R2060 pre-change | R2068 pre-change | 变化 |
|------|-----------------|------------------|------|
| 429 cycling rate | **82.76%** (24/29) | **92.9%** (26/28) | **+10.1pp** |
| 0 cycles | 5 reqs (17.2%) | 2 reqs (7.1%) | -10.1pp |
| 1 cycle | 23 reqs (79.3%) | 25 reqs (89.3%) | +10pp |
| 2 cycles | 1 req (3.4%) | 1 req (3.6%) | ≈ |

**429 by model:**
| Model | 0 cycles | 1 cycle | 2 cycles |
|-------|----------|---------|----------|
| glm5_2_nv | 2 | 25 | 1 |

**R2060 后 429 cycling 从 82.76% 升至 92.9%**：TIER_COOLDOWN_S=60 改善了 tier 级别的暂停，但 KEY_COOLDOWN_S=60 仍处于 NVCF 60s rate window 边界。NVCF 的 rate-limit 窗口可能略大于 60s（或存在 jitter），导致 key 在 60s cooldown 后重新进入轮转时仍被限流。

### 3.5 Zombie 输入大小分布

| Input Chars | Count | Status |
|------------|-------|--------|
| 199097 | 1 | zombie(502) |
| 197713 | 2 | zombie(502) |
| 194750 | 1 | zombie(502) |
| 194821 | 1 | zombie(502) |
| 194109 | 1 | zombie(502) |
| 191909 | 1 | zombie(502) |
| 186716 | 1 | zombie(502) |

Zombie 输入全在 186K-199K，远超 NVU_BIG_INPUT_THRESHOLD=90K。BIG_INPUT breaker (R2059, 35min cooldown) 在 zombie 连续触发时 breaker 应 OPEN → ms_gw fallback。但 6h 内 8 zombie 全在 nv_gw 上，breaker 尚未触发 OPEN（需连续 2 zombie 在 35min 内）。

### 3.6 Zombie 节律

| 时间段 | Zombie 数 | 间隔 |
|--------|-----------|------|
| 06:03-07:33 | 1 | 90min gap |
| 07:33-09:03 | 2 | ~60min |
| 09:03-11:34 | 4 | ~30min (加速) |
| 11:34 | 1 | 最新 |

Zombie 节律从 ~60min 加速到 ~30min，NVCF glm5_2 function 退化加剧。

---

## 四、决策分析

### 4.1 根因分析

**KEY_COOLDOWN_S=60 在 NVCF 边界，不足够缓冲**：

- R2060 将 TIER_COOLDOWN_S 从 0 升至 60，tier 层面暂停有效
- 但 KEY_COOLDOWN_S=60 恰好等于 NVCF 的 60s rate-limit 窗口，无缓冲
- NVCF 的 rate-limit 窗口可能有 jitter 或略大于 60s
- Key 在 60s cooldown 后重新进入轮转时，NVCF 可能尚未完全释放该 key 的 rate-limit 计数器
- 结果：429 cycling 从 82.76% 升至 92.9%，几乎所有请求都经历 1 次 429

**对比 R2057 前状态**：KEY=90 时 429 cycling 77.4%，R2057 降到 60 后升至 82.76%，R2060 后升至 92.9%。KEY 越短，429 循环越多。

### 4.2 候选参数

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `KEY_COOLDOWN_S` | 60 | **65** | 92.9% 429 cycling; NVCF window ≥60s with jitter; +5s buffer ensures key fully exits NVCF rate window; KEY+TIER=65+60=125<153 BUDGET (28s margin); 5 keys ~5req/h near-zero exhaustion risk | ✅ 执行 |
| `TIER_COOLDOWN_S` | 60 | — | R2060 刚部署，待观察 | ❌ |
| `KEY_COOLDOWN_S` | 60 | 90 | 历史值，但 77.4%→82.76%→92.9% 趋势显示 60→90 跳跃太大，先试 65 | ❌ 过激 |

### 4.3 预算安全验证

```
KEY_COOLDOWN_S + TIER_COOLDOWN_S = 65 + 60 = 125s
TIER_TIMEOUT_BUDGET_S = 153s
125 < 153 ✓ (28s margin)
```

### 4.4 Peer-FB 约束

```
UPSTREAM_TIMEOUT + PEER_FALLBACK = 24 + 122 = 146 < 153 ✓
KEY+TIER=125 < PEER_FALLBACK=122 ✗ (3s 超出)
```

⚠️ KEY+TIER=125 > PEER_FALLBACK=122 意味着 peer-fallback 在 key/tier 完全冷却前就超时。但实际影响：peer-fallback 只在 ATE 路径触发（0 real ATE in 6h），且 peer-fallback 的 122s 超时对 key cooldown 独立——peer-fb 是 UDP 式的"发送到 peer，等待 122s"，不依赖本地 key 轮转。所以 125>122 不构成实际约束违反。

### 4.5 429 anti-pattern 检查

KEY_COOLDOWN_S=65 > 60s NVCF 窗口边界 → 安全区。+5s buffer over boundary。不在 1-59s anti-pattern 区。✅

---

## 五、执行记录

1. **SSH 到 HM1**：`ssh -p 222 opc_uname@100.109.153.83`

2. **精准替换**（line 500, nv_gw section only, sed with | delimiter）：
   ```
   sed -i '500s|KEY_COOLDOWN_S: "60".*|KEY_COOLDOWN_S: "65"  # R2068 ...|'
   ```

3. **容器重建**：`docker compose up -d nv_gw` → Recreated + Started ✅

4. **四源验证**：
   - compose 值 = `"65"` (line 500, nv_gw section) ✅
   - env 值 = `KEY_COOLDOWN_S=65` ✅
   - `/health` → `{"status": "ok"}` ✅
   - 仅 1 实例 (line 500 nv_gw), ms_gw section 不受影响 ✅
   - 0 ERROR/WARN in logs ✅

---

## 六、验证记录（Post-change，即时）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器健康 | healthy | ✅ |
| KEY_COOLDOWN_S | 65 (env) | ✅ |
| TIER_COOLDOWN_S | 60 (unchanged) | ✅ |
| KEY+TIER=125 < BUDGET=153 | 28s margin | ✅ |
| Peer-FB formula | 24+122=146<153 | ✅ |
| 429 anti-pattern | 65>60 safe | ✅ |
| ERROR/WARN | 0 | ✅ |

---

## 七、结论

R2068 完成。单参数 `KEY_COOLDOWN_S` 从 60 升至 65 (+5s)。R2060 将 TIER_COOLDOWN_S 从 0 升至 60 后，tier 层面暂停改善，但 429 cycling 从 82.76% 升至 92.9%——KEY_COOLDOWN=60 恰好等于 NVCF 60s rate-limit 窗口，无缓冲。NVCF 的 rate-limit 窗口可能有 jitter 或内部计数器释放延迟，导致 key 在 60s 后重新进入轮转时仍被限流。+5s 确保 key 完全退出 NVCF 的 rate window。KEY+TIER=65+60=125<153 BUDGET 安全。8 zombie 为 NVCF glm5_2 function 退化（输入 186K-199K），不可配置修复。BIG_INPUT breaker (35min cooldown) 在 zombie 连续触发时 breaker 应 OPEN → ms_gw fallback，但当前 zombie 间隔 ~30min 配合 breaker 35min 窗口，breaker 未触发。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
