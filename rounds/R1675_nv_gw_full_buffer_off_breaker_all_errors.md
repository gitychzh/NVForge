# R1675: 关 FULL_BUFFER + breaker 记所有 error_type (框架层根治"成功响应被吞")

**状态**: 已部署 HM2, 验证 283k stream 实时收内容. 只改 HM2 (R1648 系列豁免铁律).
**提交**: (本轮 commit)

## 背景 (R1674 后 CC 又卡, 系统性深挖)

R1673/R1674 部署后, 用户报告 CC 又卡住, 要求框架层解决. 深挖 18:15-18:17 真实复现,
发现 **R1627 FULL_BUFFER 全量缓冲模式的架构假设错了** ——

### 系统性根因: FULL_BUFFER 把"NVCF 发部分内容后挂住不发[DONE]"误判为卡死, 丢弃已生成的真实答案

`NVU_STREAM_FULL_BUFFER` (R1627, 默认 True): nv_gw 把 NVCF 整个 SSE 流**全量缓冲**到内存,
**等流正常结束(收到 [DONE]/EOF)才一次性 flush 给 cc4101**. 设计意图"防 mid-response 卡死"——
NVCF 中途挂了则丢弃缓冲, 下游收到零内容(content_filter)→ CC 自动重试.

**假设错的**: NVCF glm5.2 对大 input(~290k)的**实际失败模式**不是"200 头不发首字节"(那被 first-byte
deadline 45s 砍), 而是 **"发部分真实内容后挂住不发 [DONE]"**. 此时:
- buffer 里**已有用户真实答案** (passthrough_content_chars > 0)
- 但 NVCF 不发 [DONE]/EOF, nv_gw read 循环不退出, FULL_BUFFER 不 flush
- 直到 idle deadline 90s 触发 → `error_type=stream_total_deadline` → flush 跳过 (L1508 条件
  `not error_type` 失败) → **buffer 被丢弃, 已生成答案扔了**
- cc4101 收到零内容 content_filter → CC 重试同一个 290k → NVCF 又挂 → 死循环

**实测证据** (18:15-18:17):
```
18:15:21.9 NV-GLM52-SUCCESS k3 succeeded     ← NVCF 成功开始返回流
            (99秒静默, buffer 攒着不 flush)
18:17:00.6 NV-STREAM-DEADLINE idle 90s exceeded, breaking (SSE keep-alive stall)
18:17:00.6 NV-UPSTREAM-ERROR-CHUNK content_filter  ← 丢弃 buffer, 发 error
18:17:01.7 CC 重试(又发同一个大请求)
```
`NV-GLM52-SUCCESS` 后**无 `NV-STREAM-BUFFER-FLUSH`** —— 成功响应被吞.

### R1673 breaker 为什么没救住
R1673 record 只在 `zombie_detected=True` 时记 (handlers L1561). 但 18:17 失败是
`stream_total_deadline` (idle 90s, **非 zombie**, zombie_detected=False) → **漏记 → breaker 永不 OPEN
→ ms fallback 永不触发**. R1673 只覆盖了 zombie 路径, 漏了 idle deadline 主路径.

## 改动 (只 HM2)

### Task#9 (根因): 关 FULL_BUFFER
`docker-compose.yml` 加 `NVU_STREAM_FULL_BUFFER=0`. 关后 `buffer_chunks=None` (L1249), 走 L1471
else 分支: 每个 chunk **立即 `wfile.write + flush`** (增量). NVCF 发部分内容后挂住时, 已发内容
已 flush 给 cc4101 (R1674 recv-fallback 能从崩坏 fp 收尾), 不再零内容死循环.

### Task#10 (兜底): breaker 记所有 error_type (非仅 zombie)
`handlers.py` 把 R1673 record 块从 `if zombie_detected:` (L1561) 扩展到
`if (zombie_detected or metrics.get("error_type")) and not all_429:`, 移到 `conn.close()` 前公共位置
(覆盖路径A content_filter + 路径B [DONE] 收尾). 让 idle deadline / first-byte timeout / stream break
等所有大 input 失败都记 breaker failure → OPEN → 下次直走 ms 省 ~90s.

### Task#11 (确认): 非 FULL_BUFFER 路径天然增量
L1471 else 分支每 chunk 即 `wfile.write+flush`, 关 FULL_BUFFER 后天然增量, 无需额外改.

### 修复: R1695 误删 nv_breaker import 导致 nv_gw 崩溃
部署时发现 `upstream.py` L67 缺 `from . import nv_breaker` (R1695 别的进程把 nv_breaker import 行
整个替换成了 big_input_breaker, 而非新增), 且 L70 有重复的空 `class UpstreamResult:`. 每个 execute_request
L1454 `nv_breaker.is_ms_fallback_open()` → NameError → nv_gw 每请求崩溃. 已恢复 import + 删重复 class.

## 验证 (HM2, 改后)

- **env**: `NVU_STREAM_FULL_BUFFER=0`, config `FULL_BUFFER=False`, `NVU_BIG_INPUT_FAIL_N=1` ✅
- **283k stream 探测**: curl 实时收到内容 `"content":"Your"` `"content":" message is,"` ✅
  (改前 FULL_BUFFER 会攒到结束才 flush, NVCF 挂住则丢弃零内容)
- **cc4101 nonstream 中请求**: 200 完整 JSON (`text":"我是一个...助手"`) ✅
- **nv_gw 无 NameError**: 重启后日志干净, 请求正常处理 ✅

## 参数表 (最终)

| 参数 | 值 | 来源 |
|---|---|---|
| NVU_STREAM_FULL_BUFFER | 0 (R1627 默认1) | Task#9 根因 |
| NVU_BIG_INPUT_FAIL_N | 1 | R1674 B |
| NVU_BIG_INPUT_THRESHOLD | 250000 | R1673 |
| NVU_BIG_INPUT_COOLDOWN_S | 180 | R1673 |
| NVU_MS_FALLBACK_ENABLED | 1 | R1673 副作用激活 R1648c |
| breaker record 条件 | zombie OR error_type (非仅 zombie) | Task#10 兜底 |

## 风险与回退
- **关 FULL_BUFFER 风险**: R1627 当年为治 mid-response 卡死弹窗引入, 关后可能回归"半截响应被打断"
  弹窗. 但 CC 重试机制 + cc4101 recv-fallback (R1674) + breaker fast-fail (R1673/10) 三重兜底,
  且"半截内容"远优于"零内容死循环". 可接受.
- **回退**: `NVU_STREAM_FULL_BUFFER=1` (改回 R1627 全量缓冲, 但需同时恢复 breaker 只记 zombie 的
  R1673 原逻辑, 否则 buffer 又被吞).
- **HM1 未同步**: 本轮只改 HM2.

## 框架层总结 (用户要"系统性框架解决")
三层链路的所有卡点现已系统性修通:
1. **nv_gw 层**: FULL_BUFFER 关(根因, 不再吞成功响应) + breaker 记所有 error_type(兜底, idle deadline
   也 OPEN) + R1673 fast-fail 到 ms + R1672 first-byte deadline 分档.
2. **cc4101 层**: R1674 collect recv-fallback (http.client fp 崩坏后 sock.recv 兜底) + R1640 breaker.
3. **CC 客户端**: API_TIMEOUT_MS=600s, 自身超时打印 `{ Request timed out}` 并重试 (不归我们改).

## 后续
- R1648e: cc4101 纯透传 (删 R1643 fallback + breaker; handlers 转发到 nv_gw:40006/v1/messages).
- R1648f: 切换 + ≥6h 长跑, 更新 compose + memory, HM1 同步.
