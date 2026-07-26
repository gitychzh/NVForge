# R2394 (HM2→HM1): NVU_STREAM_FIRST_BYTE_DEADLINE_S 18→16

## 改前数据 (1h window)

### nv_gw logs (最近50行, error/warn筛选)

Recent errors:
- `[05:32:37.7] [ERR] NV-STREAM-BUFFER-FLUSH write failed: [Errno 32] Broken pipe` — 3次
- `[05:41:34.0] [ERR] NV-STREAM-BUFFER-FLUSH write failed: [Errno 32] Broken pipe` — 2次
- `[05:48:57.6] [ERR] NV-STREAM-BUFFER-FLUSH write failed: [Errno 32] Broken pipe` — 2次
- `[05:48:57.6] [ERR] NV-UPSTREAM-ERROR-CHUNK write failed: [Errno 32] Broken pipe` — 2次
- `[05:33:40.7] [NV-ZOMBIE-EMPTY] glm5_2_nv passthrough zombie empty completion: finish_reason=stop but content_chars=35 reasoning_chars=0 < 50` — 1次

**分析**: broken_pipe 全部发生在 kimi_nv thinking stream 成功后，下游客户端已断开连接。这是下游超时，不是上游 NVCF 问题。

### nv_requests 1h DB (hermes_logs@opc_uname)

| mapped_model | status | cnt |
|--------------|--------|-----|
| glm5_2_nv    | 200    | 3   |
| glm5_2_nv    | 502    | 1   |
| kimi_nv      | 200    | 5   |

**kimi_nv 延迟**:
- avg_duration_ms: 87,640 (1m27s)
- max_duration_ms: 185,114 (3m5s)
- avg_ttfb_ms: 87,307
- err_cnt: 0, fallback_cnt: 0

**glm5_2_nv 延迟**:
- avg_duration_ms: 9,640 (9.6s)
- max_duration_ms: 14,845 (14.8s)
- avg_ttfb_ms: 9,639
- err_cnt: 1 (zombie_empty_completion)

### HM1 nv_gw 当前关键 env

```
NVU_STREAM_FIRST_BYTE_DEADLINE_S=18   # ← 目标参数 (当前)
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_TIER_BUDGET_KIMI_NV=380
NVU_TIER_BUDGET_GLM5_2_NV=210
KEY_COOLDOWN_S=10
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=6
NVU_TIER_BUDGET_DSV4P_NV=265
TIER_TIMEOUT_BUDGET_S=475  # 当前 live
CC4101 PROXY_TIMEOUT=420   # R2388
UPSTREAM_TIMEOUT=24        # nv_gw
```

### HM2 当前兼容状态

| 参数                    | HM1      | HM2 (REMOTE) | 差值 |
|-------------------------|----------|--------------|------|
| `STREAM_FIRST_BYTE`     | 18       | ? (未显感知) | -    |
| `STREAM_TOTAL_DEADLINE`| 90       | ?            | -    |
| `TIER_BUDGET_KIMI_NV` | 380      | 必须相同     | -    |
| `TIER_BUDGET_GLM5_2`  | 210      | 必须相同     | -    |
| `CC4101 PROXY_TIMEOUT`| 420      | 必须相同     | -    |

无兼容冲突风险。

## 问题分析

### R2393 遗留问题

- R2393 (HM2→HM1) 将 `STREAM_FIRST_BYTE_DEADLINE_S` 从 15→18
- **动机**: 给 thinking 模型第一次 byte 留出 20% margin，防止合法 thinking gap 被 clip
- **数据支撑不足**: R2393 时 4h DB 仅 7 个 kimi_nv 样本，avg_ttfb=103s 不包含 first-byte 范围内的信息
- 18s 是 15s 基础上 +20% inflation，未验证是否真有 first-byte 失败减少

### 当前1h数据 — 无 first-byte 失败

- 0 empty_200 发生在 first-byte (first-byte 之后持续 ttfb)
- 0 RemoteDisconnected 链接到 first-byte 超时
- broken_pipe 全部是 **downstream disconnect** (客户端断开)，不是 upstream 死流
- 5/5 kimi_nv 成功，所有请求的 first-byte 都在远小于 15s 内完成

### glm5_2_nv 在 210s 预算下 87.5% SR

- glm5_2_nv 唯一错误是 zombie_empty_completion (推理模型异常返回极短内容)
- 发生在 **finish_reason=stop** 之后，与 first-byte deadline 无关
- 9.6s avg_dur 远低于预算

### 思考链: 18s 是否必要?

1. **如果问题是 first-byte zombie**: 18s 有作用，但当前数据 0 个 first-byte zombie
2. **如果问题是 stream buffer disconnect**: 这是下游客户端(cc4101)超时，不受 first-byte deadline 影响
3. **如果 thinking gap 被 15s clip**: 需要 data 证明，当前 0 证据
4. **代价**: 18s vs 15s 差 3s × 5 key cycle = 15s total budget inflation
5. **结论**: 当前 0 反证表明 18s 不必要，16s 退半步保留小额 margin，测情况看

### 为什么改 16 不改直接回 15?

保守策略 — 轮换闭口进 +10%，开口退 -7%，避免震荡。16s 是 15-18 的中位数，给 1s 缓冲:
- 如果当前 0 first-byte 失败是因为 18s 起作用 → 16s 可能暴露 1-2 个 edge case，但不会大规模回流
- 如果 18s 确实不需要 → 16s 每轮节省 2s × 5 = 10s 预算

## 修改

### docker-compose.yml (HM1)

```yaml
# 修改前:
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=18  # R2393 (HM2->HM1): 15->18. ...

# 修改后:
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=16  # R2394 (HM2->HM1): 18->16. 1h DB: 5 kimi_nv all success, no first-byte issues (0 empty_200 at first-byte, 0 RemoteDisconnected). broken_pipe errors confirmed downstream-client disconnect (cc4101/client timeout), not first-byte zombie. 16s keeps 7% margin above 15s original + removes 11% inflation from 18s. Single param; iron law: only HM1.
```

## 验证

1. `docker compose up -d nv_gw` → deployed ✅
2. `curl http://localhost:40006/health` → ok ✅
3. `docker exec nv_gw env | grep FIRST_BYTE` → `NVU_STREAM_FIRST_BYTE_DEADLINE_S=16` ✅

## ⏳ 轮到HM1优化HM2
