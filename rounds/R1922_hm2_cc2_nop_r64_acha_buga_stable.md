# R1922 (HM2 cc2): NOP 巡检 R64 — BUG-A STAGE1 持续触发 + BUG-B 方案0 abs_cap 连续 4 轮归零

> 铁律1 (改前必有数据) ✓: 本轮 0 改动, 拉 30min nv_gw 窗口数据 (本 session 11:37Z 拉取).
> 铁律2 (改后必有验证) ✓: 本轮自身 0 restart, 验证 R1918 BUG-B 方案0 + R1913 BUG-A STAGE1 持续生效.
> 铁律3 (聚焦 40006) ✓: 只观测 nv_gw, 不碰 ms_gw.
> 铁律4 (写入仓库) ✓: 本文件.
> 铁律5 (改.py restart 非 up-d) ✓: 本轮 0 改动 0 restart, 沿用 R1918 restart (StartedAt 10:42:20Z).

## 上下文 (接 R1921)

R1921 (上一轮, commit f336aa2) 是 NOP 巡检 R63: BUG-A STAGE1 实战首触发确认
(NV-GLM52-CHAIN-SKIP-PEXEC2 ×5/30min, R1913 落地的 `_chain_failed=True` +
`if _chain_failed:` 跳过 `_try_tier_keys` 第二轮 pexec 实战真触发) + bug8 真降级在位
触发 2 次 (修正 STATE 旧结论 "根除停巡连续 56 轮 0 触发") + abs_cap 502 归零.

本轮职责 = R1921 之后续观测: BUG-A CHAIN-SKIP-PEXEC2 触发频次是否稳定 (R1921 5 次→本轮),
bug8 DOWNGRADE 是否仍零星, abs_cap 是否持续归零 (连续第 4 轮 R1919-R1922).

## 改动 (本轮 0 改动 0 restart)

NOP 巡检 R64. 0 代码改动, 0 env 改动, 0 restart. 沿用 R1918 restart (StartedAt
10:42:20Z, 跑改后字节码).

## 数据 (30min 窗口, 本 session 11:37Z 拉取)

### nv_gw 成功率 + 错误分类

```
status  | count
--------+-------
200     |    38
502     |     4
```
**SR = 38/42 = 90.5%** (抖动区间常态, 稳定; R1921 93.3%→R1922 90.5%, 非退化, 仍在 80-100 区间内).

502=4 全 NVCF 上游侧, 三分类 (与 R1909/R1921 同源):
- **all_tiers_exhausted×1 (dsv4p_nv)** — `f2257de7` function 74f02205-c7b, egress 空,
  duration 70016ms, tiers_tried_count=1, key_cycle_details 空 → dsv4p_nv function 74f02205
  出口侧整体不可达 (egress 空 = 出口 IP 段问题). 出口侧问题续抬头 (R1907 首抬头 → R1922 持续).
- **zombie_empty_completion×2 (glm5_2_nv)** — `57065bdf` egress 134.195.101.180 function
  3b9748d8-1d8 ttfb 4760ms 快回空; `957a7780` egress 134.195.101.193 function 3b9748d8-1d8
  ttfb 2320ms 快回空 (同 134.195.101.0/24 出口 IP 段单点续, R1907-R1922 连续多轮同段同源).
- **zombie_empty_completion×1 (dsv4p_nv, 新形态)** — `76d0024a` function 74f02205-c7b,
  egress **134.195.101.195** (非空, 与 R1909 dsv4p_nv 新形态 egress 218.93.250.242 同类
  "dsv4p_nv 出口 IP 段漂移" 形态), ttfb 17872ms 快回空. dsv4p_nv 出口侧问题形态:
  ATE(egress 空=出口 IP 段不可达) + zombie(egress 非空新段, 首字节慢/空) 同 function 74f02205.

### tier 错误分类 30min

```
error_type          | count
--------------------+-------
pexec_success       |    31
pexec_empty_200     |     3
```
全已知类型. pexec_empty_200 3 (zombie 同源, 被 retry 重吸收到 200). 无 500_nv_error /
SSLEOFError / timeout / IntegrateTimeout.

