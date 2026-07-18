# R1855 (HM2 cc2): 巡检轮 — bug8 降级兜底 in-vivo 后第13轮持续 0 触发, 链路稳 SR 94.6%

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底已落地 in-vivo 生效. 连续巡检确认链路稳.
本轮 NOP (0 改动 / 0 restart). STATE.md 入口落后于仓库 (写 R1850, 仓库已 R1854),
经 git pull 校准本轮从 R1855 起 防 peer 撞号.

## 改前数据 (30min 窗, 本 session 拉取)
- SR 106/112 = **94.6%** (200:106 / 502:6). 抖动区间下沿, 非 system 退化:
  近 4 轮 R1852 96.1% / R1853 94.8% / R1854 94.7% / 本轮 94.6%,
  全在 94-98% 抖动区间, **未连 >=3 轮破 93%**.
- 6 条 502:
  - zombie_empty_completion x3
  - stream_first_byte_timeout x2
  - stream_absolute_cap x1
  全 NVCF 侧偶发降级路径外分支, **config 不可修** (与 R1851-R1854 同构).
- tier pexec (30min):
  - pexec_success x82
  - pexec_429 x10
  - pexec_SSLEOFError x2
  - pexec_empty_200 x1
  - pexec_timeout x1
  - 无 zombie, 无 ATE (all_tiers_exhausted).
  - pexec elapsed: max 60.4s / avg 12.7s / >=60s 1 条 / >=200s 0 条 (与 R1854 60.4s 持平, 持续自愈).
- fallback (cc4101 30min):
  - 4 条 fallback 计数, 其中 07:25 PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt
    nv_gw retry, 非 nv_gw 失败 NOT counted) → 随后 FALLBACK-OK ms 成功 (递进合法, 0 中断).
  - **0 中断**. 非跳过类真请求失败仅 1 条 (走 ms 兜住), 远 < 4 阈值.

## bug8 关键检查 (R1839 in-vivo 兜底)
- 实战降级触发 **0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空).
- 兜底在位但 args 全合法不需触发 = 符合 R1839 "兜底保险就该几乎不触发" 原话.
- oai_to_anth.py md5 = **4983bcec1d1203a1f3f8acf371786c6c** (550 行) 宿主/容器一致
  (host: /opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py
   container: /app/gateway/format/oai_to_anth.py),
  R1839 改后字节码 (format/ 子目录 _detect_bad_tool_args / _downgrade_to_end_turn /
  两处 final_stop 强制 end_turn 四要素) 在位.

## breaker
- 30min 窗:
  - NV-ANTH-ABS-CAP x1 (cap_elapsed=159s 超 150s, 一条 stream_absolute_cap).
  - NV-ANTH-BREAKER-FAIL x4 全 state=('CLOSED', *) (1,0)/(1,0)/(2,0)/(1,0),
    zombie_empty_completion 软挂 + 1 stream_absolute_cap, **未 OPEN**, 设计内.
- 无 OPEN, 未触发介入条件.

## 环境
- env 无漂移 (全与 R1850-R1854 一致):
  - UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25
  - NVU_BIG_INPUT_FAIL_N=1 / MIN_OUTBOUND_INTERVAL_S=0
  - TIER_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60
  - NV_INTEGRATE_KEY_COOLDOWN_S=90 / NVU_BIG_INPUT_COOLDOWN_S=180
- /health ok (passthrough, 5 keys, 3 nvcf pexec models 含 glm5_2_nv).
- nv_gw StartedAt = **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1855 未再 restart)
  → 跑 R1839 改后字节码.

## 决策
介入触发四条全不满足:
1. SR 未连 >=3 轮破 93% (近 4 轮 94.6-96.1, 抖动非退化).
2. fallback 非跳过类真请求失败 < 4 阈值 (本轮仅 1 条, 走 ms 兜住 0 中断).
3. NV-ANTH-BREAKER-FAIL 未 OPEN (4 条全 CLOSED).
4. 无新可配置错误分类 (6 条 502 = zombie/first_byte/abs_cap, 与 R1851-R1854 同构).
→ NOP 硬改违反铁律 (改前必有数据 + 无据不改).

## 验证结果
- 0 restart / 0 中断 / StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码.
- /health ok, docker ps 同历轮.
- 链路稳 (SR 94.6% 抖动区间下沿非退化) + bug8 0 触发 + breaker 全 CLOSED + env 无漂移.

## 下一轮
继续常规巡检. 介入触发条件 (任一满足才动手, 否则 NOP):
1. SR 连续 >=3 轮跌破 93% (系统退化信号).
2. fallback 非跳过类真请求失败 (FALLBACK-OK 由 nv_gw 真失败引出) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 第一字段变 OPEN).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap).
至 R1855 已连续 13 轮 NOP (R1842-R1855), 链路稳态. 无数据支持主动改, 维持巡检.
