# R1266: openclaw "primary 和 fallback 均不可用" 根因修复

## 时间
2026-08-15 19:00 CST

## 症状
opclaw4103 频繁报 `⚠️ primary 和 fallback 均不可用, 请稍后重试.`
- primary (oc45001) 返回 429 (pacer_queue_timeout)
- fallback (dsv4f0731_nv40666) 返回 timeout (70s header timeout 不够)
- 两者均失败 → 错误消息

## 根因分析

### BUG 1: oc45001 MAX_CONCURRENCY=1 (根因)
oc45001 同时服务 3 个 caller: opclaw4103, hm4104, oc4105
- `OZ_MAX_CONCURRENCY=1` → 同时只允许 1 个请求
- 其余 2 个排队等 `OZ_QUEUE_TIMEOUT_S=10s` → 超时返回 429 (code=pacer_queue_timeout)
- opclaw4103 的 `_is_pacer_queue_timeout` 将 429 重分类为 server_5xx → 触发 fallback

**实测验证**: 3 个并发请求 → 1 个 200 (15s), 2 个 429 (10s 超时)

### BUG 2: FALLBACK_HEADER_TIMEOUT=70s 太短
dsv4f0731_nv40666 (NVCF pexec + thinking budget 1024) 单 key TTFB 需 60-120s
- `UPSTREAM_TIMEOUT=120s` (容器内单 key 上游超时)
- `FALLBACK_HEADER_TIMEOUT=70s` (opclaw4103 等待 fallback 首字节)
- 70s < 90s → fallback 尚未拿到 NVCF 响应就被 opclaw4103 kill 掉

dsv4f0731_nv40666 日志显示 empty 200 (NVCF 限流) + key 轮转, 但 70s 内无法完成
任何一次完整 key 尝试 → timeout → "均不可用"

## 修复

### Fix 1: oc45001 pacer 放宽
```
OZ_MAX_CONCURRENCY: 1 → 3   # 3 个 caller 各占 1 slot
OZ_QUEUE_TIMEOUT_S: 10 → 30 # 第 3 个请求需等 2×5=10s, 30s 余量充足
OZ_MIN_INTERVAL_S: 8 → 5    # 29 个出口 IP, 每个 IP 独立限流, 全局间隔可放宽
```

### Fix 2: opclaw4103 timeout 调整
```
PRIMARY_HEADER_TIMEOUT: 90 → 60   # pacer 修复后 queue ≤10s + TTFB ≤30s = 40s, 60s 足够
FALLBACK_HEADER_TIMEOUT: 70 → 100 # NVCF pexec 单 key 需 90-120s, 100s 覆盖 1 次 key 尝试
# 60 + 100 = 160 < 170 PROXY_TIMEOUT ✓
```

### Fix 3: hm4104 + oc4105 同步修复 FALLBACK_HEADER_TIMEOUT
```
hm4104: FALLBACK_HEADER_TIMEOUT 70 → 100
oc4105: FALLBACK_HEADER_TIMEOUT 70 → 100
```

## 验证

### 并发测试 (修复前 vs 修复后)
| 场景 | 修复前 | 修复后 |
|---|---|---|
| 3 并发到 oc45001 | 1×200 + 2×429 | 3×200 (2.8s/10.5s/14.7s) |
| 3 并发到 opclaw4103 | 1×200 + 2×fallback | 3×200 (4.9s/13.6s/18.9s) |

### 健康检查
- opclaw4103: ok ✅
- oc45001: ok (healthy) ✅
- hm4104: ok ✅
- oc4105: ok ✅
- dsv4f0731_nv40666: ok ✅

### 日志确认
opclaw4103 无 PRIMARY-FAIL / FALLBACK-FAIL / "均不可用" 错误

## 影响范围
- 改动容器: oc45001, opclaw4103, hm4104, oc4105
- 未改动: nv_gw (40006), dsv4p_nv40066, cc4101, dsv4f0731_nv40666 (容器本身)
- 不违反铁律: 未碰 ms_gw, 未改 cc2 链路, 只改 openclaw 生态

## 下一步
- 观察 30min 窗口 opclaw4103 日志, 确认 pacer_queue_timeout 消除
- 若 oc45001 上游 (opencode.ai) 仍间歇 429 (free_usage_limit), 考虑增加出口 IP
- dsv4f0731_nv40666 empty 200 问题 (NVCF 限流) 需单独跟踪
