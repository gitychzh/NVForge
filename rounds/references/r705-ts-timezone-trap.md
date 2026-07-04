# R705: DB `ts` 列时区陷阱 — CST/UTC 偏移 8h

> **教训**: R705 数据收集阶段发现 `nv_requests.ts` 列存在 CST/UTC 时区偏移，导致基于 `ts` 的查询包含跨时区边界数据。

## 问题描述

`nv_requests.ts` 列类型为 `timestamptz`（带时区的时间戳），但写入时使用了 Asia/Shanghai (UTC+8) 时间，却标记为 `+00`（UTC 零时区）。

| 列 | 实际存储内容 | 示例 |
|----|-------------|------|
| `ts` | CST 时间标记为 `+00` | `2026-07-05 03:33:20+00` = 实际 UTC 2026-07-04 19:33 |
| `created_at` | 正确 UTC 时间 | `2026-07-04 19:33:11+00` ✓ |

## 影响

- 使用 `ts >= now() - interval '6 hours'` 查询时，实际覆盖了 ~14 小时的数据（6h 前 CST + 8h 偏移）
- 使用 `ts >= '2026-07-04 19:23:45+00'` 查询时，实际过滤的是 CST 19:23 = UTC 11:23，导致大量部署前数据混入
- 历史轮次（R704 及之前）使用 `ts` 的查询结果可能包含跨时区边界数据，但整体趋势判断不受影响

## 验证

```sql
-- 对比同一请求的 ts 和 created_at
SELECT ts, created_at, request_id
FROM nv_requests
WHERE created_at >= '2026-07-04 19:23:45+00'
ORDER BY created_at DESC LIMIT 3;
```

结果：
```
ts                              | created_at
2026-07-05 03:56:52.502542+00   | 2026-07-04 19:57:09.418176+00
2026-07-05 03:54:56.961325+00   | 2026-07-04 19:55:27.105331+00
2026-07-05 03:53:25.082737+00   | 2026-07-04 19:53:55.362399+00
```

`ts` 始终比 `created_at` 早 8 小时（CST = UTC+8）。

## 修复建议

**所有后续轮次查询使用 `created_at` 过滤，而非 `ts`：**

```sql
-- ✅ 正确
SELECT ... FROM nv_requests WHERE created_at >= now() - interval '6 hours';

-- ❌ 错误（会包含跨时区数据）
SELECT ... FROM nv_requests WHERE ts >= now() - interval '6 hours';
```

同样适用于 `nv_tier_attempts` 表。

## 根本原因

网关代码中 `_log_metrics` 函数写入 `ts` 时可能使用了 `datetime.now()`（本地时间）而非 `datetime.utcnow()`（UTC 时间），导致 CST 时间被标记为 UTC 时区存储。此为代码层面问题，影响范围仅限 `ts` 列，`created_at` 由 PostgreSQL `DEFAULT now()` 生成，时间正确。