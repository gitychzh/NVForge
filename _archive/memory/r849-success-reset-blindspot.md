---
name: r849-success-reset-blindspot
description: "R848盲区根治; record_primary_success在connect成功(HTTP 200 header到达)时就调会重置fail_count=0, 致GLM5.2劣化(connect成功+流到一半静默)时流式failure永远累积不到阈值5, circuit永远不开R848形同虚设; R849移除connect处success调用, 改在stream.py真正流式成功完成(非zombie非interrupted)时才record_primary_success"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# R849: circuit breaker success 重置点错位 (R848 盲区根治)

## 用户报错
`API Error: Server error mid-response. The response above may be incomplete.` — R848 部署后仍卡死.

## 真根因 (R848 盲区)
R848 让流式中途失败调 `record_primary_failure()`, 但 `record_primary_success()` 在 **upstream.py connect 成功(HTTP 200 header 到达)时**就调用, 重置 `fail_count=0`. GLM5.2 劣化模式 = "connect 200 + 流到一半静默":
```
请求A: connect 200 → record_primary_success() → fail_count=0  ← 重置!
        流式中断 → record_primary_failure() → fail_count=1
请求B: connect 200 → record_primary_success() → fail_count=0  ← 又重置!
        流式中断 → record_primary_failure() → fail_count=1
...永远到不了 5, circuit 永远 CLOSED, R848 形同虚设.
```
这就是 R848 部署后 18:48(req=4001ac0b)仍卡死、circuit 没开的根因.

## 修复 R849 (已应用, bind mount 宿主源码)
- `upstream.py` `_try_primary` success 路径: **移除** `record_primary_success()` (connect 成功不再重置).
- `stream.py` `_emit_graceful_end` 正常成功路径(非 zombie/非 interrupted/有 finish_reason): 调 `record_primary_success()`. import 加 `record_primary_success`.
  - 条件: `if metrics.get("upstream_used")=="primary" and not interrupted and not zombie: record_primary_success()`
  - 插入点: `_emit_graceful_end` 内发 `message_stop` 前(stream_to_anth 的, line ~187).
- collect_stream_to_anth (stream=false) 未动 — CC 主要走 stream=true; collect 路径不再 reset(connect 处已移除), 偶发失败能累积, 不影响.

## 修复后语义
- circuit 只在 **流式真正成功完成** 时 reset (不是 connect 成功时).
- connect 成功 + 流式中断 = 不 reset, failure 累积 → 连续 5 次 OPEN → 直走 fallback.
- 真正健康的 primary (流式完成) 正常 reset, 偶发失败不会误开 circuit.

## 待解决 (R850 候选, 未修)
缺陷2: nv_gw idle deadline break 后发 content_filter err_chunk, cc4101 没解析到(走 idle-stall 而非 zombie). req=4001ac0b 时序: nv_gw 18:50:36 发 chunk, cc4101 18:51:24(48s后)才 idle-stall 兜底且无 ZOMBIE-CONTENT-FILTER 日志. R847(IDLE_GAP 60→100s)时序数值对了(100>90)但 chunk 仍丢失, 需加 wire 诊断. 但 R849 让 circuit 即使 chunk 丢失也能累积 failure 开 breaker 绕开 primary, 兜住了卡死.

## 验证
- 语法 OK, 包 import OK, 容器重启正常.
- live 请求 200/54chunks/7.5s 成功, 走 stream_to_anth 正常路径.

## 关联
- [[r848-stream-circuit-breaker-fix]] — R848 流式 failure 记 circuit, R849 修其 success 重置点盲区, 两者配套才有效.
- [[r847-deadline-inversion-root-cause]] — deadline 倒挂修复.
EOF