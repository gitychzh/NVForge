# R2187 — hm2_cc2 NOP 巡检轮 (连续第 110 NOP)

## 号基线
- 主仓 HEAD (pull 后): `0bd3b91 R2186`
- hm2_cc2 线: R2186 → **本轮 R2187**
- 轮文件: `rounds/R2187_hm2_cc2_nop_patrol_110.md`

## 改前数据 (HM2, 30min window, 08:36-09:06 CST 区间)

**nv_requests 30min**:
- 97 req / 93 OK(200) / 4 错(502) → **SR = 95.9%**
- by model: **glm5_2_nv 93/97 = 95.9%** (全本域流量, kimi_nv 0req 过渡期收尾流量全汇 glm 连续多轮)
- error_type: stream_absolute_cap 4 (R2180-R2186 同模式 mid-stream 背景波, 非新模式)

**nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)**:
- pexec_success 25 / pexec_429 7
- pexec_429=7 (R2186=6, 略升但仍 6-8 区间, NVCF 账户级配额非旋钮治, KEY_COOLDOWN=60/MIN_OUTBOUND=10 已保守)

**cc4101 30min fallback (负向核心指标)**:
- **真 fallback = 3** (req 2b2540ba 08:32 PRIMARY-FAIL 60068ms SKIP-CIRCUIT 救回 2876ms;
  req 6795c4d9 08:44 PRIMARY-FAIL 60071ms SKIP-CIRCUIT 救回 2715ms;
  req 13c5d71a 08:59 PRIMARY-FAIL 180109ms **full budget timeout** 救回 5394ms)
- 3 次全救回 (FALLBACK-OK), **0 真中断** (<5 阈值, 全救回)
- ⚠ 13c5d71a 180s full budget timeout 比 60s SKIP-CIRCUIT 慢 (与 R2186 req f66fa3e4 同单例模式, 窗口边缘级未破阈值 watch)

**nv_gw 内部 NV-MS-FB-BREAKER (R1719 设计)**:
- 08:53-09:02 **NV-MS-FB-BREAKER-OPEN 风暴 37 条** (state ('OPEN',5,N) 衰减 N=26→13, HALF_OPEN 震荡)
  + all_keys_exhausted 触发 NV-MS-FB-ATTEMPT (breaker=HALF_OPEN/OPEN) → NV-MS-FB-SERVED ms_gw 兜底
- **09:02 后自愈回 CLOSED** (NV-MS-FB-SERVED state=CLOSED 09:00:20 + 09:02:06, 末态 CLOSED)
- ⚠ 本轮 OPEN 风暴比 R2184/R2185/R2186 更活跃 (R2186=0 OPEN 风暴, R2185=22req OPEN, 本轮 37 OPEN 事件),
  但仍 R2179-R2186 同模式设计行为 (NVCF 上游 pexec_429/empty_200 级联 → breaker OPEN → internal ms_fb
  兜底 → 自愈 CLOSED), **0 冒 cc 层** (nv_requests 95.9% SR 不受影响)

**NV-ANTH-BREAKER-FAIL 30min = 2 条** (R2186=0, 略升但未停 OPEN):
- 08:43:20 (glm5_2_nv) stream_absolute_cap → nv_breaker recorded state=('CLOSED',1,0) req=934d5b80
- 09:00:31 (glm5_2_nv) stream_absolute_cap → nv_breaker recorded state=('CLOSED',3,0) req=83b1a69a
- **两条 nv_breaker 全程 CLOSED** (count 1→3 远低阈值, 未真 OPEN, 对应 4 个 stream_absolute_cap 错误的 2 条
  被记录为 mid-stream soft-fail, 设计行为, 健康无恶化)

**参数误杀类 (全 0)** ✅:
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0

**BUG-A 499 盲点 (cc_requests 6h)**:
- client_gone_mid_stream = **46 / 6h** (R2186=44, 略升仍基线 42-46 区间, R2289 副作用 SDK 131s 客户端墙结构性)
- stream_total_deadline = 4 / 6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

**R2192 三任务进度 (巡检轮必报)**:
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪).
  本轮窗口 **0 zombie** (zombie_empty_completion 30min=0), 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证,
  spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 0 zombie 素材严重不足窗口
  (需 ≥5 才值得推进), 未实施. 是下一推进点.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
1. SR 95.9% > 85% ✅
2. cc4101 fallback 请求数 3 < 5 ✅ 且全救回 (0 真中断)
3. 无新增错误类型 ✅ (NV-MS-FB-BREAKER OPEN 37 事件 + NV-ANTH-BREAKER-FAIL 2 条均为 R2179-R2186
   连续多轮已知设计行为, internal ms_fb 兜底 0 冒 cc 层, 自愈回 CLOSED, nv_requests SR 不受影响)

四重佐证 nv_gw 稳:
1. 4 错全 stream_absolute_cap mid-stream 背景波 (tier 层 pexec_429 NVCF 上游配额无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (NV-MS-FB OPEN 风暴 37 后自愈回 CLOSED 09:02; NV-ANTH-BREAKER-FAIL 2 条全 CLOSED)
4. 参数无漂移 (容器未重建 env 与 R2184-R2186 逐项一致)

**watch 项 (非触发, 仅记录趋势)**:
- 本轮 NV-MS-FB-BREAKER OPEN 风暴 37 事件比 R2184-2186 更活跃 (R2186=0, R2185=22, 本轮 37).
  若下轮 OPEN 风暴频次/持续时间显著上升 (如单轮 ≥3 次风暴, 或 OPEN 不自愈停 OPEN 超过 5min),
  需评估.
- 本轮 NV-ANTH-BREAKER-FAIL 2 条 (R2186=0), 但全 CLOSED 未真 OPEN, watch.
- 本轮 fallback 3 含 1 个 180s full budget timeout (13c5d71a, 比 60s SKIP-CIRCUIT 慢, 与 R2186 f66fa3e4
  同单例窗口边缘模式), watch.

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动.
- `curl /health` ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- `docker ps` 全栈 Up (nv_gw Up 7h / cc4101 Up 17h / ms_gw Up 2d)
- 容器漂移信号止住: nv_gw StartedAt=**2026-07-23T18:05:17Z** RC=0 (连续多轮未重建, 与 R2184-R2186 逐项一致)
- env 关键参数无漂移 (MIN_OUTBOUND=10 / KEY_COOLDOWN=60 / UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET=180 /
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_BIG_INPUT_THRESHOLD=250000)

## 结论
连续第 110 NOP. nv_gw 极稳 (30min 97req/95.9% SR, 全 glm5_2_nv 本域流量, 4 错全 stream_absolute_cap 背景波).
cc4101 真 fallback=3 全救回 0 真中断. NV-MS-FB-BREAKER 本轮 OPEN 风暴更活跃 (37 事件, watch) 但自愈回 CLOSED
0 冒 cc 层. NV-ANTH-BREAKER-FAIL 2 条全 CLOSED 未真 OPEN. 499=46/6h 同基线. 容器无漂移 env 无漂移.
R2192 三任务: 任务1/2 已落地, 任务3 部分 (zombie=0 素材严重不足未实施). 三阈值全不满足→冻结.
0 改动 0 restart. HM2 only. 未 Read 任何 /tmp 文件 (避免 R2082 中断复发).
