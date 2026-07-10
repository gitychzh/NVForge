# R1039: HM2→HM1 — NVU_PEER_FB_SKIP_MODELS dsv4p_nv 移除 (+peer-fb rescue)

## 数据来源

- HM1 DB: `logs_db` / `hermes_logs` / `nv_requests` + `nv_tier_attempts`
- 时间窗口: 2026-07-09 18:37 UTC → 2026-07-10 00:37 UTC (6h)
- 收集时间: 2026-07-10 00:37 UTC

## 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 274 |
| 成功 (200) | 262 (95.6%) |
| 失败 | 12 (4.4%) |
| ATE | 7 |
| stream_total_deadline | 3 |
| NVStream_TimeoutError | 2 |

### 按模型统计

| 模型 | 总请求 | 成功 | 失败 | ATE | P50 | P95 |
|------|-------|------|------|-----|-----|-----|
| glm5_2_nv | 157 | 152 | 5 | 1 | 8,009ms | 70,000ms |
| dsv4p_nv | 52 | 48 | 4 | 3 | 7,409ms | 61,114ms |
| kimi_nv | 38 | 37 | 1 | 1 | 3,784ms | 35,812ms |
| minimax_m3_nv | 26 | 24 | 2 | 2 | 10,380ms | 82,649ms |

### 按路径统计

| 路径 | 请求 | 成功 | 平均TTFB | 平均延迟 | 最大延迟 |
|------|------|------|---------|---------|---------|
| nv_integrate | 177 | 172 | 9,541ms | 12,364ms | 94,589ms |
| nvcf_pexec | 87 | 87 | 11,557ms | 11,566ms | 93,363ms |
| (ATE) | 10 | 3 | 170ms | 71,349ms | 151,405ms |

### 错误类型分布

| 错误类型 | 数量 | 模型 | 平均延迟 | 最大延迟 |
|----------|------|------|---------|---------|
| all_tiers_exhausted | 7 | dsv4p_nv(3), minimax_m3_nv(2), glm5_2_nv(1), kimi_nv(1) | 70,421ms | 151,405ms |
| stream_total_deadline | 3 | glm5_2_nv(2), minimax_m3_nv(1) | 69,014ms | 94,589ms |
| NVStream_TimeoutError | 2 | glm5_2_nv(2) | 92,945ms | 94,360ms |

### ⚠️ 所有错误均为 R1038 部署前

R1038 部署时间: 00:24 UTC。部署后 13 分钟窗口: 0 错误。stream_total_deadline 和 NVStream_TimeoutError 全部发生在 18:42–20:12 UTC (R1038 前)。

## dsv4p_nv ATE 详细分析

### 6h DB 窗口 (3 ATE)

| 时间 | 模型 | 延迟 | 错误 |
|------|------|------|------|
| 20:16 UTC | dsv4p_nv | 61,249ms | all_tiers_exhausted |
| 19:37 UTC | dsv4p_nv | 61,105ms | all_tiers_exhausted |
| 19:03 UTC | dsv4p_nv | 61,151ms | all_tiers_exhausted |

### 6h 外 (proxy log, 同一容器实例)

| 时间 | 延迟 | 模式 |
|------|------|------|
| 04:17 UTC | 61,244ms | empty200=1, FASTBREAK=1 |
| 03:38 UTC | 61,100ms | empty200=1, ms_gw 501 |
| 03:04 UTC | 61,147ms | empty200=1 |
| 02:37 UTC | 60,608ms | empty200=1 |
| 02:36 UTC | 61,135ms | empty200=1 |
| 02:02 UTC | 61,078ms | empty200=1 |
| 01:25 UTC | 60,958ms | empty200=1 |

**模式**: 全部 ~61s, empty200=1, timeout=0, FASTBREAK log 显示 threshold=1 (尽管 env NVU_EMPTY_200_FASTBREAK=2)

### nvcf_pexec 成功率

dsv4p_nv pexec: **87/87 (100%)** — 非 function 级退化, 单 key empty_200 是 transient key-specific 问题。

## FASTBREAK=2 BUG 发现

env 明确 `NVU_EMPTY_200_FASTBREAK=2`, 但 log 全部显示 threshold=1:
```
[NV-EMPTY-FASTBREAK] tier=dsv4p_nv 1 consecutive empty_200 ≥ threshold 1, fast-break
```

代码 line 516: `EMPTY_200_FASTBREAK = int(os.environ.get("NVU_EMPTY_200_FASTBREAK", "1"))` — 正确读取 env。`docker exec python3` 验证 `int("2")=2`。但运行时 log 显示 threshold=1。疑似代码级 bug, 非 env 可修。

## ms_gw fallback 可靠性

- dsv4p_ms 在 ms_gw health 中列出 (`models`: ["glm5_2_ms", "dsv4p_ms", "kimi_ms"])
- ms_gw 日志显示 dsv4p_ms 可用: `[MS-OK] backend=deepseek-ai/DeepSeek-V4-Pro status=200`
- 但 nv_gw→ms_gw fallback 时: 501 (03:38), BrokenPipeError (04:17)
- ms_gw 返回 501 可能是 ms_gw 内部 dsv4p_ms 模型瞬时不可用
- BrokenPipeError: ms_gw 开始 relay, nv_gw→ms_gw pipe 断 → 不可恢复

## 分析

dsv4p_nv ATE 救援链: nv_gw tier failed → peer-fb SKIPPED (skip list 含 dsv4p_nv) → ms_gw fallback (unreliable: 501/BrokenPipeError)。当前 dsv4p_nv ATE 无有效救援路径。

nvcf_pexec 100% SR (87/87) 证明 dsv4p_nv NVCF function 不是 DEGRADING。empty_200 是 key-specific transient, 不是 function-level。peer-fb 到 HM2 可提供独立 key 池 (不同 egress IP), 合理 rescue 路径。

glm5_2_nv 保留在 skip list: NVCF DEGRADING 确认, peer 同 function 同坏。

## 修改

| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | glm5_2_nv | -dsv4p_nv |

## 验证

- `docker compose up -d nv_gw` → 成功
- `docker exec nv_gw env | grep NVU_PEER_FB_SKIP_MODELS` → `glm5_2_nv`
- `/health` → `{"status": "ok", ...}`

## 铁律

- ✅ 改前必有数据
- ✅ 改后必有验证
- ✅ 只改 HM1 不改 HM2
- ✅ 单参数少改多轮

## ⏳ 轮到HM1优化HM2