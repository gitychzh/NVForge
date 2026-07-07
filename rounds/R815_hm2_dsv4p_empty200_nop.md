# R815: HM2 dsv4p_nv 偶发 empty-200-after-65s NOP (数据确认不可安全优化)

> 承接 R814 (glm5_2_nv DEGRADED tier 短路). 远程 HM2 8轮定时优化 R2.
> 铁律: 改前有数据, 改后有验证, 改动 ≤5 处.
> 角色: HM2-only. 不动 HM1, 不动 agent 模型选择.

## 改前数据 (2026-07-08 01:25 UTC, 远程 HM2, 90min 窗口)

### dsv4p_nv 失败模式 (9 例 502 / 90min)
| utc_t | duration_ms | error_type |
|---|---|---|
| 15:58:35 | 60769 | all_tiers_exhausted |
| 16:01:49 | 60744 | all_tiers_exhausted |
| 16:12:34 | 60760 | all_tiers_exhausted |
| 16:16:38 | 60846 | all_tiers_exhausted |
| 16:28:15 | 60787 | all_tiers_exhausted |
| 16:31:34 | 60742 | all_tiers_exhausted |
| 17:10:04 | 64749 | all_tiers_exhausted |
| 17:17:29 | 60983 | all_tiers_exhausted |
| 17:25:45 | 60734 | all_tiers_exhausted |

全部 ~60-65s 失败, error_type 全 all_tiers_exhausted.

### 日志根因 (以 01:08:59-01:10:04 请求为例)
```
01:08:59.3 REQ dsv4p_nv stream, k5 → NVCF pexec
01:10:04.0 NV-EMPTY-200 k5 → 200 Content-Length:0 (stream)   ← 65s 后才吐空响应
01:10:04.0 NV-EMPTY-CYCLE → NV-EMPTY-FASTBREAK (1≥1) → TIER-FAIL elapsed=64743ms
01:10:04.0 NV-PEER-FB skip → 502 for agent ms_gw fallback
```
真相: NVCF pexec 对单次请求卡 ~65s 后吐 Content-Length:0 空 200. 网关 fastbreak 逻辑正确
(1 次 empty 即 break, 未试 5 key), elapsed=64s 是单次 k5 等 NVCF 的 wall clock.

### dsv4p_nv 200 ttfb 分布 (60min, 健康)
| min | p50 | p95 | max |
|---|---|---|---|
| 6704ms | 27456ms | 43686ms | 49827ms |

## 决策: NOP (零网关侧改动)

### 为什么不能改 (数据支撑)
1. **ttfb 重叠**: 正常 200 的 ttfb 在 6.7-49.8s, 失败 case 65s 只比 max 多 15s.
   任何能提前放弃的阈值 (如 55s) 都会误杀 ttfb=49.8s 的正常慢请求.
2. **偶发非系统**: 9 例/90min, dsv4p_nv 60min SR=73/77=94.8%, 非系统性故障.
3. **UPSTREAM_TIMEOUT=66 合理**: 略高于 max 正常 ttfb (49.8s), 给慢请求留余量.
4. **容错链路已通**: empty-200 → fastbreak → 502 → ms_gw fallback 100% ok.
5. **NVCF 上游侧问题**: 65s 吐空 200 是 NVCF pexec 行为, 网关不可修.

强行加 ttfb 提前放弃阈值会误伤 dsv4p_nv 正常 27s 慢请求, 违反稳定优先不误伤.

## 改动
无. 零容器重启, 零参数变更.

## 下轮候选 (R816)
- kimi_nv 60min 无流量, 健康未知 — 可主动发探测请求确认可用性
- ms_gw [DONE] 关连接 (R813 修) 是否在流式大输出下稳定 — 看 ms_requests duration 分布
- glm5_2_nv function 3b9748d8 是否从 DEGRADED 恢复 (周期性) — 再测 NVCF 直连
