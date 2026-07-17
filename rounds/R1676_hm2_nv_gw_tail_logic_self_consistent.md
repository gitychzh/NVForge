# R1676: HM2 nv_gw 收尾逻辑自洽 — 去掉 _r1627_should_emit_cf 的 `or buffer_chunks is None` 析取项

> 铁律遵守: 改前有数据(DB 3h 失败分布 + 代码静态分析) / 改后有验证(AST + restart + md5 + grep) / 聚焦 nv_gw / 写入仓库.
> 破例改 HM2: 沿用 R1672~R1697 既定方向 (HM2 是 nv_gw 优化主战场, HM1 镜像滞后), 不动 HM1.

## 背景与真根因

远程 CC 反复报 `API Error: Server error mid-response`, R1672~R1697 改了 5+ 轮仍复发. 本轮深挖发现
**两个叠加的真因**, 其中一个是结构性的、一个是运维性的:

### 真因 1 (运维性, 首要): bind-mount 改 .py 不重启 = 没改

`/opt/cc-infra/proxy/nv-gw/gateway/` bind-mount 到容器 `/app/gateway`. 改 .py 后容器内文件确实变
(md5 一致), `__pycache__` 自动重编译, **但 Python 进程只在启动时 import 一次, 已加载的 module
对象不会重新加载**. R1675/R1695/R1696 的磁盘改动在 10:36 容器启动后陆续写入, 但未 restart,
进程内存仍跑 10:36 启动时的旧版.

铁证:
- 磁盘 grep `is_ms_fallback_open` = 0 (R1696 已删), 可进程 18:34 仍报
  `line 327 NameError: name 'nv_breaker' is not defined` — 内存 != 磁盘.
- DB 3h: big_input breaker 0 次 OPEN, 0 次 ms_fallback, 而 8 条 360607c 大 input hang
  (`stream_total_deadline`) + 13 条中等 input `stream_no_content_gap` 按磁盘代码 (handlers.py:1589
  公共块 + upstream.py:1751) 都该喂 breaker. 0 次触发 = 喂 breaker 的代码不在内存里.

→ 这是"改了 5 轮仍稳不住"的首因: 每轮 commit 后测试请求要么走旧内存、要么恰逢重启窗口假性通过,
下一轮写新代码覆盖却仍不 restart, 恶性循环.

### 真因 2 (结构性, 治 mid-response 主体): 收尾判定与 buffer 模式不自洽

R1675 关 `NVU_STREAM_FULL_BUFFER=0` 后, `buffer_chunks` 恒为 `None`. handlers.py:1540 原判定:

```python
_r1627_should_emit_cf = (zombie_detected or metrics.get("error_type")) \
    and (not _r1627_flushed_downstream) \
    and (passthrough_content_chars == 0 or buffer_chunks is None)
```

析取项 `or buffer_chunks is None` 在 FULL_BUFFER=0 下恒真, 整条化简成"几乎所有失败都命中" →
**所有失败 (无论下游有没有已 flush 真内容) 统统走 content_filter 注入分支**, 而下面 Scenario B
(已有内容时只发 `[DONE]`+`connection.close()` 让下游自然收尾) 的 `else` 块**永远走不进去**.

这重新打开了 R1413 当年专门修过的"在已输出中途塞 error → mid-response":
- NVCF glm5.2 流式吐少量真 content (101c "是你" / 1444c / 1603c / 220c) 后 60s 静默 stall.
- nv_gw `NV-NO-CONTENT-GAP` (60s 无真内容) 命中 → break.
- 此时 FULL_BUFFER=0 已把那点真 content 实时 flush 给 cc4101 了.
- 旧判定仍注入 `content_filter` error chunk → cc4101 收到"中途 content_filter" → 判
  `ZOMBIE-CONTENT-FILTER mid-flight` → emit api_error → CC `Server error mid-response`.

→ 中等 input 的 content_filter 失败 (不喂 big_input_breaker, 因 input 不过 250k 阈值, 设计如此)
  的 mid-response 主体, 根因在此收尾判定, 不在 breaker.

## 改前数据 (HM2 hermes_logs, 2026-07-17 16:00~19:06 CST, 改前 3h)

| error_type | count | avg_s | input 范围 | 性质 |
|---|---|---|---|---|
| stream_no_content_gap | 13 | 162.9 | 60k~343k | NVCF 吐部分内容后 60s 静默 → 注 content_filter → **mid-response 主体** |
| stream_first_byte_timeout | 9 | 72.2 | ~353k | 200-then-hang |
| stream_total_deadline | 8 | 147.7 | **360607** (同一大 ctx 反复) | NVCF 超大 input 真 hang 到 180s |
| all_tiers_exhausted | 2 | 70.2 | 117k | 全 key 失败 |
| zombie_empty_completion | 1 | 3.3 | 121k | stop 但 content<50c |

