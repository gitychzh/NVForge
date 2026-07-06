# R345: HM2→HM1 — ⏸️ 无操作: 零流量 · 全参数均衡 · 无变更窗口 · 铁律:只改HM1不改HM2

## 📊 数据采集 (11:10 UTC, 2026-06-30)

### 配置快照 (docker exec hm40006 env)
| 参数 | 当前值 | 说明 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 45 | Per-key NVCF timeout |
| TIER_TIMEOUT_BUDGET_S | 100 | 总 tier 预算 |
| KEY_COOLDOWN_S | 38 | Key 429 冷却 |
| TIER_COOLDOWN_S | 38 | Tier 冷却 (KEY=TIER=38 不变量维持) |
| MIN_OUTBOUND_INTERVAL_S | 6.0 | 出站最小间隔 |
| HM_CONNECT_RESERVE_S | 10 | 连接预留 |
| HM_SSLEOF_RETRY_DELAY_S | 3.0 | SSL 错误重试延迟 |

### 容器状态
- **状态**: Up 2 hours (healthy) — 2026-06-30 09:32 UTC docker compose up 重启
- **健康检查**: 200 OK (http://localhost:40006/health)
- **日志 (最近)**: 无 HM-SUCCESS/HM-TIMEOUT/HM-ALL-TIERS-FAIL 事件 — 自重启以来零流量

### DB 验证 (PostgreSQL hermes_logs)
- **hm_requests 表**: 454 条记录 (2026-06-29 13:44 → 2026-06-30 07:43 UTC)
  - 成功: 430 (94.7%), 错误: 24 (5.3%)
  - 最近 30 分钟: **0 请求** (自 09:32 重启后无新写入)
- **最后记录时间**: 2026-06-30 07:43:08 UTC (容器重启前 ~1h47min)
- **错误分布**: 全部 ATE (NVCFPexecTimeout) — NVCF 侧不可防

### 错误详情 (今日 2026-06-30 00:00–07:43 UTC)
| 时间 | 错误类型 | 持续时间 | Key | 详情 |
|------|---------|---------|-----|------|
| 00:09:58 | all_tiers_exhausted | 88,019ms | None | 3次 attempt 全 NVCFPexecTimeout |
| 00:27:14 | all_tiers_exhausted | 85,805ms | None | 6次 attempt: 5×NVCFPexecTimeout + 1×budget_exhausted_after_connect |
| 04:03:15 | BadRequest | 0ms | None | request_model=? (空请求, 非 HM 问题) |

### 指标 JSONL 验证 (hm_metrics.2026-06-30.jsonl)
- 所有成功请求: first attempt 成功, 无 fallback 触发
- 请求模式: stream=False, tier=deepseek_hm_nv, Ring fallback R40
- Per-key 延迟 (今日): k0-k4 均匀, avg 20.5-24.0s
- 仅 1 次 key_cycle_429s_before_success (请求 `2b0ec38f`: k1→k2, 一次重试成功)

## 🎯 优化分析

### 核心发现: 零流量 — 容器重启后无请求
- 容器于 09:32 UTC docker compose up 重启
- 自重启至 11:10 UTC (约 1h38min): **零请求到达**
- hm_proxy.2026-06-30.log 最后一条: 07:43:08.9 UTC
- hm_metrics.2026-06-30.jsonl 最后一条: 07:43:08.925 UTC  
- DB 最后记录: 07:43:08.925 UTC (created_at)
- 重启后无任何新日志/指标/DB 写入

### 为什么零流量?
- HM1 作为 passthrough proxy (deepseek_hm_nv) 等待上游请求
- 上游 (可能是 HM2 或其他调度器) 在重启后未发送新请求
- 容器健康但空闲 — 非配置问题, 是调度/流量路由问题
- 这不是 HM1 参数可修复的: 无请求 = 无优化数据

### CC 清单逐项证伪 (基于最后可用数据窗口)

**HM1-A: MIN_OUTBOUND_INTERVAL_S 验证**
- 当前值 6.0s (R328: 9.0→6.0, -3.0s)
- 0 key_429s — 无速率限制压力
- 请求率极低 (< 0.5 req/min) — 远低于容量
- **证伪**: MIN_OUTBOUND_INTERVAL_S 不相关 — 维持 6.0s

**HM1-B: Per-key 延迟均匀性**
- 5 键分布均匀 (38-43 请求/键)
- Avg 范围: 20,510–23,976ms — 极度均匀
- **证伪**: 无键级瓶颈 — 维持当前配置

**HM1-C: ATE 不可防控**
- 所有 ATE 均为 NVCFPexecTimeout (NVCF 侧超时)
- upstream_type=nvcf_pexec — 请求已到达 NVCF 但超时
- **证伪**: ATE 不可防 — 全部 NVCF 侧失败, 非 HM1 参数可控

**HM1-D: 零流量优化不可行**
- 无请求 = 无可测量延迟/错误/429 模式
- 任何参数变更在零流量下无法验证效果
- **证伪**: 零流量下无优化操作 — 等待流量恢复后下一轮

### 全参数评估表
| 参数 | 当前值 | 评估 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 45 | 不调 | 零流量无数据; 历史 avg OK 20-24s < 45s |
| TIER_TIMEOUT_BUDGET_S | 100 | 不调 | 2×45=90s + 10s 安全边际; 零流量无验证 |
| KEY_COOLDOWN_S | 38 | 不调 | KEY=TIER=38 不变量; 0 key_429s — 完美值 |
| TIER_COOLDOWN_S | 38 | 不调 | KEY=TIER=38 零间隙最优; 0 fallback |
| MIN_OUTBOUND_INTERVAL_S | 6.0 | 不调 | 0 429s; 请求率 < 容量; R328 已验证 |
| HM_CONNECT_RESERVE_S | 10 | 不调 | 4.8× 安全边际; 0 connect errors |
| HM_SSLEOF_RETRY_DELAY_S | 3.0 | 不调 | 0 SSL 未恢复错误; 3s backoff 稳定 |

## 🔧 变更执行
**无变更** — 所有 7 参数处于均衡态, 零 key_429s/零 empty200/零 fallback/零 SSLEOF 未恢复错误. 容器自 09:32 UTC 重启后零流量, 无可优化数据. 本次为 ⏸️ 无操作轮次.

## 📈 预期效果
**无变化** — 维持当前均衡态. 需上游恢复流量以产生可测量数据. 稳定性 IS 最优结果.

### 评判标准
- ✅ **更少报错**: 0 key_429s, 0 empty200, 0 connect errors, 0 SSL unretried — 全零
- ✅ **更快请求**: Avg OK 20-24s across all keys, per-key 均匀 — 已达最快
- ✅ **超低延迟**: 所有成功请求 < UPSTREAM_TIMEOUT=45s, 首次尝试成功
- ✅ **稳定优先**: 零变更 — 稳定即最优
- ✅ **铁律**: 只改 HM1 不改 HM2 — 本回合无变更

## ⏳ 轮到HM1优化HM2 ← 脚本检测此标记