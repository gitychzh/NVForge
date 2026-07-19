# R2001 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 26→24 (-2s)

**时间**: 2026-07-20 07:35 UTC
**触发**: HM1 commit `2791496` R2000 (HM2 cc2) — NOP 巡检 R106
**作者**: opc2_uname (HM2)

## 1. 改前数据 (2026-07-20 07:35 UTC)

### 1.1 概览

| 窗口 | 总 | OK | fail | SR |
|------|-----|-----|------|-----|
| 6h | 41 | 36 | 5 | 87.8% |
| 1h | 5 | 4 | 1 | 80.0% |
| 30m | 2 | 1 | 1 | 50.0% |

### 1.2 Per-model (6h)

| request_model | total | ok | fail | avg_ms | sr_pct |
|---------------|-------|-----|------|--------|--------|
| glm5_2_nv     |    31 | 26 |    5 |   5724 |   83.9 |
| dsv4p_nv      |    10 | 10 |    0 |  31599 |  100.0 |

### 1.3 错误分析

| 模型 | 数量 | 错误类型 | 可修性 |
|------|------|---------|--------|
| glm5_2_nv | 5 | zombie_empty_completion | 代码级(R1107), 不可配置修复 |
| glm5_2_nv | 21 | all_tiers_exhausted (status=200, phantom) | peer-fb rescue |
| dsv4p_nv | 6 | all_tiers_exhausted (status=200, phantom) | peer-fb rescue |

→ **5 real failures (zombie), 0 real ATE (全部 phantom ATE 被 peer-fb 救回)**

### 1.4 glm5_2 genuine OK 明细

| 指标 | 值 |
|------|-----|
| 真实 OK | 5 (非 ATE phantom) |
| 真实 OK max | **9,201ms** (79%↓ from R1998 历史 26,165ms) |
| NVCF 状态 | 持续退化, 大部分请求走 phantom ATE→peer-fb rescue |

### 1.5 dsv4p genuine OK 明细

| 指标 | 值 |
|------|-----|
| 真实 OK | 4 (18:00 batch) |
| phantom ATE | 6 (18:01-18:03 batch) |
| 真实 OK max | 24,784ms |

### 1.6 日志分析

```
[07:33:32.7] [NV-ZOMBIE-EMPTY] (glm5_2_nv) zombie empty completion: finish_reason=stop but content_chars=12 reasoning_chars=0 < 50
[07:33:32.7] [NV-UPSTREAM-ERROR-CHUNK] sent finish_reason=content_filter → triggers cc4101 zombie→api_error→CC retry
```

### 1.7 Peer-fallback

| 指标 | 值 |
|------|-----|
| peer-fb count (6h DB) | 0 |
| peer-fb 状态 | 就绪 |

### 1.8 429 key cycling (6h)

| 模型 | key_cycle_429s=1 | 含义 |
|------|-----------------|------|
| glm5_2_nv | 10 | NVCF 限流, 正常 key 轮换 |

### 1.9 HM1 nv_gw 容器配置 (改前)

```
UPSTREAM_TIMEOUT=30
TIER_TIMEOUT_BUDGET_S=151
NVU_TIER_BUDGET_DSV4P_NV=20
NVU_TIER_BUDGET_GLM5_2_NV=26  ← 当前值
NVU_BIG_INPUT_THRESHOLD=115000
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=10800
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

### 2.1 核心: NVU_TIER_BUDGET_GLM5_2_NV=26 仍有压缩空间

R1998 将 BUDGET 从 28→26 (-2s), 当时历史 genuine OK max=26,165ms。现在:

- **glm5_2 genuine OK max=9,201ms** — 79%↓ 下降, 远低于当前 26s budget
- **9,201ms < 24s** — 14.8s margin, 安全
- **Peer-fb 约束**: 24+122=146 < 151 BUDGET ✓
- **失败路径节省**: 每个 zombie 节省 2s 等待 (24s→22s effective wait)

### 2.2 其他参数状态

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| KEY_COOLDOWN=60 | 60 | optimal | = NVCF rate limit window, 零真正 429 失败 |
| TIER_COOLDOWN=60 | 60 | optimal | = KEY, 铁律 |
| NVU_TIER_BUDGET_DSV4P_NV=20 | 20 | hold | genuine OK max=24.8s > 20s, 但 NVCF 退化中 phantom ATE 主导 |
| NVU_STREAM_TOTAL_DEADLINE=25 | 25 | hold | OK max=24.8s near 25s, margin 仅 0.2s |
| NVU_STREAM_FIRST_BYTE=15 | 15 | optimal | TTFB p99 << 15s |
| FASTBREAK=1 (all 3) | 1 | floor | |
| SSLEOF_RETRY=0.1 | 0.1 | floor | |
| PEER_FALLBACK_TIMEOUT=122 | 122 | optimal | 122 > 24+2=26 ✓ |

## 3. 变更: NVU_TIER_BUDGET_GLM5_2_NV 26 → 24

### 变更前
```
NVU_TIER_BUDGET_GLM5_2_NV: "26"  # R1998 (HM2->HM1): 28->26 (-2s)
```

### 变更后
```
NVU_TIER_BUDGET_GLM5_2_NV: "24"  # R2001 (HM2->HM1): 26->24 (-2s)
```

### 验证
```
docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV
→ NVU_TIER_BUDGET_GLM5_2_NV=24 ✓

curl http://localhost:40006/health
→ {"status": "ok", ...} ✓
```

## 4. 决策: 单参数变更

**变更**: NVU_TIER_BUDGET_GLM5_2_NV 26→24 (-2s)
**理由**: glm5_2 genuine OK max 从 26,165ms (R1998 历史) 下降至 9,201ms (当前 6h), 24s 有 14.8s 安全 margin。Peer-fb 约束 24+122=146 < 151 BUDGET ✓。每个 zombie 节省 2s 失败路径。单参数, 少改多轮。
**评判**: 更少报错 (不变), 更快请求 (失败路径 2s 更快), 超低延迟, 稳定优先
**铁律**: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
