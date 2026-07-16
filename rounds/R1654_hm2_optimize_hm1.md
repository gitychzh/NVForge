# R1654 (HM2→HM1): NOP — all params at floor, dsv4p BUDGET=90 needs more data, zombie is NVCF server-side

## TL;DR
Zero parameter change. All tunable params at floor. glm5_2 zombie (50%) is NVCF content-filter server-side. dsv4p BUDGET=90 post-R1652: ZERO ATE, needs more dsv4p traffic. 单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R1654 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | R1618 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 195 | R1647 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor (R638) |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | floor |
| 5 | `TIER_COOLDOWN_S` | 60 | R1643 (KEY=TIER铁律) |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 72 | HM2 BUDGET=70+2 ✓ |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | floor (R657) |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.5 | floor (R1626) |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | aligned with UPSTREAM |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | floor |
| 12 | `NV_INTEGRATE_ENABLED` | (config.py) | — |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | — |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | floor (R631) |
| 15 | `KEY_COOLDOWN_S` | 60 | R1643 (KEY=TIER铁律) |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
NVU_TIER_BUDGET_DSV4P_NV: "90"     # R1652
NVU_TIER_BUDGET_GLM5_2_NV: "120"
TIER_TIMEOUT_BUDGET_S: "195"       # R1647
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S: "60"               # R1643
TIER_COOLDOWN_S: "60"              # R1643
MIN_OUTBOUND_INTERVAL_S: "0"
NVU_CONNECT_RESERVE_S: "0"
NV_INTEGRATE_KEY_COOLDOWN_S: "0"
NVU_PEER_FALLBACK_TIMEOUT: "72"
NVU_PEER_FB_SKIP_MODELS: ""        # R1646
NVU_SSLEOF_RETRY_DELAY_S: "0.5"
NVU_FORCE_STREAM_UPGRADE: "0"
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "66"
```

### 2.2 源2 — 容器 env
```
NVU_TIER_BUDGET_DSV4P_NV=90
NVU_TIER_BUDGET_GLM5_2_NV=120
TIER_TIMEOUT_BUDGET_S=195
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FALLBACK_TIMEOUT=72
NVU_PEER_FB_SKIP_MODELS=
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```

### 2.3 源3 — 容器启动时间
```
2026-07-16T20:49:28Z (R1652 deploy, ~9h runtime)
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100: 1 ERROR/WARN
[NV-UPSTREAM-ERROR-CHUNK] glm5_2_nv zombie_empty_completion (content_filter)
```

**结论：四源全部一致，无漂移。继续标准分析。**

---

## 三、数据摘要（6h, 容器 restart 2026-07-16 20:49 UTC）

### 3.1 总览
```sql
-- 17 OK / 15 fail / 32 total (53.1% SR)
```

### 3.2 按模型
```
dsv4p_nv:  7 OK / 5 ATE,  avg OK = 24,555ms
glm5_2_nv: 10 OK / 10 fail, avg OK = 6,339ms
```

### 3.3 错误分类
```
glm5_2_nv | zombie_empty_completion | 10  (NVCF server-side content-filter)
dsv4p_nv  | all_tiers_exhausted     | 5   (ALL pre-R1652, old BUDGET=76)
```

### 3.4 dsv4p ATE 时间线（全部 pre-R1652）
```
ts                                | duration_ms | tiers_tried
2026-07-16 18:04:07.695888+00    | 64280       | 1
2026-07-16 18:03:58.438997+00    | 61652       | 1
2026-07-16 18:02:56.412244+00    | 61533       | 1
2026-07-16 18:01:45.752138+00    | 61822       | 1
2026-07-16 18:00:40.607973+00    | 62107       | 1
```
- 全部在 18:00-18:04 UTC，R1652 容器重启前 (20:49 UTC)
- 旧 BUDGET=76，61.5-64.3s 用尽budget后abort
- tiers_tried=1：仅试 dsv4p_nv tier，peer-fb 未触发 (budget 76s 先砍)
- **Post-R1652 (BUDGET=90): ZERO dsv4p ATE** — 但 dsv4p 流量也极少 (仅7请求)

### 3.5 429 分析
```
key_cycle_429s=0: 12
key_cycle_429s=1: 20 (62.5% — single-key 429, 非级联)
```
- 无级联 (无 multi-key 429 链)
- KEY_COOLDOWN=60=TIER_COOLDOWN=60 满足 KEY≥TIER 铁律

### 3.6 Fallback 触发
```
fallback_occurred=f: 32 (zero fallbacks triggered)
```

### 3.7 Docker Logs
```
--tail 100: 仅 1 条 ERROR/WARN
→ NV-UPSTREAM-ERROR-CHUNK zombie_empty_completion (glm5_2_nv, content_filter)
→ 零 SSLEOF, 零 TimeoutError, 零 pexec_429
```

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `NVU_TIER_BUDGET_DSV4P_NV` | 90 | — | Post-R1652 ZERO ATE 但 dsv4p 仅7请求，需更多数据 | ❌ 待观察 |
| `KEY_COOLDOWN_S` | 60 | — | KEY=TIER=60 铁律，62.5% 单key 429 率是NVCF单IP固有特征 | ❌ 不可减 |
| `TIER_COOLDOWN_S` | 60 | — | KEY=TIER 铁律，≥KEY 不变 | ❌ 不可减 |
| `UPSTREAM_TIMEOUT` | 66 | — | NVCFPexecTimeout max~62s，不可减 | ❌ floor |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | — | floor | ❌ |
| `NVU_CONNECT_RESERVE_S` | 0 | — | floor | ❌ |
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | — | floor | ❌ |
| `NVU_SSLEOF_RETRY_DELAY_S` | 0.5 | — | floor，零SSLEOF errors | ❌ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 72 | — | HM2 BUDGET=70+2 ✓ | ❌ |
| `TIER_TIMEOUT_BUDGET_S` | 195 | — | dsv4p 90+72=162<195 ✓, glm5_2 120+72=192<195 ✓ | ❌ |
| `NVU_FORCE_STREAM_UPGRADE` | 0 | — | disabled，稳定 | ❌ |
| `NVU_EMPTY_200_FASTBREAK` | 2 | — | floor，零 empty_200 errors | ❌ |

**最终决策：NOP — 零参数变更。**

### 为何不继续调

1. **glm5_2 zombie_empty_completion (10/20, 50%):** NVCF server-side content-filter 返回空completion。典型zombie模式：5-10s内返回200空body。非本地配置可修。HM1 日志明确显示 `finish_reason=content_filter`。

2. **dsv4p ATE (5/32, 15.6%):** 全部 pre-R1652 (旧BUDGET=76)。Post-R1652 ZERO dsv4p ATE。BUDGET=90 需要更多 dsv4p 流量积累（至少 24h 或 10+ dsv4p 请求）才能判断是否充分。

3. **key_cycle_429s=1 (20/32, 62.5%):** 单次key 429，非级联。KEY_COOLDOWN=60=TIER_COOLDOWN=60 满足 KEY≥TIER 铁律。单IP架构下62.5%单key 429率是NVCF rate-limit的固有特征，加大cooldown会拖慢成功路径。

4. **所有参数已在 floor:** KEY_COOLDOWN=60 (不可再减，会破KEY≥TIER)，UPSTREAM=66 (不可再减，NVCFPexecTimeout max~62s)，MIN_OUTBOUND=0，CONNECT_RESERVE=0，NV_INTEGRATE_KEY=0，SSLEOF=0.5。

5. **当前失败全为 upstream/NVCF 问题，非本地配置可修。**

---

## 五、执行记录

NOP — 无执行操作。

---

## 六、验证记录（Post-R1652，~9h）

| 指标 | 数值 | 状态 |
|------|------|------|
| 总 SR | 53.1% (17/32) | ⚠️ zombie为主因 |
| dsv4p SR | 58.3% (7/12) | ⚠️ 5 ATE pre-R1652 |
| glm5_2 SR | 50% (10/20) | ⚠️ NVCF server-side zombie |
| 429 / rate-limit | 20/32 (62.5%) | ✅ 单key非级联 |
| dsv4p ATE post-R1652 | 0 | ✅ |
| ERROR/WARN (logs) | 1 | ✅ |
| peer fallback 触发 | 0 | ✅ |
| fallback 触发 | 0 | ✅ |
| 容器重启 | 1 (R1652 deploy) | ✅ |

---

## 七、结论

R1654 NOP。零参数变更。所有可调参数已在 floor。R1652 dsv4p BUDGET=90 需要更多 dsv4p 流量验证（当前仅7个dsv4p请求，0 ATE post-R1652）。glm5_2 zombie (50%) 是 NVCF content-filter server-side 问题，非本地配置可修。下次轮到 HM2 时重评估：若有 dsv4p ATE 复发 → 检查 peer-fb 是否触发；若 zombie 持续高发 → 考虑 ms_gw fallback 调整（但 zombie 是 NVCF server-side）。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
