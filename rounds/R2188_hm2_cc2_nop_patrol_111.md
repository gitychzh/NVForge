# R2188 (hm2_cc2): NOP 巡检轮 111 — 连续第 111 NOP, 三阈值冻结

> 全新 session 接棒. STATE.md 停 R2184, git pull 后 HEAD=6c0ca6e 但 hm2_cc2 线最新=R2187
> (commit d9c9418, 连续第 110 NOP). STATE.md 滞后修正: 接棒停 R2184 实际 git 到 R2187,
> 以 git log + DB 重建. 本轮 hm2_cc2 续 R2188. 未 Read 任何 /tmp 文件.

## 数据 (HM2, 30min window)

### nv_requests SR + 错误
- 95 req / 92 OK(200) / 3 错 → **SR = 95.8%**
- by model: **glm5_2_nv 79/82 = 96.3%** (主力, 3 错全 stream_absolute_cap mid-stream 背景波)
  ; claude-opus-4-8 13/13 = 100% (cc4101 passthrough 非 NV 路径, 不计入败笔)
- error_type (nv_requests 层): stream_absolute_cap × 3
- 无 content_filter / timeout / conn / 429 / all_tiers_exhausted (nv_requests 层)
- host_machine 全 HM2 本域

### nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)
- pexec_success 40 / pexec_429 10 / pexec_empty_200 3 / pexec_SSLEOFError 2 / pexec_conn_RemoteDisconnected 1
- pexec_429=10 (R2187=7 略升仍 6-10 区间, NVCF 账户级配额非旋钮能治 KEY_COOLDOWN=60/MIN_OUTBOUND=10 已保守, 改大反触发更多 primary timeout 恶化)

### cc4101 30min fallback (负向核心指标)
- **真 fallback = 0** (grep "FALLBACK|FALLBACK-OK|切到 ms_gw|PRIMARY-FAIL|SKIP-CIRCUIT|circuit|BREAKER" 全 0)
- **0 真中断** (比 R2187=3 更干净, 全部 nv_gw 内部 ms_fb 兜底, 0 冒 cc4101 层)

### nv_gw 内部 NV-MS-FB-BREAKER (R1719 设计)
- NV-MS-FB-BREAKER-OPEN **28 事件** (11:55 集中, state ('OPEN',5,10/27/24/16/6) 衰减)
- 全自愈: 11:58 后 NV-MS-FB-ATTEMPT breaker=CLOSED, internal ms_fb 兜底全 OK
  (NV-MS-FB-OK after 2610ms~41869ms, NV-MS-FB-SERVED state=CLOSED)
- 0 冒 cc 层 (cc4101 fallback=0 证实, nv_requests 95.8% SR 不受直接影响)
- **NV-ANTH-BREAKER-FAIL 30min = 0 条** (健康)
- R2179-R2187 同模式设计行为 (NVCF 上游 pexec_429/empty_200/SSL 级联 → breaker OPEN → internal ms_fb 兜底 → 自愈 CLOSED)

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **52 / 6h** (R2187=46 略升, R2289 副作用 SDK 131s 客户端首字节墙结构性基线区间波动 42-52)
- stream_total_deadline = 2/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2179-R2187 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- docker ps: nv_gw Up 10h / cc4101 Up 20h / ms_gw Up 2d / logs_db Up 7d

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
1. SR 95.8% > 85% ✅
2. cc4101 fallback 请求数 0 < 5 ✅ 且全救回 (0 真中断, 比 R2187=3 更干净)
3. 无新增错误类型 ✅ (NV-MS-FB-BREAKER OPEN 28 是 R2179-R2187 连续多轮已知设计行为, internal ms_fb 兜底 0 冒 cc 层)

四重佐证 nv_gw 稳:
1. nv_requests 95.8% SR (3 错全 stream_absolute_cap mid-stream 背景波, tier 错误全 NVCF 上游连接类无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (28 OPEN 事件 11:55 集中后 11:58 全自愈回 CLOSED, NV-ANTH-BREAKER-FAIL=0)
4. 参数无漂移 (容器未重建 env 与 R2187 逐项一致, nv_gw StartedAt 连续多轮稳定 07-23T18:05)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.

## R2192 三任务进度
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮窗口 0 zombie, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 0 zombie 素材严重不足窗口 (需 ≥5 才值得推进), 未实施. 是下一推进点.

## HM2 only
铁律: 只改 HM2 nv_gw, 不改 HM1 (R22xx 是 HM1 peer 轮 only HM1).
