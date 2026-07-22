# R2280: HM2→HM1 — NOP 巡检轮 80 — 介入四条全不满足 冻结

## TL;DR
R2279 (TIER_COOLDOWN_S 66→55) 部署后仅 50min 窗口，4 请求全 200 OK，零失败。所有关键参数已触底，zombie 仍为 NVCF 底层结构性衰减，无 config 可修故障。介入四条全不满足 → NOP 冻结。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2280 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R10→24 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 275 | R2277 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | floor |
| 5 | `TIER_COOLDOWN_S` | 55 | R2279 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R2220→122 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | near floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R2268 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | floor |
| 12 | `NV_INTEGRATE_ENABLED` | (unset) | disabled |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | disabled |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | floor |
| 15 | `KEY_COOLDOWN_S` | 66 | R2267 saezone boundary |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
TIER_COOLDOWN_S=55
KEY_COOLDOWN_S=66
TIER_TIMEOUT_BUDGET_S=275
UPSTREAM_TIMEOUT=24
```

### 2.2 源2 — 容器 env
```
TIER_COOLDOWN_S=55
KEY_COOLDOWN_S=66
NVU_TIER_BUDGET_DSV4P_NV=160
NVU_TIER_BUDGET_GLM5_2_NV=200
```

### 2.3 源3 — 容器启动时间
```
StartedAt: 2026-07-22T22:12:33.420971742Z
连续第45轮 RC=0 未重建（R2279 重启后 50min）
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 50
→ [NV-CYCLE] glm5_2_nv k5→429 (429_nv_rate_limit), cycling
→ [NV-CYCLE] glm5_2_nv k1→429 (429_nv_rate_limit), cycling
→ [NV-CYCLE] glm5_2_nv k2→429 (429_nv_rate_limit), cycling
→ [NV-KEY] glm5_2_nv k2 in cooldown, skipping
→ 0 ERROR, 0 WARN, 0 zombie, 0 ATE
```

**结论：四源全部通过，无漂移。容器 R2279 重启后稳定运行。**

---

## 三、数据摘要（部署前窗口）

### 3.1 6h 窗口（UTC 16:00-22:00, 2026-07-22）

| 指标 | 数值 |
|---|---|
| 总请求 | 46 |
| 成功 | 32 |
| 失败 | 14 |
| 成功率 | 69.6% |

#### 各模型 6h

| 模型 | 总数 | OK | 失败 | SR | avg_ok_ms |
|---|---|---|---|---|---|
| dsv4p_nv | 16 | 12 | 4 | 75.0% | 31164 |
| glm5_2_nv | 30 | 20 | 10 | 66.7% | 19416 |

#### 错误分布 6h

| 错误类型 | dsv4p_nv | glm5_2_nv | 说明 |
|---|---|---|---|
| ATE (all_tiers_exhausted) | 4 (502) | 7 (3 phantom-200, 3 429, 1 502) | dsv4p ATE 全在 R2279 重启前 |
| zombie_empty_completion | 0 | 6 | 30min cron pattern, NVCF 底层 |
| tier-level 429_nv_rate_limit | 0 | 24 | key cycling 健康 |

#### Key Cycle 6h

| 模型 | 1-cycle | 2-cycle | 3-cycle | 4-cycle |
|---|---|---|---|---|
| glm5_2_nv | 7 | 1 | 4 | 1 |
| dsv4p_nv | 2 | 0 | 0 | 0 |

### 3.2 Post-restart 窗口（R2279 重启后 ≈ 50min）

| 指标 | 数值 |
|---|---|
| 总请求 | 4 |
| 成功 | 4 |
| 失败 | 0 |
| 成功率 | 100% |
| avg_ok_ms | 10062 |

| 模型 | 总数 | OK | 失败 | SR | avg_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 4 | 4 | 0 | 100% | 10062 |
| dsv4p_nv | 0 | 0 | 0 | N/A | N/A |

#### Post-restart dsv4p_nv tier_attempts
```
ZERO — 零 dsv4p 流量，零 tier_attempts
```

### 3.3 HM2 对比（调用方视角）
HM2 脚本报告：30min 85req/92.9% SR，glm5_2_nv 60/62=96.8%，dsv4p_nv 19/23=82.6%（4 ATE NVCF 上游已知良性）。HM2 流量正常，HM1 不等于 HM2 本地。

---

## 四、介入四条判定

### 1. 有可修故障 ❌
- Post-restart: 0 failures, 100% SR
- 6h zombie (6 glm5_2): 30min cron pattern, NVCFPexecRemoteDisconnected, NVCF 底层结构性衰减，非 config 可修
- 6h glm5_2 ATE (7): 3 phantom-200 (peer-fb rescue), 3 429 (big-input breaker + rate limit), 1 502 — 混合原因，非单一 config 可修
- 6h dsv4p ATE (4): 全部在 R2279 重启前（18:00-18:25Z），R2279 已降低 TIER_COOLDOWN_S 66→55 应对，零 post-restart dsv4p 流量无法验证

### 2. 有真实 ATE ❌
- Post-restart: 0 ATE (real or phantom)
- Pre-restart ATE 已由 R2279 处理，等待新数据

### 3. 参数未到底 ❌
- KEY_COOLDOWN_S=66: 安全区边界（R2126 验证 66=0% 429, 64=58% 429），不可降
- TIER_COOLDOWN_S=55: 刚由 R2279 降低，等待验证
- MIN_OUTBOUND_INTERVAL_S=0: floor
- NVU_CONNECT_RESERVE_S=0: floor
- NVU_PEXEC_TIMEOUT_FASTBREAK=1: floor
- NVU_EMPTY_200_FASTBREAK=2: floor
- UPSTREAM_TIMEOUT=24: floor
- NVU_SSLEOF_RETRY_DELAY_S=0.1: near floor
- KEY_AUTHFAIL_COOLDOWN_S=0: floor
- NV_INTEGRATE_KEY_COOLDOWN_S=0: floor

### 4. 有可优化参数 ❌
- 所有参数已触底，无调整空间
- glm5_2 key cycling (13 events in 6h) 是正常行为，KEY_COOLDOWN_S=66 不可降
- Zombie 为 NVCF 底层问题，非 config 旋钮可治
- Post-restart 数据极少（4 请求），无优化依据

---

## 五、结论：NOP

介入四条全不满足 → NOP 无据不改。

R2279 (TIER_COOLDOWN_S 66→55) 部署仅 50min，4 请求全成功，零失败。所有关键参数已触底，zombie 为 NVCF 底层结构性衰减（BUG-A cc2 SDK ~131s 客户端首字节墙），非 config 可修。Key cycling 正常（KEY_COOLDOWN_S=66 安全区边界），TIER_COOLDOWN_S=55 刚降低需更多数据验证。

**零改动，零重启。连续第 80 轮 NOP（hm2_optimize_hm1 独立 NOP 计数）。**

单参数少改多轮。铁律：只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2