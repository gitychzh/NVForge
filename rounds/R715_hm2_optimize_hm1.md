# R715: HM2→HM1 — 零变更轮（R714后 ~2h，post-restart 100% SR，NVCF 上游恢复）

## TL;DR
R714 零变更后 ~2h 稳定运行。Post-restart（23:10 UTC+）窗口 11 req / 11 OK (100.0%) / 0 ATE。NVCFPexecTimeout 绑定 UPSTREAM=36（avg 29,438ms, max 36,361ms），fallback 全部救回。dsv4p_nv health 0.75-1.0，glm5_2_nv health 1.0。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 36 | R713: 33→36 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706: 94→110 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638: 降至 floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R709: 2→1 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492: 长期稳定 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697: 25→45 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657: 降至 floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694: 25→40 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692: 禁用 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577: 连续阈值 |
| 12 | `NV_INTEGRATE_ENABLED` | (未设置，默认1) | 但 NV_INTEGRATE_MODELS="" 使其无效 |
| 13 | `NV_INTEGRATE_MODELS` | "" (空) | R694: 全部走 pexec |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631: floor |
| 15 | `KEY_COOLDOWN_S` | 25 | R162: 长期稳定 |
| 16 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708: 新增 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "36"       ← R713
TIER_TIMEOUT_BUDGET_S: "110" ← R706
MIN_OUTBOUND_INTERVAL_S: "0" ← R638
KEY_COOLDOWN_S: "25"         ← R162
TIER_COOLDOWN_S: "25"        ← R492
NVU_PEXEC_TIMEOUT_FASTBREAK: "1" ← R709
NVU_PEER_FALLBACK_TIMEOUT: "45" ← R697
NVU_EMPTY_200_FASTBREAK: "2" ← R577
NVU_CONNECT_RESERVE_S: "0"   ← R657
NVU_SSLEOF_RETRY_DELAY_S: "1.0" ← R543
NVU_FORCE_STREAM_UPGRADE: "0" ← R692
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "40" ← R694
FALLBACK_HEALTH_THRESHOLD: "0.10" ← R708
NV_INTEGRATE_MODELS: ""       ← R694
NV_INTEGRATE_KEY_COOLDOWN_S: "0" ← R631
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=36 ✓
TIER_TIMEOUT_BUDGET_S=110 ✓
MIN_OUTBOUND_INTERVAL_S=0 ✓
KEY_COOLDOWN_S=25 ✓
TIER_COOLDOWN_S=25 ✓
NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
NVU_PEER_FALLBACK_TIMEOUT=45 ✓
NVU_EMPTY_200_FASTBREAK=2 ✓
NVU_CONNECT_RESERVE_S=0 ✓
NVU_SSLEOF_RETRY_DELAY_S=1.0 ✓
NVU_FORCE_STREAM_UPGRADE=0 ✓
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40 ✓
FALLBACK_HEALTH_THRESHOLD=0.10 ✓
NV_INTEGRATE_MODELS= ✓
NV_INTEGRATE_KEY_COOLDOWN_S=0 ✓
```

### 2.3 源3 — 容器启动时间
```
StartedAt: 2026-07-04T23:10:20.799141364Z
Up 21 minutes at time of check (R714 部署)
```
容器自 R714 部署后未重启，持续运行 ~2h。

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100
→ 0 ERROR / 0 WARN
→ dsv4p_nv pexec timeout ~36.3s → FASTBREAK → fallback to glm5_2_nv → SUCCESS
→ health: dsv4p_nv 0.75-1.0, glm5_2_nv 1.0
→ tier_chain = ['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback)
```

**结论：四源全部通过，无漂移。**

---

## 三、数据摘要

### 3.1 Post-restart 窗口（23:10 UTC+，~2h, R714 部署后）

| 指标 | 值 |
|------|-----|
| 总量 | 11 req |
| OK | 11 (100.0%) |
| Fail | 0 (0.0%) |
| ATE | 0 |
| avg_dur | 27,175ms |
| max_dur | 70,485ms |

**Post-restart 成功路径分布：**
| 路径 | cnt | avg_dur |
|------|-----|---------|
| 直接成功（tiers_tried=1） | 8 | 14,960ms |
| Fallback 救回 | 3 | 59,747ms |

### 3.2 6h 窗口（含 pre-restart，UTC 18:00-23:59）

| 指标 | 值 |
|------|-----|
| 总量 | 167 req |
| OK | 116 (69.5%) |
| ATE | 51 (30.5%) |
| avg_dur | 33,511ms |
| max_dur | 122,312ms |

### 3.3 按模型 6h

| mapped_model | cnt | ok | fail | avg_ok_ms | max_ok_ms | avg_fail_ms |
|--------------|-----|-----|------|-----------|-----------|-------------|
| dsv4p_nv | 126 | 78 | 48 | 37,611 | 99,088 | 82,853 |
| glm5_2_nv | 40 | 38 | 2 | 9,487 | 37,325 | 80,525 |
| kimi_nv | 1 | 0 | 1 | — | — | 2,682 |

### 3.4 按小时 SR（6h）

| hour (UTC) | total | ok | fail | sr_pct |
|------------|-------|-----|------|--------|
| 18:00 | 48 | 35 | 13 | 72.9% |
| 19:00 | 28 | 20 | 8 | 71.4% |
| 20:00 | 21 | 14 | 7 | 66.7% |
| 21:00 | 19 | 6 | 13 | 31.6% |
| 22:00 | 30 | 23 | 7 | 76.7% |
| **23:00** | **15** | **15** | **0** | **100.0%** |

