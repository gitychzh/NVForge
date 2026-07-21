# R2185 — hm2_cc2 NOP 巡检轮

> 0 改动 0 restart. 三阈值全不满足→冻结. R2182 的 "PRIMARY+FALLBACK 双 timeout 没救回" 恶化趋势本轮止住(全救回).

## 基线
- 上一轮 hm2_cc2: R2182 (commit 9c94f1a, 0改动, 但出现 cc4101 PRIMARY+FALLBACK 双 timeout 没救回恶化趋势)
- 主仓最新: 5c8d429 R2184 (HM2->HM1 peer 轮, TIER_COOLDOWN_S 12->10, only HM1, 非本域)
- 本轮: R2185 hm2_cc2 NOP 巡检

## 数据 (HM2, 30min window, ~19:48 时点)

### nv_requests 30min
- 107 请求 / 102 OK(200) / 5 错(502) → **SR = 95.3%** (较 R2182 93.8% 回升, 较 R2179 94.8% 微升, 稳态带)
- by mapped_model:
  - **glm5_2_nv 64/67 = 95.5% SR** (3错: 较 R2182 95.8% 基本持平, 稳态带)
  - dsv4p_nv 38/40 = 95% (2错全 all_tiers_exhausted, NVCF function 上游瞬态, 非本域已知良性)
- 5 错 error_type: 2 all_tiers_exhausted + 2 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 NVStream_IncompleteRead
  (IncompleteRead 是本轮新增瞬态类, R2179/R2182 未见, 同族 NVCF 上游 SSE 软失败, nv_gw 内部重试/NV-MS-FB 已吸收)
- 无 content_filter / timeout / conn / 429 (nv_gw 入口侧非上游软失败类)

### cc4101 30min fallback 事件 (负向核心指标)
- **req=b7c07489** [19:22:58] PRIMARY-FAIL (glm5_2_nv header/ttfb timeout 120s) → [19:23:03] **FALLBACK-OK** (ms_gw 5295ms 救回 200)
- **req=e276c910** [19:25:32] PRIMARY-FAIL (glm5_2_nv header/ttfb timeout 120s) → [19:25:35] **FALLBACK-OK** (ms_gw 3510ms 救回 200)
- **实际 cc4101 fallback 请求数 = 2, 全 FALLBACK-OK 救回** (6 行日志 = 4 行 PRIMARY-FAIL 判定 + 2 行 FALLBACK-OK, 每 req 2 行)
- **R2182 的 "PRIMARY+FALLBACK 双 timeout 没救回" 本轮止住**: 本轮 0 条 FALLBACK-FAIL, 2 个 fallback 全救回
- cc4101 fallback 请求数 2 < 5 阈值 ✅ 未触发 (R2182 也是 2, 但 R2182 有 1 个没救回)

### fallback_occurred / actually_attempted (DB)
- fallback_actually_attempted=true 12 条 (status=200, 全 nv_gw 入口记 cc4101 甩 ms 成功)
- fallback_occurred=true 10 条 (status=200, nv_gw 内部 NV-MS-FB tier 兜底 glm5_2_nv→glm5_2_ms)
- 两类全 status=200, 即 nv_gw 内部 NV-MS-FB + cc4101 层 fallback 全救回, 0 真中断

### nv_gw breaker 30m
- **NV-ANTH-BREAKER-FAIL 3 条, 全 state=CLOSED** (计数 2/3/4, 未达 OPEN 阈值)
  - 19:27:07 err=zombie_empty_completion state=(CLOSED,4,0)
  - 19:41:42 err=NVAnth_IncompleteRead state=(CLOSED,2,0)
  - 19:44:50 err=zombie_empty_completion state=(CLOSED,3,0)
  - breaker 正常 record 软失败, 未真 OPEN (R1719 设计), 非恶化信号
- 无 STREAM-STALL-FAIL / 75s_timeout / BIG-INPUT / UPSTREAM-ERROR-SEEN 事件 → **非参数误杀**
- NV-MS-FB 内部兜底 27 次 (glm5_2_nv→glm5_2_ms 正常吸收)

### 容器状态
- **nv_gw RestartCount=0 StartedAt=2026-07-21T10:52:21Z** (R2179/R2182 是 01:44:55Z → 容器在 R2182 后被整体重建, RC 归零)
  - 但 env 关键参数与 R2179 快照逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/ FORCE_STREAM_UPGRADE_TIMEOUT=150/BIG_INPUT 阈值同), **无参数漂移** → 非 env 改动触发, 可能宿主/docker 层重建, nv_gw 逻辑不变
