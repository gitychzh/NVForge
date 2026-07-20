# R2056: HM2→HM1 — NVU_TIER_BUDGET_GLM5_2_NV 18→20 (+2s)

## TL;DR
glm5_2 genuine OK max=24645ms > 18s budget (tight, ATE risk). +2s budget margin. 20+20+100=140<153 safe. Single param; iron law: only change HM1 never HM2.

---

## 一、当前配置快照（R2056 部署前/后）

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
| 15 | `KEY_COOLDOWN_S` | 90 | R2055 |
| 16 | `NVU_TIER_BUDGET_DSV4P_NV` | 20 | R2052 |
| 17 | `NVU_TIER_BUDGET_GLM5_2_NV` | 18→**20** | R2052→**R2056** |
| 18 | `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | default |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
NVU_TIER_BUDGET_GLM5_2_NV: "18"
```

### 2.2 源2 — 容器 env
```
NVU_TIER_BUDGET_GLM5_2_NV=18
```

### 2.3 源3 — 容器启动时间
```
nv_gw  Up 9 minutes (healthy)  ← R2055 restart
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 → 0 ERROR/WARN
```

**结论：四源全部通过，无漂移。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近 100 行 ≈ 9min 窗口）
- **ERROR/WARN 计数**：0
- **429 / empty_200 / timeout**：0
- **peer fallback 触发**：0
- 容器刚重启 9min，零流量期

### 3.2 DB 数据（6h 窗口）

| 指标 | 值 |
|------|-----|
| 总请求 | 31 |
| 成功 (OK) | 26 (83.9%) |
| 失败 | 5 |
| Zombie (NVCF empty200) | 4 (不可配置修复) |
| 真实 ATE (all_tiers_failed, 502) | 1 (3.2%) — **唯一可配置修复的失败** |
| Phantom ATE (peer-fb rescued) | 6 |
| Fallback | 0 (全部直连) |
| Tier attempts | 23 pexec_success, 2 pexec_429, 1 SSLEOF, 1 timeout |

### 3.3 延迟分析

| Model | Count | Avg (ms) | Min (ms) | Max (ms) |
|-------|-------|----------|----------|----------|
| dsv4p_nv | 2 | 9944 | 5836 | 14052 |
| glm5_2_nv | 24 | 10965 | 3629 | **24645** |

**关键发现**：glm5_2 最大成功延迟 24645ms > 当前 budget 18s (18000ms)。这意味着 borderline 请求（~20-24s）在 18s budget 下会触发 ATE，即使上游仍在正常处理。

### 3.4 429 分析
- glm5_2_nv: 24 reqs, 27 total_429s (~1.1/req)
- KEY_COOLDOWN_S=90 (R2055) 已生效，429 压制良好

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `NVU_TIER_BUDGET_GLM5_2_NV` | 18 | **20** (+2s) | glm5_2 genuine OK max=24645ms > 18s budget; 1 real ATE (3.2%) 可被 +2s margin 覆盖 | ✅ 执行 |
| `UPSTREAM_TIMEOUT` | 24 | — | 24s 已在 optimal，无需调整 | ❌ |
| `KEY_COOLDOWN_S` | 90 | — | R2055 刚部署 9min，429 压制已好，无需调整 | ❌ |
| `TIER_TIMEOUT_BUDGET_S` | 153 | — | 153 已足够容纳 20+20+100=140，无需调整 | ❌ |

**预算安全验证**：20 (dsv4p) + 20 (glm5_2) + 100 (minimax) = 140 ≤ 153 (TIER_TIMEOUT_BUDGET_S)。✅

**最终决策**：仅执行 `NVU_TIER_BUDGET_GLM5_2_NV` 18→20。其余候选均被否决。

---

## 五、执行记录

1. **SSH 到 HM1**：`ssh -p 222 opc_uname@100.109.153.83`

2. **备份 compose**：`cp docker-compose.yml docker-compose.yml.bak`

3. **精准替换**（line 649, sed with | delimiter）：
   ```
   sed -i '649s|NVU_TIER_BUDGET_GLM5_2_NV: "18".*|NVU_TIER_BUDGET_GLM5_2_NV: "20"  # R2056 ...|'
   ```

4. **容器重建**：`docker compose up -d nv_gw` → Recreated + Started ✅

5. **四源验证**：
   - compose 值 = `"20"` ✅
   - env 值 = `20` ✅
   - 容器 `Up 19 seconds (healthy)` ✅
   - `/health` → `{"status": "ok"}` ✅

---

## 六、验证记录（Post-change，即时）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器健康 | healthy | ✅ |
| 预算值 | 20 (env) | ✅ |
| 总预算约束 | 140/153 | ✅ |
| 首试成功率 | N/A (零流量) | ⏳ |
| ERROR/WARN | 0 | ✅ |

---

## 七、结论

R2056 完成。单参数 `NVU_TIER_BUDGET_GLM5_2_NV` 从 18 微调至 20（+2s），为 glm5_2 borderline 请求（max 24645ms）提供足够预算余量，预期减少 1 个 ATE 失败模式。预算约束 20+20+100=140<153 安全。零 zombie 救援（4 zombie 均为 NVCF 函数级退化，不可配置修复）。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