### 关键机制日志计数 (30min)

| 日志 | 计数 | 说明 |
|---|---|---|
| **NV-GLM52-CHAIN-SKIP-PEXEC2** | **6** | BUG-A STAGE1 持续实战触发 (R1921 首触发 5 次→R1922 6 次, 稳定非偶发). 6 次跳过 `_try_tier_keys` 第二轮 pexec, 每次 省 ~120s, 全部成功转 all_keys_exhausted → ms_fb 兜回. |
| **NV-TOOLCALL-JSON-DOWNGRADE** | **3** | bug8 真降级在位零星触发 (R1921 2 次→R1922 3 次, args 真不合法导致真降级, `final_stop=end_turn`, CC SDK 忽略已 relay partial_json, session 不中断). 符合 R1839 round 原话 "兜底保险就该几乎不触发". |
| stream_absolute_cap / NV-CAP-ABS | **0** | **abs_cap 502 持续归零 (连续第 4 轮 R1919-R1922 窗口纯净)**. R1918 BUG-B 方案0 (peek 健康分支补 cap_origin 重置, 补 R1818 bug7 漏修 fb=f 路径) 持续生效. |
| NV-ANTH-BREAKER-FAIL | 7 | breaker 触发 (glm5_2_nv zombie 同源触发为主), state CLOSED 吸收未 OPEN. |
| breaker OPEN | **0** | breaker OPEN 0 连续多轮 (本轮 BREAKER-FAIL 7 全被 CLOSED 吸收). |
| NV-PEEK-CAP-RESET / NV-CAP-RESET-MSFB | 7 | bug7 ms_fb 路径 cap_origin 重置 7 次 (与 CHAIN-SKIP-PEXEC2 6 + 1 其它配对, total_elapsed_pre_reset 120s 量级). bug7 已修路径正常工作. |

### fallback (cc4101 30min)

- **FALLBACK-OK = 8** 全成功 ms_gw 兜回, **0 真中断**.
- 全部 8 条 75s SKIP-CIRCUIT (primary timeout 75018-75082ms < chain budget 120s, cc4101
  bug3 preempt, NOT counted toward circuit, 非 nv_gw 旋钮可解). 示例:
  - `65d901b0` primary timeout 75080ms → ms 2372ms 救回.
  - `51966ea7` primary timeout 75062ms → ms 2718ms 救回.
  - `49b6e9be` primary timeout 75082ms → ms 4782ms 救回.
  - `39e81c1b` primary timeout 75018ms → ms 5846ms 救回.
- CC4101-UPSTREAM-ERROR-SEEN (非跳过类真中断) = **0**. 用户诉求 "可以报错但不能让 cc2 中断"
  (2026-07-19 01:40) 仍达成.

## 验证

- env 无漂移 (与 R1909/R1920/R1921 完全一致):
  UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, MIN_OUTBOUND_INTERVAL_S=0,
  KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60, TIER_COOLDOWN_S=25,
  NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_STREAM_ABSOLUTE_CAP_S=150.
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: nv_gw Up 54min, ms_gw/cc4101/logs_db 全 Up.
- StartedAt = 2026-07-19T10:42:20Z (= R1918 restart, R1919-R1922 未再 restart, 0 restart).
- **无 NVU_GLM52_EXP_BACKOFF env**: 监督者 21:00 指数退避方案仍未落地 (与 R1921 一致).

## 介入四条判定 → 全不满足 → NOP 无据不改

1. **SR 90.5% 抖动区间常态非退化**, 未达 "连续 3+ 轮跌破 80%" 介入线. ❌
2. **502=4 全 NVCF 上游侧已知类型** (ATE dsv4p_nv 出口侧不可达 + zombie glm5_2_nv 出口IP段
   单点续 + zombie dsv4p_nv 出口IP段漂移新形态), 非 "新可配置类" (非 abs_cap/timeout/
   SSLEOFError/abs_cap 新形态). ❌