- cc4101 Up 6h, logs_db Up 4d (RC=0 无漂移, 同 R2182)

## 决策: NOP 冻结, 不改代码

STATE 三触发改动阈值全不满足:
1. 30min SR = 95.3% > 85% ✅ 仍远在阈值之上
2. cc4101 fallback 请求数 = 2 < 5 ✅ 在阈值之下 (6 行日志含 4 行 PRIMARY-FAIL 判定行, 实际 2 个请求全救回)
3. 错误类型: 出现 NVAnth_IncompleteRead + NVStream_IncompleteRead 新瞬态类, 但同属 NVCF 上游 SSE 软失败族 (zombie 同族), 非参数误杀类 (无 75s_timeout/STALL/big_input)

根因分析 (为何不该动 nv_gw 参数):
- cc4101 PRIMARY-FAIL 根因 = **NVCF 上游 glm5_2_nv header/ttfb 120s 超时** (cc4101 自己的 120s 判定, 比 nv_gw TIER_TIMEOUT_BUDGET_S=180s 短, cc4101 先判 nv timeout → 甩 ms) — cc4101 不是 cc2 管 (只改 HM2 nv_gw)
- IncompleteRead/zombie 全 NVCF 上游 SSE 软失败, nv_gw 内部重试 + NV-MS-FB tier 兜底已吸收 (27 次 NV-MS-FB + 10 fallback_occurred 全 200)
- breaker 全 CLOSED 未 OPEN, 参数无漂移 → 非参数误杀
- 调 nv_gw 任何参数都不会让 NVCF 上游变快/不软失败, 也不会改 cc4101 的 120s 判定
- 改了反而破坏 R2154 稳定带, 且治不了根因 (NVCF 上游瞬态)

## ⚠ 趋势警告 (写进 STATE 给下个 session)
- R2177-R2179 cc4101 fallback=0 (3轮) → R2180 1条救回 → R2182 1双失败没救回(恶化) → **R2185 2条全救回(止住)**.
  虽本轮止住, 但 cc4101 fallback 连续 3 轮非 0 (R2180/R2182/R2185), glm5_2_nv 上游 header/ttfb 120s 超时仍间歇出现.
  若下一轮再出现 PRIMARY+FALLBACK 双失败没救回, 或 fallback 请求数升到 ≥5, 需评估 (但动也治不了 NVCF 上游慢/软失败, 顶多让 nv_gw 更快放弃 glm5_2_nv 甩 ms — NV-MS-FB 已在跑).
- nv_gw 容器在 R2182 后被重建 (StartedAt 01:44:55 → 10:52:21), 但 RC=0 + 参数无漂移, 非 cc2 改动所致 (可能 HM1 peer 轮或宿主维护), 逻辑不变, 保持 NOP 基线.
- NV-ANTH-BREAKER-FAIL 本轮 3 条 (R2179=0), 全 CLOSED 未 OPEN. 若单轮 +5 或逼近 OPEN 阈值再评估.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok (nv_num_keys=5, passthrough, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]) + docker ps 全栈 Up (nv_gw Up 57min / cc4101 Up 6h / logs_db Up 4d) + 容器 RC=0 (nv_gw StartedAt=2026-07-21T10:52:21Z, cc4101 SA 同 R2182) + env 关键参数与 R2179 快照逐项一致 (无漂移).

## commit
R2185 hm2_cc2 NOP 巡检: 0 改动 0 restart. 30min 107req/95.3% SR. glm5_2_nv 95.5%(3错,2ATE+1zombie+2IncompleteRead新瞬态类). cc4101 fallback=2请求全FALLBACK-OK救回(R2182没救回恶化趋势本轮止住, 0双失败). NV-MS-FB内部兜底27次+10fallback_occurred全200救回0真中断. NV-ANTH-BREAKER-FAIL 3条全CLOSED未OPEN. 无75s_timeout/STALL/big_input非参数误杀. nv_gw容器被重建(StartedAt 01:44→10:52)但RC=0+env参数无漂移非cc2改动逻辑不变. STATE三阈值全不满足→冻结. 根因NVCF上游glm5_2_nv header/ttfb 120s超时非nv_gw参数能治.
