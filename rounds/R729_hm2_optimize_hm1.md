# R729: HM2→HM1 — UPSTREAM_TIMEOUT 44→46 (+2s)

## TL;DR
dsv4p_nv NVCFPexecTimeout max=44,408ms + glm5_2_nv max=44,256ms 双双绑定 UPSTREAM=44。+2s捕获44-46s边缘窗口，减少直接fallback到glm5_2_nv的频率。BUDGET=110>>46+46=92s (FASTBREAK=2) 安全，fallback max success=99,088ms<110s零误杀。

---

## 一、数据收集 (2026-07-05 ~12:40 UTC)

### 容器状态
- 容器: nv_gw, Up 4 minutes (healthy) — R728 部署后
- FASTBREAK=2 ✓ (R728), UPSTREAM_TIMEOUT=44, FORCE_STREAM_UPGRADE_TIMEOUT=44 ✓
- TIER_TIMEOUT_BUDGET_S=110, FALLBACK_HEALTH_THRESHOLD=0.10
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=0, MIN_OUTBOUND_INTERVAL_S=0
- NVU_CONNECT_RESERVE_S=0, NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_EMPTY_200_FASTBREAK=2

### 6h DB 聚合 (07:00–13:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 316 |
| OK (200) | 212 (67.1%) |
| 失败 (ATE) | 104 (32.9%) |
| 其他失败 | 0 |

### 按模型 SR

| 模型 | 总请求 | OK | ATE | SR% | avg_ttfb_ok | avg_dur_ok | max_dur_ok | avg_dur_fail | max_dur_fail |
|------|--------|-----|-----|-----|-------------|------------|------------|--------------|--------------|
| dsv4p_nv | 236 | 136 | 100 | 57.6% | 36,691ms | 36,758ms | 99,088ms | 77,786ms | 177,317ms |
| glm5_2_nv | 79 | 76 | 3 | 96.2% | 20,082ms | 20,100ms | 90,312ms | 83,178ms | 88,486ms |
| kimi_nv | 1 | 0 | 1 | 0.0% | — | — | — | 2,682ms | 2,682ms |

### ATE 分类

| 指标 | 值 |
|------|-----|
| ATE 总数 | 104 |
| tiers_tried=1 | 39 (avg 50,826ms, max 80,546ms) — 全部 fallback_actually_attempted=f |
| tiers_tried=2 | 65 (avg 93,055ms, max 177,317ms) |

### Single-tier ATE 明细

| start_tier_idx | fallback_actually_attempted | cnt | avg_dur |
|----------------|-----------------------------|-----|---------|
| 0 (kimi_nv) | f | 1 | 2,682ms |
| 1 (dsv4p_nv) | f | 36 | 50,514ms |
| 3 (glm5_2_nv) | f | 2 | 80,525ms |

> 36/39 single-tier ATE 来自 dsv4p_nv，全部 fallback_actually_attempted=f。大部分为 pre-R728 restart 窗口（FASTBREAK=1 时1次timeout即放弃跳转fallback，但fallback被HEALTH_THRESHOLD阻断或未部署）。

### 成功 fallback 统计

| fallback_occurred | cnt | avg_dur | max_dur | min_dur |
|-------------------|-----|---------|---------|---------|
| f (直接) | 153 | 19,875ms | 60,099ms | 1,335ms |
| t (fallback) | 59 | 59,083ms | 99,088ms | 34,410ms |

### 按小时 SR 趋势

| 小时 (UTC) | 总请求 | OK | ATE | SR% |
|-----------|--------|-----|-----|-----|
| 22:00 (Jul 4) | 10 | 7 | 3 | 70.0% |
| 23:00 (Jul 4) | 9 | 8 | 1 | 88.9% |
| 00:00 | 2 | 2 | 0 | 100.0% |
| 01:00 | 13 | 8 | 5 | 61.5% |
| 02:00 | 49 | 35 | 14 | 71.4% |
| 03:00 | 27 | 20 | 7 | 74.1% |
| 04:00 | 21 | 14 | 7 | 66.7% |
| 05:00 | 20 | 7 | 13 | 35.0% |
| 06:00 | 29 | 22 | 7 | 75.9% |
| 07:00 | 24 | 21 | 3 | 87.5% |
| 08:00 | 23 | 13 | 10 | 56.5% |
| 09:00 | 21 | 17 | 4 | 81.0% |
| 10:00 | 26 | 12 | 14 | 46.2% |
| 11:00 | 18 | 12 | 6 | 66.7% |
| 12:00 | 24 | 14 | 10 | 58.3% |

### NVCFPexecTimeout 按 key 分布 (dsv4p_nv)