- 全部 `caller=cc4101-primary`, 全部 `model=glm5_2_nv` (CC 自身请求).
- `fallback_occurred` 全 false, `fallback_to` 全空 (45 条无一条触发 fallback).
- big_input_breaker 0 次 OPEN, ms_fallback 0 次 (真因 1: 代码没进内存).
- cc4101 日志 18:58 / 19:06 两次完整 mid-response 链: `recv-fallback got 93b tail=content_filter` →
  `ZOMBIE-CONTENT-FILTER mid-flight` → `api_error`. 93b 正是 handlers.py:1543 注入的 err_chunk 逐字节.

## 改动 (两步)

### 步 A: restart nv_gw (治真因 1, 零代码改动)

```bash
cd /opt/cc-infra && docker compose restart nv_gw   # 非 up -d (后者配置未变跳过报 Running)
```

- StartedAt: 10:36:34Z → 11:31:41Z (R1676 最终重启时刻; 中间 11:23:52 为首次 restart).
- 启动日志干净: `[NV-PROXY] Listening on 0.0.0.0:40006`, 无 NameError.
- 容器内 md5 = 宿主 = `0dbefb3...` (含 R1696 + R1676).
- 让磁盘上 R1675/R1695/R1696 真正进进程内存: big_input breaker 公共块 (handlers.py:1589) +
  upstream.py:1751 喂入点 + NameError 修复, 全部生效.

### 步 B: handlers.py:1540 去掉析取项 (治真因 2, 治 mid-response 主体)

原:
```python
_r1627_should_emit_cf = (...) and (not _r1627_flushed_downstream) and (passthrough_content_chars == 0 or buffer_chunks is None)
```
改后:
```python
_r1627_should_emit_cf = (...) and (not _r1627_flushed_downstream) and (passthrough_content_chars == 0)
```

恢复 R1410 单一判定: 仅零内容 (`passthrough_content_chars==0`) 才注入 content_filter 走重试;
已 flush 真内容的失败走 else 路径 B 发 `[DONE]`+`self.connection.close()` 强制 FIN, cc4101 读到
`[DONE]+EOF` 走 `_emit_graceful_end` 把已输出内容当完整响应收尾 (end_turn), 不再中途插 error.

- 备份: `handlers.py.bak.R1676` (md5 c949eed3, 原文件).
- AST parse OK (容器内 py3.12).
- md5: c949eed3 → 0dbefb3.
- 改后 restart 生效, 容器内 grep `R1676` 注释 = 1, 旧 `or buffer_chunks is None` 仅剩注释文字.

## 预期效果

1. 中等 input (不过 250k) 的 `stream_no_content_gap` 失败不再注入 content_filter → cc4101 不再判
   mid-flight zombie → 不再 emit api_error → CC 不再 mid-response. 失败时 CC 收到已 flush 的部分
   内容 + 干净 `[DONE]` 收尾 (end_turn), 比中途弹 error 可接受.
2. 步 A 让 big_input breaker 真正生效: 360607c 大 input hang 连续失败 → 喂 breaker → OPEN
   (FAIL_N=1) → 走 ms_gw (glm5_2_ms) fallback. 8 条 360607 死循环类应被接住.
3. NameError 崩溃 (dsv4p_nv 路径) 消除.

## 验证清单 (待 CC 打够请求后, 目标 30~60min 窗口)

- [ ] nv_gw 日志: 中等 input `stream_no_content_gap` 失败出现 `NV-STREAM-DONE-FLUSH` (路径 B 收尾),
      而非 `NV-UPSTREAM-ERROR-CHUNK` (注入 content_filter). 两者此消彼长 = R1676 步 B 生效.
- [ ] cc4101 日志: `ZOMBIE-CONTENT-FILTER mid-flight` + `api_error` 频率显著下降.
- [ ] big_input_breaker: `NV-BIGINPUT-FAIL` 出现 → 累计 FAIL_N=1 → `NV-BIGINPUT-FB-OPEN` →
      `ms_fallback` 触发 (步 A 生效). DB `fallback_occurred=true` / `fallback_to=glm5_2_ms` 非零.
- [ ] nv_gw 无 `NameError` / `Traceback`.
- [ ] DB 成功率上升, mid-response (cc4101 api_error) 下降.
- [ ] 若 30min 内 CC 仍报 mid-response: 取该请求 nv_gw 日志, 看 `passthrough_content_chars` 值 —
      若 >0 却仍走 ERROR-CHUNK, 说明路径 B 的 `else` if 条件 (`passthrough_content_chars > 0 and
      not (buffer_chunks is None and NVU_STREAM_FULL_BUFFER)`) 在 FULL_BUFFER=0 下有同类析取 bug,
      需 R1677 续修.

## 未尽事项

- HM1 代码同步滞后 (本地仓库仅到 R1672 快照, HM1 nv_gw 可能仍跑更早版本). 步 B 改动需择期
  同步到 HM1 `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py` + restart, 但 HM1 非 nv_gw 优化
  主战场, 优先级低.
- 步 B 只治"已 flush 内容"的 mid-response. 零内容路径 A 仍走 content_filter 注入 (设计如此,
  触发重试), 若 NVCF 对零内容也频繁 content_filter, 那是另一类 (R1673 big_input_breaker + 步 A
  生效后应被 ms fallback 接走).
