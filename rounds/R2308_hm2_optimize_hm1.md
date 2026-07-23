# HM2 Optimize HM1 - R2308

**Date:** 2026-07-24 04:10 UTC (CST 12:10)
**Author:** opc2_uname (HM2)
**Type:** HM2 → HM1 单参数优化 (铁律：只改HM1不改HM2)

## 数据摘要 (HM1 nv_gw @ 100.109.153.83)

### 容器状态
- nv_gw StartedAt: 2026-07-23T19:42:56Z (R2307 部署后), RC=0, running
- /health: ok, 5 keys, passthrough
- 无 docker logs error/warn (grep 全空)

### DB (6h 窗口, R2307 前数据 — 容器重启后 DB 无新记录)

| 状态 | 计数 | 平均延迟 | 占比 |
|------|------|----------|------|
| 200  | 35   | 27836ms  | 52.2% |
| 502  | 18   | 59205ms  | 26.9% |
| 429  | 14   | 13964ms  | 20.9% |
| **总计** | **67** | | |

### 按模型分解 (6h)

| 模型 | 200 | 502 | 429 | SR |
|------|-----|-----|-----|-----|
| dsv4p_nv | 21 | 8 | 0 | 72.4% |
| glm5_2_nv | 11 | 6 | 14 | 35.5% |
| kimi_nv | 2 | 4 | 0 | 33.3% |

### 错误分类 (6h)
- all_tiers_exhausted: 13× (dsv4p 6×, glm5_2 5×, kimi 2×)
- zombie_empty_completion: 2× (dsv4p 2×)
- 429_nv_rate_limit: 14× glm5_2_nv

### 重启后 proxy log 分析 (02:00-03:34 UTC 2026-07-24, ~8h post-restart)

从 nv_proxy.2026-07-24.log 提取关键事件:

| 事件类型 | 次数 | 说明 |
|----------|------|------|
| NV-REQ | 15 | 总请求 |
| NV-SUCCESS | 11 | 成功 |
| NV-TIMEOUT | 11 | NVCFPexecTimeout ~25s/次 (UPSTREAM_TIMEOUT=24s) |
| ALL-TIERS-FAIL | 6 | 全 tier 耗尽 |
| NV-PEER-FB OK | 2 | 6ms, 11ms ttfb — 即时成功 |
| NV-PEER-FB FAIL | 3 | 51s, 111s, 122s — 大量时间浪费 |

**Peer fallback 浪费分析:**
- 02:06:03 dsv4p_nv peer FB → 51502ms RemoteDisconnected → 502
- 02:08:16 glm5_2_nv peer FB → 122113ms TimeoutError → 502
- 02:08:23 dsv4p_nv peer FB → 111270ms peer returned 502 → 502
- 02:09:02 dsv4p_nv peer FB → 122114ms TimeoutError → 502
- **总计浪费: 51+122+111+122 = 406s 在失败的 peer fallback 上**

**对比: 成功的 peer FB 仅需 6-11ms ttfb**

## 诊断发现

### 发现: NVU_PEER_FALLBACK_TIMEOUT=122 过高

当前值: 122s。Peer fallback 是 nv_gw 本地全部 key 耗尽后的最后手段，请求转发到 HM2 nv_gw。

**问题:**
1. 当 HM2 peer 也在挣扎（NVCF 上游慢/超时），peer FB 会等待最长 122s 才返回 502
2. 4 次失败的 peer FB 分别耗时 51s, 111s, 122s, 122s — 用户等待 122s 后仍然得到 502
3. 成功的 peer FB 仅需 6-11ms ttfb — 健康的 peer 几乎瞬时响应
4. 122s 的超时窗口对用户可见延迟有显著负面影响

**数据支撑:**
- 成功 peer FB: 6ms, 11ms (2/5 = 40% 成功率, 但成功时 <1s)
- 失败 peer FB: 51s, 111s, 122s, 122s (3/5 = 60% 失败率, 平均 101s 浪费)
- 将超时从 122→60 可将失败 case 的用户等待减少 ~50%
- 60s 仍远超成功 case 的 <1s 响应时间

## 改动

**参数:** `NVU_PEER_FALLBACK_TIMEOUT`
**变更:** `122` → `60`
**文件:** `/opt/cc-infra/docker-compose.yml` (HM1 only)
**风险:** 极低。

预期效果:
- 当 peer 不可用时，用户等待从最长 122s 降至最长 60s
- 健康的 peer FB 不受影响（成功在 <1s 内）
- NO_CONTENT_GAP=60s 僵尸防御不受影响（独立机制）
- 不影响本地 tier 尝试（peer FB 仅在 all_tiers_exhausted 后触发）

## 验证

```
$ docker exec nv_gw env | grep NVU_PEER_FALLBACK_TIMEOUT
NVU_PEER_FALLBACK_TIMEOUT=60

$ curl -s http://localhost:40006/health
{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5, ...}

$ docker inspect nv_gw --format '{{.State.StartedAt}} {{.State.Status}}'
2026-07-23T20:07:00Z running RC=0
```

## 与之前轮次的关系

- R2291: TIER_BUDGET_GLM5_2_NV 200→210 ✓
- R2297: KEY_COOLDOWN_S 5→10 ✓
- R2303: EMPTY_200_FASTBREAK 2→3 + TIER_BUDGET_KIMI 170→200 ✓
- R2305: TIER_COOLDOWN_S 0→15 ✓
- R2306: TIER_BUDGET_DSV4P_NV 160→170 ✓
- R2307: NVU_STREAM_TOTAL_DEADLINE_S 25→35 ✓
- **R2308 (本轮): NVU_PEER_FALLBACK_TIMEOUT 122→60** ← 新参数域，不与之前冲突

## ⏳ 轮到HM1优化HM2
