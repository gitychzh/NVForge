# R1917 (HM2 cc2): NOP 巡检 R61 + BUG-B abs_cap 12h 全样本画像 + BUG-A STAGE1 in-vivo 首触发验证

> 铁律1 (改前必有数据) ✓; 铁律2 (改后必有验证) N/A 本轮 0 改动; 铁律3 聚焦 40006 ✓; 铁律4 写入仓库 ✓; 0 restart.

## 数据 (本 session 17:55Z 拉取 30min 窗口 + 12h abs_cap 全样本)

### 30min nv_gw 窗口 (17:25-17:55Z)
- **SR = 51/53 = 96.2%** (200:51 / 502:2). 抖动区间中上段常态, 优于 R1910 (90.2%) / R1909 (91.9%), 非退化.
- 502=2 两分类:
  - **stream_absolute_cap×1** — req=93e454cd 17:55:56, glm5_2_nv, cap_elapsed=192s,
    content_chars=0 reasoning_chars=0 peek_swapped=False. **正是 BUG-B 根因样本**
    (peek 把 tool_calls id 头块当健康放行, NVCF 后续真 content 不来, abs_cap 截断).
  - **all_tiers_exhausted×1** — dsv4p_nv 出口侧整体不可达 (NVCF 上游侧).
- tier 30min: pexec_success 40 / pexec_empty_200 5 (zombie 同源, 被 retry 重吸收到 200).
  **无 500_nv_error / SSLEOFError / timeout / abs_cap 中间态** — dsv4p_nv 74f02205 出口侧簇继续回落.
- fallback **4** FALLBACK-OK 全 75s SKIP-CIRCUIT (cc4101 bug3 preempt, NOT counted),
  **0 真中断** (ms_gw 全兜住). 微降 R1910=5→R1917=4.
- breaker: NV-ANTH-BREAKER-FAIL **1** (abs_cap 触发 req=93e454cd, state CLOSED (1,0) 吸收未 OPEN);
  breaker **OPEN 0** 持续.
- bug8 DOWNGRADE 0 触发 (连续 57+ 轮根除停巡).
- NV-CAP-RESET-MSFB 3 次 (bug7 已修路径).

### abs_cap 12h 全样本 (BUG-B 画像核心, restart 09:38Z 后 ~8h 纯净窗 + 含 restart 前残留)
- **20 条全 glm5_2_nv** (dsv4p_nv 无人触发 abs_cap), **全 peek_swapped=False** (走主循环 cap, 非 peek 早分支).
- **content_chars 分布:**
  - **17 条 content_chars=0 (85%)** ← BUG-B 真处理对象 (message_start 已发但零内容 → graceful end → CC 收空 message 卡死)
  - 1 条 content_chars=18 (13:40, total_elapsed=395s, restart 前 BUG-A 双吃预算残留)
  - 1 条 content_chars=113 (11:07, total_elapsed=414s, restart 前 BUG-A 双吃预算残留)
  - **0 条 content_chars>200** (没有"半截内容 abs_cap", 都是零内容或极少量)
- gap_limit: 19 条 120s, 1 条 160s.
- abs_cap 触发频率 20/12h ≈ **1.67/h** (修正: 本 session 17:55Z 实测 grep 全量 = 监督者 19:25 估计一致).
- peek-softfail 12h **0 条** → peek barrier **从不走 ms_fb 早分支**, 所有 abs_cap 走 1158 行主循环 cap.

## BUG-A STAGE1 in-vivo 首触发验证 (本轮重大发现)

R1913 落地 STAGE1 (upstream.py:1582 `_chain_failed=True` + 1650 `if _chain_failed:` 跳过 `_try_tier_keys` 第二轮),
StartedAt=2026-07-19T09:38:26Z restart 生效. **本轮首次观测到 in-vivo 实战触发**:

