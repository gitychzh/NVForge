# R1926 (HM2 cc2): 指数退避+ms 双层方案 — step2.0 编码 (cc4101 层: STREAM_TOTAL_DEADLINE 360→480 + 透传层重复 message_start 容错验证)

> 铁律1 (改前必有数据) ✓: 拉 30min nv_gw 窗口 + 读 R1924 核对轮结论 (7 条清单逐条核对, 发现 3 设计偏差 + 2 风险点). 本轮基于 R1924 核对结论动 step2.0.
> 铁律2 (改后必有验证) ✓: env 改后 up -d cc4101 → health ok + StartedAt fresh + E2E 流式完整 + 2min 后窗 0 异常.
> 链路3 (聚焦 40006/4101) ✓: 只改 cc4101(4101) env 一行 (STREAM_TOTAL_DEADLINE_S). 不碰 ms_gw(40007). nv_gw(40006) 本轮 0 改动.
> 铁律4 (写入仓库) ✓: 本文件 + docker-compose.yml 改动 (commit).
> 铁律5 (改.py restart 非 up-d / 改 env up-d 非 restart) ✓: 本轮改 compose env, 用 `docker compose up -d cc4101` (非 restart), 容器 recreated 生效.

## 上下文 (接 R1924 核对轮 + 监督者 21:00/21:15 指令)

监督者 2026-07-19 21:00 定稿 + 21:15 指令交 cc2 编码 "指数退避 + ms 双层兜底":
- 层1 nv_gw per-key 指数退避 (60/120/240, chain_budget 420s) + post-200 软挂换 key
- 层2 cc4101 PRIMARY_HEADER_TIMEOUT 对齐 + ms 兜底不变
- 数学保证: nv 420s + ms 5s = 425s < CC API_TIMEOUT_MS 600s, 留 175s 余量, cc2 不中断

R1924 完成 step1 (逻辑核对, 7 条清单), 发现:
- [3] 设计偏差: chain_budget 心智过时 (实际 env=120 + R1418 input 缩放, 非 70s)
- [6] 坑确认: `CC4101_STREAM_TOTAL_DEADLINE_S` 默认 360s (env 未设) 会抢断指数退避 (stream.py:84/121)
- [7] 坑确认: `NVU_STREAM_ABSOLUTE_CAP_S=150` 与指数退避冲突
- [5] 最大风险点: post-200 软挂换 key 时 message_start 重放, cc4101 透传层是否容错待验证

R1924 结论: 不编码 (跨 3 组件大改造 + 当前稳态, 留半成品风险), 给 R1926 留 step2.0 (cc4101 容错验证 + STREAM_DEADLINE) + step2.1 (nv_gw 指数退避 + abs_cap 同步). **本轮 = step2.0 (cc4101 层)**.

## 改动 (本轮 1 行 env)

### 改前数据 (30min, 本 session 20:05Z 拉取)
```
nv_gw status: 200×39 / 502×2 → SR 95.1% (抖动区间常态)
tier 30min: pexec_success 31 / pexec_empty_200 6 / IntegrateTimeout 2 (zombie 同源被 retry 吸收到 200, 非 nv_gw 旋钮可解)
abs_cap 0 (R1918 BUG-B 方案0 连续多轮归零持续)
breaker OPEN 0
fallback: 0 真中断 (cc4101 未拉但链路稳)
```
链路稳态, 供 step2.0 铺路 (不破坏稳态为前提).

### 改动内容

**`/opt/cc-infra/docker-compose.yml` cc4101 段新增 1 行 env** (UPSTREAM_IDLE_TIMEOUT 后, PYTHONUNBUFFERED 前):
```yaml
    - CC4101_STREAM_TOTAL_DEADLINE_S=480  # R1926: 360(默认)->480. step2.0铺路...
```

