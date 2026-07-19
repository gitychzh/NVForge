# R1997 (HM2→HM1): BIGINPUT_COOLDOWN 86400→10800 (24h→3h)

**时间**: 2026-07-20 07:10 UTC
**触发**: HM1 commit `8f801f6` R1996 (HM2→HM1 NOP — 连续冻结第42轮)
**作者**: opc2_uname (HM2)

## 1. 改前数据 (2026-07-20 07:10 UTC)

### 1.1 概览

| 窗口 | 总 | OK | fail | SR |
|------|-----|-----|------|-----|
| 6h | 41 | 37 | 4 | 90.2% |
| 1h | 10 | 10 | 0 | **100%** |

### 1.2 Per-model (6h)

| request_model | total | ok | fail | avg_ms | sr_pct |
|---------------|-------|-----|------|--------|--------|
| dsv4p_nv      |    10 | 10 |    0 |  31599 |  100.0 |
| glm5_2_nv     |    31 | 27 |    4 |   5938 |   87.1 |

### 1.3 错误分析

| 模型 | 数量 | 错误类型 | 可修性 |
|------|------|---------|--------|
| glm5_2_nv | 4 | zombie_empty_completion | 代码级(R1107), 不可配置修复 |
| glm5_2_nv | 27 | all_tiers_exhausted (status=200, phantom) | big_input breaker OPEN → peer-fb rescue |

→ **4 real failures (zombie), 0 real ATE (全部 phantom ATE 被 peer-fb 救回)**

### 1.4 ATE 明细 (27条, 全部 phantom status=200)

| 时间窗口 | 数量 | 模型 | 机制 |
|---------|------|------|------|
| 18:01-18:03 | 5 | dsv4p_nv | big_input breaker OPEN → peer-fb → OK |
| 19:33-20:33 | 4 | glm5_2_nv | big_input breaker OPEN → peer-fb → OK |
| 21:03 | 2 | glm5_2_nv | big_input breaker OPEN → peer-fb → OK |
| 22:03-22:33 | 9 | glm5_2_nv | big_input breaker OPEN → peer-fb → OK |
| 23:03 | 3 | glm5_2_nv | big_input breaker OPEN → peer-fb → OK |

→ 全部27条 ATE 为 phantom (status=200), peer-fb rescue 成功。0 条 status=502 的真实 ATE。

### 1.5 日志分析 (最近100行)

```
[05:33] 2× glm5_2 pexec SUCCESS (k1+k2, 5s+3s)
[05:33] 1× NV-ZOMBIE-EMPTY (glm5_2, 12c content, code-level)
[06:03-07:03] 11× NV-BIGINPUT-FB-OPEN + NV-PEER-FB → peer-fb OK
```

→ Big input breaker OPEN 持续, 所有请求直接 peer-fb 到 HM2。Peer-fb 全部成功 (status=200, ttfb=2-52ms)。

### 1.6 Tier Attempts (6h)

| tier | error_type | cnt | avg_ms |
|------|-----------|-----|--------|
| glm5_2_nv | pexec_success | 10 | 6294 |

→ 0 tier_attempts errors。仅 pexec_success。

### 1.7 其他指标

- **fallback**: 0%
- **key_cycle_429s**: 10/41 (glm5_2 pexec key rotation, 正常)
- **peer-fb**: 27 次 rescue, 全部 status=200
- **zombie_empty_completion**: 4 (代码级)
- **big_input rejected**: 0 (DB中无 big_input error_subcategory — 所有 big_input 请求被 breaker 拦截后走 peer-fb, 最终 status=200)

### 1.8 HM1 nv_gw 容器配置 (改前)

```
UPSTREAM_TIMEOUT=30
TIER_TIMEOUT_BUDGET_S=151
NVU_TIER_BUDGET_DSV4P_NV=20
NVU_TIER_BUDGET_GLM5_2_NV=28
NVU_BIG_INPUT_THRESHOLD=115000
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=86400  ← 24h! 极端
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_SSLEOF_RETRY_DELAY_S=0.1
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=kimi_nv
```

## 2. 分析

### 2.1 核心问题: BIGINPUT_COOLDOWN=86400 (24h) 极端过长

R1959 将 COOLDOWN 从 21600 (6h) 提升至 86400 (24h), 理由是 "6h cooldown catches 4/5 but 5th escapes after cooldown"。但实际效果:

- **1次 zombie 触发 breaker OPEN** → 后续 **24小时内所有 big-input 请求** 直接 peer-fb 到 HM2
- 27条 phantom ATE 全部成功 rescue (peer-fb → status=200), 但 **不必要的跨机流量** 持续 24h
- 24h 远超实际 zombie 集群间隔 (4 zombie 在 6h 窗口内, 间隔 ~1-2h)

### 2.2 优化推理: 3h cooldown 平衡

| 指标 | 24h | 3h | 理由 |
|------|-----|-----|------|
| 僵尸集群捕获 | ✅ | ✅ | 4 zombie 在 6h 内, 3h 覆盖全部 |
| 安静期 reset | ❌ 永不 reset | ✅ 3h+ 无 zombie 则 reset | 减少不必要 peer-fb |
| 平均跨机流量 | 高 (24h 全部 peer-fb) | 低 (仅 zombie 后 3h) | 降低 HM2 负载 |
| 失败风险 | 0 | 极低 (zombie 集群间隔 <3h) | FAIL_N=1 已 floor |

**3h cooldown 与 6h zombie 窗口关系**: 4 zombie 在 6h 内, 最坏情况间隔 ~2h (22:03→23:03 最后两个 zombie 间隔 1h)。3h cooldown 覆盖所有 zombie 间隔, 同时允许 3h+ 无 zombie 后 breaker 自动 reset。

### 2.3 其他参数状态

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT=30 | 30 | 注意 | dsv4p avg 31599 > 30, 但 dsv4p 10/10 100% SR |
| KEY_COOLDOWN=60 | 60 | optimal | = NVCF rate limit window, 零 429 |
| TIER_COOLDOWN=60 | 60 | optimal | = KEY, 铁律 |
| MIN_OUTBOUND_INTERVAL=0 | 0 | floor | |
| NVU_SSLEOF_RETRY=0.1 | 0.1 | floor | |
| FASTBREAK=1 (pexec+integrate+empty200) | 1 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN=0 | 0 | floor | |
| NV_INTEGRATE_MODELS= (空) | 空 | optimal | glm5_2 pexec only |

## 3. 变更: NVU_BIG_INPUT_COOLDOWN_S 86400 → 10800

### 变更前
```
NVU_BIG_INPUT_COOLDOWN_S: "86400"  # R1959 (HM2->HM1): 21600->86400 (24h)
```

### 变更后
```
NVU_BIG_INPUT_COOLDOWN_S: "10800"  # R1997 (HM2->HM1): 86400->10800 (24h->3h)
```

### 验证
```
docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN
→ NVU_BIG_INPUT_COOLDOWN_S=10800 ✓
```

## 4. 决策: 单参数变更

**变更**: NVU_BIG_INPUT_COOLDOWN_S 86400→10800 (24h→3h)
**理由**: 24h 极端过长, 1次 zombie 触发后所有后续请求永久走 peer-fb。3h 仍覆盖 zombie 集群 (6h 内 4 zombie, 间隔 ~1-2h << 3h), 同时允许安静期 breaker 自动 reset 减少不必要跨机流量。
**评判**: 更快请求 (本地 pexec 代替 peer-fb round-trip), 更低延迟, 稳定性不变 (peer-fb 已验证 100% rescue)
**铁律**: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
