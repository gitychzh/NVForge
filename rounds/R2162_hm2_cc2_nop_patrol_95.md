# R2162 (hm2_cc2): NOP 巡检轮 95 — 三阈值冻结, 0 改动 0 restart

## 数据 (HM2, 30min window, 改前必有数据)

### nv_gw 30min by model/status
- **glm5_2_nv**: 60 OK / 60 total → **100%** (零错！本域主链路 nv_requests 侧全 200)
- **kimi_nv**: 6 OK / 14 total → **42.9%** (8 错 = 6 ATE + 2 zombie, R2286 过渡期阵痛延续)
- 合计: 66 OK / 74 total → **SR 89.2%**

### error_type 30min
- glm5_2_nv: 0 (nv_requests 侧干净)
- kimi_nv: 6 all_tiers_exhausted + 2 zombie_empty_completion
- 无 content_filter / timeout / conn / 429 (429 在 tier 层不在 nv_requests 层)
- host_machine 全 HM2 本域

### ⚠ 本轮新信号: cc4101 30min fallback = 1 (打破连续多轮=0)
- req `8ce1b120`, 19:34:36 发起, model=glm5_2_nv, input_chars=149689 (~150K 大请求), msgs=13 tools=27, hdr_to=160s
- **19:37:16 PRIMARY-FAIL**: glm5_2_nv timeout status=0 after **160008ms** (cc4101 header/ttfb timeout after 160s: timed out)
- → cc4101 fallback ms_gw glm5_2_ms, **19:37:35 FALLBACK-OK after 19927ms** (救回, 0 真中断)
- **画像**: 一条 ~150K 大请求撞上 NVCF 侧慢节点, ttfb 超过 cc4101 header 160s 墙. nv_gw 侧未记 502(还在等首字节, cc4101 先到 header 墙主动断).
- **非系统性**: 30min 仅 1 条, 同时段后续 glm5_2_nv NV-PEEK-PROBE 显示 ttfb 22-30s 健康, 偶发 89s(接近 UPSTREAM_TIMEOUT=90s). 是上游慢节点单点, 非旋钮能治.
- 与 R2161 fallback=0 对比: 单点回升, 但 < 5 阈值, 是 cc4101 兜底机制按设计正常工作.

### nv_gw tier 错误 30min (nv_tier_attempts)
- pexec_success 46 / **pexec_429 8** / NVCFPexecRemoteDisconnected 3 / pexec_SSLEOFError 2
- 全 NVCF 上游连接类(kimi tier), 非旋钮能治

### nv_gw BREAKER-FAIL 30min (R1719 设计)
- nv_gw 日志 grep BREAKER/ANTH-BREAKER = **0 条** (比 R2161 的 1 还干净, 远未 OPEN)

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **29 / 6h** (vs R2161=28, 基本持平, R2289 副作用受益持续)
- timeout = 164/6h (cc4101 自身非本域) / server_5xx = 6 / stream_total_deadline = 1
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 属 CLAUDE.md BUG-A 待查项

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], **default=glm5_2_nv**)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2161 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2161 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2161 逐项一致, **无参数漂移**
- docker ps 全栈 Up

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮 30min kimi 2 zombie 属过渡期单点波动, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 kimi zombie=2, 素材不充分(需连续多轮 ≥5 窗口), 未实施. 是下一推进点.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值**全不满足**:
1. SR 89.2% > 85% ✅ (glm5_2_nv 100%, kimi 42.9% 被本域拉起, 总体稳; kimi 低 SR 是 R2286 过渡期已知特征)
2. cc4101 fallback 请求数 1 < 5 ✅ (单点大请求 ttfb 超时被 ms_gw 救回, 0 真中断, 非系统性)
3. 无新增错误类型 ✅ (glm5_2_nv nv_requests 侧 0 错; kimi 6 ATE + 2 zombie 是过渡期已知非旋钮可治上游类)

四重佐证 nv_gw 稳:
1. 8 错全 kimi 上游无害类 (6 ATE + 2 zombie, 全 NVCF 上游连接类; glm5_2_nv nv_requests 侧零错)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (30min 0 条, 比 R2161 更干净)
4. 参数无漂移 (容器未重建, env 与 R2161 逐项一致)

改了反而破坏稳定带. 本轮 1 次 fallback 是 cc4101 兜底机制按设计工作(NVCF 慢节点单点 ttfb 超时), 救回 0 真中断, 不构成改动依据. kimi_nv 过渡期阵痛是 NVCF 上游问题, 改 nv_gw 旋钮治不了反而可能误伤 glm5_2_nv 主链路.

## 验证
0 改动 0 restart 无需验证改动.
- curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移
- 容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z

## 本轮摘要
R2162 hm2_cc2 NOP 巡检轮 95, 连续第 95 NOP, 0 改动 0 restart. 30min 74req/89.2% SR (glm5_2_nv 60/60=100% nv_requests侧零错极稳; kimi_nv 6/14=42.9% R2286过渡期阵痛延续 8错=6ATE+2zombie NVCF上游连接类). ⚠cc4101 fallback=1(打破连续多轮=0): 1条~150K大请求glm5_2_nv撞NVCF慢节点ttfb超160s墙→ms_gw救回0真中断(单点非系统性,cc4101兜底按设计工作). NV-ANTH-BREAKER-FAIL 30min 0条比R2161更干净. 参数误杀全0. 499=29/6h同基线R2289副作用受益持续. 容器无漂移(nv_gw StartedAt=07-22T15:10:34Z RC=0连续多轮)+env无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie=2素材不足未实施. 三阈值全不满足→冻结. HM2 only.
