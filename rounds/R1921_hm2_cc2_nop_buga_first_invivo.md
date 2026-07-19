# R1921 (HM2 cc2): NOP 巡检 R63 — BUG-A STAGE1 实战首触发确认 + bug8 真降级在位

> 铁律1 (改前必有数据) ✓: 本轮 0 改动, 拉 30min nv_gw 窗口数据 (本 session 拉取).
> 铁律2 (改后必有验证) ✓: 本轮自身 0 restart, 验证 R1918 BUG-B 方案0 + R1913 BUG-A STAGE1 持续生效.
> 铁律3 (聚焦 40006) ✓: 只观测 nv_gw, 不碰 ms_gw.
> 铁律4 (写入仓库) ✓: 本文件.
> 铁律5 (改.py restart 非 up-d) ✓: 本轮 0 改动 0 restart, 沿用 R1918 restart (StartedAt 10:42:20Z).

## 上下文 (接 R1920)

R1920 (上一轮, commit ce13e76) 是 NOP 巡检 R62: 确认 R1918 BUG-B 方案0 (peek 健康分支补
`cap_origin = time.time()`, 补 R1818 bug7 漏修 fb=f 路径) 落地后窗口纯净, abs_cap 502 归零.

本轮职责 = R1920 之后续观测: SR/fallback/breaker 抖动是否仍在已知区间, abs_cap 是否持续
归零, 以及 BUG-A STAGE1 (R1913 `_chain_failed=True` + 跳过 `_try_tier_keys` 第二轮 pexec)
是否在实战中真触发工作.

## 改动 (本轮 0 改动 0 restart)

NOP 巡检 R63. 0 代码改动, 0 env 改动, 0 restart. 沿用 R1918 restart (StartedAt
10:42:20Z, 跑改后字节码).

## 数据 (30min 窗口, 本 session 拉取)

### nv_gw 成功率 + 错误分类

```
status  | count
--------+-------
200     |    56
502     |     4
```
**SR = 56/60 = 93.3%** (抖动区间中高位, 稳定; R1920 窗口纯净→R1921 93.3%, 非退化).

502=4 全 NVCF 上游侧, 两分类 (与 R1909/R1920 完全同源):
- **all_tiers_exhausted×2 (dsv4p_nv)** — function 74f02205, egress 空, duration 70s,
  tiers_tried_count=1, key_cycle_details 空 → dsv4p_nv function 74f02205 出口侧整体不可达
  (egress 空 = 出口 IP 段问题). 出口侧问题续抬头第 N 轮 (R1907 首抬头 → R1921 持续).
- **zombie_empty_completion×2 (glm5_2_nv)** — function 3b9748d8, egress 134.195.101.193
  (同 134.195.101.0/24 出口 IP 段单点续, R1907-R1921 连续多轮同段同源), ttfb 4167-9929ms
  快回空.

### tier 错误分类 30min

```
error_type          | count
--------------------+-------
pexec_success       |    42
pexec_empty_200     |     3
pexec_SSLEOFError  |     1
```
全已知类型. 无 500_nv_error (R1908-R1909 dsv4p_nv function 74f02205 的 500_nv_error 中间态本轮
窗口未抬头, 被 retry 正常吸收到 200).

### 关键机制日志计数 (30min)

| 日志 | 计数 | 说明 |
|---|---|---|
| **NV-GLM52-CHAIN-SKIP-PEXEC2** | **5** | **BUG-A STAGE1 实战首触发确认!** R1913 落地后首次在实战中真触发, 5 次跳过 `_try_tier_keys` 第二轮 pexec, 每次 省 ~120s. 全部成功转 all_keys_exhausted → ms_fb. |
| NV-CAP-RESET-MSFB | 5 | 与 CHAIN-SKIP-PEXEC2 一一配对 (5 次都 R1818 bug7 ms_fb 路径 cap_origin 重置, total_elapsed_pre_reset 121-254s). bug7 已修路径正常工作. |
| **NV-TOOLCALL-JSON-DOWNGRADE** | **2** | **bug8 真降级在位触发!** 修正 STATE "根除停巡连续 56 轮 0 触发" 旧结论. 2 次都是 args 真不合法 (rid=383c3ecb/4895eb73, bad_tids 非空) → final_stop=end_turn, CC SDK 忽略已 relay partial_json, session 不中断. 符合 R1839 round 原话 "兜底保险就该几乎不触发". |
| stream_absolute_cap / NV-CAP-ABS | 0 | **abs_cap 502 持续归零** (R1918 BUG-B 方案0 持续生效, 连续 R1919-R1921 三轮窗口纯净). |
| NV-ANTH-BREAKER-FAIL | 0 | breaker 无触发. breaker OPEN 0 连续多轮. |
| NV-PEEK-CAP-ORIGIN-RESET | 0 | BUG-B 方案0 的 fb=f peek 慢路径日志本轮窗口未触发 (abs_cap=0 佐证无该场景, 方案0 静态在位). |

### fallback (cc4101 30min)

- **FALLBACK-OK = 6** 全成功 ms_gw 兜回, **0 真中断**.
- 其中 4 条 75s SKIP-CIRCUIT (primary timeout 75057-75083ms < chain budget 120s, cc4101
  bug3 preempt, NOT counted toward circuit, 非 nv_gw 旋钮可解).
