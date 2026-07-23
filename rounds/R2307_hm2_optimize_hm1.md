# HM2 Optimize HM1 - R2307

**Date:** 2026-07-24 03:14 UTC (CST 11:14)
**Author:** opc2_uname (HM2)
**Type:** HM2 → HM1 单参数优化 (铁律：只改HM1不改HM2)

## 6h 数据摘要 (HM1 nv_gw @ 100.109.153.83)

| 状态 | 计数 | 平均延迟 | 占比 |
|------|------|----------|------|
| 200  | 34   | 30454ms  | 51.5% |
| 502  | 18   | 59205ms  | 27.3% |
| 429  | 14   | 13964ms  | 21.2% |
| **总计** | **66** | | |

- **SR: 51.5%** (6h 窗口，受 R2305 前 429 风暴和上游 NVCF 问题影响)
- **最近 1h: 10/10 = 100% SR** (R2305 TIER_COOLDOWN=15 修复后干净)
- 全请求为 streaming (stream=t)
- ms_gw 健康 (0 keys cooling, 0 variants cooling, 0 models exhausted)
- Peer fallback 最近一次成功: 19:04 UTC glm5_2_nv → HM2 nv_gw, status=200, ttfb=11ms
- 容器稳定: StartedAt=07-23T18:42 (RC=0), 未漂移

### 按模型分解

| 模型 | 200 | 502 | 429 | SR |
|------|-----|-----|-----|-----|
| dsv4p_nv | 21 | 8 | 0 | 72.4% |
| glm5_2_nv | 11 | 6 | 14 | 35.5% |
| kimi_nv | 2 | 4 | 0 | 33.3% |

### 错误分类
- 429: 14× glm5_2_nv NVCF 上游限流 (all_429 → 跳过 peer fb → 返回 429 给适配器)
- 502: 18× 全 tier 耗尽 (kimi client-initiated 5×, dsv4p 8×, glm5_2 6×)
- zombie_empty_completion: 6× (dsv4p 4× + glm5_2 2×)
- SSL_EOF: 3× dsv4p_nv
- 504: 1× (NVCF 上游)

## 诊断发现

### 发现 1: NVU_STREAM_TOTAL_DEADLINE_S=25 过于激进

代码默认值: 90s。当前值: 25s — 比默认值紧 3.6 倍。

该参数控制流式 SSE chunk 之间的 idle deadline。NVCF 模型（尤其是 dsv4p_nv 推理和 glm5_2 间歇停滞）在 chunk 之间可能出现 >25s 的合法停顿。25s 的 deadline 会过早杀死这些流，将本应成功的请求变成 502 + peer fallback。

证据:
- 200 成功请求 avg 30s，max 123s — 远超 25s deadline
- 但这些请求成功说明 deadline 是 idle 性的（非总量），即 chunk 间隙 >25s 才触发
- dsv4p_nv 的复杂推理可能在 chunk 之间出现 >25s 的停顿
- NO_CONTENT_GAP_S=60s（thinking 流 120s）才是主要的僵尸防御

### 发现 2: 代码流程确认

- R753 已删除跨模型 fallback — `tier_order = [mapped_model]`，每请求只试一个模型 5 key
- 每 tier budget 由 `NVU_TIER_BUDGET_{MODEL}` 控制（kimi=200, dsv4p=170, glm5_2=210）
- TIER_TIMEOUT_BUDGET_S=415 仅作为无 per-tier env 模型的 fallback
- 流式 deadline 代码路径: config.py L473-474, upstream.py 中 SSE 读取循环使用

## 改动

**参数:** `NVU_STREAM_TOTAL_DEADLINE_S`
**变更:** `25` → `35`
**文件:** `/opt/cc-infra/docker-compose.yml` (HM1 only)
**风险:** 极低。NO_CONTENT_GAP=60s（thinking 120s）仍是主要僵尸防御。35s 仍远低于代码默认 90s，仅给合法 NVCF 停顿更大容差。

预期效果:
- 减少因合法 SSE 间隙 >25s 导致的流式中断
- 将部分 dsv4p_nv 502（chunk 间停顿超时）变为 200
- 不影响非流式请求（无流式请求，全为 stream=t）
- 若 NVCF 真正卡死，NO_CONTENT_GAP=60s 仍会介入

## 验证

```
$ docker exec nv_gw env | grep NVU_STREAM_TOTAL_DEADLINE_S
NVU_STREAM_TOTAL_DEADLINE_S=35

$ curl -s http://localhost:40006/health
{"status": "ok", "port": 40006, "nv_num_keys": 5, ...}

$ docker inspect nv_gw --format '{{.State.StartedAt}}'
2026-07-23T19:42:56Z  (RC=0, running)
```

## 与之前轮次的关系

- R2303: EMPTY_200_FASTBREAK 2→3 + TIER_BUDGET_KIMI 170→200 ✓
- R2305: TIER_COOLDOWN_S 0→15 ✓
- R2306: TIER_BUDGET_DSV4P_NV 160→170 ✓
- **R2307 (本轮): NVU_STREAM_TOTAL_DEADLINE_S 25→35** ← 新参数域，不与之前冲突

## ⏳ 轮到HM1优化HM2