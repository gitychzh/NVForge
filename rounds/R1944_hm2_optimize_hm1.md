# R1944 (HM2→HM1): NOP — false trigger, 0 new data, 0 config-fixable

## 触发
HM1提交新commit到GitHub (fdba850: "这是我提交的, 不触发")。脚本判定HM2执行优化。

## 数据采集 (2026-07-19 23:50 UTC)

### nv_gw 日志 (最近100行)
- 模式: 9 zombie_empty_completion + 6 peer-fb 100% success
- 无新错误类型, 无429, 无SSLEOF, 无connect error
- 日志模式与R1943完全一致

### DB 6h 快照
```
 total | ok | fail | sr_pct
    35 | 26 |    9 |   74.3
```
- 9 failures: 全 zombie_empty_completion, glm5_2_nv, big_input (>130K chars)
- 0 real ATE (12 all_tiers_exhausted rows 全 status=200 phantom → peer-fb rescued)
- dsv4p_nv: 2/2 OK, avg 30487ms
- glm5_2_nv success: 24 OK, avg 10937ms, max 27809ms
- 6/6 peer-fb 100% success (HM2独立key pool rescue)
- key_cycle_429s: 23次 (glm5_2_nv, 1 cycle each — normal)

### 僵尸时间线 (~30min间隔, NVCF function-level)
```
15:03:20  zombie 16331ms  input=144775
14:03:54  zombie  2937ms  input=144688
13:03:20  zombie  5504ms  input=142479
12:33:20  zombie 10822ms  input=141704
12:03:28  zombie  6853ms  input=141578
11:33:20  zombie  6060ms  input=140288
11:03:32  zombie  4026ms  input=140201
10:33:24  zombie  9085ms  input=131323
10:04:06  zombie  2139ms  input=139513
```

### 参数状态
全部参数在 floor:
- FASTBREAK=1, EMPTY_200_FASTBREAK=1, KEY_COOLDOWN=60 (NVCF窗口)
- TIER_COOLDOWN=60, MIN_OUTBOUND=0, CONNECT_RESERVE=0
- SSLEOF=0.1, UPSTREAM=30, STREAM_FIRST_BYTE=15, STREAM_TOTAL=25
- PEXEC_TIMEOUT_FASTBREAK=1, INTEGRATE_TIMEOUT_FASTBREAK=1
- BIG_INPUT: FAIL_N=1, COOLDOWN=21600, THRESHOLD=115000
- PEER_FALLBACK_TIMEOUT=122 (= HM2_BUDGET=120+2, constraint floor)
- BUDGET=152 (= UPSTREAM 30 + PEER 122, boundary equality)
- PEER_FB_SKIP_MODELS=kimi_nv, ms_gw fallback=120s

## 介入四条判定

1. **新错误类型** ❌ — 无。9 zombie 全 glm5_2_nv NVCF function-level degradation, 与R1943/R1942/R1941相同。
2. **可配置修复的错误** ❌ — 无。僵尸=NVCF空200, 非配置可达。BREAKER已正确处理 (FAIL_N=1 open后 → peer-fb rescue)。
3. **参数未到 floor** ❌ — 全部已到 floor。FASTBREAK=1不可再降, KEY_COOLDOWN=60不可再降(NVCF窗口), UPSTREAM=30不可再降 (max OK=27.8s), STREAM_TOTAL=25不可再降 (maxOK=24.3s), PEER_FALLBACK=122不可再降 (HM2_BUDGET=120+2 constraint), BUDGET=152不可再降 (UPSTREAM 30+PEER 122=152 boundary)。
4. **BREAKER异常** ❌ — 无。BIG_INPUT正确触发 (FAIL_N=1, COOLDOWN=21600), peer-fb 100% rescue。

## 判决: NOP

四条全不满足，NOP 无据不改。9 zombie 是 NVCF glm5_2_nv function-level 空200 劣化，不是 HM1 配置可修复的。Breaker 正确将 big_input zombie 转为 peer-fb → HM2 rescue (100% success)。SR 74.3% 是 NVCF 后端约束，非配置可达。

## 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
