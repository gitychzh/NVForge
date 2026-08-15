# R1258: OpenClaw 模型链路 BUG 排查与修复

## 日期
2026-08-15 (CST)

## 架构核实结果

用户描述: opclaw4103 → oc45001(primary), dsv4f0731_nv40666(fallback)

**实际链路:**
```
openclaw → opclaw4103 (4103)
  ├─ primary: oc45001 (45001) → opencode.ai/zen/v1 (big-pickle, 免费模型)
  └─ fallback: nv_gw (40006) → NVCF glm5_2_nv       ← 不是 dsv4f0731_nv40666
```

dsv4f0731_nv40666 (40666) 是 hm4104 和 oc4105 的 fallback, 不是 opclaw4103 的。

## 修复内容

### BUG #1: oc_requests.status=0 (已修复, 当前代码已 OK)
- 旧 handlers.py 在成功路径上缺失 `request_row["status"] = 200`
- 导致 pacer.report_ok 永不触发, 429 冷却永不重置
- 状态: 16:14 CST 已修复, 本轮验证 DB 新请求 status=200 ✅

### BUG #2: oc_requests.ttfb_ms 永远为 NULL → 修复
- `_nonstream_passthrough` 和 `_stream_passthrough` 都不设 `request_row["ttfb_ms"]`
- 修复: 在 `_upstream_exchange` 成功路径 (line 275) 同步 `attempt_row.ttfb_ms` → `request_row["ttfb_ms"]`
- 验证: DB 新请求 ttfb_ms 有值 (2377ms, 3087ms, 4518ms) ✅

### BUG #3: docker-compose.yml opclaw4103 注释与实际不符 → 修复
- 注释引用 "ms_gw primary" → 实际 primary 是 oc45001
- 注释引用 "dsv4f0731 全败→glm5_2_nv" → 实际 primary 是 oc45001
- depends_on 引用 ms_gw → 改为 nv_gw (fallback 目标)
- NV_GW_API_KEY 注释语义修正

### BUG #4: 34 个死 IP 浪费请求时间 → 修复
- 64 个 proxy IP 中 34 个 0% 成功率 (全 429)
- 每个死 IP 浪费 1-4 秒, 单请求最多遍历 22 IP
- 修复: 从 OZ_PROXY_LIST 移除 34 死 IP, 保留 29 有效 IP
  - 20 GOOD (100% SR): 7910, 7937, 7939-7945, 7948-7949, 7951-7953, 7955-7956, 7963-7970, 7978
  - 9 MIXED (SR > 40%): 7915(52%), 7919(94%), 7931(50%), 7938(67%), 7942(67%), 7945(67%), 7956(50%)
- 验证: 新请求只尝试保留列表中的 IP ✅

## IP 轮转机制
- 使用 `itertools.count()` 全局原子计数器, 每请求起始 IP = `counter % n`
- 429 时顺序尝试下一个 IP
- **确认: ✅ 按顺序轮流使用**

## dsv4f0731_nv40666 5key 健康度 (24h)

| key | 总请求 | SR | avg_ttfb | 评价 |
|-----|--------|-----|----------|------|
| 0 | 33 | 84.8% | 14.2s | 最差 (5x all_tiers_exhausted) |
| 1 | 24 | 91.7% | 12.6s | TTFB 最快 |
| 2 | 28 | 96.4% | 28.4s | TTFB 最慢 |
| 3 | 27 | 96.3% | 22.1s | 最均衡 (0 次重试) |
| 4 | 23 | 91.3% | 12.8s | TTFB 快 |

所有错误均为 NVCF 后端问题 (529_nv_overloaded, stream_absolute_cap), 非 key 层面可修。

## 改动文件
1. `/opt/cc-infra/proxy/oc-proxy/gateway/handlers.py` — 加 ttfb_ms 同步到 request_row
2. `/opt/cc-infra/proxy/oc-proxy/docker-compose.yml` — 移除 34 死 IP (64→29)
3. `/opt/cc-infra/docker-compose.yml` — opclaw4103 注释/depends_on 清理

## 验证
- oc45001 health: ok ✅
- opclaw4103 health: ok ✅
- smoke test: 200 OK ✅
- DB 新请求: status=200, ttfb_ms 有值 ✅
- IP 列表: 29 个有效 IP 加载 ✅