| nv_key_idx | cnt | avg_ms | max_ms |
|------------|-----|--------|--------|
| 0 | 14 | 32,282 | 40,443 |
| 1 | 16 | 32,970 | **44,408** |
| 2 | 19 | 32,629 | 40,457 |
| 3 | 11 | 31,213 | 36,475 |
| 4 | 12 | 33,465 | **44,350** |

> dsv4p_nv NVCFPexecTimeout max=44,408ms (k1) + 44,350ms (k4) ≈ UPSTREAM=44 + ~400ms overhead → **UPSTREAM 是绑定约束**

### NVCFPexecTimeout 按 key 分布 (glm5_2_nv)

| nv_key_idx | cnt | avg_ms | max_ms |
|------------|-----|--------|--------|
| 0 | 2 | 28,566 | 31,797 |
| 1 | 4 | 39,312 | **44,247** |
| 2 | 5 | 37,708 | 42,283 |
| 3 | 4 | 39,648 | **44,256** |
| 4 | 6 | 39,499 | 42,291 |

> glm5_2_nv NVCFPexecTimeout max=44,256ms (k3) + 44,247ms (k1) ≈ UPSTREAM=44 + ~256ms → **也是 UPSTREAM 绑定约束**

### 日志关键发现

```
[12:42:35.9] tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={})  ← FALLBACK_GRAPH 活跃
[12:43:39.7] tier_chain=... health={'74f02205...': 1.0}  ← dsv4p_nv health=1.0 (刚启动)
[12:44:48.2] tier_chain=... health={'74f02205...': 1.0}
[12:45:08.3] [NV-PEXEC-FASTBREAK] tier=dsv4p_nv 2 consecutive NVCFPexecTimeout → fast-break
[12:45:08.3] [NV-FALLBACK] Tier dsv4p_nv all-failed → falling back to glm5_2_nv
[12:45:59.2] tier_chain=... health={'74f02205...': 0.5}  ← dsv4p_nv health 下降中
[12:46:16.9] [NV-PEXEC-FASTBREAK] tier=dsv4p_nv 2 consecutive → fast-break
[12:46:37.0] [NV-ALL-TIERS-FAIL] All 2 tiers failed, elapsed=177317ms, ABORT-NO-FALLBACK
[12:46:37.0] [NV-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted
```

- **FALLBACK_GRAPH 双向正常工作** (dsv4p_nv↔glm5_2_nv)
- **FASTBREAK=2 生效**: 2次 pexec timeout 即 fast-break，省去剩余3键
- **dsv4p_nv health**: 1.0 → 0.5 快速下降 (NVCF 上游函数不稳定)
- **peer-originated hop=1**: HM2→HM1 转发请求也双 tier 耗尽，非 HM1 配置问题
- **kc429=0**: 零 rate-limit

### 最近15条请求

| 时间 | 模型 | 状态 | 耗时 | 路径 |
|------|------|------|------|------|
| 12:43:39 | dsv4p_nv | 502 | 177,317ms | 双tier耗尽 |
| 12:42:35 | dsv4p_nv | 200 | 21,040ms | pexec直接 |
| 12:35:37 | glm5_2_nv | 200 | 5,343ms | pexec直接 |
| 12:33:20 | glm5_2_nv | 502 | 88,486ms | 双tier耗尽 |
| 12:31:34 | dsv4p_nv | 502 | 88,656ms | 双tier耗尽 |
| 12:30:23 | dsv4p_nv | 502 | 88,648ms | 双tier耗尽 |
| 12:29:14 | dsv4p_nv | 200 | 37,757ms | pexec直接 |
| 12:26:53 | dsv4p_nv | 200 | 37,111ms | pexec直接 |
| 12:24:41 | dsv4p_nv | 200 | 84,080ms | fallback成功 |
| 12:23:33 | dsv4p_nv | 502 | 88,661ms | 双tier耗尽 |
| 12:22:00 | dsv4p_nv | 502 | 88,777ms | 双tier耗尽 |
| 12:20:51 | dsv4p_nv | 200 | 43,868ms | pexec直接 |
| 12:19:46 | dsv4p_nv | 200 | 23,547ms | pexec直接 |
| 12:18:08 | dsv4p_nv | 502 | 88,642ms | 双tier耗尽 |
| 12:16:41 | dsv4p_nv | 200 | 24,034ms | pexec直接 |

---

## 二、优化决策

### 问题诊断

1. **dsv4p_nv NVCFPexecTimeout max=44,408ms (k1)** 精确绑定 UPSTREAM=44，+408ms overhead
2. **glm5_2_nv NVCFPexecTimeout max=44,256ms (k3)** 同样绑定 UPSTREAM=44，+256ms overhead
3. dsv4p_nv health 1.0→0.5 快速下降 — NVCF 上游函数不稳定，部分请求在 44-46s 边缘被 UPSTREAM 截断
4. 36 single-tier ATE fallback_actually_attempted=f — 主要是 pre-R728 restart 窗口（FASTBREAK=1 时仅1次 timeout），R728 的 FASTBREAK=2 已改善
5. 65 double-tier ATE — NVCF 双函数同时不健康时，非配置可修复
6. FALLBACK_GRAPH 双向正常工作，fallback 59次成功 (avg 59s, max 99s)

