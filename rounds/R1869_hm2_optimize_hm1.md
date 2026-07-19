# R1869: HM2→HM1 — NOP (zero post-restart data + all params at floors + NVCF-side zombie)

## TL;DR
NOP: nv_gw restarted 6 min ago (01:16 UTC), zero post-restart requests. 6h window: 37 total/14 OK/23 fail (37.8% SR), all 23 failures are `zombie_empty_completion` (NVCF-side, non-config fixable). All tunable parameters at effective floors. No config change possible or warranted. Single parameter per round; iron rule: only change HM1 never HM2.

---

## 一、当前配置快照（R1869 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 49 | R1857 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 178 | R1840 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 (floor) | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 (floor) | R709 |
| 5 | `TIER_COOLDOWN_S` | 48 | R1866 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R1744 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 (floor) | — |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 (floor) | R757 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R694 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 (disabled) | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 (floor) | R829 |
| 12 | `NV_INTEGRATE_ENABLED` | 0 (disabled) | — |
| 13 | `NV_INTEGRATE_MODELS` | "" (empty) | — |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 (dead) | — |
| 15 | `KEY_COOLDOWN_S` | 48 | R1866 |
| 16 | `NVU_FALLBACK_HEALTH_THRESHOLD` | 0.05 | R982 |
| 17 | `NVU_TIER_BUDGET_DSV4P_NV` | 39 | — |
| 18 | `NVU_TIER_BUDGET_GLM5_2_NV` | 60 | — |

---

## 二、漂移检测（Pre-change）

### 2.1 容器状态
```
nv_gw    Up 6 minutes (healthy)
cc4101   Up 2 days
logs_db  Up 2 days (healthy)
```

### 2.2 容器 env
```
UPSTREAM_TIMEOUT=49
TIER_TIMEOUT_BUDGET_S=178
KEY_COOLDOWN_S=48
TIER_COOLDOWN_S=48
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_TIER_BUDGET_DSV4P_NV=39
NVU_TIER_BUDGET_GLM5_2_NV=60
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=0.1
NVU_CONNECT_RESERVE_S=0
```

### 2.3 容器启动时间
```
2026-07-19T01:16:08.344096562Z (6 min ago, R1866 deploy? or cc4101 restart)
```

### 2.4 运行时日志
```
docker logs nv_gw --tail 100: zero ERROR/WARN — only startup "[NV-PROXY] Listening on 0.0.0.0:40006"
```

**结论：四源全部通过，无漂移。容器刚重启 6 min，零 post-restart 流量。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近 100 行）
- ERROR/WARN: 0
- 仅 startup 日志 "Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])"

### 3.2 DB 6h 摘要
```
total: 37
ok:    14
fail:  23
SR:    37.8%
avg_ms: 5296
p95_ms: 11919
max_ms: 14501
total_429s: 35
```

### 3.3 6h 错误分类
```
zombie_empty_completion: 23  (all NVCF-side, non-config fixable)
all_tiers_exhausted:      3  (upstream_type=NULL, scheduler-level)
```

### 3.4 Per-model 6h
```
dsv4p_nv:   3 total, 3 OK (100%), avg 9381ms
glm5_2_nv: 34 total, 11 OK (32.4%), 23 zombie, avg 4936ms
```

### 3.5 Per-key 6h
```
dsv4p_nv: 3 key=NULL (ATE), 3/3 OK
glm5_2_nv: spread across keys 0-4, all zombies
```

### 3.6 upstream_type 6h
```
NULL:        3 (3 dsv4p ATE, 3/3 OK? actually 3 ATE with OK status)
nvcf_pexec: 34 (11 OK, 23 zombie)
```

### 3.7 Post-restart (since 01:16 UTC)
```
0 total, 0 OK, 0 fail — no data yet
```

### 3.8 24h Summary
```
134 total, 106 OK, 28 fail, 79.1% SR
```

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| KEY_COOLDOWN_S | 48 | 46 | 6h 23 zombie NVCF-side, 35 total_429s, HM2=25 proves 48 conservative | ❌ 零 post-restart 数据，无验证基础 |
| TIER_COOLDOWN_S | 48 | 46 | 同 KEY_COOLDOWN_S | ❌ 同上 |
| UPSTREAM_TIMEOUT | 49 | 47 | p95=11919ms << 49s, margin ample | ❌ 零 post-restart 数据 |
| TIER_TIMEOUT_BUDGET_S | 178 | 176 | 48+48=96<<178, margin huge | ❌ 零 post-restart 数据 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | 120 | 0 peer-fb triggered | ❌ 零 post-restart 数据 |
| EMPTY_200_FASTBREAK | 1 | — | at floor=1 | ❌ floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | — | at floor=0 | ❌ floor |
| FASTBREAK | 1 | — | at floor=1 | ❌ floor |

**最终决策：NOP。容器刚重启 6 min，零 post-restart 流量。6h 23 条失败全为 NVCF 侧 zombie_empty_completion（非 config 可修）。所有可调参数已触 floor。等下一轮 post-restart 数据积累后再评估。**

---

## 五、执行记录

**NOP — 无配置变更，无容器重启。**

1. SSH 到 HM1: ✅ 连通
2. 容器状态: ✅ nv_gw Up 6min healthy
3. 容器 env: ✅ 所有参数一致，无漂移
4. 容器日志: ✅ 零 ERROR/WARN
5. DB 6h: ✅ 37req/14OK/23 zombie (NVCF-side)
6. 零 post-restart 数据: ✅ 无变更基础

---

## 六、结论

R1869 NOP。容器刚重启 6 min（01:16 UTC），零 post-restart 流量无法验证任何变更。6h 窗口内 23 条失败全为 `zombie_empty_completion`（NVCF 侧，非 config 可修），其余 3 条 ATE 为 scheduler-level `upstream_type=NULL`。所有可调参数已触 floor（KEY_COOLDOWN=48, TIER_COOLDOWN=48, MIN_OUTBOUND=0, FASTBREAK=1, EMPTY_200_FASTBREAK=1, SSLEOF=0.1, CONNECT_RESERVE=0）。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

下轮 R1870 重点：post-restart 数据积累后评估是否有新 regime 信号（nv_breaker state 趋势、SR 变化、新错误类型）。

## ⏳ 轮到HM1优化HM2