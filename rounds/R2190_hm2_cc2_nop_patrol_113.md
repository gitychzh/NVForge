# R2190 — hm2_cc2 NOP 巡检轮 (连续第 113 NOP)

> 全新 session 接棒. STATE.md 停 R2188 (滞后 1 轮), `git pull` HEAD=55084fe (R2189). hm2_cc2 线最新 = R2189, 本轮续 R2190. STATE.md 滞后修正: 接棒停 R2188 实际 git 到 R2189, 以 git log 为准续号. 未 Read 任何 /tmp 文件 (铁律遵守, 避免上轮 session 死循环重蹈覆辙).

## 数据 (HM2, 30min window, 2026-07-24 ~12:51 CST)

> 本轮窗口 ~12:21-12:51, 与 R2189 (~12:00-12:30) 重叠约 9min. 增量: 捕捉到 R2189 窗口之后的 **12:43-12:44 NV-MS-FB-BREAKER OPEN 风暴 24 事件** (R2189 报 0, 因窗口截止在风暴前).

### nv_requests (nv_gw 出口成功率, 核心指标)
- **103 req / 98 OK(200) / 5 错(502) → SR = 95.1%** ✅
- by model: **glm5_2_nv 98/103 = 95.1%** (全本域流量, 5 错 = 2 zombie_empty + 3 stream_absolute_cap)
- error_type: zombie_empty_completion × 2, stream_absolute_cap × 3
- host_machine 全 HM2 本域

### nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)
- pexec_success 61
- pexec_429 **17** (R2189=12 略升, 仍 6-17 正常区间; NVCF 账户级配额)
- pexec_empty_200 **7** (R2189=10 略降)
- pexec_conn_RemoteDisconnected 3
- pexec_SSLEOFError 2
- 全 NVCF 上游连接/配额类波动, 非旋钮治 (KEY_COOLDOWN=60/MIN_OUTBOUND=10 已保守)

### cc4101 30min fallback (负向核心指标)
- **真 fallback = 1** (req 80c04277 @12:31:08, 与 R2189 同一请求 — 本轮窗口起点覆盖)
  - PRIMARY-FAIL primary (glm5_2_nv) timeout status=0 after 60061ms: header/ttfb timeout after 60s
  - PRIMARY-FAIL-SKIP-CIRCUIT: 60s < chain budget 120s, NOT counted toward circuit
  - → FALLBACK-OK fallback (glm5_2_ms) succeeded after 2332ms
- **0 真中断** (救回, < 5 阈值)
- 与 R2189=1 同一请求, 无新增 fallback

### nv_gw 内部 NV-MS-FB (R1719 设计, 不冒 cc 层)
- **NV-MS-FB-BREAKER-OPEN 24 事件** (R2189=0 大幅上升 — 本轮增量捕捉到 12:38+12:43-12:44 两波风暴)
  - 12:38:07-12:38:55 第一波 (~11 事件)
  - 12:43:31-12:44:38 第二波 (~13 事件, state 衰减 28→7)
- **全自愈**: 12:46:13 breaker=HALF_OPEN 恢复中, 之后无新 OPEN 事件 → CLOSED
- 全是 internal ms_fb 兜底 (NV-MS-FB-ATTEMPT/SERVED), **0 冒 cc4101 层** (cc4101 真fallback 仅 1 与 breaker 无关)
- 与 R2188=28 / R2187=37 同模式设计行为 (NVCF 上游 pexec_429/empty_200 级联 → breaker OPEN → internal ms_fb 兜底 → 自愈 CLOSED), R2179-R2189 连续多轮已知模式

### NV-ANTH-BREAKER (mid-stream soft-fail)
- NV-ANTH-BREAKER-FAIL **2 条** (与 R2189 同, 对应本轮 2 个 zombie)
  - dd84c2c6 @04:26 UTC (12:26 CST) err=zombie_empty_completion, duration 52174ms, fallback_occurred=f
  - f73280e7 @04:29 UTC (12:29 CST) err=zombie_empty_completion, duration 27469ms, fallback_occurred=f
