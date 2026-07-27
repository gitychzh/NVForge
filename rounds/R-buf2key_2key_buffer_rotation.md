# R-buf2key: buffer 层 2-key 轮转 (key2→key5), 150s×2, NVCF 直连不经 ms_gw

**时间**: 2026-07-27 11:02 CST
**作者**: opc_uname (HM1, 用户直接指令)

## 背景

R-keyretry 实测: 同 key1 重试 3 次 (2s→4s→8s) 0 救回 (全 429).
R-keyrotate 实测: 换 key5 重试救回 3/7 请求, NVCF SR 28.6%→71.4%.
但 R-keyrotate 在 NVCF 层重试, execute_request 内部 ms_gw fallback 抢先,
buffer 层拿到的总是 ms_gw 的流, 没机会试 key5.

## 改动

### buffer_stream.py
- _execute_and_drain: 所有 attempt 直接调 _try_glm52_mode_chain (NVCF only)
- 第一次用原始 caller (key2), 重试用 opencode caller (key5, 不同代理IP)
- max_retries=2, timeout_stairs=[150,150], total_deadline=600
- 不经 execute_request 的 ms_gw fallback

### handlers.py
- NVU_BUFFER_CALLERS caller + stream=True: 拦截, 不调 execute_request
- 直接发 SSE 200 headers, 交 BufferStreamSession.run() 处理
- buffer 内部调 NVCF, 2 次全败后发 error → CC 重试

### config.py
- NVU_BUFFER_MAX_RETRIES 默认 3→2
- NVU_BUFFER_TIMEOUT_STAIRS 默认 150,200,200 → 150,150
- NVU_BUFFER_TOTAL_DEADLINE_S 默认 580→600

### upstream.py
- NVCF 层恢复 max_attempts=1 (R-keyretry/R-keyrotate 废弃)
- NVCF 失败立刻 all_keys_exhausted, 交给 buffer 层处理

### docker-compose.yml
- NVU_BUFFER_MAX_RETRIES=2, NVU_BUFFER_TIMEOUT_STAIRS=150,150
- NVU_BUFFER_TOTAL_DEADLINE_S=600, NVU_CALLER_RETRY=0

## 验证

- py_compile OK ✓
- health OK ✓
- NV-BUF2KEY-INTERCEPT 拦截正常 ✓
- key2 成功: NVCF → buffer drain → flush ✓
- key2 失败→key5 重试: 待 NVCF 429 再现时验证

## 数据 (150s 覆盖率)

45 个成功请求耗时分布: p99=135s, 150s 覆盖 44/45=97.8%
150×2=300s NVCF 预算 + ms_gw 兜底, 总预算 600s 对齐 SDK 600s 墙
