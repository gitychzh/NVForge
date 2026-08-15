# R1257 — oc45001 pacer 信号量泄漏修复

**日期**: 2026-08-15
**容器**: oc45001 (oc-proxy, opencode zen big-pickle 网关)
**改动文件**: `proxy/oc-proxy/gateway/handlers.py`
**备份**: `handlers.py.bak.R1257`

## 问题

hermes (hm4104) 报错:
```
queue timeout: global concurrency gate busy (pacer_queue_timeout)
```

## 根因

`handle_chat_completions()` pacer 超时路径有两个 bug:

### Bug 1: 信号量泄漏 (严重)

`pacer.acquire()` 超时时, 信号量未获取. 但 `finally` 块无条件调用 `pacer.release()`,
导致信号量计数 +1 (从未被 acquire 的 sem 被 release). 每次 pacer 超时, `MAX_CONCURRENCY`
实际值 +1, 逐步瓦解限流:

```
sem = Semaphore(1)
# pacer.acquire() 超时 (sem 未获取)
# finally: pacer.release() → sem 计数 = 2
# 下次: 2 个并发请求可同时获取 sem
# 再次 pacer 超时 → sem 计数 = 3
# ... 直到容器重启
```

实测: 容器 07:06 启动后 3 次 pacer 超时, sem 计数可能已达 3-4, 允许 3-4 并发
(本应 1), 导致上游 opencode zen 429 率升高.

### Bug 2: 双 db.enqueue (轻微)

pacer 超时 `except` 块调用 `db.enqueue(request_row)`, `finally` 块也调用.
`ON CONFLICT (request_id) DO UPDATE` 使第二次覆盖第一次, 无重复行,
但 duration_ms 可能在第一次写入时还是 0 (竞态).

## 修复

1. 新增 `sem_acquired = False` 标志, `pacer.acquire()` 成功后设为 True
2. `finally` 块: `if sem_acquired: pacer.release()` — 防止虚假 release
3. pacer 超时 `except` 块: 删除 `db.enqueue(request_row)`, 统一由 `finally` 入库

## 验证

- `docker compose restart oc45001` → Up (healthy)
- `curl localhost:45001/health` → `{"status":"ok"}`
- 容器内 `grep sem_acquired /app/gateway/handlers.py` 确认 bind-mount 加载
- 待观察: 后续 pacer 超时不再导致并发数膨胀