- **未真 OPEN** (nv_breaker=CLOSED, 计数 2), 对应 2 zombie 的 mid-stream soft-fail 记录, 设计行为健康无恶化
- NV-ZOMBIE-KEYRETRY 标记 = 0 (任务3 未实施, 符合预期)

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **50 / 6h** (R2189=49 略升, R2289 副作用 SDK 131s 客户端首字节墙结构性基线 42-52 区间波动)
- stream_total_deadline = 2/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- **nv_gw RestartCount=0 StartedAt=2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 与 R2188/R2189 逐项一致, 无漂移) ✅
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- docker ps: nv_gw Up 11h / cc4101 Up 21h / ms_gw Up 2d / logs_db Up 7d
- env 关键参数与快照逐项一致, **无参数漂移** ✅

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 工作正常. **本轮 2 zombie 都落盘** (dd84c2c6+f73280e7, /app/logs/zombie_dumps/), 累计 **47 sample**. 速览 dd84c2c6 body: top-level 仅 [model,messages,stream,stream_options,max_tokens,max_completion_tokens,tools], **无 context_management/output_config/thinking/cache_control 非标字段** → 继续佐证 hypothesis A 强证伪 (body 干净, zombie 非字段干扰所致). 累积素材待续.
- 任务3 (路径B zombie 内部重试): ⏳ 未实施. 本轮 zombie 仅 2 (STATE 要求连续多轮累计 ≥5 才值得推进). spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待素材充分窗口推进.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
1. SR 95.1% > 85% ✅
2. cc4101 fallback 请求数 1 < 5 ✅ (且救回, 0 真中断, 与 R2189 同一请求无新增)
3. 无新增错误类型 ✅ (2 zombie + 3 stream_absolute_cap 全已知类型; NV-MS-FB-BREAKER-OPEN 24 是 R2179-R2189 连续多轮已知设计行为, 已自愈 12:46 HALF_OPEN→CLOSED, 0 冒 cc 层; NV-ANTH-BREAKER-FAIL 2 条但 nv_breaker=CLOSED 未真 OPEN)

四重佐证 nv_gw 稳:
1. nv_requests 95.1% SR (5 错全 mid-stream 背景波/zombie, tier 错误全 NVCF 上游连接类无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (NV-MS-FB-BREAKER 24 OPEN 事件全自愈回 CLOSED; NV-ANTH-BREAKER-FAIL 2 条但 CLOSED 未真 OPEN)
4. 参数无漂移 (容器未重建 env 与 R2188/R2189 逐项一致, nv_gw StartedAt 连续多轮稳定 07-23T18:05)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. commit 待 push.

## watch 信号 (下轮接棒者注意)
- **NV-MS-FB-BREAKER-OPEN 24 事件** (R2189=0 大幅上升): 本轮增量捕捉到 12:38+12:43-44 两波风暴, 但全自愈 12:46 HALF_OPEN→CLOSED, 0 冒 cc 层. 若下轮 OPEN 风暴频次/持续时间显著上升 (如单轮 ≥3 次风暴或 OPEN 不自愈), 需评估. 当前属 R2179-R2189 已知设计行为.
- **2 zombie 连续第二窗口** (R2189+R2190 各 2): dd84c2c6+f73280e7. 若下��持续出现 zombie (连续多轮累计 ≥5), 可主动推进 R2192 任务3 (spec 复核 + grep -n 核实行号 + 实施). 当前累计 2, 不够.
- pexec_429=17 (R2189=12 略升): NVCF 上游波动, 非旋钮治, 持续上升才 watch.
- 499=50/6h (R2189=49 略升): SDK 131s 客户端墙基线, 待 BUG-A 查清 SDK 可调否.