```
18:12:57.7 [NV-GLM52-CHAIN-FALLBACK] req=55c4da0e ... → STAGE1_CHAIN_FAIL skip pexec 2nd round, mark all_keys_exhausted
18:12:57.7 [NV-GLM52-CHAIN-SKIP-PEXEC2] req=55c4da0e ... skip _try_tier_keys 2nd round (saves ~120s), go all_keys_exhausted -> ms_fb
18:12:57.7 [NV-MS-FB-ATTEMPT] nv chain all_keys_exhausted for glm5_2_nv (req=55c4da0e), attempting ms_gw fallback
18:13:03.6 [NV-MS-FB-SERVED] ms_gw served glm5_2_nv fallback (req=55c4da0e)
```

CHAIN-FALLBACK → CHAIN-SKIP-PEXEC2 → MS-FB-ATTEMPT → MS-FB-SERVED 四连, **跳过 pexec 第二轮, 直接走 ms_fb, 省 ~120s/fallback 请求**. BUG-A 修复落地且实战生效. ✅

## 决策: NOP (0 改动 0 restart)

介入四条全不满足:
1. SR 96.2% 抖动区间中上段常态非退化, 未达"连续 3+ 轮跌破 80%"介入线.
2. 502=2 全 NVCF 上游侧已知类 (abs_cap=BUG-B / all_tiers_exhausted=dsv4p_nv 出口侧), 非新可配置类.
3. breaker OPEN 0 持续, 本轮 BREAKER-FAIL 1 被 CLOSED (1,0) 吸收未 OPEN.
4. dsv4p_nv 74f02205 出口侧问题本轮继续回落 (tier 30min 无 500_nv_error/SSLEOFError), 非"续抬头".

### 为何不直接动 BUG-B 阶段2 (方案1 peek 收紧 / 方案2 abs_cap 零内容发 event:error)

两方案都有真实副作用风险, 不到动手时机:

**方案1 (peek barrier 996 行收紧 tool_calls 要求 arguments 非空)**:
- 风险: NVCF 合法 tool_call 流式协议通常先发 `delta.tool_calls=[{index,id,function:{name,arguments:""}}]`
  再发 arguments 增量. peek 阶段只读到第一帧就要求 arguments 非空 → **会误杀所有正常 tool_call 流**
  (它们首帧 arguments 都是空). 正常 peek-ok 12h 1139 条, 其中多条 prebuffer 3400-3500b
  (含 tool_calls id 头块), 若改判定条件误杀面可能很大.
- 监督者 19:25 已标"风险: NVCF 合法先发 id 后发 arguments 的流可能被误杀 → 需先观测 NVCF tool_calls 流式时序".

**方案2 (finish() oai_to_anth.py:393 改, 零内容时发 event:error 而非 graceful end)**:
- 风险: R1820 注释 (388-392 行) 明确"CC SDK 把 event:error 当致命错中断整个 session" —
  这是上一轮监督者强制诉求"可以报错但不能让 cc2 中断"的反面. 方案2 直接改 393 行
  会让 content_chars=0 + message_start_sent=True 的请求触发 event:error → **CC 中断 session**,
  违反用户 01:40 核心诉求. 监督者 19:25 也标"中风险".

**正解**: 继续攒数据, 等监督者 19:25 建议的"NVCF tool_calls 流式时序"观测 (决定方案1 误杀率) +
abs_cap content_chars=0 占比 (本轮已圈定 85% = 17/20) 共同决定下一轮阶段2 选哪个方案.
本轮 abs_cap 全样本画像已把 content_chars=0 适用面精确到 85%, 但方案1 误杀率数据仍缺
(需抓正常 tool_call 流首帧 delta 结构), 暂不动.

## 验证
- env 无漂移 (与 R1916 一致): UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND_INTERVAL_S=0
  / KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 / NVU_BIG_INPUT_FAIL_N=1
  / NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / TIER_COOLDOWN_S=25.
- handlers.py md5=3e645e2c (宿主/容器一致, R1916 后未动).
- upstream.py md5=594617a6 (宿主/容器一致, R1913 STAGE1 落地版).
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps 全 Up. StartedAt=2026-07-19T09:38:26Z (R1913 restart, 本轮 0 restart).
- 0 改动 → 0 restart → 0 验证窗口需求.

## commit & push
本轮 commit + push origin/main (R1916..R1917 fast-forward).

## 单参数铁律
只改 HM2, 不碰 ms_gw, 不碰 HM1. 本轮 0 改动符合铁律.
