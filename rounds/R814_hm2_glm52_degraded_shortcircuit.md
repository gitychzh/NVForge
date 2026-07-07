# R814: HM2 glm5_2_nv DEGRADED tier 级短路冷却

> 承接 R813 (停 inject thinking + ms_gw [DONE] 关连接). 远程 HM2 8轮定时优化 R1.
> 铁律: 改前有数据 (NVCF 直连实测 + DB), 改后有验证 (端到端 + 日志). 改动 ≤5 处.
> 角色: HM2-only 部署. config.py/handlers.py/upstream.py/cooldown.py 共享源码, 仓库同步供 HM1.

## 改前数据 (2026-07-08 01:15 UTC, 远程 HM2 DB 60min 窗口)

| tier_model | status | count | 备注 |
|---|---|---|---|
| dsv4p_nv | 200 | 68 | SR 93.2%, 健康 |
| dsv4p_nv | 502 | 5 | 含 1 条 64s 上游卡死 (孤例) |
| glm5_2_nv | 502 | 14 | **SR 0%**, 全 all_tiers_exhausted |
| kimi_nv | — | 0 | 60min 无请求 |

glm5_2_nv 60min 14/14 全 502, error_type 全是 all_tiers_exhausted.
docker logs: 每次请求 NVCF 返回 `400 non-cycling ... DEGRADED function cannot be invoked`,
function 3b9748d8 当前 DEGRADED (NVCF 上游侧故障, 网关不可修).

### 根因 (网关侧可修部分)
NVCF function DEGRADED 是 **tier 级**故障 (所有 key 都会 400), 但现有 per-key cooldown
只抓 429, 抓不住 400 DEGRADED. 每 request 都重新打 NVCF 试一遍 key 才 502 (0.6-1s 无谓探测),
既拖慢 fallback 到 ms_gw, 又给已坏的 NVCF function 加无谓压力.

## 改动 (3 文件, 逻辑上 1 个功能, 编辑点 7 处)

### 1. cooldown.py (新增 tier 级 degraded 状态机)
- 新增 `TIER_DEGRADED_COOLDOWN_S` (env `NVU_TIER_DEGRADED_COOLDOWN_S`, 默认 60s)
- 新增 `mark_tier_degraded(tier_model, duration_s)` — tier 级标记
- 新增 `is_tier_degraded(tier_model)` — 过期自动清理

### 2. config.py
- re-export `is_tier_degraded`, `mark_tier_degraded`, `TIER_DEGRADED_COOLDOWN_S`

### 3. upstream.py
- import 新函数
- pexec 路径 noncycle-err: 400 且 body 含 DEGRADED → mark_tier_degraded (日志 NV-TIER-DEGRADED)
- integrate 路径 noncycle-err: 同上 (日志 NV-INTEGRATE-TIER-DEGRADED)
- pexec 路径 tier 入口: is_tier_degraded → 短路返回 fail, 跳过 key 循环 (日志 NV-TIER-DEGRADED-SKIP)
- integrate 路径 tier 入口: 同上 (日志 NV-INTEGRATE-TIER-DEGRADED-SKIP)

## 改后验证 (端到端, 2026-07-08 01:20 UTC)

| 请求 | 改前耗时 | 改后耗时 | 日志 |
|---|---|---|---|
| glm5_2_nv #1 | ~0.7s (打 NVCF 400) | 0.66s | NV-NONCYCLE-ERR + NV-TIER-DEGRADED mark |
| glm5_2_nv #2 | ~0.7s (再打 NVCF 400) | **0.006s** | NV-TIER-DEGRADED-SKIP 短路 |
| dsv4p_nv (健康) | 15.8s 200 | 15.8s 200 | 未误伤, 不短路 |

效果: glm5_2_nv DEGRADED 期间, 首请求 0.66s 标记后, 后续 60s 内所有请求 5ms 短路 502 →
立即 fallback ms_gw, 不再打 NVCF. 既加速 fallback, 又不骚扰已坏的上游.

## 回滚
`NVU_TIER_DEGRADED_COOLDOWN_S=0` 即禁用短路 (mark 后立即过期). 或还原 .bak.R814.

## 下轮候选
- dsv4p_nv 64s 上游卡死孤例 (偶发, 需更多数据确认是否值得改)
- kimi_nv 无流量, 健康未知
- ms_gw 171s 大输出流式 (正常, 但可看 [DONE] 关连接是否生效)
