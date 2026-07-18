# R1852 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第 10 轮持续 0 触发, 链路稳 SR 96.1%

## 改前数据 (30min 窗, 拉 R1851 ff0f955 之后)
- **SR 124/129 = 96.1%** (200:124 / 502:5). 比 R1851 的 95.6% 微涨, 连续 9 轮 R1842-R1851 全在
  94-98% 抖动区间, **非系统退化** (未连 ≥3 轮破 93%, 近 3 轮 94.8/95.6/96.1 持续微回弹上扬).
- 5 条 502 = 2 zombie_empty_completion + 1 all_tiers_exhausted + 1 stream_absolute_cap
  + 1 stream_first_byte_timeout, **全 NVCF 侧偶发降级路径外分支 config 不可修** (与 R1851 同构).
- tier pexec: success 92 / 429 4 / SSLEOF 2 / empty_200 2 / timeout 1, 无 zombie 无 ATE.
  pexec_success 92 与 R1851 的 97 同密度持平偏强.
- **fallback 2** 全 bug3 75s 抢断 SKIP-CIRCUIT (07:14/07:25, cc4101 preempt nv_gw retry,
  非 nv_gw 可控, NOT counted, 未达 ≥4 阈值非恶化). **0 中断**.
- **bug8 关键**: 实战降级触发 **0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空). 兜底保险在位
  但 args 全合法不需触发, **符合 R1839 round 文件原话"兜底保险就该几乎不触发"**.
- breaker: 1 NV-ANTH-BREAKER-FAIL (stream_absolute_cap, state=('CLOSED',1,0) 未 OPEN 设计内)
  + 对应 1 NV-ANTH-ABS-CAP (cap_elapsed=159s 超过 150s wall-clock).
- env 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1
  全与 R1850/R1851 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致,
  R1839 改后字节码四要素全在 (_detect_bad_tool_args()@319 + _downgrade_to_end_turn
  flag@97/375/381 + 两处 final_stop 强制 end_turn@399-400/442-443).

## 改了什么
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 决策理由
介入触发四条全不满足 → NOP, 硬改违反铁律:
1. SR 96.1% 未跌破 93%, 非系统退化 (近 3 轮微回弹上扬).
2. fallback 非跳过类 0 (2 次全 bug3 抢断 SKIP-CIRCUIT NOT counted), 未达 ≥4.
3. breaker state=('CLOSED',1,0) 未 OPEN.
4. 无新可配置错误分类 (5 条 502 全 NVCF 侧 zombie/exhausted/abs_cap/first_byte).

## 验证结果
- /health ok (nv_num_keys=5, glm5_2_nv 在位, proxy_role=passthrough).
- StartedAt 仍 **2026-07-18T21:26:29Z** (= R1836 restart, R1839 至 R1852 未再 restart)
  → 确认跑 R1839 改后字节码.
- env 无漂移, oai_to_anth md5=4983bcec 宿主/容器一致.
- 链路稳 (SR 96.1% 在抖动区间上沿微涨) + bug8 0 触发 + breaker CLOSED + 0 中断 + 0 restart.
- 用户诉求 "可以报错但不能让 cc2 中断" 达成 (本轮 0 中断, fallback 全 SKIP-CIRCUIT 兜住).

## 下一轮
继续常规巡检. 介入触发条件不变 (见 STATE.md). 连续 10 轮 NOP (R1842-R1852) 链路稳态,
当前无数据支持主动改, 维持 bug8 兜底在位观测节奏.
