# R2177 hm2_cc2 NOP 巡检轮 100 (连续第 100 NOP)

> 全新 session 接棒. STATE.md 头部严重滞后 (停 R2160 patrol 93), git pull 后 hm2_cc2 线实际
> 最新 = R2176 (commit 3146348, 连续第 99 NOP, 已 commit). 本轮 hm2_cc2 续 R2177 (patrol 100).
>
> ⚠ 本轮核心信号: **容器漂移出现 + NV-MS-FB-BREAKER-OPEN 风暴持续 + cc4101 fallback 回升到 2**.
> 但根因非旋钮能治 (NVCF 上游 SSLEOFError/429/504), 0 真中断 (ms_gw 热备全兜成功),
> 三阈值未触发 → 仍冻结 NOP. env 参数逐项比对无漂移 (容器是 up -d recreate 非改 env).

## 数据 (HM2, 30min window)

**nv_requests 30min (by model+status)**:
- glm5_2_nv: 65×200 + 5×502 = 70 req, SR = **92.9%** (本域主链路稳, 与 R2176 93.0% 持平)
- kimi_nv: **0 req** (30min 窗口恰好未覆盖 kimi 流量; 6h 看 kimi 仍有 120/140 流量但过渡期阵痛收尾中)
- dsv4p_nv: 0

**error_type 30min (nv_requests)**:
- stream_absolute_cap: 4 (mid-stream 背景波, glm5_2_nv, 历史已知类)
- zombie_empty_completion: 1 (glm5_2_nv, 单点)
- 无 content_filter / timeout / conn / 429

## cc4101 30min fallback (负向核心指标)

- **fallback = 2** ✅ (回升, 打破连续多轮=0, 但 < 5 阈值; 2 次均 FALLBACK-OK 救回 0 真中断)
  - req=ebb18c0c: primary timeout 60076ms (cc4101 pre-empted nv_gw retry, SKIP-CIRCUIT 不计 circuit) → ms_gw 救回 2.5s
  - req=d692f59d: primary timeout 180059ms (cc4101 PRIMARY header/ttfb 180s 墙, NVCF TTFB 超 180s) → ms_gw 救回 7.8s
  - 2 次均单点救回, 非系统性双失败. 比 R2176 fallback=0 多 2, 但远未到 >5 且新错误类型触发阈值

## nv_gw 内部 NV-MS-FB-BREAKER-OPEN (R1719/R2192 设计)

- 30min grep `BREAKER|ANTH-BREAKER` = **75 条** (主体是 NV-MS-FB-BREAKER-OPEN for glm5_2_nv)
- detail: `breaker OPEN for glm5_2_nv (req=xxx), skipping nv chain, serving ms_gw directly (state=('OPEN', 5, N))`
- 6h 精确 `NV-MS-FB-BREAKER-OPEN` = 21 条 (docker logs 滚动截断, 非完整 6h; 30min 风暴密集段真实)
- 根因: glm5_2_nv 5 keys NVCF 上游 SSLEOFError/429/504 压力 (nv_tier_attempts 30min: pexec_429=8, pexec_504=7, SSLEOF=1, conn=1, success=24)
- **注意区分**: NV-MS-FB-BREAKER-OPEN (nv_gw 内部, 把请求直甩 ms_gw) ≠ cc4101 fallback (cc4101 层切 ms_gw). 前者是 nv_gw 自身兜底, 后者是负向核心指标(本轮=2).
- breaker 设计即"宁可走 ms 也不死循环", OPEN 后 ms_gw 热备全兜成功 → 0 真中断. 目标是让 breaker 几乎不 OPEN, 但根因 NVCF 上游非旋钮能治, 不靠调高阈值"假装不 OPEN".

## 参数误杀类 (全 0) ✅
75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **42 / 6h** (与 R2176 记 29 同量级, R2289 副作用受益持续; 根因 cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项)
- stream_total_deadline = 2 / 6h
- 空白 error_type 行 = 769 (正常成功请求无 error_type, 非异常)