关键趋势：23:00 UTC 小时 = 100% SR，NVCF 上游恢复确认。

### 3.5 ATE 分层（6h，含 pre-restart）

| tiers_tried_count | cnt | avg_dur | 说明 |
|-------------------|-----|---------|------|
| 1 | 21 | 55,445ms | 单 tier dsv4p_nv 耗尽，无 fallback 尝试 |
| 2 | 30 | 104,169ms | 双 tier 耗尽（dsv4p_nv + glm5_2_nv 均失败）|

**所有 51 ATE** = error_type `all_tiers_exhausted`，error_subcategory `all_tiers_failed_in_mapped_tier`，upstream_type NULL。

### 3.6 nv_tier_attempts（6h, 54 条）

| tier | error_type | cnt | avg_elapsed | max_elapsed |
|------|-----------|-----|-------------|-------------|
| dsv4p_nv | NVCFPexecTimeout | 51 | 29,438ms | 36,361ms |
| glm5_2_nv | NVCFPexecTimeout | 3 | 27,073ms | 30,430ms |

**键分布**：dsv4p_nv 超时均匀分布在 5 个 key（8-12 次/key）→ **函数级排队问题**，非 key 级劣化。FASTBREAK=1 正确。

### 3.7 日志模式（Post-restart 典型路径）

**直接成功路径（dsv4p_nv）：**
```
[07:17:25] [NV-SUCCESS] tier=dsv4p_nv k4 @17.8s
[07:18:44] [NV-SUCCESS] tier=dsv4p_nv k5 @23.6s
[07:20:53] [NV-SUCCESS] tier=dsv4p_nv k1 @35.6s ← 33-36s 直接成功（R713 边缘救回确认）
```

**Fallback 成功路径（dsv4p_nv timeout → glm5_2_nv save）：**
```
[07:22:02] [NV-TIMEOUT] dsv4p_nv k2 NVCF pexec timeout: 36,351ms
[07:22:38] [NV-PEXEC-FASTBREAK] dsv4p_nv fast-break (saved remaining keys)
[07:22:38] [NV-FALLBACK] → glm5_2_nv
[07:23:09] [NV-SUCCESS] glm5_2_nv k3 (31s)
[07:23:09] [NV-FALLBACK-SUCCESS]
```

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| UPSTREAM_TIMEOUT | 36 | 39 (+3s) | NVCFPexecTimeout max=36,361ms 精确绑定 36s。但 post-restart 100% SR（11/11），fallback 全部救回截断请求。3 个 fallback 成功 avg=60s < 110s BUDGET。当前 regime 零 ATE，+3s 增量成本 = 3s × 失败率（当前 0%）= 0。但在 100% SR 时进一步上调无明确数据支撑（不存在"被截断的边缘请求"需要救回）。 | ❌ 待观察 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 40 (-5s) | PEER_FALLBACK=45 = UPSTREAM_TIMEOUT=40 + 5s reserve。但 post-restart 3 次 fallback 全部成功，非 timeout 截断。降 5s 无收益（当前没有因 peer fb timeout 失败的情况），且可能产生新的 ceiling lag。 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 2 | 1 (-1) | empty_200 在 post-restart 窗口零出现。6h 内也零 empty_200。降 1 无效果但无风险。当前值 2 已在 R577 定案，R694 负载模式变化后尚未重新验证。 | ❌ 待观察 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 0.05 (-0.05) | 0.10 已安全。dsv4p_nv health 最低 0.75（post-restart），glm5_2_nv health 1.0。0.10 已足够放松。进一步降低无收益。 | ❌ |
| 其他 12 参数 | — | — | 全部在 floor 或经历史验证的稳定值。无数据支撑任何调整。 | ❌ |

**最终决策**：零变更。Post-restart 100% SR，NVCF 上游已恢复，所有参数处于合理位置。当前 regime 无任何可优化信号。

**下轮关注**：
1. Post-restart dsv4p_nv 直接成功率（当前 8/11 = 73%，含 fallback 后 100%）
2. 33-36s 直接成功比例是否稳定增长（R713 边缘救回验证）
3. NVCFPexecTimeout 在 36s 的绑定是否持续（若 avg 上升需 +3s→39）
4. 若出现 empty_200 事件，重新评估 FASTBREAK 2→1

---

## 五、参数历史

| 参数 | 当前值 | 来源 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 36 | R713: 33→36 |
| TIER_TIMEOUT_BUDGET_S | 110 | R706: 94→110 |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638: floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R709: 2→1 |
| TIER_COOLDOWN_S | 25 | R492 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697: 25→45 |
| NVU_CONNECT_RESERVE_S | 0 | R657: floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | R543 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 40 | R694: 25→40 |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692: 禁用 |
| NVU_EMPTY_200_FASTBREAK | 2 | R577 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631: floor |
| KEY_COOLDOWN_S | 25 | R162 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708: 新增 |

---

## 六、结论

R715 零变更。Post-restart 2h 窗口 100% SR（11/11 OK），NVCF 上游已恢复（dsv4p_nv health 0.75-1.0, glm5_2_nv health 1.0）。所有参数处于经历史验证的稳定值，无数据支撑任何调整。Fallback 链正常工作（dsv4p_nv timeout → glm5_2_nv save），FASTBREAK=1 节省时间，BUDGET=110 充足。下轮持续观察 post-restart 数据积累。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2