### 决策: UPSTREAM_TIMEOUT 44→46 (+2s)

| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| UPSTREAM_TIMEOUT | 44 | 46 | +2s |

**理由:**
- dsv4p_nv 和 glm5_2_nv 的 NVCFPexecTimeout max 均在 UPSTREAM=44 绑定边缘
- +2s 捕获 44-46s 边缘窗口，允许边缘请求在直接路径完成，而非 fallback
- FASTBREAK=2 下: 46×2=92s < BUDGET=110s per tier → 安全
- 减少 fallback 到 glm5_2_nv 的频率（dsv4p_nv health 正下降，glm5_2 健康更重要）
- 成功 fallback max=99,088ms < BUDGET=110s → 零误杀

**安全边界:**
- Per-tier budget: 46+46=92s < 110s → 充足余量
- 若两层都失败: 92s + 92s = 184s 最大 ATE 延迟（从当前 177s 增加 7s）— 可接受
- 成功 fallback max=99,088ms < 110s → 现有成功路径不受影响
- FASTBREAK=2 不变: 2次 timeout 后 fast-break，不会浪费额外键

**为什么不继续改其他参数:**
- FASTBREAK=2 (R728) 刚部署，需观察效果
- FORCE_STREAM_UPGRADE_TIMEOUT=44 已与 UPSTREAM=44 对齐 (R727)，但 UPSTREAM 现在升到 46 → 下一轮可将 FORCE_STREAM 也升到 46 恢复对齐
- BUDGET=110 安全，无需调整
- FALLBACK_HEALTH_THRESHOLD=0.10 地板
- 所有其他参数已在地板 (KEY_COOLDOWN=25, TIER_COOLDOWN=25, NV_INTEGRATE_KEY_COOLDOWN=0, MIN_OUTBOUND=0, CONNECT_RESERVE=0, SSLEOF=1.0)

### 铁律确认
- [x] 改前有数据 — 6h DB 聚合 + tier_attempts + 日志 + 健康度 + 按模型 SR
- [x] 单参数每轮 — 仅改 UPSTREAM_TIMEOUT
- [x] 只改 HM1 不改 HM2

---

## 三、部署验证

### 部署前
```
UPSTREAM_TIMEOUT=44
FASTBREAK=2
FORCE_STREAM_UPGRADE_TIMEOUT=44
TIER_TIMEOUT_BUDGET_S=110
```

### 部署后
```
UPSTREAM_TIMEOUT=46  ✅
FASTBREAK=2
FORCE_STREAM_UPGRADE_TIMEOUT=44
TIER_TIMEOUT_BUDGET_S=110
```

### 验证
- `sed -i '483s/"44"/"46"/' docker-compose.yml` → 行483值已改
- `python3 -c 'import yaml; yaml.safe_load(...)'` → YAML OK ✓
- R729 注释插入行484
- `docker compose up -d nv_gw` → Recreated + Started
- `docker ps` → nv_gw Up (healthy) ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → UPSTREAM_TIMEOUT=46 ✓
- Clean startup logs, no errors ✓

---

## 四、参数状态 (post-R729)

| 参数 | 值 | 趋势 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 46 | 30→25→28→31→34→32→30→36→38→40→42→44→46 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 44 | 61→59→...→44 |
| TIER_TIMEOUT_BUDGET_S | 110 | - |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | - |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | 2→1→2 (R728) |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | - |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |

### ⚠️ 已知漂移 (下一轮可修复)
- FORCE_STREAM_UPGRADE_TIMEOUT=44 与 UPSTREAM=46 不对齐（R727 对齐于 UPSTREAM=44，本轮 UPSTREAM 升到 46）
- R728 的 FASTBREAK 注释在行592，行593 有旧的 R709 注释
- 下一轮 HM1 可通过零变更轮或单参数轮修复对齐

---

## 五、结论

R729: UPSTREAM_TIMEOUT 44→46 (+2s)。dsv4p_nv 和 glm5_2_nv 的 NVCFPexecTimeout max 均在 UPSTREAM=44 绑定边缘。+2s 捕获 44-46s 窗口，减少直接 fallback 频率。BUDGET=110>>46+46=92s per-tier 安全，FASTBREAK=2 不变。成功 fallback max=99,088ms < 110s 零误杀。NVCF 双函数上游不健康（dsv4p_nv health 0.5 下降中）是 ATE 根因，UPSTREAM 扩展仅缓解但不能消除。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2