## 容器漂移信号 (本轮新发现, docker inspect 实测)

- **nv_gw StartedAt = 2026-07-23T18:05:17Z** (R2175 之前连续多轮 STATE 记 07-22T15:10:34Z; 本轮实测变了) ← **漂移出现**
- nv_gw RestartCount = 0 (非 restart, 是 `docker compose up -d` recreate, 不累计 RestartCount)
- 推测触发者: peer 改 compose env 触发 up -d 重建 (HM1 peer 轮 R2303/R2305/R2306 改了 TIER_COOLDOWN_S 等, 但铁律只改 HM1, HM2 nv_gw 不应被改; 可能是 compose 文件共享导致 up -d 时 HM2 nv_gw 也 recreate)
- **env 参数逐项比对 STATE 快照无漂移** ✅ (UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 / TIER_COOLDOWN_S=180 / MIN_OUTBOUND=10 / KEY_COOLDOWN=60 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_TIER_BUDGET_DSV4P_NV=180 / NVU_BIG_INPUT_FAIL_N=1 / KEY_AUTHFAIL_COOLDOWN_S=60 / NV_INTEGRATE_KEY_COOLDOWN_S=90 全一致)
- 结论: 容器 recreate 但 env 未变, 跑的是同参数同字节码, 不影响行为. 漂移是 up -d 副作用非改码. 下轮继续盯 StartedAt 是否再变 + env 是否漂移.

## 6h 背景窗口 (nv_requests)
- glm5_2_nv: 725×200 + 76×502 = 90.5% (主域, 6h 持平稳态)
- kimi_nv: 120×200 + 20×502 = 85.7% (R2286/R2292 过渡期阵痛收尾中)
- dsv4p_nv: 3×502 (非本域, NVCF 74f02205 恶化延续)
- zombie 6h: glm5_2_nv=17, kimi_nv=11 (共 28, 分散; 30min 仅 1, 素材不足)

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮 30min zombie=1 未触发新增 dump (符合单点波动)
- 任务3 (路径B zombie 内部重试): ⏳ 部分. 双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 `~/cc_ps/cc2_repair_self/specs/`. 本轮 30min zombie=1, 6h=28 但分散(30min 素材不足, 需连续多轮 ≥5/30min 才值得推进). 是下一推进点.

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
- SR 92.9% > 85% ✅
- cc4101 fallback 请求数 2 < 5 ✅ (2 次单点救回 0 真中断, 非系统性双失败)
- 无新增错误类型 ✅ (stream_absolute_cap 历史已知 mid-stream 背景波; zombie 历史已知; NV-MS-FB-BREAKER-OPEN 风暴是 R2175 起已知振荡根因 NVCF 上游)

四重佐证 nv_gw 稳:
1. 5 错全上游无害类 (glm5_2_nv 4 cap mid-stream 背景波 + 1 zombie 单点; NV-MS-FB breaker OPEN 是兜底非真失败)
2. 无参数误杀 (全 0)
3. breaker OPEN 后 ms_gw 热备全兜 0 ��中断 (设计即"走 ms 不死循环")
4. env 参数无漂移 (容器 recreate 但 env 逐项一致, 跑同字节码)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok (passthrough, nv_num_keys=5, 3 models, default=glm5_2_nv) + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=2026-07-23T18:05:17Z (本轮新漂移, RC=0 up -d recreate) / cc4101=2026-07-23T07:38:11Z (RC=0) / ms_gw=2026-07-21T12:50:09Z (RC=0).

## 备注 (HM2 only, 铁律: 只改 HM2 不改 HM1, 不碰 proxy/ms-gw/)
本轮 0 改动 0 restart, 连续第 100 NOP. 主仓 R23XX (HM1 peer / opclaw / openclaw2) 线不参与, 保持 HM2 nv_gw 稳态.
