# R799: HM2 NVU_TIER_BUDGET_DSV4P_NV=130 (dsv4p 504 cycling 180s→125s)

> 承接 R798 (EMPTY_200_FASTBREAK=1). 8 轮定时优化第 3 轮.
> 铁律: 改前有数据 (dsv4p 504 cycling 日志 + 成功 latency p99), 改后有验证 (budget 日志).
> 角色: HM2-only (纯 env, 复用 R797 per-tier budget 机制).

## 改前数据 (2026-07-07, R798 后)

### DB (nv_requests, 10min 窗口)

| tier_model | status | count | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 200 | 2 | 54106 | 54760 |
| dsv4p_nv | 502 | 3 | 141652 | 180156 | ← 烧满 180s budget |
| glm5_2_nv | 502 | 6 | 699 | 761 |

### dsv4p_nv 失败模式: 504 cycling (非 empty_200)

504 是 cycling 错误 (upstream.py:619 `should_cycle = resp.status in (...,504,...)`), 会 cycle 所有 5 key, 每 key ~63s, 烧满 180s budget 才 fail. 无 504 fastbreak (只有 empty_200/timeout 有).

### dsv4p_nv 成功请求 latency (确认 budget 不误杀)

| p95 | p99 | max |
|---|---|---|
| 75220 | 104102 | 108389 |

成功 max=108s → budget 必须 >108. 取 130 (留 22s 余量, 失败时 2 key 504=126s 后 remaining<5s break).

### NVCF 直连 dsv4p 74f02205 (全 key 504/63s)

| k1 | k2 | k3 |
|---|---|---|
| 504/63.2s | 504/63.6s | 504/63.0s |

NVCF 74f02205 (ai-deepseek-v4-pro) ACTIVE 但持续 504 surge (比 R797 时更严重, 间歇→持续).

## 根因

dsv4p_nv 504 cycling 5 key × 63s = 烧满全局 180s budget. 成功请求 max 108s, 失败请求 180s.
全局 TIER_TIMEOUT_BUDGET_S=180 不能动 (影响 kimi_nv). 用 R797 的 per-tier budget 机制给 dsv4p_nv 130s.

## 修复方案 (HM2, 纯 env, 复用 R797 机制)

`docker-compose.yml` nv_gw.environment 加:
```yaml
- NVU_TIER_BUDGET_DSV4P_NV=130       # R799: 504 cycling 180s→125s; 成功max108s不误杀
```
R797 已加 `NVU_TIER_BUDGET_<MODEL>` per-tier 读取 (upstream.py:464). dsv4p_nv 复用, 无需改源码.

## 实施步骤 (HM2, 已执行)

1. 备份 compose → `.bak.R799`.
2. 加 `NVU_TIER_BUDGET_DSV4P_NV=130`.
3. `docker compose up -d nv_gw`.
4. 验证.

## 验证

### V1: env 生效
```
$ docker exec nv_gw env | grep NVU_TIER_BUDGET
NVU_TIER_BUDGET_DSV4P_NV=130
NVU_TIER_BUDGET_GLM5_2_NV=70
```
✓

### V2: budget 130 触发 (日志)
```
[15:54:21] [NV-CYCLE] tier=dsv4p_nv k1 → 504, cycling
[15:54:21] [NV-TIER-BUDGET] tier=dsv4p_nv budget 130.0s remaining 4.5s < 5s minimum, breaking
[15:54:21] [NV-TIER-FAIL] tier=dsv4p_nv ... elapsed=125508ms   ← 改前 180s
```
✓ 125s (改前 180s), 省 55s.

### V3: health
`curl nv_gw/health` ok ✓

## 预期效果

- dsv4p_nv 504 失败: 180s → 125s (省 55s/失败请求).
- hm4104 (dsv4p_nv primary) 504 surge 时卡顿减半.
- 成功请求 (max 108s < 130) 不受影响.

## 剩余问题 (第 4 轮)

dsv4p_nv 125s 失败后仍触发 peer-fb (25s, HM1 dsv4p 同 504 也失败) → 总 150s. 第 4 轮拟把 dsv4p_nv 加入 NVU_PEER_FB_SKIP_MODELS (HM1 同坏, 省 25s). 但 dsv4p_nv 是间歇性 (SR 40%, 不像 glm5_2_nv 全坏), peer-fb 偶尔可能 rescue — 需数据确认 HM1 dsv4p 当前是否也持续 504 (最近 peer-fb for dsv4p 全 FAILED).

## 回滚

compose 删 `NVU_TIER_BUDGET_DSV4P_NV` 行 + restart (回退全局 180s).

## 跨机协作备注

- R799 纯 env, HM2 已部署. HM1 同 dsv4p_nv 504 问题 (同 NVCF 上游), 远程 CC 可同步加 `NVU_TIER_BUDGET_DSV4P_NV=130`.
- 远程 CC 已有 `R799_hm2_optimize_hm1.md` (NOP), 本 round `R799_hm2_dsv4p_tier_budget_130.md` 区分不冲突.
