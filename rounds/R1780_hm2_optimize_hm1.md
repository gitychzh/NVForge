# R1780: HM2→HM1 — NOP (100% SR零故障, 全参数 floor/optimal, false trigger)

**时间**: 2026-07-18 16:20 UTC
**触发**: HM1 commit `这是我提交的, 不触发` (false trigger — R1778 author=opc2_uname, NOP)
**作者**: opc2_uname (HM2)

## 数据收集

### 6h DB (nv_requests, 10:00-16:00 UTC)
```
request_model | total | ok  | fail | sr_pct | avg_ms | max_ms
glm5_2_nv     |    24 |  24 |    0 |  100.0 |   8632 |  19968
dsv4p_nv      |     0 |   0 |    0 |      - |      - |      -
```

### 24h DB (nv_requests)
```
request_model | total | ok  | fail | sr_pct | avg_ms | max_ms
glm5_2_nv     |   163 | 140 |   23 |   85.9 |  10375 |  51823
dsv4p_nv      |     3 |   1 |    2 |   33.3 |  54729 |  70017
```

### 24h 错误明细
| 模型 | 错误类型 | 数量 | 可修性 |
|------|---------|------|--------|
| glm5_2_nv | zombie_empty_completion | 23 | 代码级检测功能, 不可配置修复 |
| dsv4p_nv | all_tiers_exhausted | 2 | 仅3请求, 样本太小无法诊断 |

### 6h 零错误 — 详细
- glm5_2_nv: 24/24 100% SR, pexec_us_rr mode, all first-key success
- 0 fallback, 0 ATE, 0 tier_attempts 错误 (仅 pexec_success 24 + pexec_500 1)
- key_cycle_429s: 24/24 请求均有 key_cycle_429s=1 (正常key轮转, 100% SR证明已吸收)
- 日志: 100% NV-GLM52-SUCCESS, 零 ERROR/WARN/FAIL

### 容器状态 (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=55
TIER_TIMEOUT_BUDGET_S=195
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=65
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=60
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_MS_GW_FALLBACK_TIMEOUT=120
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS="" (空)
NV_GLM52_MODE_CHAIN=pexec_us_rr
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_STREAM_FIRST_BYTE_DEADLINE_S=17
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```

### 容器漂移检测
- Compose md5: `753d934dd582ba776d2efa66d95048c7`
- 所有参数 compose ↔ container env 一致: **零漂移** ✓

## 分析

### 1. 6h 100% SR — 系统处于最佳状态
- 24/24 OK, 零错误, 零 fallback, 零 ATE
- glm5_2_nv pexec_us_rr mode, 全部 first-key success
- avg=8632ms, max=19968ms << UPSTREAM=55s (buffer=35s, 充足)
- 日志干净: 100% SUCCESS, 零 ERROR/WARN

### 2. 24h 错误全部不可配置修复
- 23 zombie_empty_completion (glm5_2_nv): 代码级ZOMBIE检测功能(R1107), 快速abort替代hang, 不可配置修复
- 2 dsv4p_nv ATE: 24h仅3请求, 样本太小(33.3% SR), 无法诊断。6h内零 dsv4p_nv 流量, peer-fb路径未触发

### 3. key_cycle_429s 100% 但 SR 100%
- 24/24请求均有 key_cycle_429s=1, 但全部成功
- KEY_COOLDOWN=65 + TIER_COOLDOWN=65 (R1740 boundary-alignment), 429s被key轮转机制完全吸收
- 调整KEY_COOLDOWN无依据: SR=100%证明当前机制有效, 调大只会增加不必要的key恢复等待

### 4. 所有参数 floor/optimal
- FASTBREAK=1 (floor), EMPTY_200_FASTBREAK=1 (floor), MIN_OUTBOUND=0 (floor)
- CONNECT_RESERVE=0 (floor), NV_INTEGRATE_KEY_COOLDOWN=0 (floor)
- SSLEOF_RETRY=0.5 (floor), BIG_INPUT_FAIL_N=1 (floor)
- INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
- STREAM_FIRST_BYTE=17, STREAM_TOTAL=25 (optimal, p99 TTFB=10.8s << 17s)
- 无进一步优化空间

### 5. 零容器漂移
- Compose md5 与 running env 完全一致
- 所有关键参数 100% 匹配

## 决策: NOP (零变更)

**理由**: 6h 零错误 100% SR, 24h 错误全部代码级 zombie_empty_completion 或样本太小无法诊断。所有参数 floor/optimal, 零漂移。零可配置修复故障。铁律:只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
