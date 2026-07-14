# opclaw4103 fallback 机制迁移 + 超时 bug 修复

## 目标
把 cc4101 已验证的 fallback 全套机制移植进 opclaw4103，替换当前简陋版，修复超时分层 bug，**保留** opclaw4103 特有的 openclaw 适配层（content_filter zombie 拦截、supplement reasoning→content、FALLBACK_NOTICE、prompt 预检）。

## 决策（已与用户确认）
- 迁移范围：cc4101 全套（超时分层 25s/150s、circuit 三态、retry primary、total budget、4xx 不 fallback）
- 已发流处理：切 fallback 时插 FALLBACK_NOTICE 继续（保持现状，不回溯已发 primary content）
- 落地：直接远程改源码 + 重建镜像 + 重启 + 测试

## 实证（opclaw4103 日志 + 当前 env）
当前 env 实配：`PRIMARY_STREAM_TIMEOUT_S=90` `FALLBACK_TIMEOUT_S=240` `FALLBACK_RECOVER_S=120` `CIRCUIT_FAILURE_THRESHOLD=5` `CIRCUIT_OPEN_S=60` `SUPPLEMENT_REASONING_AS_CONTENT=1` `PROMPT_TOKEN_LIMIT=120000`。

日志实锤的 bug：
- `23:04:56 REQ → 23:06:26 UPSTREAM-ERR: TimeoutError: timed out`，**等 90s 才切 fallback**。根因：`_post_upstream` 里 `socket.create_connection(timeout=CC_CONNECT_TIMEOUT_S=10)` 建连后立刻 `sock.settimeout(timeout_s=90)`，导致 `getresponse()`（含 connect 完成后的 TTFB）用的是 90s read timeout 而非 10s connect timeout——R763 的 connect/read 分离没贯彻到 getresponse 阶段，connect 抖动时仍卡满 read timeout。
- `PRIMARY_STREAM_TIMEOUT_S=90` 同时管 TTFB 和 body idle，thinking 静默期 >90s 会被误判卡死；TTFB 若 >90s（理论可能）会被误杀。
- `CONTENT_FILTER_ZOMBIE` / `PRIMARY-ZOMBIE-FALLBACK` 在 01:05/03:05 实际触发——R842c 拦截在工作，保留。

## 改造范围（只动 opclaw4103，不动 cc4101/nv_gw/ms_gw/openclaw）

### 文件 1：`/app/gateway/config.py` — 新增超时分层参数
新增（对齐 cc4101 命名，保留 opclaw4103 env 兼容）：
- `PRIMARY_HEADER_TIMEOUT`（默认 25）—— primary connect+TTFB，短，失败快切 fallback
- `FALLBACK_HEADER_TIMEOUT`（默认 30）—— fallback connect+TTFB
- `UPSTREAM_IDLE_TIMEOUT`（默认 150）—— 响应头到达后 body chunk 间隔，长，容纳 thinking 静默期
- `CC4101_TOTAL_BUDGET_S`（默认 80，env 名沿用）—— 跨 stage 总预算
- `RETRY_PRIMARY_AFTER_FALLBACK`（默认 "1"）—— fallback 失败后是否 retry primary
保留旧参数 `PRIMARY_STREAM_TIMEOUT_S` / `FALLBACK_TIMEOUT_S` 作 fallback 兜底默认值（env 不删，平滑）。
保留 `FALLBACK_RECOVER_S`（单次 fallback 后短冷却，cc4101 没有但 opclaw4103 有价值）。
保留 `CIRCUIT_FAILURE_THRESHOLD` / `CIRCUIT_OPEN_S`。
保留 `SUPPLEMENT_REASONING_AS_CONTENT` / `PROMPT_TOKEN_LIMIT` / `FALLBACK_NOTICE` / `CC_CONNECT_TIMEOUT_S`。

### 文件 2：`/app/gateway/forwarder.py` — 核心改造

