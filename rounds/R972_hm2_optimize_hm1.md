# HM2 Optimize HM1 — Round R972

## 触发分析

- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit author**: `opc2_uname` (HM2)
- **脚本正确检测到自提交并标记 "不触发"**
- **cron 仍被派遣 — 误触发 (false trigger)**

## 数据收集 (改前必有数据)

### HM1 nv_gw 6h 窗口 (2026-07-09 01:00–07:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 成功 | 32 (100.0%) |
| 失败 | 0 |
| ATE | 0 |
| Fallback | 14 (43.8%, 全部 glm5_2→dsv4p, 100% SR) |

### 按模型

| 模型 | 总计 | 200 | 失败 | SR | ATE | Fallback |
|------|------|-----|------|-----|-----|----------|
| dsv4p_nv | 19 | 19 | 0 | 100.0% | 0 | 14 |
| glm5_2_nv | 13 | 13 | 0 | 100.0% | 0 | 0 |

### nv_tier_attempts 6h

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 13 | 56,740 | 62,461 |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | — | — |
| glm5_2_nv | empty_200 | 3 | — | — |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51,838 | 51,838 |

NVCFPexecTimeout max=62,461ms = UPSTREAM=62 + 461ms overhead → binding edge. 但所有 timeout 请求都通过 fallback 到 dsv4p_nv 成功 (dsv4p_nv 14 fallback, 100% SR)。

### 24h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 192 |
| 成功 | 191 (99.5%) |
| 失败 | 1 (0.5%) |
| ATE | 1 (glm5_2_nv) |

### ms_gw 6h: 5req, 0 OK (0.0%) — 未使用/无活跃流量

### HM1 当前配置 (container restarted 10 min ago, R971 live)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 62 | R969 +2s, binding edge (62,461 ≈ 62+461ms) |
| TIER_TIMEOUT_BUDGET_S | 112 | R971 -2s, >>62 safe (50s headroom) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 最小值 |
| NVU_EMPTY_200_FASTBREAK | 3 | 最小值 |
| KEY_COOLDOWN_S | 25 | 稳定 |
| TIER_COOLDOWN_S | 25 | 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 最小值 |
| NVU_CONNECT_RESERVE_S | 0 | 最小值 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | ≥62 safe |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | 双模型跳过 |

## 决策: NOP (零变更)

### 理由

1. **100% 6h SR, 0 ATE, 0 errors**: 系统完美运行，无需调整
2. **所有参数在底线**: FASTBREAK=1, EMPTY_200=3, MIN_OUTBOUND=0, CONNECT_RESERVE=0 — 无法再降
3. **UPSTREAM=62 处于 binding edge** (NVCFPexecTimeout max=62,461ms): 但所有 timeout 请求都通过 fallback 到 dsv4p_nv 成功救援 (14 fallback, 100% SR)。BUDGET=112 提供足够 headroom (50s for second key)。增加 UPSTREAM 会浪费 NVCF 等待时间，不增加更有利于整体吞吐
4. **ms_gw 无优化空间**: EMPTY_200=3 (floor), KEY_COOLDOWN=60 (defensive)
5. **False trigger**: 脚本正确检测到 HM2 自提交，非真实触发

## ⏳ 轮到HM1优化HM2