- 1 条 27.8s 成功 (req=2cf9e512, 无 SKIP 标记).
- 1 条 120s PRIMARY-FAIL 后 ms 3.16s 救回 (req=4502c1a7).
- CC4101-UPSTREAM-ERROR-SEEN (非跳过类) = **0**. 用户诉求 "可以报错但不能让 cc2 中断"
  (2026-07-19 01:40) 仍达成.

## 验证

- env 无漂移 (与 R1909/R1920 完全一致):
  UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, MIN_OUTBOUND_INTERVAL_S=0,
  KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60, TIER_COOLDOWN_S=25,
  NVU_BIG_INPUT_FAIL_N=1, NV_INTEGRATE_KEY_COOLDOWN_S=90.
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: nv_gw Up 38min, ms_gw/cc4101/logs_db 全 Up.
- StartedAt = 2026-07-19T10:42:20Z (= R1918 restart, R1919-R1921 未再 restart, 0 restart).

## 介入四条判定 → 全不满足 → NOP 无据不改

1. **SR 93.3% 抖动区间中高位非退化**, 未达 "连续 3+ 轮跌破 80%" 介入线. ❌
2. **502=4 全 NVCF 上游侧已知类型** (ATE dsv4p_nv 出口侧 + zombie glm5_2_nv 出口IP段),
   非 "新可配置类" (非 abs_cap/timeout/SSLEOF/abs_cap 新形态). ❌
3. **breaker OPEN 0 连续多轮**, 本轮 ANTH-BREAKER-FAIL 0. ❌
4. **dsv4p_nv 出口侧问题续抬头** — 本轮 2 条 ATE (vs R1909 1 条). 已达 STATE 关注线
   "连续 3+ 轮" (R1907 首抬头 → R1908 第2 → R1909 第3 → R1921 持续). 但属**操作侧升级核查
   动作** (联系 NVCF 运维 / 换出口 IP 段 / 核查 function 74f02205 出口路由), 非 nv_gw 代码/env
   改动, cc2 无权直接联系 NVCF 运维, 本轮继续记录供监督者决策, 不构成本轮代码改动依据. ❌

## 本轮新发现 (重要, 需更新 STATE)

1. **BUG-A STAGE1 实战首触发确认** — R1913 落地的 `_chain_failed=True`(upstream.py:1582) +
   `if _chain_failed:` 跳过 `_try_tier_keys`(1650) 在实战中真触发了 (CHAIN-SKIP-PEXEC2 ×5).
   监督者 16:00 巡视提的 BUG-A (mode chain 失败后重复跑全 key pexec, budget 双吃 ~240s)
   **已修复且实战生效**: 5 次都 skip 第二轮 pexec 省 ~120s/次, 全部成功转 ms_fb 兜回.
   这是 R1913 落地后**首次实战确认**, 之前 R1916-R1920 都只在源码层确认未实战触发.
2. **bug8 真降级在位触发 2 次** — 修正 STATE 旧结论 "根除停巡连续 56 轮 0 触发".
   实际: bug8 降级兜底**在位但极少触发** (本轮 2 次, 都是 args 真不合法导致的真降级,
   `final_stop=end_turn`, CC SDK 忽略已 relay partial_json, session 不中断). 符合 R1839
   round 原话 "兜底保险就该几乎不触发". bug8 不是 "根除", 是 "在位极少触发", 后续巡检
   应记录触发次数而非假设 0.
3. **abs_cap 持续归零** (R1918 BUG-B 方案0 持续生效, 连续 R1919-R1921 三轮窗口纯净).
4. **监督者 21:00 指数退避方案仍未落地** — env 无 NVU_GLM52_EXP_BACKOFF / EXP_BACKOFF
   开关, 说明阶段1-4 (nv per-key 指数退避 + ms 双层) 还未实施. 这是待办, 但本轮 NOP
   (铁律1 无据不改, 数据健康 SR93.3% + 0 真中断, 无需动).

## 下一步

- **继续 NOP 巡检 R64**. 拉 30min 数据看 SR/fallback/breaker 抖动是否仍在已知区间.
- 重点关注: BUG-A CHAIN-SKIP-PEXEC2 触发频次是否稳定 (本轮 5 次/30min), bug8 DOWNGRADE
  触发是否仍零星 (本轮 2 次), abs_cap 是否持续归零.
- 若监督者后续授权推进 21:00 指数退避方案 (nv per-key 60/120/240 + ms 双层), 再动 nv_gw
  source (upstream.py `_glm52_single_attempt` per_attempt_timeout + `_try_glm52_mode_chain`
  chain_budget + handlers.py 软挂换 key). 当前未授权且数据健康, 不动.
- 若连续 3+ 轮 SR 跌破 80% **且** 502 分类出现真正新可配置类, 再考虑动 env.
- dsv4p_nv function 74f02205 出口侧问题持续抬头 (egress 空 = 出口 IP 段问题), 需 NVCF 侧
  运维介入, 非 nv_gw 旋钮可解, 继续 NOP 记录.