#### 2a. `_post_upstream` 超时分层重写（修 connect 卡 90s + TTFB/idle 混用）
签名改为分离三参数：`_post_upstream(base_url, model, api_key, oai_body, stream, header_timeout, idle_timeout)`。
逻辑对齐 cc4101 `_call_upstream`：
- `sock = socket.create_connection((host,port), timeout=CC_CONNECT_TIMEOUT_S)` —— TCP 建连阶段用 10s
- `sock.settimeout(header_timeout)` —— getresponse 阶段用 PRIMARY_HEADER_TIMEOUT=25s（不是 90s）
- `conn.request()` + `conn.getresponse()`，期间 socket.timeout → 抛 `_UpstreamError("timeout", ...)`
- 响应头到达后 `_restore_read_timeout(conn, idle_timeout)` —— 切 UPSTREAM_IDLE_TIMEOUT=150s 供后续 body read
- 非 200 读 error body 分类 client_4xx/server_5xx
返回 `(resp, conn)` 或抛 `_UpstreamError`（带 kind/status/error_json/message）。
新增 `_UpstreamError` 类（移植自 cc4101）。
新增 `_restore_read_timeout(conn, read_timeout)`（移植自 cc4101）。
删掉旧的"建连后立刻 settimeout(timeout_s)"逻辑。

#### 2b. `CircuitState` → 模块级三态函数（对齐 cc4101 circuit.py）
当前 `CircuitState` 类替换为 cc4101 的模块级 `_fail_count`/`_open_until`/`_lock` + 三函数：
- `is_primary_open()` —— CLOSED/HALF_OPEN 返回 False（允许探活），OPEN 返回 True。用 `time.monotonic()`（修 time.time 时钟跳变）。
- `record_primary_success()` —— 清零 _fail_count **且** 清 _open_until=0.0（CLOSED，修当前"清计数不清 open_until"怪态）。
- `record_primary_failure()` —— 计数+1，到阈值开路 _open_until=now+CC4101_PRIMARY_SKIP_S；已开路时 re-arm。
保留 `should_try_primary()` 语义但内部调用 `is_primary_open()` + `FALLBACK_RECOVER_S` 冷却（opclaw4103 特有，cc4101 没有，保留）。
`time.time()` 全换 `time.monotonic()`。

#### 2c. `forward_non_stream` 改造（用新 _post_upstream + 失败分类）
- primary 用 `_post_upstream(..., header_timeout=PRIMARY_HEADER_TIMEOUT, idle_timeout=UPSTREAM_IDLE_TIMEOUT)`
- 捕获 `_UpstreamError`：`client_4xx` 不 fallback 直接透传；`server_5xx`/`conn`/`timeout` 调 record_primary_failure 进 fallback
- 保留 `all_tiers_exhausted` body 文本判定（opclaw4103 特有，cc4101 没有）—— 合进 _is_primary_failure 或在 _UpstreamError kind 外单独判
- fallback 用 `FALLBACK_HEADER_TIMEOUT` + `UPSTREAM_IDLE_TIMEOUT`
- fallback 失败 + RETRY_PRIMARY_AFTER_FALLBACK + remaining>=PRIMARY_HEADER_TIMEOUT + not is_primary_open() → retry primary 一次（移植自 cc4101，门控严格）
- 保留 `_inject_notice_non_stream`

#### 2d. `forward_stream` 改造（用新 _post_upstream + 失败分类 + retry primary + 保留 content_filter 拦截）
- primary 阶段：先 `is_primary_open()` 判断（circuit OPEN 则跳 primary 直进 fallback，移植自 cc4101 Stage 1）
- primary `_post_upstream(..., header_timeout=PRIMARY_HEADER_TIMEOUT, idle_timeout=UPSTREAM_IDLE_TIMEOUT)`
  - 连接失败/5xx/timeout → record_primary_failure → 进 fallback
  - client_4xx → 读 body 发 err_chunk 透传（不切 fallback，对齐 cc4101 + 当前行为）
- primary 正常 2xx → 调 `_stream_from_upstream`，**保留 R842c content_filter zombie 拦截**：收到 content_filter_zombie 信号 → break + record_primary_failure → 进 fallback 流（现状，不改）
  - primary 流正常结束 → record_primary_success → return
