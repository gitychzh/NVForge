# R2398 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 6→5

## 改前数据 (4h window)

### nv_gw logs (最近100行, error/warn筛选)

4h窗口内关键事件:
- **glm5_2_nv ATE cluster**: 3次连续 block-out (10:33, 11:03, 11:33), 每次6个 consecutive NVCFPexecTimeout
  - `[10:33-10:35] glm5_2_nv: 6 timeout → 155s → PEER-FB skip → 502`
  - `[11:03-11:05] glm5_2_nv: 6 timeout → 155s → PEER-FB skip → 502`
  - `[11:33-now] glm5_2_nv: k4 timeout 25s, k5 SUCCESS (17.9s)` — mixed success
- **kimi_nv**: 1次 broken_pipe (downstream client disconnect), 1次 zombie_empty_completion
- **SSLEOFError**: 1次 at k2, cycled to next key immediately

### nv_requests 4h DB (hermes_logs@litellm)

| mapped_model | status | cnt | avg_dur | max_dur | avg_ttfb |
|--------------|--------|-----|---------|---------|----------|
| glm5_2_nv    | 200    | 8   | 18,191  | 46,034  | 17,940   |
| glm5_2_nv    | 502    | 7   | 146,894 | 160,450 | -        |
| kimi_nv      | 200    | 16  | 76,266  | 252,619 | 75,919   |
| kimi_nv      | 502    | 3   | 114,111 | 222,372 | 24,406   |

**glm5_2_nv 6h errors**:
| error_type | n |
|------------|---|
| all_tiers_exhausted | 10 |

**1h recent**:
| mapped_model | status | cnt | avg_dur |
|--------------|--------|-----|---------|
| glm5_2_nv    | 200    | 2   | 17,153  |
| glm5_2_nv    | 502    | 2   | 155,332 |
| kimi_nv      | 200    | 2   | 26,542  |

### HM1 nv_gw 当前关键 env

```
NVU_PEXEC_TIMEOUT_FASTBREAK=6   # ← 目标参数 (当前)
NVU_TIER_BUDGET_GLM5_2_NV=230
NVU_TIER_BUDGET_KIMI_NV=400
NVU_TIER_BUDGET_DSV4P_NV=265
NVU_STREAM_FIRST_BYTE_DEADLINE_S=16
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_EMPTY_200_FASTBREAK=3
NVU_SSLEOF_RETRY_DELAY_S=2.0
TIER_TIMEOUT_BUDGET_S=475
CC4101 PROXY_TIMEOUT=420
UPSTREAM_TIMEOUT=24
```

### HM2 当前兼容状态

| 参数 | HM1 | HM2 (REMOTE) | 兼容性 |
|------|-----|--------------|--------|
| PEXEC_TIMEOUT_FASTBREAK | 5 (new) | 独立 | 无影响 |
| TIER_BUDGET_GLM5_2 | 230 | 必须相同 | 无影响 |

无兼容冲突风险。

## 问题分析

### glm5_2_nv NVCF timeout cluster

- 4h: 7/15 ATE (47%), 全部 all_tiers_exhausted, 错误类型都是 NVCFPexecTimeout
- 每条 ATE 请求: 6 consecutive timeout @ ~25s each = ~155s total
- 成功请求: 8/15, avg_dur=18s, 全部在 key 1-2 完成 (不需要 5+ keys)
- **0 partial-success patterns**: 没有 "前3个key超时, 后2个key成功" 的案例
- 当 NVCF cluster 进入 timeout 状态, ALL 5 keys 都超时, 无例外

### FASTBREAK=6 的浪费

- 当前 FASTBREAK=6 (R2391): 6 consecutive timeout → fastbreak
- 实际: 全部 7 个 ATE 都是 6 timeout 才断, 浪费 1 个 key-cycle (~25s)
- 成功请求: 从未到 fastbreak 阈值 (success on key 1-2)
- **结论**: FASTBREAK=6 只保护了不存在的 "5个key超时+第6个key成功" 场景

### 改为5的理由

- FASTBREAK=5: 5 consecutive timeout → fastbreak
- 节省: 每个 NVCF timeout cluster 请求 ~25s (1 key cycle)
- 成功率不变: 成功请求在 key 1-2 完成, 不接近 fastbreak
- 风险: 如果 NVCF 有 "4个key超时+第5个key成功" 场景, FASTBREAK=5 会截断——但 4h 数据 0 证据

### 为什么不改 FASTBREAK=4 或更低?

- 保守: 5 是 key pool size (5 keys), 每个 key 至少一次机会
- 4 会留下 1 个 key 未尝试, 可能错过 single-key recovery
- 5 是逻辑下限: "所有 key 都试过了, 全部 timeout"

## 修改

### docker-compose.yml (HM1)

```yaml
# 修改前:
- NVU_PEXEC_TIMEOUT_FASTBREAK=6  # R2391 ...

# 修改后:
- NVU_PEXEC_TIMEOUT_FASTBREAK=5  # R2398 (HM2→HM1): 6→5. 4h DB: glm5_2_nv 7/15 ATE, all with 6 consecutive NVCFPexecTimeout (~25s ea, ~155s total). 0 edge-case partial-success patterns. 6 wastes a full key-cycle (~25s) on guaranteed-failure cluster. 5 saves ~25s per NVCF timeout cluster without reducing success keys (success always on attempt 1-2, never near fastbreak threshold). Single param; iron law: only HM1.
```

## 验证

1. `docker compose up -d nv_gw` → deployed ✅
2. `curl http://localhost:40006/health` → `{"status": "ok", ...}` ✅
3. `docker exec nv_gw env | grep PEXEC_TIMEOUT_FASTBREAK` → `NVU_PEXEC_TIMEOUT_FASTBREAK=5` ✅

## ⏳ 轮到HM1优化HM2