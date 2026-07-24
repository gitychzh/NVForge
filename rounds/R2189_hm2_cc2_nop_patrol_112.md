# R2189 — hm2_cc2 NOP 巡检轮 (连续第 112 NOP)

> 全新 session 接棒. STATE.md 停 R2188 (与 git HEAD 一致, 无滞后). `git pull` HEAD=272fb5a (R2188).
> hm2_cc2 线最新 = R2188, 本轮续 R2189. 未 Read 任何 /tmp 文件 (铁律遵守).

## 数据 (HM2, 30min window, 2026-07-24 ~12:30 CST)

### nv_requests (nv_gw 出口成功率, 核心指标)
- **106 req / 103 OK(200) / 3 错(502) → SR = 97.2%** ✅
- by model: **glm5_2_nv 101/104 = 97.1%** (主力, 3 错 = 2 zombie_empty + 1 stream_absolute_cap)
  ; claude-opus-4-8 2/2 = 100% (cc4101 passthrough 非 NV 路径)
- error_type: zombie_empty_completion × 2, stream_absolute_cap × 1
- host_machine 全 HM2 本域

### nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)
- pexec_success 95
- pexec_429 **12** (R2188=10 略升, 仍正常区间; NVCF 账户级配额)
- pexec_empty_200 **10** (R2188=3 升; NVCF 服务端空响应)
- pexec_conn_RemoteDisconnected 5 (R2188=1 升)
- pexec_SSLEOFError 3 (R2188=2)
- pexec_504 1
- 全 NVCF 上游连接/配额类波动, 非旋钮治 (KEY_COOLDOWN=60/MIN_OUTBOUND=10 已保守)

### cc4101 30min fallback (负向核心指标)
- **真 fallback = 1** (req 80c04277 @12:31:08)
  - PRIMARY-FAIL primary (glm5_2_nv) timeout status=0 after 60061ms: header/ttfb timeout after 60s
  - PRIMARY-FAIL-SKIP-CIRCUIT: 60s < chain budget 120s, NOT counted toward circuit
  - → FALLBACK-OK fallback (glm5_2_ms) succeeded after 2332ms
- **0 真中断** (救回, < 5 阈值)
- 比 R2188=0 多 1, 仍窗口边缘级单例 (60s timeout 走 SKIP-CIRCUIT 快速救回, 与 R2186/R2184 同模式)

### nv_gw 内部 NV-MS-FB (R1719 设计, 不冒 cc 层)
- NV-MS-FB-ATTEMPT 11 / NV-MS-FB-OK 12 (全 OK 兜底, 0 冒 cc4101)
- NV-MS-FB-BREAKER-OPEN **0** (R2188=28 大幅干净, 本轮无 OPEN 风暴)
- 即 11 个请求在 nv_gw 内部被 ms_fb 兜底成功, cc4101 完全无感

### NV-ANTH-BREAKER (mid-stream soft-fail)
- NV-ANTH-BREAKER-FAIL **2 条** (R2188=0 略升)
  - dd84c2c6 @12:26:10 err=zombie_empty_completion → nv_breaker=('CLOSED',2,0)
  - f73280e7 @12:29:05 err=zombie_empty_completion → nv_breaker=('CLOSED',2,0)
- **未真 OPEN** (state CLOSED, 计数 2), 对应本轮 2 个 zombie 的 mid-stream soft-fail 记录, 设计行为健康无恶化

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **49 / 6h** (R2188=52 略降, R2289 副作用 SDK 131s 客户端首字节墙结构性基线 42-52 区间波动)
- stream_total_deadline = 2/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- **nv_gw RestartCount=0 StartedAt=2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 与 R2188 逐项一致, 无漂移) ✅
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- docker ps: nv_gw Up 10h / cc4101 Up 21h / ms_gw Up 2d / logs_db Up 7d
- env 关键参数与 R2188 快照逐项一致, **无参数漂移** ✅

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). **本轮 2 zombie 窗口** — 近 5 轮首次有素材 (R2184-R2188 全 0 zombie), 累积素材待续
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/). 本轮 2 zombie 素材仍不足 (STATE 要求连续多轮 ≥5 才值得推进). 未实施.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
1. SR 97.2% > 85% ✅
2. cc4101 fallback 请求数 1 < 5 ✅ (且救回, 0 真中断)
3. 无新增错误类型 ✅ (2 zombie + 1 stream_absolute_cap 全已知类型; NV-ANTH-BREAKER-FAIL 2 条但 nv_breaker=CLOSED 未真 OPEN, 对应 zombie mid-stream soft-fail 设计行为)

四重佐证 nv_gw 稳:
1. nv_requests 97.2% SR (3 错全 mid-stream 背景波/zombie, tier 错误全 NVCF 上游连接类无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (NV-MS-FB-BREAKER-OPEN=0; NV-ANTH-BREAKER-FAIL 2 条但 CLOSED 未真 OPEN)
4. 参数无漂移 (容器未重建 env 与 R2188 逐项一致, nv_gw StartedAt 连续多轮稳定 07-23T18:05)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. commit 待 push.

## watch 信号 (下轮接棒者注意)
- **2 zombie 本轮首次素材** (近5轮首次): dd84c2c6+f73280e7. 若下轮持续出现 zombie (连续多轮累计 ≥5), 可主动推进 R2192 任务3 (spec 复核 + grep -n 核实行号 + 实施). 当前仅 2 个, 不够.
- pexec_429=12 / pexec_empty_200=10 (R2188=10/3 略升): NVCF 上游波动, 非旋钮治, 持续上升才 watch.
- 499=49/6h (R2188=52 略降): SDK 131s 客户端墙基线, 待 BUG-A 查清 SDK 可调否.
