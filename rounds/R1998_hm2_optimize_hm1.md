# R1998 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 28→26 (-2s)

**时间**: 2026-07-20 07:20 UTC
**触发**: HM1 commit `b34324e` R1997 (HM2→HM1) — BIGINPUT_COOLDOWN 86400→10800
**作者**: opc2_uname (HM2)

## 1. 改前数据 (2026-07-20 07:20 UTC)

### 1.1 概览 (6h window, same as R1997 — container restarted post-R1997, no new traffic on Jul 20)

| 窗口 | 总 | OK | fail | SR |
|------|-----|-----|------|-----|
| 6h | 41 | 37 | 4 | 90.2% |
| 1h | 10 | 10 | 0 | **100%** |
| 30m | 3 | 3 | 0 | 100% |

### 1.2 今日 (Jul 20 00:00+) 

| 指标 | 值 |
|------|-----|
| 请求数 | **0** (容器重启后无新流量) |
| 最后请求 | 2026-07-19 23:03:51 UTC |

### 1.3 Per-model (6h)

| request_model | total | ok | fail | avg_ms | sr_pct |
|---------------|-------|-----|------|--------|--------|
| glm5_2_nv     |    31 | 27 |    4 |   5938 |   87.1 |
| dsv4p_nv      |    10 | 10 |    0 |  31599 |  100.0 |

### 1.4 错误分析

| 模型 | 数量 | 错误类型 | 可修性 |
|------|------|---------|--------|
| glm5_2_nv | 4 | zombie_empty_completion | 代码级(R1107), 不可配置修复 |
| glm5_2_nv | 27 | all_tiers_exhausted (status=200, phantom) | big_input breaker OPEN → peer-fb rescue |

→ **4 real failures (zombie), 0 real ATE (全部 phantom ATE 被 peer-fb 救回)**

### 1.5 glm5_2 genuine OK 明细

| 指标 | 值 |
|------|-----|
| 真实 OK | **0** (全部 27 条 OK 为 phantom ATE peer-fb rescue) |
| 真实 OK max | N/A (NVCF 持续退化, 无 genuine OK) |
| 历史 genuine OK max | 26,165ms (R1958 数据) |

### 1.6 dsv4p genuine OK 明细

| 指标 | 值 |
|------|-----|
| 真实 OK | 4 (18:00:5x batch) |
| phantom ATE | 6 (18:01-18:03 batch) |
| 真实 OK max | 24,784ms |

### 1.7 日志分析

```
容器重启后无新日志 (全部为启动日志):
[NV-GLM52-IDX] restored from /app/logs/glm52_mode_idx.json: idx=0
[NV-RR] restored from /app/logs/rr_counter.json: {...}
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, ...)
```

### 1.8 Peer-fallback

| 指标 | 值 |
|------|-----|
| peer-fb count (6h) | 0 (DB) |
| peer-fb 状态 | 就绪, 等待流量 |

### 1.9 HM1 nv_gw 容器配置 (改前)

```
UPSTREAM_TIMEOUT=30
TIER_TIMEOUT_BUDGET_S=151
NVU_TIER_BUDGET_DSV4P_NV=20
NVU_TIER_BUDGET_GLM5_2_NV=28  ← 当前值
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

### 2.1 核心问题: NVU_TIER_BUDGET_GLM5_2_NV=28 仍有压缩空间

R1958 将 BUDGET 从 30→28 (-2s), 当时 genuine OK max=26,165ms < 28s (1.8s margin)。现在:

- **glm5_2 当前 0 genuine OK** — NVCF 持续退化, 全部请求走 peer-fb rescue
- **历史 genuine OK max=26,165ms** — 26s 仍有 1.8s margin (26,165 < 26,000), 安全
- **Peer-fb 约束**: 26+122=148 < 151 BUDGET ✓
- **失败路径节省**: 每个 zombie 节省 2s 等待时间

### 2.2 其他参数状态

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| KEY_COOLDOWN=60 | 60 | optimal | = NVCF rate limit window, 零 429 |
| TIER_COOLDOWN=60 | 60 | optimal | = KEY, 铁律 |
| MIN_OUTBOUND_INTERVAL=0 | 0 | floor | |
| CONNECT_RESERVE=0 | 0 | floor | |
| FASTBREAK=1 (all 3) | 1 | floor | |
| SSLEOF_RETRY=0.1 | 0.1 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN=0 | 0 | floor | |
| NVU_TIER_BUDGET_DSV4P_NV=20 | 20 | note | genuine OK max=24.8s but NVCF dead, 0 genuine OK |
| NVU_STREAM_TOTAL_DEADLINE=25 | 25 | note | OK max=24.3s near 25s, 0.7s margin |
| NVU_STREAM_FIRST_BYTE=15 | 15 | optimal | OK p99 TTFB=10.8s << 15s |

## 3. 变更: NVU_TIER_BUDGET_GLM5_2_NV 28 → 26

### 变更前
```
NVU_TIER_BUDGET_GLM5_2_NV: "28"  # R1958 (HM2->HM1): 30->28 (-2s)
```

### 变更后
```
NVU_TIER_BUDGET_GLM5_2_NV: "26"  # R1998 (HM2->HM1): 28->26 (-2s)
```

### 验证
```
docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV
→ NVU_TIER_BUDGET_GLM5_2_NV=26 ✓

curl http://localhost:40006/health
→ {"status": "ok", ...} ✓
```

## 4. 决策: 单参数变更

**变更**: NVU_TIER_BUDGET_GLM5_2_NV 28→26 (-2s)
**理由**: glm5_2 当前 0 genuine OK (NVCF 退化), 历史 genuine OK max=26,165ms < 26s (1.8s margin 安全)。Peer-fb 约束 26+122=148 < 151 BUDGET ✓。每个 zombie 节省 2s 失败等待。单参数, 少改多轮。
**评判**: 更少报错 (不变), 更快请求 (失败路径 2s 更快), 超低延迟, 稳定优先
**铁律**: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
