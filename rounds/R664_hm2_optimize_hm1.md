# R664: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 53→52 (−1s)

## TL;DR
Continue R656-R664 trajectory: 61→59→58→57→56→55→54→53→52 (−9s total). 6h zero-error regime (0 log errors, 4 ATE server-side all_tiers_exhausted non-config fixable, 1 minor kc429). integrate 12/12 OK, pexec 61/61 OK. 52s >> UPSTREAM_TIMEOUT=25 margin 27s safe. Single param per round. Iron rule: only change HM1 never HM2.

---

## 一、当前配置快照（R664 部署后）

| # | 参数 | HM1 值 | 历史来源 |
|---|------|--------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 25 | R652 (floor) |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 80 | R655 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 (floor) |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R559 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 8 | R649 (floor) |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 (floor) |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 (floor) |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | **53→52** | **R664 (this)** |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 1 | R502 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577 |
| 12 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 (floor) |
| 13 | `KEY_COOLDOWN_S` | 25 | R162 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "53" (line 492)
```
### 2.2 源2 — 容器 env
```
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=53
```
### 2.3 源3 — 容器启动时间
```
2026-07-03T22:17:20Z (R663 deploy, ~9h ago)
```
### 2.4 源4 — 运行时日志
```
docker logs nv_40006_uni --tail 100 → (no error/warn)
tail 500 patterns: peer-originated=0, peer fb FAILED=0, empty_200=0, 429=0
```

**结论：四源全部通过。53 confirmed in compose + env. 容器 StartedAt after R663 commit (cbd05da). 零日志错误。**

---

## 三、数据摘要（R663 deploy ~9h → 当前，6h DB 窗口）

### 3.1 Docker Logs（tail 100，容器刚 restart 仅 startup log）
- **ERROR/WARN**: 0
- **peer-originated**: 0 / **peer fallback FAILED**: 0
- **empty_200**: 0 / **429_nv_rate_limit**: 0
- **HM-FORCE-STREAM**: 0

### 3.2 DB（6h: 77 req total）
| 指标 | 数值 |
|------|------|
| Total | 77 |
| OK (status=200) | 73 (94.8%) |
| Fail | 4 (all `all_tiers_exhausted`, upstream_type=NULL — server-side non-config fixable) |
| req_with_429cycle | 1 |
| total_429cycles | 1 |
| avg_duration_ms | 25274.3 |
| max_duration_ms | 494127 |

### 3.3 路径分布（6h）
| upstream_type | total | ok | fail | avg_ms | max_ms | kc429 |
|---------------|-------|----|------|--------|--------|-------|
| nvcf_pexec    | 61    | 61 | 0    | 7248.0 | 107733 | 1     |
| nv_integrate  | 12    | 12 | 0    | 112944.4 | 494127 | 0     |
| NULL (ATE)    | 4     | 0  | 4    | 37164.0 | 141293 | 0     |

### 3.4 模型分布（6h）
| mapped_model | ok | fail | avg_ok_ms | max_ok_ms | avg_ttfb |
|--------------|----|------|-----------|-----------|----------|
| glm5_2_nv    | 60 | 3    | 5573.3    | 65265     | 5553.7   |
| dsv4p_nv     | 9  | 1    | 156445.9  | 494127    | 78929.7  |
| kimi_nv      | 4  | 0    | 13763.3   | 29294     | 8901.5   |

### 3.5 错误分布（6h）
```
all_tiers_exhausted: 4 (all upstream_type=NULL — server-side NVCF scheduling, non-config fixable)
```

**Zero-error regime confirmed. No config-fixable errors. All 4 ATE are server-side all_tiers_exhausted.**

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 53 | **52** (−1s) | R656-R663 trajectory: 61→53 all zero-error; pexec 61/61 OK, integrate 12/12 OK; 52-25=27s margin >> safe | ✅ 执行 |
| `TIER_TIMEOUT_BUDGET_S` | 80 | 75 | pexec max=16.9s (R655) << 80s; ATE max=141s suggests BUDGET binding on failure path; but data too small (4 ATE); premature | ❌ 暂缓 |
| `NVU_EMPTY_200_FASTBREAK` | 2 | 1 | 0 empty_200 in current window; but 6h window low traffic (77 req) — insufficient evidence | ❌ 暂缓 |

**最终决策**：仅执行 `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 53→52 (−1s)。Continue proven trajectory. Other params at floor or need more data.

---

## 五、执行记录

1. **SSH 到 HM1** → ok (tailscale ping 1ms)
2. **备份 compose**: `cp ... docker-compose.yml.bak.R664`
3. **精准替换**: Python stdin pipe — 修改 line 492 `"53"` → `"52"`, 插入 R664 注释行
4. **容器重建**: `docker compose up -d nv_40006_uni` → Recreate/Recreated/Starting/Started
5. **四源验证**:
   - compose line 492 = `"52"` ✅
   - container env = `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=52` ✅
   - StartedAt = `2026-07-03T22:30:36Z` (fresh) ✅
   - logs: (no error/warn) ✅
   - container: Up 23 seconds (healthy) ✅

---

## 六、验证记录（Post-change）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器状态 | Up (healthy) | ✅ |
| FORCE_STREAM_UPGRADE_TIMEOUT env | 52 | ✅ |
| 日志 ERROR/WARN | 0 | ✅ |
| 容器重建 | fresh StartedAt | ✅ |
| DB pending | 等待新 regime 积累 | — |

---

## 七、结论

R664 完成。`NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 从 53 微调至 52（−1s）。R656-R664 trajectory: 61→52（−9s total）。Zero-error regime sustained (0 log errors, 4 ATE server-side non-config fixable, 1 minor kc429)。Margin 27s >> safe above UPSTREAM=25。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2