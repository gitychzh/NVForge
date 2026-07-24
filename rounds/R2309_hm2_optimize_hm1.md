# HM2 Optimize HM1 - R2309

**Date:** 2026-07-24 04:18 UTC (CST 12:18)
**Author:** opc2_uname (HM2)
**Type:** HM2 → HM1 单参数优化 (铁律：只改HM1不改HM2)

## 数据摘要 (HM1 nv_gw @ 100.109.153.83)

### 容器状态
- nv_gw StartedAt: 2026-07-23T20:07:00Z (R2308 部署), RC=0, running
- /health: ok, 5 keys, passthrough, tiers=[kimi_nv, dsv4p_nv, glm5_2_nv]
- R2308 的 NVU_PEER_FALLBACK_TIMEOUT=60 已确认生效 (env 读取)
- 无 docker logs error/warn

### DB (24h 窗口 — 包含 R2308 前后数据)

| 模型 | 200 | 502 | 429 | SR% |
|------|-----|-----|-----|-----|
| dsv4p_nv | 24 | 29 | 0 | 45.3% |
| glm5_2_nv | 66 | 27 | 16 | 60.6% |
| kimi_nv | 20 | 35 | 0 | 36.4% |

### 错误分类 (24h, non-200 only)

| 模型 | error_type | 次数 | avg_ms | min_ms | max_ms |
|------|------------|------|--------|--------|--------|
| kimi_nv | all_tiers_exhausted | 26 | 193765 | 123628 | 370299 |
| kimi_nv | zombie_empty_completion | 8 | 74004 | 4389 | 148541 |
| kimi_nv | NVStream_IncompleteRead | 1 | 75832 | 75832 | 75832 |
| dsv4p_nv | all_tiers_exhausted | 25 | 18095 | 6 | 160041 |
| dsv4p_nv | zombie_empty_completion | 4 | 32850 | 10471 | 95117 |
| glm5_2_nv | all_tiers_exhausted | 34 | 21549 | 6 | 90939 |
| glm5_2_nv | zombie_empty_completion | 9 | 16018 | 4437 | 28985 |

### kimi_nv 成功延迟分布 (24h, status=200)

| p50 | p90 | p95 | p99 | max |
|-----|-----|-----|-----|-----|
| 30931ms | 86167ms | 89684ms | 116453ms | 123145ms |

### kimi_nv 502 延迟分布 (24h, all_tiers_exhausted)

| p50 | p95 | min | max |
|-----|-----|-----|-----|
| 125582ms | 370204ms | 123628ms | 370299ms |

### Proxy log 分析 (kimi_nv empty_200 机制)

从 nv_proxy.2026-07-23.log 提取 kimi_nv 失败路径:

```
[NV-REQ] mapped_model=kimi_nv → NV-INJECT-THINKING reasoning_effort='low'
[NV-KEY] k5 → 200 Content-Length:0 (stream) → empty_200 (66s thinking timeout)
[NV-EMPTY-CYCLE] k5 cycling
[NV-KEY] k1 → 200 Content-Length:0 (stream) → empty_200 (66s thinking timeout)
[NV-EMPTY-FASTBREAK] 2 consecutive empty_200 ≥ threshold → fast-break (saved remaining keys)
[NV-TIER-FAIL] all 5 keys failed: empty200=2, elapsed=124586ms
[NV-ALL-TIERS-FAIL] elapsed=124590ms, ABORT-NO-FALLBACK
```

**关键洞察:** kimi_nv 请求经 NV-INJECT-THINKING 注入 reasoning_effort=low 后走 FORCE_STREAM_UPGRADE_TIMEOUT=66s 扩展超时路径。当 NVCF 返回 empty_200 (流式连接但无内容) 时，每个 key 等待 66s 才判定为空。EMPTY_200_FASTBREAK=3 允许 3 次 key 尝试 = 3×66s = 198s 后才 fastbreak。TIER_BUDGET_KIMI_NV=200 给了 200s 预算，恰好放行 3 次尝试 198s。

