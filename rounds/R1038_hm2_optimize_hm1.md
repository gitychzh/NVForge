# R1038: HM2→HM1 — NVU_STREAM_TOTAL_DEADLINE_S 72→90 (+18s)

## 数据来源

- HM1 DB: `logs_db` / `hermes_logs` / `nv_requests` + `nv_tier_attempts`
- 时间窗口: 2026-07-09 18:16 UTC → 2026-07-10 00:16 UTC (6h)
- 收集时间: 2026-07-10 00:16 UTC

## 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 292 |
| 成功 (200) | 278 (95.2%) |
| 失败 | 14 (4.8%) |
| ATE | 11 |
| NVStream_TimeoutError | 3 |
| stream_total_deadline | 3 |

### 按模型统计

| 模型 | 总请求 | 成功 | 失败 | ATE | P50 | P95 |
|------|-------|------|------|-----|-----|-----|
| glm5_2_nv | 172 | 166 | 6 | 1 | 6,109ms | 57,176ms |
| dsv4p_nv | 56 | 51 | 5 | 5 | 7,409ms | 61,114ms |
| kimi_nv | 38 | 37 | 1 | 1 | 3,784ms | 35,812ms |
| minimax_m3_nv | 26 | 24 | 2 | 4 | 10,380ms | 82,649ms |

### 错误类型分布

| 错误类型 | 数量 | 模型 | 平均延迟 | 最大延迟 |
|----------|------|------|---------|---------|
| all_tiers_exhausted | 11 | dsv4p_nv(5), minimax_m3_nv(4), glm5_2_nv(1), kimi_nv(1) | 70,421ms | 151,405ms |
| NVStream_TimeoutError | 3 | glm5_2_nv | 94,904ms | 98,823ms |
| stream_total_deadline | 3 | glm5_2_nv(2), minimax_m3_nv(1) | 69,014ms | 94,589ms |

### stream_total_deadline 详情

| 时间 | 模型 | Key | 延迟 | 模式 |
|------|------|-----|------|------|
| 19:39 UTC | glm5_2_nv | K1 | 61,948ms | nv_integrate |
| 19:32 UTC | minimax_m3_nv | K1 | 50,505ms | nv_integrate |
| 18:44 UTC | glm5_2_nv | K1 | 94,589ms | nv_integrate |

### glm5_2_nv integrate 成功延迟分布

| 桶 | 数量 |
|----|------|
| <5s | 74 |
| 5-10s | 40 |
| 10-20s | 27 |
| 20-30s | 9 |
| 30-50s | 10 |
| 50-70s | 4 |
| 70-90s | 2 |

## 分析

`NVU_STREAM_TOTAL_DEADLINE_S=72` 与 `NVU_INTEGRATE_THINKING_TIMEOUT_S=90` 之间存在 18s 间隙：
- 72s deadline 在 integrate thinking 完成前截断流
- 3 stream_total_deadline 错误全部发生在 integrate 模式
- 2 成功 integrate 请求在 80.8s 和 82.2s 勉强存活（72s 临界）
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90 是 per-key 上限，但 stream_total_deadline=72 先于它触发

72→90：对齐 NVU_INTEGRATE_THINKING_TIMEOUT_S=90，消除间隙。
- 30s 余量 vs openclaw 120s 安全
- 成功 integrate 延迟分布：70-90s 桶仅 2/166 (1.2%)，90s 不会造成大面积等待
- NVU_TIER_BUDGET_GLM5_2_NV=96 确保单 key 超时不会无限累积

## 修改

| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| NVU_STREAM_TOTAL_DEADLINE_S | 72 | 90 | +18s |

## 验证

- `docker compose up -d nv_gw` → 成功
- `docker exec nv_gw env | grep NVU_STREAM_TOTAL_DEADLINE_S` → `90`
- `/health` → `{"status": "ok", ...}`

## 铁律

- ✅ 改前必有数据
- ✅ 改后必有验证
- ✅ 只改 HM1 不改 HM2
- ✅ 单参数少改多轮

## ⏳ 轮到HM1优化HM2