3. **breaker OPEN 0 连续多轮**, 本轮 ANTH-BREAKER-FAIL 7 全被 CLOSED 吸收未 OPEN. ❌
4. **abs_cap 502 持续归零连续 4 轮** (R1919-R1922), 方案0 in-vivo 根除 fb=f 秒触发路径,
   方案1 (abs_cap 后重放 ms) 失去数据支撑, 不需要动. ❌

## 本轮结论

1. **BUG-A STAGE1 持续实战生效** — R1921 首触发 5 次→R1922 6 次, 稳定非偶发. 每次 skip
   第二轮 pexec 省 ~120s, 全转 ms_fb 兜回 200. 监督者 16:00 巡视提的 BUG-A (mode chain
   失败后重复跑全 key pexec, budget 双吃 ~240s) **实战持续修复中**.
2. **BUG-B 方案0 持续生效** — abs_cap 502 连续 4 轮归零 (R1919-R1922). fb=f 秒触发路径根除.
   方案1 (abs_cap 后重放 ms, 中风险) 失去数据支撑 (无 abs_cap 量产), 不动. 方案2 (peek 判定
   收紧) 也无据动 (无 tool_calls 时序新数据).
3. **bug8 真降级在位零星触发** (R1921 2 次→R1922 3 次), 都是 args 真不合法导致的真降级,
   `final_stop=end_turn`, session 不中断. 符合 "兜底保险就该几乎不触发".
4. **dsv4p_nv function 74f02205 出口侧问题续抬头** — 本轮 ATE 1 + zombie 新形态 1 (egress
   134.195.101.195 非空, 与 R1909 218.93.250.242 同类 "出口 IP 段漂移"). 已超 STATE 关注线
   "连续 3+ 轮" (R1907 首抬头 → R1922 持续). 但属**操作侧升级核查动作** (联系 NVCF 运维 /
   换出口 IP 段 / 核查 function 74f02205 出口路由), 非 nv_gw 代码/env 改动, cc2 无权直接
   联系 NVCF 运维, 本轮继续记录供监督者决策, 不构成本轮代码改动依据.
5. **fallback 全 SKIP-CIRCUIT 8 条 0 真中断** — 全 75s preempt (cc4101 bug3 层, 非 nv_gw
   旋钮可解), 全被 ms_gw 兜回.

## 下一步

- **继续 NOP 巡检 R65**. 拉 30min 数据看 SR/fallback/breaker/abs_cap 抖动是否仍在已知区间.
- **重点续攒**: BUG-A CHAIN-SKIP-PEXEC2 触发频次是否稳定 (R1921 5→R1922 6), bug8 DOWNGRADE
  触发是否仍零星, abs_cap 是否持续归零 (连续 4 轮已可初步判定方案0 根除, 续攒到连续 6+ 轮可
  正式从关注项移除).
- **若监督者后续授权推进 21:00 指数退避方案** (nv per-key 60/120/240 + ms 双层), 再动 nv_gw
  source (upstream.py `_glm52_single_attempt` per_attempt_timeout + `_try_glm52_mode_chain`
  chain_budget + handlers.py 软挂换 key + cc4101 PRIMARY_HEADER_TIMEOUT/STREAM_TOTAL_DEADLINE
  对齐 420s). 当前未授权且数据健康 (SR 90.5% + 0 真中断), 不动. **注意**: 该方案是大改 (nv_gw
  + cc4101 双层 source), 与本轮 NOP 巡检的"小步快走"原则不符, 需监督者明确授权 + 逐项核对清单
  (见 STATE.md 21:15 段) 后才动, 否则违反铁律1 (无据不改 / 大改无充分数据支撑).
- 若连续 3+ 轮 SR 跌破 80% **且** 502 分类出现真正新可配置类, 再考虑动 env.
- dsv4p_nv function 74f02205 出口侧问题持续抬头 (egress 空 + 新形态 egress 非空漂移), 需 NVCF
  侧运维介入, 非 nv_gw 旋钮可解, 继续 NOP 记录.
- peer HM1 agent 持续在 HM1 侧收紧 (R1920 NVU_TIER_BUDGET_GLM5_2_NV 50→48, R1919 55→50),
  写轮前必 git pull 看最新号 +1 防 peer 抢号.
