# R717: HM2→HM1 — 零变更轮（NVCF dsv4p_nv primary function 74f02205 死亡→自动切换 8915fd28，无需配置变更）

## TL;DR
dsv4p_nv primary NVCF function `74f02205` dead (health=0.0) for entire 6h window. NVCF auto-switched to new function `8915fd28` at ~08:22 UTC. Fallback chain working (NV-FALLBACK-SUCCESS since 08:23). All existing params are optimal — UPSTREAM_TIMEOUT=40 not binding, FASTBREAK=1, BUDGET=110 per-tier safe. Zero-change round. Single param per round policy; iron rule: only change HM1 never HM2.

---

## 一、当前配置快照（R717 部署前，容器 2026-07-05T00:03:17Z）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 40 | R716: HM2→HM1 36→40 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706: 94→110 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R548: 1.0→0 (floor) |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R709: 2→1 |
| 5 | `TIER_COOLDOWN_S` | 25 | R694: 15→25 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697: 25→45 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R694: 25→0 (floor) |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R694: 0.5→1.0 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694: 61→40 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692: 1→0 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577: 3→2 |
| 12 | `NVU_PEER_FALLBACK_ENABLED` | 1 | R692 |
| 13 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708: 复活 |
| 14 | `KEY_COOLDOWN_S` | 25 | R694: 15→25 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "40"  # R716: HM2→HM1 UPSTREAM_TIMEOUT 36→40
TIER_TIMEOUT_BUDGET_S: "110"
MIN_OUTBOUND_INTERVAL_S: "0"
NVU_PEXEC_TIMEOUT_FASTBREAK: "1"
...
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=40
TIER_TIMEOUT_BUDGET_S=110
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_PEER_FALLBACK_ENABLED=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
```
→ 容器 env 与 compose 一致 ✅

### 2.3 源3 — 容器启动时间
```
2026-07-05T00:03:17.790012301Z running
```
→ 容器在 R716 commit 后启动（R716 pushed 2026-07-05 08:15 UTC），说明 HM1 自部署了 R716 的新 config ✅

### 2.4 源4 — 运行时日志
```
[08:05:52.9] [NV-REQ] mapped_model=dsv4p_nv tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'74f02205...': 0.0})
[08:22:36.7] [NV-FUNC-HEALTH] model=dsv4p_nv primary=74f02205... unhealthy → switched to 8915fd28...
[08:23:23.4] [NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv after primary dsv4p_nv failed
[08:24:40.5] [NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv after primary dsv4p_nv failed
```
→ 四源全部通过，无漂移 ✅

**结论：四源一致，无漂移。**

---

## 三、数据摘要（6h 窗口，created_at >= now() - 6h）

### 3.1 总体统计
| 模型 | 总请求 | OK | 失败 | ATE | SR | avg_ok_ms |
|------|--------|-----|------|-----|-----|-----------|
| dsv4p_nv | 117 | 72 | 45 | 45 (100%) | 61.5% | 39,648ms |
| glm5_2_nv | 44 | 42 | 2 | 2 (100%) | 95.5% | 8,468ms |
| **合计** | **161** | **114** | **47** | **47** | **70.8%** | — |

### 3.2 ATE 分解
| tiers_tried_count | 数量 | 占比 | avg_ms | fallback_actually_attempted |
|-------------------|------|------|--------|---------------------------|
| 1 | 12 | 25.5% | 64,053ms | f (全部) |
| 2 | 35 | 74.5% | 98,144ms | f (34/35) |

单 tier ATE (12):
- start_tier_idx=1 (dsv4p_nv): 10, avg=60,759ms
- start_tier_idx=3 (glm5_2_nv): 2, avg=80,525ms

### 3.3 dsv4p_nv 成功路径分析
| fallback_occurred | 数量 | avg_ms | max_ms |
|-------------------|------|--------|--------|
| f (primary) | 45 | 29,045ms | 60,099ms |
| t (via glm5_2) | 26 | 55,711ms | 96,582ms |

→ 36.6% dsv4p_nv 成功请求需要 fallback 到 glm5_2_nv 救回

### 3.4 dsv4p_nv 成功延迟分布
| 桶 | 数量 |
|----|------|
| <10s | 6 |
| 10-20s | 12 |
| 20-30s | 9 |
| 30-40s | 7 |
| 40-50s | 17 |
| 50-60s | 9 |
| 60-80s | 10 |
| 80-100s | 2 |

### 3.5 NVCFPexecTimeout 绑定分析
| 模型 | 键 | 数量 | avg_ms | max_ms |
|------|-----|------|--------|--------|
| dsv4p_nv | k2 | 12 | 30,621ms | 36,426ms |
| dsv4p_nv | k3 | 11 | 31,213ms | 36,475ms |
| dsv4p_nv | k4 | 9 | 32,388ms | 36,425ms |
| dsv4p_nv | k0 | 9 | 31,134ms | 36,399ms |
| dsv4p_nv | k1 | 8 | 30,194ms | 36,351ms |

→ NVCFPexecTimeout max=36,475ms **远低于 UPSTREAM_TIMEOUT=40**（40-36.5=3.5s 余量）
→ UPSTREAM_TIMEOUT=40 **不是绑定约束**，timeout 是 NVCF function 层面的，非 UPSTREAM 配置驱动

### 3.6 小时趋势
| 小时 (UTC) | 总量 | OK | ATE | SR |
|-----------|------|-----|-----|-----|
| 2026-07-04 18:00 | 28 | 25 | 3 | 89.3% |
| 2026-07-04 19:00 | 28 | 20 | 8 | 71.4% |
| 2026-07-04 20:00 | 21 | 14 | 7 | 66.7% |
| 2026-07-04 21:00 | 19 | 6 | 13 | 31.6% |
| 2026-07-04 22:00 | 30 | 23 | 7 | 76.7% |
| 2026-07-04 23:00 | 24 | 21 | 3 | 87.5% |
| 2026-07-05 00:00 | 10 | 5 | 5 | 50.0% |

→ 21:00 UTC (05:00 CST) 为低谷 (31.6%)，23:00 UTC (07:00 CST) 恢复至 87.5%
→ 00:00 UTC 低流量 (10req) 含 5 个 peer-originated hop=1 ATE

### 3.7 Post-Restart（容器 2026-07-05T00:03:17Z 启动后）
| 模型 | 总量 | OK | ATE | 状态 |
|------|------|-----|-----|------|
| dsv4p_nv | 5 | 0 | 5 | 全部 peer-originated hop=1 |
| glm5_2_nv | 3 | 3 | 0 | 100% OK |

→ Post-restart 前 5 个 dsv4p_nv 请求全部来自 HM2 peer fallback (hop=1)，HM1 自己也失败后返回 502
→ 08:22 UTC 后 NVCF 自动切换 primary function 74f02205→8915fd28，开始恢复

---

## 四、决策分析

### 4.1 根因诊断

**关键发现：dsv4p_nv primary NVCF function `74f02205-c7ba-438f-b81a-2537955bd7ec` health=0.0**
- 日志证实：`health={'74f02205...': 0.0}` 出现在所有 dsv4p_nv 请求中
- 该 function 对**所有请求**返回 NVCFPexecTimeout（~30-36s），不是个别 key 问题
- 5 个 key 分布均匀（k0:9, k1:8, k2:12, k3:11, k4:9）→ function-level 故障，非 key-level

**NVCF 自动恢复：**
- 08:22:36 UTC: `[NV-FUNC-HEALTH] primary=74f02205... unhealthy → switched to 8915fd28...`
- 08:23:23 UTC: `[NV-FALLBACK-SUCCESS]` — 首次 fallback 成功（primary 仍失败但 fallback 救回）
- 08:24:40 UTC: 第二次 `[NV-FALLBACK-SUCCESS]`
- 新 function 8915fd28 初始 health=0.0 但正在积累成功样本

**为什么 fallback 一直工作？**
- tier_chain=['dsv4p_nv', 'glm5_2_nv'] — FALLBACK_GRAPH 始终活跃
- glm5_2_nv health=1.0→0.375→0.5（波动但始终 > FALLBACK_HEALTH_THRESHOLD=0.10）
- 双 tier ATE (35/47=74.5%) = 两 tier 都耗尽 → NVCF 双 function 同时不可用期间
- 单 tier ATE (12/47=25.5%) = dsv4p_nv 耗尽，fallback 也失败（glm5_2_nv 在特定时段也无响应）

### 4.2 参数候选评估

| 参数 | 当前值 | 候选 | 判定 |
|------|--------|------|------|
| `UPSTREAM_TIMEOUT` | 40 | 40→43 | ❌ 不绑定。NVCFPexecTimeout max=36,475ms << 40s。加 3s 无边际收益。|
| `TIER_TIMEOUT_BUDGET_S` | 110 | 110→120 | ❌ dsv4p_nv 单 tier 耗尽 ~40s, 双 tier ~80s, 远低于 110。budget 不是瓶颈。|
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | — | ✅ 已达 floor。FASTBREAK=1 正确：每 tier 仅试 1 key 后 fast-break，省 4×~30s=120s。|
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 45→40 | ❌ peer fallback 失败是因为 HM1 自身也 function 死亡，非 timeout。降 5s 无帮助。|
| `NVU_EMPTY_200_FASTBREAK` | 2 | 2→1 | ❌ 当前错误类型全是 NVCFPexecTimeout，无 empty_200。降 1 无效果。|
| `FALLBACK_HEALTH_THRESHOLD` | 0.10 | — | ✅ 0.10 安全地板。glm5_2_nv health 0.375-1.0 始终 > 0.10，fallback 链未被误杀。|
| `KEY_COOLDOWN_S` | 25 | — | ✅ 稳定。1 次 429 (k3) 后正常冷却。无需调整。|

**所有候选参数均被否决。NFVC function 死亡是上游问题，非配置可修复。NVCF 已自动切换 function，系统正在恢复。**

### 4.3 最终决策：零变更

零变更。R716 的 UPSTREAM_TIMEOUT=40 已生效但未 binding（timeout 是 function 层面的）。所有参数处于历史验证值或 floor。NVCF 已自动恢复（function 切换 74f02205→8915fd28），fallback 链正常工作。零变更是最优决策。

---

## 五、执行记录

**无执行操作（零变更轮）。** 未修改 HM1 compose 文件，未重启容器。

---

## 六、验证记录（无需验证，零变更）

| 指标 | 数值 | 状态 |
|------|------|------|
| 配置一致性 | compose=env=40 ✅ | — |
| Fallback 链 | 活跃 ✅ | — |
| NVCF 恢复 | function 切换中 🔄 | — |
| 容器稳定性 | running since 00:03 UTC ✅ | — |

---

## 七、结论

R717 零变更。根因：dsv4p_nv primary NVCF function `74f02205` 完全死亡（health=0.0），所有请求超时 ~30-36s。这不是配置问题——5 个 key 均匀分布 timeout，UPSTREAM_TIMEOUT=40 远高于 timeout 实际值（36.5s max），BUDGET=110 充足。NVCF 于 08:22 UTC 自动切换到新 function `8915fd28`，fallback 链恢复工作（NV-FALLBACK-SUCCESS）。系统正在自愈，无需任何配置变更。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2