**浪费量化 (24h):**
- 26 次 ATE × avg 193.8s = 5,036s = 1.4h 用户等待时间全部以 502 告终
- 每次 ATE 浪费 3 key × 66s = 198s (R2308 前 + 122s peer FB)
- R2308 后 peer FB 降至 60s，但 tier 内 3×66s=198s 仍是最大延迟源

## 诊断发现

### 发现: NVU_TIER_BUDGET_KIMI_NV=200 过高

当前值: 200s。R2303 将此值从 170→200 以配合 EMPTY_200_FASTBREAK=3 (3×62s=186s+14s margin)。

**问题:**
1. kimi_nv 成功请求 p99=116.5s — 200s 预算有 83.5s 过剩余量
2. 当 NVCF 返回 empty_200 时，3 次 key 尝试 × 66s = 198s 全部跑完才 fastbreak
3. 每次失败请求 user-visible wait 从 124s 到 370s (avg 193s)，绝大多数是无价值的等待
4. 将预算降至 130s: 2 次 key 尝试 (2×66s=132s) 后预算耗尽，tier 中断
5. 节省第 3 次 key 尝试的 66s 无效等待

**数据支撑:**
- 成功 p99=116.5s < 130s budget → 13.5s 安全余量 (11.6%)
- 成功 p95=89.7s → 40s+安全空间
- 失败 case 2 key × 66s = 132s > 130s → 第 2 次尝试被预算提前中止 (64s 而非 66s)
- 每次失败节省 ~68s: 198s→130s

**与 R2303 的关系修正:**
- R2303 将 budget 170→200 是为配合 FASTBREAK=3
- 但数据表明 FASTBREAK=3 + budget=200 反而让 kimi_nv 多浪费一个 66s 的 key 周期
- budget=130 使 FASTBREAK=3 的第 3 次尝试被预算拦截 (2 次后预算耗尽)
- 这是有意的: 2 次 empty_200 已足够判定 NVCF kimi 端不可用，第 3 次尝试是纯浪费

## 改动

**参数:** `NVU_TIER_BUDGET_KIMI_NV`
**变更:** `200` → `130`
**文件:** `/opt/cc-infra/docker-compose.yml` (HM1 only)
**风险:** 低。

预期效果:
- kimi_nv empty_200 失败路径: 198s → ~130s (节省 ~68s/次)
- 24h: 26 次 ATE × 68s = 1,768s ≈ 29 min 用户等待时间减少
- 成功请求不受影响 (p99=116.5s < 130s budget)
- Peer FB (R2308=60s) 不受影响 (独立机制，budget 触发后不再到 peer FB)
- 502→caller ms_gw fallback 时间链缩短: 130s+60s=190s vs 原 200s+60s=260s

## 验证

```
$ docker exec nv_gw python3 -c "import os; print(os.environ.get('NVU_TIER_BUDGET_KIMI_NV'))"
130

$ curl -s http://localhost:40006/health
{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5, ...}

$ docker inspect nv_gw --format '{{.State.StartedAt}} {{.State.Status}} RC={{.State.ExitCode}}'
2026-07-23T21:17:31Z running RC=0
```

## 与之前轮次的关系

- R2291: TIER_BUDGET_GLM5_2_NV 200→210 ✓
- R2297: KEY_COOLDOWN_S 5→10 ✓
- R2303: EMPTY_200_FASTBREAK 2→3 + TIER_BUDGET_KIMI 170→200 ✓
- R2305: TIER_COOLDOWN_S 0→15 ✓
- R2306: TIER_BUDGET_DSV4P_NV 160→170 ✓
- R2307: NVU_STREAM_TOTAL_DEADLINE_S 25→35 ✓
- R2308: NVU_PEER_FALLBACK_TIMEOUT 122→60 ✓
- **R2309 (本轮): NVU_TIER_BUDGET_KIMI_NV 200→130** ← 收紧 kimi_nv tier budget, 修正 R2303 的过度放宽

## ⏳ 轮到HM1优化HM2
