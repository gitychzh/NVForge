# R845: HM2→HM1 — 修复 metrics gap (logger.py 静默吞异常 + db worker 自愈)

**Date**: 2026-07-08 11:45 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (100.109.153.83) nv_gw
**Type**: CODE FIX (gateway/*.py, bind-mount, restart only)

---

## 改前数据 (铁律1)

### 症状: metrics 入库自 02:33 UTC 起中断 8h

| 指标 | 值 | 来源 |
|------|-----|------|
| `nv_requests` DB 最新 ts | 2026-07-08 02:33:34 UTC | `select max(ts)` |
| `nv_requests` last_10min | 0 | DB |
| `nv_metrics.2026-07-08.jsonl` 最新 | 03:33:44 UTC (80行) | grep timestamp |
| `nv_metrics` 按小时 | 00时5 / 01时6 / 02时7 / 03时6, 03:33:44 后无 | grep |
| proxy log (`nv_proxy.2026-07-08.log`) | 正常记录到 11:33+ (NV-SUCCESS 频频) | tail |
| container health | ok (Up 3h) | curl /health |
| docker logs [NV-DB]/traceback | **0 条** (since 6h) | docker logs grep |
| DB 连通 (psycopg2) | OK | docker exec python |
| 03:36 重启 | **未恢复** metrics gap | 时序对比 |

### 决定性证据: worker 线程状态 (docker exec nv_gw python)

```
DB_ENABLED: True  _HAS_PSYCOPG: True
worker_thread: <Thread(hm-db-writer, started daemon ...)>
worker alive: True
queue size: 0          ← 关键: 队列空
_conn: None
```

### 根因链

1. worker 线程 **alive=True**, **queue size=0** → worker 一直空转
   (`_queue.get(timeout=2)` 永远 `queue.Empty` → `continue`), 无 flush 无失败无打印.
2. queue 空 = **`enqueue_metrics` 从未被调用** = `_log_metrics` 自 03:33:44 后
   **整体不再被调用** (JSONL 同步停在 03:33:44 佐证).
3. `_log_metrics` 不被调用 + `logger.py` 两个 `except Exception: pass` 完全静默
   → 问题 100% 不可见, 违反铁律1 (改前必有数据).
4. 02:33:34-03:33:44 这1h: JSONL 继续写 (6条) 但 DB 停 → enqueue 路径先失效
   (worker 不消费 / enqueue 未入队); 03:33:44 后 `_log_metrics` 整体停止.
5. 03:36 重启未恢复 → 运行时状态损坏 + 静默吞异常共同致因, 非纯连接问题.

> 注: `_log_metrics` 在 03:33:44 后不再被调用的**确切运行时触发点**靠当前
> 静默代码无法继续推断 (无打印无 traceback). R845 用"加可见性 + worker 自愈
> + 重启重置运行时状态"组合拳: 重启恢复调用, 新打印暴露任何复发.

---

## 改动 (4 编辑点, 2 文件, ≤5)

### 1. `gateway/logger.py` — `_log_metrics` 两个 `except Exception: pass` → 打印错误

```python
# JSONL try (原 pass):
except Exception as e:
    print(f"[METRICS-ERR] jsonl write failed rid={rid}: {e!r}", flush=True)
# enqueue try (原 pass):
except Exception as e:
    print(f"[METRICS-ERR] db enqueue failed rid={rid}: {e!r}", flush=True)
```
新增 `rid = entry.get("request_id")` 便于关联. 让 JSONL 写入失败 / enqueue 失败
从此可见 (进 docker stdout, `docker logs nv_gw` 可查).

### 2. `gateway/db.py` — `_worker_loop` 的 `_flush_batch(batch)` 包 try/except

```python
try:
    _flush_batch(batch)
except Exception as e:
    print(f"[NV-DB-WORKER] flush crashed (worker survived): {e!r}", flush=True)
```
`_flush_batch` 自带内部 try/except, 但若任何异常逃逸 → daemon worker 死亡 →
所有 DB 写入静默停止. 双保险: 线程不再被单次 flush 异常杀死.

### 3. `gateway/db.py` — `enqueue_metrics` 加 worker 自愈

```python
if _worker_thread is None or not _worker_thread.is_alive():
    try:
        start_worker()
    except Exception as e:
        print(f"[NV-DB] worker self-heal restart failed: {e!r}", flush=True)
```
worker 若死亡, 下次 `enqueue_metrics` 自动重启, 无需容器重启.

---

## 备份

- `gateway/logger.py.bak.R845`
- `gateway/db.py.bak.R845`

## 部署

```bash
scp -P 222 logger.py db.py → HM1 /opt/cc-infra/proxy/nv-gw/gateway/
docker restart nv_gw   # bind-mount, 无需 rebuild
```

## 改后验证 (铁律2)

| 检查 | 结果 |
|------|------|
| `curl /health` | ok (Up 15s healthy) |
| worker alive | True, q=0 |
| 启动 error/traceback | 0 |
| 语法 | ast.parse OK |

### 待验证 (重启后需真实请求触发 metrics)
- 下一次 openclaw 请求 (~30min 周期) 后: `nv_metrics.jsonl` 有新行 + `nv_requests` DB 有新 ts.
- 若仍失败: `docker logs nv_gw | grep METRICS-ERR` 将暴露真因 (jsonl 或 enqueue 的具体异常).
- R846 将基于恢复后的新鲜数据分析瓶颈.

---

## 预期效果

- **即时**: 重启重置运行时状态, 恢复 `_log_metrics` 调用 → metrics JSONL+DB 恢复写入.
- **长期**: 任何未来 metrics 写入失败不再静默 (METRICS-ERR 打印); worker 不再因
  单次异常永久死亡 (自愈); 即使真因复发也可观测定位, 不再 8h 盲区.

## 回滚预案

```bash
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra/proxy/nv-gw/gateway && \
  cp logger.py.bak.R845 logger.py && cp db.py.bak.R845 db.py && \
  docker restart nv_gw'
```
