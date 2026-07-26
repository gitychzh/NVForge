# R-buffer: cc2 zombie 流 buffer-then-flush 根治 (2026-07-27)

## 背景

Session 0e098783 (2026-07-26 22:12~22:51) 第 4 次 generator restart, 根因 = NVCF Form B
僵尸流: 发了部分 content chunk 后沉默, 不发 finish_reason 不发 [DONE], TCP 连接没断.
SDK 生成器无限 await queryInstance.next(), 用户手动"继续"才恢复.

[[r2264-499-two-forms-real-rootcause]] 的 Form B: 有内容无终止信号. nv_gw/cc4101 两侧都
没记 error (TCP 没断, 对端只是沉默), R2254 watchdog 600s 没来得及触发 (用户 574s 手动干预).

## 根治方案: buffer-then-flush

对 cc4101-primary caller 的流式请求, 在 nv_gw 做 store-and-forward:

1. 不立即转发 chunks 给 CC, buffer 在内存
2. 每 30s 发 `event: ping` 占位符重置 SDK idle timer
3. 流结束 → judge_stream() 判定三者齐全 (content + finish_reason + [DONE])
4. 成功 → 一次性 flush 全部 buffered content 给 CC
5. 失败 → 废弃 buffer, 同 key 重试 (150s→200s→200s)
6. 3 次全败 → `event: error` 给 CC
7. 总预算 580s (在 R2254 watchdog 600s 之内)

### 门控

- `NVU_BUFFER_CALLERS=cc4101-primary` (逗号分隔, 可扩展)
- 其他 caller (hermes/openclaw/opencode/交互式) 照常流式, 不受影响
- 回滚: `NVU_BUFFER_CALLERS=""` (空=禁用, 改 env restart, 无需改代码)

### 判定函数 (stream_success_judge.py)

成功充要条件: has_real_content + finish_reason∈{stop,length,tool_calls} + saw_done

| 成功亚型 | content | reasoning | tool_call | finish_reason |
|---|---|---|---|---|
| SUCCESS_TEXT | >0 | 0 | 无 | stop |
| SUCCESS_THINKING | >0 | >0 | 无 | stop |
| SUCCESS_THINKING_ONLY | 0 | >0 | 无 | stop |
| SUCCESS_LENGTH | ≥0 | ≥0 | 无 | length |
| SUCCESS_TOOL_CALL | 0 | ≥0 | 有真delta | tool_calls |
| SUCCESS_THINKING_TOOL | 0 | >0 | 有真delta | tool_calls |

| 失败类型 | 缺什么 | 对应已知 bug |
|---|---|---|
| ZOMBIE_PARTIAL | 无fr无done | **Form B (本次根因)** |
| ZOMBIE_EMPTY | 无内容 | zombie_empty_completion |
| FAKE_TOOL_CALL | fr=tool_calls无真delta | R1932 |
| INCOMPLETE_NO_DONE | 有fr无done | NVCF漏发[DONE] |
| INCOMPLETE_NO_FR | 有done无fr | NVCF漏发fr |
| CONTENT_FILTER | fr=content_filter | NVCF内容过滤 |

12 种情形测试全通过.

## 改动文件

| 文件 | 改动 |
|---|---|
| `gateway/stream_success_judge.py` | 新增 (判定函数+StreamState) |
| `gateway/buffer_stream.py` | 新增 (BufferStreamSession: buffer+判定+重试+ping) |
| `gateway/config.py` | +6 行 env (NVU_BUFFER_*) |
| `gateway/handlers.py` | +13 行门控分支 (_stream_openai_to_anth 入口) |
| `docker-compose.yml` | +5 行 env |

## 部署

HM2: gateway/ 是 bind-mount, 改文件 + compose up -d nv_gw 即可 (不需要 rebuild).
HM1: 需同步 (R-buffer 只在 HM2 部署, HM1 后续同步).

## 验证

### E2E 成功路径 (cc4101-primary)
```
NV-GLM52-CHAIN: caller=cc4101-primary -> fixed key=k2
NV-GLM52-ATTEMPT: pexec_us_rr k2 succeeded
NV-BUFFER-START: caller=cc4101-primary max_retries=3 stairs=[150,200,200] ping=30s
NV-BUFFER-ATTEMPT: attempt=1/3 timeout=150s input=4c thinking=False
NV-BUFFER-VERDICT: verdict=success_text content=2c fr=stop done=True buffered=685b elapsed=13s
NV-BUFFER-FLUSH: flushing 685b to CC
NV-BUFFER-SUCCESS: 1 attempt, 13.2s
```

### 非 cc4101 caller 不受影响 (hermes)
```
NV-PEEK-OK: peek healthy first content after 5238ms  ← 原有流式路径
(无 NV-BUFFER-* 日志)
```

## 参数表

| 参数 | 值 | 说明 |
|---|---|---|
| NVU_BUFFER_CALLERS | cc4101-primary | 只对 cc2 生效 |
| NVU_BUFFER_MAX_RETRIES | 3 | 最多重试 3 次 |
| NVU_BUFFER_TIMEOUT_STAIRS | 150,200,200 | 每次 attempt 超时(秒) |
| NVU_BUFFER_PING_INTERVAL_S | 30 | ping 占位符间隔 |
| NVU_BUFFER_TOTAL_DEADLINE_S | 580 | 总预算(留 20s 给 R2254 watchdog) |

## 预期效果

- Form B 僵尸流: 不再需要用户手动"继续", buffer 模式自动重试
- 正常请求: TTFB 从 ~2s 变 ~流完成时间 (cc2 无人值守, 不影响 UX)
- thinking 误杀: total_deadline 兜底, 有详细日志, 用户已接受
- NVCF 额度: 同 key 重试 (用户指定), 后期可换 key

## 回滚

```bash
# 方式1: env 禁用 (不改代码)
# docker-compose.yml NVU_BUFFER_CALLERS="" → docker compose up -d nv_gw

# 方式2: 代码回退
cp handlers.py.bak.R-buffer handlers.py
docker compose up -d nv_gw
```