理由 (基于 R1924 [6] 核对结论):
- config.py:26 `CC4101_STREAM_TOTAL_DEADLINE_S` 默认 360s (R846 ttfb 后绝对总时长兜底, stream.py:84/121 raise socket.timeout 中断流).
- 指数退避 (step2.1 待做): nv_gw 单 key 60/120/240s = 最坏 420s + NVCF ttfb 慢 (58-148s) → 总时长撞 360s 被 cc4101 stall-watcher 先杀.
- 改 480s = 420s (nv 退避) + 30s 余量 + ttfb 容差. **留 120s 到 CC 600s 线**.
- 真静默挂死仍由 `IDLE_GAP_S=100` 兜底 (100s 无 chunk 就断), TOTAL_DEADLINE 只兜 "不断有零星 chunk 但永不结束", 提到 480 对当前链路几乎无副作用 (当前 nv 单请求 chain_budget~120s, stall-watcher 靠 idle_gap 100s 触发, 360s 几乎不被命中).
- env 级单点改动, 可回滚 (删此行回默认 360).

### [5] 最大风险点验证结论 (cc4101 透传层对重复 message_start 天然容错)

读 stream.py:90-180 透传主循环: `chunk = resp.read(8192)` → `_write_bytes(chunk)` 原样转发客户端. **不解析 SSE message 语义, 不记 message_start state, 不做任何 stateful 处理** (仅 `_err_probe` 探测 `event: error` 字符串).

→ **结论**: cc4101 透传层对重复 message_start 天然容错 (它根本不解析 message_start, 只转字节). step2.1 (nv_gw 软挂换 key 重放新流) 在 cc4101 这层**不会因重复 message_start 报错或中断** — nv_gw 换 key 重放的新流会被 cc4101 原样透传给 CC SDK, cc4101 自身不卡.

剩余风险: CC SDK (Claude) 端是否容错重复 message_start — 不在 cc2 可控范围 (且 Claude SDK 对 SSE 流容错性好, 非本轮可测). 但 cc4101 这层 (R1924 [5] 标的最大风险点) 已确认**不构成阻塞**, step2.1 可动.

### 没改什么 (本轮聚焦 step2.0)
- nv_gw(40006) 0 改动 (step2.1 待 R1927).
- 不碰 ms_gw(40007) 源码 (它是重启窗口热备, 铁律).
- 不调 cc4101 PRIMARY_HEADER_TIMEOUT (60→450 那档, 留到 step2.1 与 nv_gw 指数退避同步改, 避免本轮 cc4101 header 给足但 nv_gw 没退避, 反而让 cc4101 等 nv_gw 旧 120s chain_budget 白等).
- 不调 NVU_STREAM_ABSOLUTE_CAP_S (150→250, 留到 step2.1 与 nv_gw 指数退避同步, 当前 abs_cap 连续多轮归零, 不急).

## 验证 (改后)

1. **env 生效**: `docker exec cc4101 env | grep CC4101_STREAM_TOTAL_DEADLINE_S` → `=480` ✓
2. **StartedAt fresh**: `docker inspect --format '{{.State.StartedAt}}' cc4101` → `2026-07-19T12:10:22Z` (recreated, 非旧容器) ✓
3. **容器全 Up**: nv_gw Up About an hour / cc4101 Up 13s / ms_gw Up 2 days ✓
4. **cc4101 启动日志正常**: `[START] cc4101 listening on 0.0.0.0:4101` + primary=nv_gw glm5_2_nv + fallback=ms_gw ✓
5. **E2E 流式自测** (curl cc4101:4101 /v1/messages stream): message_start → content_block_start → 2× deltas → content_block_stop → message_delta(stop_reason=end_turn) → message_stop. **clean 完整 SSE**, exit 0 ✓
6. **后窗 ~2min 0 异常**: cc4101 日志 ERR/EXC/Traceback/STREAM-STALLED/STREAM-DEADLINE/UPSTREAM-ERROR-SEEN = 0; 4 条 REQ 正常进来 ✓
7. **nv_gw 后窗全 200**: 20min 窗 (含改前改后) 仅 1 条 502 (11:56, 改前), 改后 12:10+ 全 200 ✓

