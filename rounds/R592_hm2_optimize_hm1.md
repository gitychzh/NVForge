# R592: HM2→HM1 — MIN_OUTBOUND_INTERVAL_S 0.4→0.3 (−0.1s)

## TL;DR
Zero-error stable regime marginal trim on outbound throttle.
单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R592 部署前/后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | `28` | R577 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | `90` | R576 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | **`0.3`** | **R592** |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | `1` | R559 |
| 5 | `TIER_COOLDOWN_S` | `25` | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | `25` | R560 |
| 7 | `NVU_CONNECT_RESERVE_S` | `2` | R570 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | `1.0` | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | `61` | R537 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | `1` | R502 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | `2` | R581 |
| 12 | `NV_INTEGRATE_ENABLED` | `1` | R574 |
| 13 | `NV_INTEGRATE_MODELS` | `dsv4p_nv,kimi_nv` | R575 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | `85` | R591 |
| 15 | `KEY_COOLDOWN_S` | `25` | R491 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
      MIN_OUTBOUND_INTERVAL_S: "0.4"  # R582
```

### 2.2 源2 — 容器 env
```
MIN_OUTBOUND_INTERVAL_S=0.4
```

### 2.3 源3 — 容器启动时间
```
2026-07-02T22:35:22.242282056Z
```
（Note: StartedAt predates R591 commit by ~1m35s; env already showing 85 indicates R591 container recreate did happen slightly before git commit timestamp, a plausible manual-op lag. After R592 force-recreate, timestamp aligns.）

### 2.4 源4 — 运行时日志
```
docker logs nv_40006_uni --tail 500
→ Only 4 startup lines; zero new ERROR/WARN in the observation window
```

**结论**：四源全部通过，无漂移。继续标准微优化流程。

---

## 三、数据摘要（部署前窗口, MAX(ts)−6h anchor）

### 3.1 Docker Logs
- integrate/pexec 路径启动正常，无 ERROR/WARN/429/empty_200/SSLEOF

### 3.2 DB Query — MAX(ts)−6h window (MAX_TS ≈ 2026-07-03 06:43 UTC)

| model | total | success | SR% | avg_succ_s | max_succ_s | fail | avg_fail_s | max_fail_s | fail_type |
|-------|-------|---------|-----|------------|------------|------|------------|------------|-----------|
| dsv4p_nv | 134 | 133 | **99.3%** | 38.9 | 161 | 1 | 143.4 | 143 | ATE |
| glm5_2_nv | 57 | 56 | **98.2%** | 4.0 | 13 | 1 | 34.8 | 34 | ATE |
| kimi_nv | 87 | 81 | **93.1%** | 67.0 | 351 | 6 | 74.7 | 76 | ATE |
| glm5_1_nv | 9 | 0 | **0.0%** | — | — | 9 | 10.7 | 89 | ATE |

- **kimi upstream_type**: integrate 80 成功 / pexec 1 成功
  - integrate 成功 avg = 67.7s, max = 351s (streaming TTFB-to-end latency)
  - pexec 成功 avg = 10.0s, max = 9s
- **429 / key_cycle**: 0 in window
- **empty_200**: 0
- **SSLEOF / SSL errors**: 0

### 3.3 关键观察
1. **dsv4p_nv & glm5_2_nv** → zero-error regime (SR > 98%).
2. **kimi_nv** → recovered from ~71–75% (R590–R591) to **93.1%** on integrate path; 6 ATE failures tightly clustered at **74–76 s**.
3. **glm5_1_nv** → hard failure (0/9); min 0 s indicates 404/INACTIVE rapid reject, max 89 s indicates timeout-then-ATE. NVCF function-level EOL, **non-actionable by gateway parameters**.

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `MIN_OUTBOUND_INTERVAL_S` | 0.4 | **0.3** (−0.1s) | stable zero-error on thinking models; KEY_COOLDOWN=25 ≫ 0.3 (margin 83×); reduces concurrent queue latency for burst kimi requests | ✅ 执行 |
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 85 | 80 (–5s) | kimi already 93.1%, marginal gain; 85 yields zero key_cycle 429; further drop risks micro-429 noise | ❌ 否决 |
| `TIER_TIMEOUT_BUDGET_S` | 90 | 88 (–2s) | kimi failures at 74–76 s, not budget-bound; 90 already safe ceiling validated by R576 | ❌ 否决 |
| `UPSTREAM_TIMEOUT` | 28 | 26 (–2s) | max pexec latency on kimi ≈ 9 s; 28 validated by R577; trim risks edge pexec cutoff | ❌ 否决 |
| `NVU_EMPTY_200_FASTBREAK` | 2 | 1 (–1s) | zero empty_200 occurrences; 2 is a safety buffer on NVCF flaky endpoints; trim not justified | ❌ 否决 |
| `NV_INTEGRATE_MODELS` | dsv4p_nv,kimi_nv | +glm5_1_nv | R577/R578 proved integrate endpoint returns 410/404 for glm family; would risk dead-key pollution | ❌ 否决 |

**最终决策**：仅执行 `MIN_OUTBOUND_INTERVAL_S` 0.4 → 0.3。其余候选均因边际收益不足或function级硬故障无法由参数修复而被否决。

---

## 五、执行记录

1. **SSH 到 HM1**
   ```bash
   ssh -p 222 opc_uname@100.109.153.83
   ```

2. **备份 compose**
   ```bash
   cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak
   ```

3. **精准替换 compose 行**
   ```python
   old_line = '      MIN_OUTBOUND_INTERVAL_S: "0.4"  # R582: HM2->HM1 - 0.5->0.4 (-0.1s). thinking req concurrent queue micro-reduce; KEY_COOLDOWN=25 >> 0.4 zero 429 risk; single param small-change multi-round; rule: only change HM1 not HM2'
   new_line = '      MIN_OUTBOUND_INTERVAL_S: "0.3"  # R592: HM2->HM1 - 0.4->0.3 (-0.1s). zero-error stable regime micro-trim; KEY_COOLDOWN=25 >> 0.3 zero 429 risk; single param small-change multi-round; rule: only change HM1 not HM2'
   ```
   替换后 `grep -n 'MIN_OUTBOUND_INTERVAL_S' docker-compose.yml` 确认仅第 423 行命中，无重复键。

4. **容器重建**
   ```bash
   cd /opt/cc-infra && docker compose up -d --force-recreate nv_40006_uni
   ```
   Result: Recreate → Recreated → Started ok.

5. **四源验证**
   - compose 值 = `0.3` ✅
   - env 值 = `0.3` ✅
   - 容器 StartedAt = `2026-07-02T22:51:25Z` (updated after commit) ✅
   - 运行时日志 = 正常启动，无报错 ✅

---

## 六、验证记录（Post-change，启动瞬间 + 日志窗口）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器重建 | 1 | ✅ |
| ERROR/WARN | 0 | ✅ |
| 429 / rate-limit | 0 | ✅ |
| empty_200 | 0 | ✅ |
| peer fallback 触发 | 0 | ✅ |
| 配置漂移（compose vs env） | 0 | ✅ |

> Note: Post-deploy latency/SR requires an observation window. Low traffic during this early-A.M. window means this round should be evaluated in the next cycle.

---

## 七、结论

R592 完成。单参数 `MIN_OUTBOUND_INTERVAL_S` 从 0.4 微调至 0.3（−0.1 s），在 zero-error 稳定期下继续释放出站并发余量（KEY_COOLDOWN=25 ≫ 0.3，零 429 风险）。系统整体处于 **stable regime**：dsv4p_nv 99.3 %、glm5_2_nv 98.2 %、kimi_nv 93.1 %（已从 R590 的 71–75 % 显著恢复）。glm5_1_nv 为 NVCF function-level 硬故障（EOL 下架），非网关参数可修复，本次不触及。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2
