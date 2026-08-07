# R1161 — cc2 nv_gw NOP 巡检轮

**日期**: 2026-08-08 03:19 CST
**结论**: NOP（不改码）。cc2 (cc4101-primary) 整窗 90/90 = 100% SR, 0 非-200。
总线 dsv4f0731_nv SR=98.7% (147/149), 唯二 502 均归属 **hermes** 非 cc2、非新类型。
tier 全 pexec_success 0 错误, fallback 0%, buffer 全 attempt-1 direct flush 无退避。跨轮静稳。

## 数据（实查 30min 窗口, 03:19 CST）

### cc2 (cc4101-primary) 专属
```
status | count
-------+-------
 200   |   90        ← SR = 100%, 0 非-200
```

### 30min 链路总览 (caller × status)
```
cc4101-primary|dsv4f0731_nv|200|90         ← cc2, 100% SR
hermes        |dsv4f0731_nv|200|57
hermes        |dsv4f0731_nv|502|2          ← 归属 hermes
```

### 错误分类 (status!=200, caller 归属实查)
```
 caller |   error_type               | status |   fid     | created_at
--------+----------------------------+--------+-----------+------------------
 hermes | NVStream_IncompleteRead    |   502  | 281478d0  | 18:59:58 UTC
 hermes | stream_first_byte_timeout  |   502  | 281478d0  | 19:18:05 UTC
```
- 两条 502 均 **caller=hermes**, 非 cc2 请求。同 fid 281478d0。
- `NVStream_IncompleteRead` = 与 R1160 同时段的 hermes 瞬时 egress 抖动（同类型已观测）。
- `stream_first_byte_timeout` = 新出现但归属 hermes 线瞬时首包超时, 非 cc2、非新根因。
- 无 buffer_exhausted、无 all_tiers_exhausted → 无独立 cc2 事件。

### tier (nv_tier_attempts 30min)
```
   error_type   | count
---------------+-------
 pexec_success |   92     ← 全 pexec_success, 0 429/empty/新类型
```

### buffer / wait 日志（实查）
全 `NV-BUFFER-VERDICT attempt=1 verdict=success_*` direct flush:
```
req=a631260f success_text  content=32c fr=stop  buffered=2578b  elapsed=1655ms
req=81004b35 success_tool_call content=123c tool=True fr=tool_calls buffered=4682b elapsed=14677ms
req=527c8105 success_tool_call content=413c tool=True fr=tool_calls buffered=18084b elapsed=7470ms
```
- 全部 **attempt-1 direct flush**, 无退避、无 WAIT、无 buffer_exhausted。
- 部分带 thinking + tool_calls 均正常, 无 zombie。

### fallback
30min fallback = **0 触发**（151 请求全 200 直通, 无 fallback_triggered）。

### 容器健康
nv_gw OK / cc4101 OK; nv_gw Up 24h, cc4101 Up 23h(未重启)。fid 281478d0-f307 稳定。

## 结论
cc2 整窗 90/90 全 200。唯二 502 实查 JOIN 归属 **hermes**（瞬时 IncompleteRead + 首次包
timeout 各 1）, 非 cc2、非新根因、非配置漂移。tier 全 pexec_success。跨轮静稳, **无改码条件**。

## 下一步
维持静稳观察。核心看独立 burst 复发间隔。若后续窗口再现 ≥2× buffer_exhausted 且
request_id 全新、JOIN 归属 cc2, 则按记忆 `ssleof-error-transient-egress-blip` 深挖
dsv4f0731_nv egress 线路 (mihomo 7900-7904)。当前仍瞬时 egress 抖动, NOP。