## 本轮结论

step2.0 完成: cc4101 STREAM_TOTAL_DEADLINE 360→480 铺路 + [5] 最大风险点 (cc4101 透传层重复 message_start 容错) 验证通过. 为 R1927 step2.1 (nv_gw 指数退避 + abs_cap/cap 同步 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 对齐) 扫清 cc4101 抢断坑.

- 当前链路稳: SR 95.1% (200:39/502:2) / 0 真中断 / abs_cap 连续多轮归零.
- 铁律1: 改前有数据 (30min + R1924 核对结论). 铁律5: 改 env 用 up -d 非 restart. 铁律3: 不碰 ms_gw. 铁律6: 只改 HM2.

## 下一轮 (R1927) 该做 — step2.1 (nv_gw 指数退避)

按 R1924 核对 + 本轮 [5] 验证结论, step2.1 编码清单:
1. **nv_gw per-key 指数退避**: `upstream.py _glm52_single_attempt` (per_attempt_timeout) + `_try_glm52_mode_chain` (循环上界 + chain_budget). 新增 env `NVU_GLM52_EXP_BACKOFF=true` 开关. per-key timeout 60/120/240, 前 3 轮指数后封顶 240 (R1924 [2] 建议保留 7 轮循环上界). chain_budget env `NVU_TIER_BUDGET_GLM5_2_NV=120→420` (R1924 [3]).
2. **abs_cap 同步**: `NVU_STREAM_ABSOLUTE_CAP_S=150→250` (R1924 [7] [b] 方案: abs_cap 触发换 key 而非直接 502 — 与软挂换 key 同机制, 一并做). 当前 abs_cap 连续多轮归零, 改值低风险.
3. **cc4101 PRIMARY_HEADER_TIMEOUT 对齐**: 60→450 (分档: >200K→460, >50K→450, 默认→450), 与 nv_gw 指数退避总时长对齐 (R1924 [6] 已铺 STREAM_DEADLINE 480, header 450 < 480 不抢断).
4. **post-200 软挂换 key**: handlers.py zombie/abs_cap/no_content_gap 分支加换 key 调用 (R1924 [4]). 复用 R1774 graceful end 机制处理 message_start_sent 重放 (本轮 [5] 已确认 cc4101 透传层容错, 风险降级).
5. **改后验证**: py_compile nv_gw + restart nv_gw (非 up-d) + up -d cc4101 (env) + health + E2E 流式 + 24h 观测 cc2 中断=0/SR≥92.6%/ms_fb 次数下降.

**铁律提醒**: step2.1 是跨 nv_gw 源码 + cc4101 env 大改造, 必须改前 cp *.py.bak.R1927, 改后 py_compile + restart + 验证, 失败用 .bak 回滚 + 再 restart. 不碰 ms_gw. 只改 HM2. 不撤 ms (本方案核心是 nv 指数退避层1 + ms 兜底层2 双保险).

## 介入决策 (为何本轮只动 step2.0)

- 监督者 21:15 指令 step1=核对 (R1924 已完成), step2=编码. 本轮 = step2.0 (cc4101 层, 风险最低, 为 step2.1 铺路).
- 一轮一个点 (R1924 建议): step2.0 (cc4101 env 1 行 + 风险点验证) 与 step2.1 (nv_gw 源码 + cc4101 header + abs_cap + 软挂换 key) 分开, 避免 1 轮改太多留半成品.
- [5] 最大风险点 (cc4101 透传层重复 message_start) 必先验证 (R1924 要求) → 本轮已验证通过, 降级 step2.1 风险.
- 当前稳态 (SR 95.1% / 0 真中断) 不破坏为前提. 本轮 1 行 env 改动 + 2min 后窗 0 异常, 稳态保持.
