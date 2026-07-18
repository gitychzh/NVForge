# R1854 (HM2 cc2): 巡检轮 — bug8 降级兜底 in-vivo 后第12轮持续 0 触发, 链路稳 SR 94.7%

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底已落地 in-vivo 生效. 连续巡检确认链路稳.
本轮 NOP (0 改动 / 0 restart). STATE.md 入口落后于仓库 (写 R1850, 仓库已 R1853),
经 git pull 校准本轮从 R1854 起.

## 改前数据 (30min 窗, 本 session 拉取)
- SR 107/113 = **94.7%** (200:107 / 502:6). 抖动区间下沿, 非 system 退化:
  近 4 轮 R1851 95.6% / R1852 96.1% / R1853 94.8% / 本轮 94.7%,
  全在 94-98% 抖动区间, **未连 >=3 轮破 93%**.
- 6 条 502:
  - zombie_empty_completion x3
  - stream_first_byte_timeout x2
  - stream_absolute_cap x1
  全 NVCF 侧偶发降级路径外分支, **config 不可修** (与 R1851/R1852/R1853 同构).
- tier pexec (30min):
  - pexec_success x81
  - pexec_429 x9
  - pexec_SSLEOFError x1
  - pexec_empty_200 x1
  - pexec_timeout x1
  - 无 zombie, 无 ATE (all_tiers_exhausted).
  - pexec elapsed: max 60.4s / avg 13.6s / >=60s 1 条 / >=200s 0 条 (与 R1853 43.8s 相当, 持续自愈).
- fallback (cc4101 30min):
  - 1 条 07:25 PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt nv_gw retry,
    非 nv_gw 失败 NOT counted) → 1 条 FALLBACK-OK (递进合法).
  - **0 中断**. 非跳过类真请求失败远 < 4 阈值.

## bug8 关键检查 (R1839 in-vivo 兜底)
- 实战降级触发 **0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空).
- 兜底在位但 args 全合法不需触发 = 符合 R1839 "兜底保险就该几乎不触发" 原话.
- oai_to_anth.py md5 = **4983bcec1d1203a1f3f8acf371786c6c** (550 行) 宿主/容器一致,
  R1839 改后字节码 (format/ 子目录 _detect_bad_tool_args / _downgrade_to_end_turn /
  两处 final_stop 强制 end_turn 四要素) 在位.

## breaker
- 30min 窗:
  - NV-ANTH-ABS-CAP x1 (cap_elapsed=159s 超 150s, 一条 stream_absolute_cap).
  - NV-ANTH-BREAKER-FAIL x4 全 state=('CLOSED', *) (1,0)/(1,0)/(2,0)/(1,0),
    zombie_empty_completion 软挂 + 1 stream_absolute_cap, **未 OPEN**, 设计内.
- 无 OPEN, 未触发介入条件.

## 环境
- env 无漂移 (全与 R1850-R1853 一致):
  - UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25
  - NVU_BIG_INPUT_FAIL_N=1 / MIN_OUTBOUND_INTERVAL_S=0
  - TIER_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60
  - NV_INTEGRATE_KEY_COOLDOWN_S=90 / NVU_BIG_INPUT_COOLDOWN_S=180
- /health ok (passthrough, 5 keys, 3 nvcf pexec models 含 glm5_2_nv).
- nv_gw StartedAt = **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1854 未再 restart)
  → 跑 R1839 改后字节码.

## 决策
介入触发四条全不满足:
1. SR 未连 >=3 轮破 93% (近 4 轮 94.7-96.1, 抖动非退化).
2. fallback 非跳过类真请求失败 < 4 阈值 (本轮仅 1 条 SKIP-CIRCUIT not counted).
3. NV-ANTH-BREAKER-FAIL 未 OPEN (4 条全 CLOSED).
4. 无新可配置错误分类 (6 条 502 = zombie/first_byte/abs_cap, 与 R1851-R1853 同构).
→ NOP 硬改违反铁律 (改前必有数据 + 无据不改).

## 验证
0 改动 → 0 restart → 0 验证缺口. 链路稳 (SR 94.7% 抖动区间, bug8 0 触发, breaker CLOSED,
fallback not counted, 0 中断). -18T21:26:29Z 确认跑 R1839 改后字节码.

## 结论
连续 12 轮巡检 (R1842-R1854, 期间 bug8 兜底 R1839 落地) 链路稳态. 维持 NOP 巡检节奏,
待介入触发条件满足再动手.
