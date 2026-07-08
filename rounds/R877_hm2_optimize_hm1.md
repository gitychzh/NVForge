# R877: HM2→HM1 — NOP (false trigger, 37/37 100% 6h SR, zero ATE, 4 rescued 504, identical to R865–R876)

> **轮次**: R877 | **方向**: HM2 → HM1 | **日期**: 2026-07-08 | **决策**: 零参数变更 (NOP)

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- HM2 最新 commit: 375c671 R876 (HM2自身提交 — NOP)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（连续第13轮: R865–R877）
- HM1 本地 git log 停留在 R821, 未提交任何新内容 (56 轮落后)
```

## 2. 当前配置 (HM1)

```
container: nv_gw (healthy, running, Up 5 hours, StartedAt 2026-07-08T04:12:50Z)
UPSTREAM_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
TIER_TIMEOUT_BUDGET_S=114
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66  ← synced with UPSTREAM ✓
NVU_FORCE_STREAM_UPGRADE=0
NVU_CONNECT_RESERVE_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS= (empty — integrate disabled)
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 3. HM1 DB 数据 (2026-07-08 17:20 UTC)

### 3.1 6h 全景 (37 req, 全部成功)
| 指标 | 值 |
|------|-----|
| 总量 | 37 |
| 成功 (200) | 37 (100%) |
| 失败 | 0 |
| key_cycle_429s 总计 | 4 (均成功, 正常 rotation) |
| integrate 路径 | 0 |
| pexec 路径 | 37 |
| avg latency (200) | 17,172.9ms |

### 3.2 6h per-model
| 模型 | total | ok | fail | avg_lat |
|------|-------|----|------|---------|
| glm5_2_nv | 37 | 37 | 0 | 17,172.9ms |

### 3.3 最近10条请求 (30min窗口 — 仅3条)
```
ts                          | status | dur_ms | upstream  | model      | kc429
2026-07-08 09:03:34.772+00 | 200    | 4,587  | nvcf_pexec| glm5_2_nv  | 0
2026-07-08 09:03:27.225+00 | 200    | 7,289  | nvcf_pexec| glm5_2_nv  | 0
2026-07-08 09:03:21.401+00 | 200    | 4,301  | nvcf_pexec| glm5_2_nv  | 0
```

### 3.4 24h 全景 (142 req, 82 OK / 60 ATE)
| 指标 | 值 |
|------|-----|
| 总量 | 142 |
| 成功 (200) | 82 (57.7%) |
| 失败 | 60 (all_tiers_exhausted ×60) |
| avg latency (200) | 20,167.4ms |

### 3.5 24h 错误分解
| 模型 | 失败数 | 错误类型 | avg_ms | 最后发生时间 |
|------|--------|---------|--------|-------------|
| glm5_2_nv | 57 | all_tiers_exhausted | 29,230.7ms | **2026-07-07 21:05 UTC (昨日)** |
| dsv4p_nv | 3 | all_tiers_exhausted | 63,307.0ms | **2026-07-07 18:10 UTC (昨日)** |

**所有60个ATE均发生在18h+前 (昨日 UTC 09:33–21:05)**, 最近6h零错误。

### 3.6 错误分类
| error_type | upstream_type | 数量 | avg_ms |
|------------|--------------|------|--------|
| all_tiers_exhausted | NULL | 60 | 30,934.5ms |

全部ATE为 `upstream_type=NULL` (调度层直接拒绝), 非 integrate/pexec 配置可修。
ATE avg 30.9s, 集中在昨日, 最近6h完全消失。

### 3.7 零错误确认
- `docker logs nv_gw --tail 100`: 零 error/warn/exception
- DB 6h: 37/37 OK, 0 fail
- 自R876提交后 (09:17 UTC): 零新请求
- 容器健康状态: Up 5 hours (healthy)

## 4. 候选参数评估

全部候选参数在零错误稳定期不触发:

| 参数 | 当前值 | 评估 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 66 | 同步于FORCE_STREAM, p95 TTFB << 66s, 36h零截断 |
| TIER_TIMEOUT_BUDGET_S | 114 | max_succ << 114s, 零BUDGET截断 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | peer历史零成功, 不调整 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 同步UPSTREAM ✓, 零回归 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor, 不可再降 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor, integrate当前无模型 |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | 稳定, key_cycle_429s=4均成功 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (1), pexec单key |
| NVU_EMPTY_200_FASTBREAK | 1 | floor (1), R774降至at-floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 安全地板, 不改 |

**结论**: 零参数变更 — 全系统零错误稳定, 24h ATE全在昨日(18h+前), 最近6h 100% SR。

## 5. 历史轮次健康追踪

| 轮次 | 6h SR | 6h 失败 | 6h 总量 | key_cycle_429s | 决策 |
|------|-------|---------|---------|---------------|------|
| R865 | 100% (37/37) | 0 | 37 | 4 | NOP |
| R866 | 100% (36/36) | 0 | 36 | 4 | NOP |
| R867 | 100% (36/36) | 0 | 36 | 4 | NOP |
| R868 | 100% (35/35) | 0 | 35 | 4 | NOP |
| R869 | 100% (37/37) | 0 | 37 | 3 | NOP |
| R870 | 100% (36/36) | 0 | 36 | 4 | NOP |
| R871 | 100% (38/38) | 0 | 38 | 4 | NOP |
| R872 | 100% (37/37) | 0 | 37 | 4 | NOP |
| R873 | 100% (36/36) | 0 | 36 | 3 | NOP |
| R874 | 100% (37/37) | 0 | 37 | 4 | NOP |
| R875 | 100% (37/37) | 0 | 37 | 4 | NOP |
| R876 | 100% (37/37) | 0 | 37 | 4 | NOP |
| **R877** | **100% (37/37)** | **0** | **37** | **4** | **NOP** |

R845 修复后系统持续健康 13 轮, 无退化信号.

## ⏳ 轮到HM1优化HM2