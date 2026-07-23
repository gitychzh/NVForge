# R2178 hm2_cc2 NOP 巡检轮 101 (连续第 101 NOP)

> 全新 session 接棒. STATE.md 头部仍严重滞后 (停 R2160 patrol 93), git pull 后 hm2_cc2 线实际
> 最新 = R2177 (commit fbaa351, 连续第 100 NOP, 已 commit). 本轮 hm2_cc2 续 R2178 (patrol 101).
>
> ⚠ 本轮核心信号: **NV-MS-FB-BREAKER-OPEN 风暴显著缓解 (R2177 75→本轮 2/30min)**,
> **容器漂移止住 (nv_gw StartedAt 自 R2177 起稳定在 07-23T18:05 未再变)**,
> **env 参数逐项比对无漂移**, cc4101 fallback=2 持平 R2177 (<5 阈值, 2 次单点救回 0 真中断).
> NVCF 仍有 pexec_504=24/30min 上游压力, tier retry 跨 5 key 吸收, 最终 SR 93.1%.
> 三阈值未触发 → 仍冻结 NOP. HM2 only.

## 数据 (HM2, 30min window, ~02:47-03:17 CST)

**nv_requests 30min (by model+status)**:
- glm5_2_nv: 94×200 + 7×502 = 101 req, SR = **93.1%** (本域主链路稳, 与 R2177 92.9% 基本持平)
- kimi_nv: **0 req** (R2286/R2292 过渡期阵痛收尾中, 当前流量全汇 glm5_2_nv 稳定路径)
- dsv4p_nv: 0

**error_type 30min (nv_requests)**:
- stream_absolute_cap: 5 (mid-stream 背景波, glm5_2_nv, 历史已知类)
- zombie_empty_completion: 2 (glm5_2_nv, 单点, 比 R2177=1 多 1, 非趋势)
- 无 content_filter / timeout / conn / 429 / all_tiers_exhausted

## cc4101 30min fallback (负向核心指标)

- **fallback = 2** ✅ (持平 R2177, < 5 阈值; 2 次均 FALLBACK-OK 救回 0 真中断)
  - req=d692f59d: primary timeout 180059ms (cc4101 PRIMARY header/ttfb 180s 墙, NVCF TTFB 超 180s) → ms_gw 救回 7.8s
  - req=cab9c8bd: primary timeout 60069ms (cc4101 pre-empted nv_gw retry, SKIP-CIRCUIT 不计 circuit) → ms_gw 救回 3.9s
  - 2 次均单点救回, 非系统性双失败. 远未到 >5 且新错误类型触发阈值.

## nv_gw 内部 breaker (R1719/R2192 设计)

- 30min all `BREAKER|ANTH-BREAKER` = **3 条** (R2177 风暴 75 → 本轮 3, **大幅缓解**)
  - NV-MS-FB-BREAKER-OPEN ×2 (for glm5_2_nv, state=('OPEN', 5, 7)): 02:48 breaker OPEN 把请求直甩 ms_gw (设计即"宁可走 ms 不死循环")
  - NV-ANTH-BREAKER-FAIL ×1 (03:12, glm5_2_nv, stream_absolute_cap mid-stream 软挂, state=('CLOSED', 4, 0) **未真 OPEN**)
- **注意区分**: NV-MS-FB-BREAKER-OPEN (nv_gw 内部兜底, 把请求直甩 ms_gw) ≠ cc4101 fallback (cc4101 层). 本轮前者 2, 后者 2.
- 根因 NVCF 上游 (pexec_504=24/30min) 非旋钮能治, breaker 兜底后 ms_gw 全兜成功 0 真中断. 目标让 breaker 几乎不 OPEN, 但不靠调高阈值"假装不 OPEN".

## nv_tier_attempts 30min (上游 NVCF 压力明细)
- pexec_success: 90
- pexec_504: **24** (NVCF 504 上游压力仍存, 比 R2177 的 pexec_429=8/pexec_504=7 转为 504 为主, 性质同属上游连接类)
- pexec_conn_RemoteDisconnected: 3
- pexec_SSLEOFError: 2
- pexec_empty_200: 1
- tier retry 跨 5 key 吸收, 最终 SR 93.1%. 全 NVCF 上游连接/超时类, 非旋钮能治.

## 参数误杀类 (全 0) ✅
75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **43 / 6h** (R2177=42, 同量级, R2289 副作用受益持续; 根因 cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项)
- stream_total_deadline = 2 / 6h
- 空白 error_type 行 = 765 (正常成功请求无 error_type, 非异常)

## 容器漂移信号 (docker inspect 实测, 本轮确认**漂移止住**)
- **nv_gw StartedAt = 2026-07-23T18:05:17Z** RC=0 (与 R2177 实测一致, 未再漂移; R2177 首次发现从 07-22T15:10→07-23T18:05, 本轮止住)
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (与多轮一致 无漂移)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- **env 参数逐项比对 STATE 快照无漂移** ✅ (MIN_OUTBOUND=10 / KEY_COOLDOWN=60 / UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 / TIER_COOLDOWN_S=180 / NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 / NVU_FORCE_STREAM_UPGRADE=0 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_THRESHOLD=250000 / NVU_BIG_INPUT_COOLDOWN_S=180 / NVU_BIG_INPUT_MODELS=glm5_2_nv / KEY_AUTHFAIL_COOLDOWN_S=60 / NV_INTEGRATE_KEY_COOLDOWN_S=90 全一致)
- 结论: 容器自 R2177 起稳定未再 recreate, env 无漂移. 上轮漂移是 up -d 副作用非改码, 本轮止住.

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮 30min zombie=2 未触发新增 dump 评估 (符合单点波动)
- 任务3 (路径B zombie 内部重试): ⏳ 部分. 双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 `~/cc_ps/cc2_repair_self/specs/`. 本轮 30min zombie=2 素材不足 (需连续多轮 ≥5 才值得推进). 是下一推进点.

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
- SR 93.1% > 85% ✅
- cc4101 fallback 请求数 2 < 5 ✅ (2 次单点救回 0 真中断, 非系统性双失败)
- 无新增错误类型 ✅ (stream_absolute_cap 历史已知 mid-stream 背景波; zombie 历史已知; NV-MS-FB-BREAKER-OPEN 风暴本轮从 75 缓解到 2)

四重佐证 nv_gw 稳:
1. 7 错全上游无害类 (glm5_2_nv 5 cap mid-stream 背景波 + 2 zombie 单点; NV-MS-FB breaker OPEN 兜底非真失败)
2. 无参数误杀 (全 0)
3. breaker OPEN 后 ms_gw 热备全兜 0 真中断 (设计即"走 ms 不死循环"), 风暴本轮缓解到 2
4. env 参数无漂移 (容器自 R2177 起稳定, env 逐项一致, 跑同字节码)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv) + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=2026-07-23T18:05:17Z (RC=0, 自 R2177 起稳定) / cc4101=2026-07-23T07:38:11Z (RC=0) / ms_gw=2026-07-21T12:50:09Z (RC=0).

## 备注 (HM2 only, 铁律: 只改 HM2 不改 HM1, 不碰 proxy/ms-gw/)
本轮 0 改动 0 restart, 连续第 101 NOP. 主仓 R23XX (HM1 peer / opclaw / openclaw2) 线不参与, 保持 HM2 nv_gw 稳态. 本轮未 Read 任何 /tmp 文件 (避免重蹈上轮 tool-use 死循环中断).
