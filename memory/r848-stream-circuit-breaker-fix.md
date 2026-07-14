---
name: r848-stream-circuit-breaker-fix
description: "R848 流式中途失败也触发circuit breaker; 旧洞record_primary_failure只在connect/header阶段调,流式失败(stream.py)从不记→NVCF劣化表现为connect成功+流到一半静默时circuit永远CLOSED→CC每次重试打primary每次中断死循环卡死; 修stream.py 7个失败点调_record_primary_stream_fail"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# R848: 流式中途失败触发 circuit breaker (治"卡死中断"死循环)

## 用户诉求
"尽可能让远程CC不能直接卡死中断,除非NV的GLM5.2模型彻底不能用了" — 上游临时劣化不该让CC��死。

## 真根因 (R848)
`record_primary_failure()` 只在 `upstream.py` `_try_primary` 的 **connect/header 阶段失败**(`_UpstreamError`)时调. 但流式中途失败(stall-watcher/zombie/content_filter/idle-deadline/StreamUpstreamDisconnect)全在 `stream.py` 里, **从不调 circuit**.

后果: NVCF 劣化常表现为"connect 成功 + 流到一半静默/空僵尸" → circuit 永远 CLOSED → CC 每次重试都从 primary 开始 → 每次流式中断 → **死循环卡死**. 这就是用户反复看到 `upstream stream interrupted before completion` 持续不退的根因.

## 修复 (已应用, bind mount 宿主源码)
`/opt/cc-infra/proxy/cc4101/gateway/stream.py`:
- 加 `from .circuit import record_primary_failure`
- 加 helper `_record_primary_stream_fail(reason)`: 仅当 `metrics["upstream_used"]=="primary"` 时调 `record_primary_failure()`(fallback 失败不记, 避免误伤 primary).
- 在 7 个流式失败点插调用:
  - zombie_clean_eof
  - upstream_content_filter_malformed
  - upstream_content_filter
  - zombie_empty_completion (stream_to_anth)
  - StreamStallWatcher (stall-watcher 命中)
  - StreamSocketTimeout (真 idle)
  - StreamUpstreamDisconnect (上游主动 FIN/RST)
- `client_gone_*`(客户端自己断) **不记** — 不是上游的错.
- collect_stream_to_anth (stream=false 路径) 未动 — 避免重复记录, 且 CC 主要走 stream=true.

## 机制 (修复后)
流式中断 → `_record_primary_stream_fail` → `record_primary_failure()` → 连续 5 次(`CC4101_PRIMARY_FAIL_THRESHOLD=5`)后 circuit **OPEN** → 后续请求 `is_primary_open()` 返回 True → `execute_request` 跳过 primary **直走 fallback(ms_gw)** → CC 不再卡在劣化 primary 上. 冷却 60s(`CC4101_PRIMARY_SKIP_S`)后 HALF_OPEN 探测 primary, 恢复则 CLOSED.

## 关键安全点
- 只记 primary 失败(`upstream_used=="primary"` 守卫), fallback 失败不记 primary.
- `client_gone` 不记(客户端主动断非上游错).
- success 时 `record_primary_success()` 已在 upstream.py connect 成功调过; 流���中途失败调 failure 会正确抵消那次"假成功".

## 与 R847 协同
- R847 修 deadline 倒挂(IDLE_GAP 60→100s)让 nv_gw content_filter chunk 能被 cc4101 收到.
- R848 修 circuit 不感知流式失败, 让连续劣化时自动绕开 primary 走 fallback.
- 两者互补: R847 治单次中断的信号传递, R848 治持续劣化的死循环.

## 验证
- 语法 OK, 包 import OK, 无循环依赖(circuit 不 import stream).
- 容器重启正常.
- 待观察: NVCF 下次劣化时, 连续 5 次流式失败后应见 `CIRCUIT-STREAM-FAIL` + `PRIMARY-BREAKER-SKIP` 日志, 期间请求走 FALLBACK-OK 不卡.

## 关联
- [[r847-deadline-inversion-root-cause]] — deadline 倒挂修复.
- [[r846-stream-interrupted-fix]] — 三层根因(OSError+total_deadline+malformed).
- [[r845-cc4101-stall-watcher-b2-b5-fix]] — stall-watcher 双门槛.
EOF