- fallback 阶段：`_post_upstream(..., header_timeout=FALLBACK_HEADER_TIMEOUT, idle_timeout=UPSTREAM_IDLE_TIMEOUT)`
  - 失败 → 若 retry primary 门控满足则 retry primary 一次（移植）；retry 也失败或门控不满足 → 发 err_chunk + done
  - 成功 → `_stream_from_upstream(notice=FALLBACK_NOTICE, fallback_used=True)`，保留 FALLBACK_NOTICE 注入
- **retry primary 在流式下的风险控制**：只在 fallback **连接失败/5xx/timeout**（首字节前）retry primary，不在 fallback 流中途失败 retry（避免已发 fallback content 后再拼 primary 流）。这点比 cc4101 更保守，因为 opclaw4103 是晚判定路线，流中途可能已发过 content。
- 保留 `FALLBACK_ENABLED=0` 分支

#### 2e. `_stream_from_upstream` —— 保留全部 openclaw 适配逻辑
**不改核心逻辑**，仅调整 read 超时来源（由 _post_upstream 的 _restore_read_timeout 设好 idle_timeout，本函数用 resp.read(8192) 自然继承）。保留：
- R842c content_filter zombie 信号 yield
- R766 SUPPLEMENT_REASONING_AS_CONTENT 流末补 content
- R790 流中途异常补 content
- R841b tool_calls_seen 保护
- FALLBACK_NOTICE 首个 content delta 前插

### 文件 3：`/app/gateway/app.py` — 微调
- `_handle_embeddings` 的 `_post_upstream` 调用签名对齐新签名（传 header_timeout/idle_timeout，embeddings 用 FALLBACK_HEADER_TIMEOUT + UPSTREAM_IDLE_TIMEOUT）
- import 行更新（若新增 _UpstreamError 等）
- 其余不动

## 不动的东西（明确边界）
- cc4101 容器、源码 —— 不动（CC 链路稳定，不碰）
- nv_gw / ms_gw —— 不动
- openclaw 配置（openclaw.json primary/fallbacks/compaction）—— 不动（本轮只修 adapter，openclaw 配置缺陷是下一轮）
- opclaw4103 的 R842c/R766/R790/NOTICE/预检 5 条 openclaw 适配逻辑 —— 保留

## 部署步骤
1. 本地把改好的 forwarder.py / config.py / app.py 三文件内容准备好（在本地 NVForge 目录建副本验证语法）
2. `python3 -m py_compile` 三文件过语法
3. SSH 到 HM2，docker cp 三文件进 opclaw4103 容器（先 docker cp 出原文件做 .bak 备份）
4. 重建镜像：`docker compose build opclaw4103` 或 `docker restart opclaw4103`（取决于镜像是否 COPY 源码还是挂载卷——需现场确认）
5. 重启后 health 检查 + 看启动日志确认 listening
6. 打 3 类测试请求验证：
   - 正常流式请求（应走 primary 成功）
   - 大 context + thinking（验证 150s idle 不误杀、25s TTFB 不误切）
   - 模拟 primary 故障（看是否在 ~25s 内切 fallback 而非 90s）
7. 观察 adapter.jsonl 日志确认 PRIMARY-FAIL/FALLBACK/CIRCUIT-OPEN 事件正常

## 回滚
- 保留原三文件 .bak，失败时 docker cp 回 + restart
- 旧镜像 tag 保留（重建前 docker image tag 记录当前 image id）

## 风险
- 中等：改的是 openclaw 飞书生产链路的 adapter，改错会断飞书。但本地副本语法验证 + 分文件 docker cp + .bak 回滚可控。
- retry primary 在流式下首次引入，保守门控（仅首字节前失败 retry），风险压到最低。
- env 兼容：旧 env 仍生效（PRIMARY_STREAM_TIMEOUT_S 保留作 fallback 默认），不会因 env 缺失而崩。
